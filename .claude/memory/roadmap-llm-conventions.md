# Roadmap generation + LLM provider conventions (Milestone 7)

Provider decision (user-directed in the M7 instructions): all LLM traffic goes
through `backend/app/services/llm_service.py` — Gemini primary
(`GEMINI_API_KEY`, `GEMINI_MODEL`, default `gemini-2.5-flash-lite`), OpenRouter
fallback (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, default
`cohere/north-mini-code:free`), deterministic `StubProvider` ONLY for tests and
local no-key mode. **Anthropic is intentionally not supported** — do not
reintroduce `ANTHROPIC_API_KEY` in config, `.env.example`, or docs unless the
user explicitly decides to. The stub is never a silent fallback for a failing
live provider: if any live key is configured and all live providers fail, the
call fails (LLMError), it does not degrade to the stub.

Roadmap validation is FAIL-CLOSED (`roadmap_service.validate_roadmap_structure`):
a drifted roadmap is discarded, never stored, and the status stays 'intake'.
Exact-equality fields: archetype_id/name, phase numbers, phase_title,
gate_depth, unlock_condition, the verbatim NOTE: sentences (same task index),
and the RLS-first task (verbatim AND first). Personalizable fields
(core_concept, task wording, gate-target wording, functional_unlock wording)
are checked by presence/type/count only — counts pin AI-vs-human task
classification and gate-target totals. The LLM must also ADD
`timeline_estimate` (required) and may add `stack_warning` (optional; mirrored
to the projects.stack_warning column on persist). Any other extra top-level
key is drift.

Status flip: roadmap JSONB + `status='active'` are written in ONE
`update_project` PATCH after validation passes, so 'active' can never exist
without a stored valid roadmap. Roadmap generation temperature is 0.7, fixed
by `backend/app/prompts/README.md` — the constant lives in
`roadmap_service.ROADMAP_TEMPERATURE`.

Unverified as of 2026-07-02: live Gemini/OpenRouter calls (no keys in the M7
session — both providers unit-tested against `httpx.MockTransport` only). In
the first session with a real key, run one real `POST /roadmap/generate` and
confirm the returned roadmap passes validation.
