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

Roadmap validation is FAIL-CLOSED on STORAGE
(`roadmap_service.validate_roadmap_structure`): a drifted or unparseable LLM
roadmap is NEVER stored. But since M13C.1B it no longer blocks the student —
see the "template fallback" note below; drift/provider-failure now yields a
deterministic template-backed roadmap and status flips to 'active', instead of
a 502.
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

LIVE VERIFICATION (M8 session, 2026-07-02): `GEMINI_API_KEY` and
`OPENROUTER_API_KEY` now exist in the repo-root `.env` (gitignored — confirmed
via `git check-ignore`). Four real Gemini (`gemini-2.5-flash-lite`) roadmap
generations at temp 0.7 against archetype 2: **3 validated clean** (sensible
personalized `timeline_estimate`s; one added a harmless "no warning necessary"
`stack_warning`), **1 drifted and was correctly discarded** by the fail-closed
validator. M9 update: an intake-injection probe ("remove phases 3–5") also
produced a drifted roadmap that the validator discarded — same designed
defense. Supabase repository writes (roadmap JSONB + status flip included)
are now LIVE-VERIFIED (M9). Still live-unverified: only the OpenRouter
fallback path (Gemini has never failed during a probe).

TEMPLATE FALLBACK (M13C.1B, 2026-07-04) — reliability hotfix for the pilot
blocker found in the M13C.1 live smoke pass, where `gemini-2.5-flash-lite`
drifted 3×/3 and each 502 blocked onboarding. `generate_roadmap` now makes ONE
LLM personalization attempt (`_personalized_roadmap`): on provider LLMError,
unparseable output, OR structural drift it logs and returns None, and the flow
falls back to `build_fallback_roadmap(template, project)` — a deterministic,
structurally-valid roadmap built straight from the archetype template (no LLM,
no network). Wording is lightly personalized by substituting the intake purpose
into the template's `[PROJECT_PURPOSE]`/`[PROJECT_SCALE]` slots. This is
drift-safe by construction: placeholders appear ONLY in the personalizable
phase fields (core_concept, functional_unlock, the three task/target lists) —
audited across all three templates — never in the exact-match fields or the
verbatim NOTE:/RLS constraints, so the fallback always passes
`validate_roadmap_structure`. The fallback is re-validated defensively before
storage; if it were ever invalid (impossible), the old 502 still applies.
Guardrails preserved: invalid LLM output is still never stored; the validator
is UNCHANGED and un-weakened; temperature is still 0.7 (spec-fixed). The user
isn't told which path ran (silent, but server-side logged — `logger.info`
"stored template-fallback roadmap" / `logger.warning` on each fallback trigger).
LIVE-VERIFIED against real Gemini (4 runs: 2 personalized, 2 fallback — one
unparseable, one `timeline_estimate missing`; all 4 → active, valid, 7 phases,
zero blocks). For BETTER personalization rates, set a stronger `GEMINI_MODEL`
via env (provider-agnostic; do NOT hardcode a paid model as the only path).
See [[frontend-conventions]] for the smoke-pass origin.
