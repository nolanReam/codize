"""LLM service tests — providers against mocked transports, no real API calls."""

import asyncio
import json

import httpx
import pytest

from app.core.config import Settings
from app.services.llm_service import (
    GeminiProvider,
    LLMError,
    LLMService,
    OpenRouterProvider,
    StubProvider,
    build_llm_service,
)

PROMPT = (
    "Personalize this template.\n\n"
    '{"archetype_id": 2, "phases": [{"phase": 1, "task": "Build [PROJECT_PURPOSE] now"}]}\n\n'
    "Answers: help my study group."
)


def run(coro):
    return asyncio.run(coro)


def gemini_transport(captured: dict, status=200, text="personalized output"):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]}
        )
    return httpx.MockTransport(handler)


def openrouter_transport(captured: dict, status=200, text="fallback output"):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": text}}]}
        )
    return httpx.MockTransport(handler)


# --- Gemini provider (unit, mocked transport) -----------------------------------

def test_gemini_provider_request_and_response():
    captured: dict = {}
    provider = GeminiProvider("fake-gemini-key", "gemini-2.5-flash-lite",
                              transport=gemini_transport(captured))
    result = run(provider.complete(PROMPT, temperature=0.7))
    assert result == "personalized output"
    assert "models/gemini-2.5-flash-lite:generateContent" in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "fake-gemini-key"
    assert captured["payload"]["generationConfig"]["temperature"] == 0.7
    assert captured["payload"]["contents"][0]["parts"][0]["text"] == PROMPT


def test_gemini_provider_error_becomes_llm_error():
    provider = GeminiProvider("fake-key", "gemini-2.5-flash-lite",
                              transport=gemini_transport({}, status=429))
    with pytest.raises(LLMError):
        run(provider.complete(PROMPT, temperature=0.7))


# --- OpenRouter provider (unit, mocked transport) --------------------------------

def test_openrouter_provider_request_and_response():
    captured: dict = {}
    provider = OpenRouterProvider("fake-openrouter-key", "cohere/north-mini-code:free",
                                  transport=openrouter_transport(captured))
    result = run(provider.complete(PROMPT, temperature=0.7))
    assert result == "fallback output"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer fake-openrouter-key"
    assert captured["payload"]["model"] == "cohere/north-mini-code:free"
    assert captured["payload"]["temperature"] == 0.7
    assert captured["payload"]["messages"] == [{"role": "user", "content": PROMPT}]


# --- fallback order ---------------------------------------------------------------

def test_gemini_failure_falls_back_to_openrouter():
    captured: dict = {}
    service = LLMService([
        GeminiProvider("fake-key", "gemini-2.5-flash-lite",
                       transport=gemini_transport({}, status=429)),
        OpenRouterProvider("fake-key", "cohere/north-mini-code:free",
                           transport=openrouter_transport(captured)),
    ])
    assert run(service.complete(PROMPT, temperature=0.7)) == "fallback output"
    assert captured["payload"]["model"] == "cohere/north-mini-code:free"


def test_all_providers_failing_raises_llm_error():
    service = LLMService([
        GeminiProvider("fake-key", "m", transport=gemini_transport({}, status=500)),
        OpenRouterProvider("fake-key", "m", transport=openrouter_transport({}, status=503)),
    ])
    with pytest.raises(LLMError, match="all configured"):
        run(service.complete(PROMPT, temperature=0.7))


# --- stub provider ----------------------------------------------------------------

def test_stub_provider_is_deterministic():
    stub = StubProvider()
    first = run(stub.complete(PROMPT, temperature=0.7))
    second = run(stub.complete(PROMPT, temperature=0.7))
    assert first == second
    roadmap = json.loads(first)
    assert roadmap["archetype_id"] == 2
    assert "[PROJECT_PURPOSE]" not in first  # personalization slots filled
    assert roadmap["timeline_estimate"]


# --- provider selection from settings ----------------------------------------------

def _settings(**env) -> Settings:
    return Settings(_env_file=None, **env)


def test_no_keys_selects_stub():
    assert build_llm_service(_settings()).provider_names == ["stub"]


def test_explicit_stub_mode():
    assert build_llm_service(_settings(llm_provider="stub")).provider_names == ["stub"]


def test_gemini_primary_openrouter_fallback():
    s = _settings(gemini_api_key="fake-g", openrouter_api_key="fake-o")
    assert build_llm_service(s).provider_names == ["gemini", "openrouter"]


def test_openrouter_only_key():
    s = _settings(openrouter_api_key="fake-o")
    assert build_llm_service(s).provider_names == ["openrouter"]


def test_openrouter_as_named_primary():
    s = _settings(llm_provider="openrouter",
                  gemini_api_key="fake-g", openrouter_api_key="fake-o")
    assert build_llm_service(s).provider_names == ["openrouter", "gemini"]
