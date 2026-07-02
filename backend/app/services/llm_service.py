"""Provider-agnostic LLM service (Milestone 7).

All LLM traffic goes through `LLMService.complete(prompt, temperature)`.
Callers (roadmap generation now, gates later) never touch provider-specific
code. Provider order is fixed by the milestone instructions: Gemini primary,
OpenRouter fallback, deterministic stub when no live key is configured.
Anthropic is intentionally not supported.

Keys are server-only SecretStr config; they travel only in outbound request
headers and never appear in errors or responses. Provider failures surface as
LLMError — the caller maps that to a generic client message.

LIVE PROVIDERS UNVERIFIED: built in a session without GEMINI_API_KEY or
OPENROUTER_API_KEY. Both providers are unit-tested against mocked transports;
run one real generation once a key is available.
"""

import json
import re
from typing import Protocol, Sequence

import httpx

from app.core.config import Settings, get_settings

_TIMEOUT = 60.0  # roadmap generation is a long single completion
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """A provider call failed (network, rate limit, malformed response).
    Message is for logs/tests only — never sent to the client verbatim."""


class LLMProvider(Protocol):
    name: str

    async def complete(self, prompt: str, temperature: float) -> str: ...


async def _post_json(name: str, url: str, headers: dict, payload: dict,
                     transport: httpx.AsyncBaseTransport | None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, transport=transport) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        raise LLMError(f"{name} request failed") from e


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._url = f"{_GEMINI_BASE}/models/{model}:generateContent"
        self._headers = {"x-goog-api-key": api_key}
        self._transport = transport

    async def complete(self, prompt: str, temperature: float) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        data = await _post_json(self.name, self._url, self._headers, payload, self._transport)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("gemini returned an unexpected response shape") from e
        if not text:
            raise LLMError("gemini returned an empty completion")
        return text


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, api_key: str, model: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._transport = transport

    async def complete(self, prompt: str, temperature: float) -> str:
        payload = {
            "model": self._model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = await _post_json(self.name, _OPENROUTER_URL, self._headers, payload, self._transport)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("openrouter returned an unexpected response shape") from e
        if not text or not isinstance(text, str):
            raise LLMError("openrouter returned an empty completion")
        return text


class StubProvider:
    """Deterministic stand-in for tests and local no-key mode — never a silent
    fallback when a live provider is configured but failing.

    Simulates a well-behaved model for the JSON-personalization prompts: it
    extracts the first JSON object embedded in the prompt (the archetype
    template), substitutes every `[SINGLE_BRACKET]` personalization slot with
    fixed text, and adds the `timeline_estimate` field the roadmap prompt
    requires. Same prompt in, same string out, no network.
    """

    name = "stub"

    async def complete(self, prompt: str, temperature: float) -> str:
        start = prompt.find("{")
        if start == -1:
            raise LLMError("stub: prompt contains no JSON object to personalize")
        try:
            data, _ = json.JSONDecoder().raw_decode(prompt[start:])
        except json.JSONDecodeError as e:
            raise LLMError("stub: embedded JSON is malformed") from e
        filled = re.sub(r"\[[A-Z][A-Z_]*\]", "your project", json.dumps(data))
        result = json.loads(filled)
        result["timeline_estimate"] = (
            "Stub estimate: phases distributed evenly across your stated deadline."
        )
        return json.dumps(result)


class LLMService:
    """Tries providers in order; falls back on LLMError; fails if all fail."""

    def __init__(self, providers: Sequence[LLMProvider]) -> None:
        if not providers:
            raise ValueError("LLMService needs at least one provider")
        self._providers = list(providers)

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    async def complete(self, prompt: str, temperature: float) -> str:
        for provider in self._providers:
            try:
                return await provider.complete(prompt, temperature)
            except LLMError:
                continue  # next provider in the fixed order
        raise LLMError("all configured LLM providers failed")


def build_llm_service(settings: Settings) -> LLMService:
    """Provider order from config: LLM_PROVIDER names the primary; the other
    configured live provider is the fallback; the stub runs only when no live
    key exists (or LLM_PROVIDER=stub is explicit)."""
    if settings.llm_provider == "stub":
        return LLMService([StubProvider()])

    live: list[LLMProvider] = []
    if settings.gemini_api_key.get_secret_value():
        live.append(GeminiProvider(settings.gemini_api_key.get_secret_value(),
                                   settings.gemini_model))
    if settings.openrouter_api_key.get_secret_value():
        live.append(OpenRouterProvider(settings.openrouter_api_key.get_secret_value(),
                                       settings.openrouter_model))
    if settings.llm_provider == "openrouter":
        live.sort(key=lambda p: p.name != "openrouter")
    if not live:
        return LLMService([StubProvider()])  # local no-key mode
    return LLMService(live)


def get_llm_service() -> LLMService:
    """FastAPI dependency; tests override this or rely on no-key stub mode."""
    return build_llm_service(get_settings())
