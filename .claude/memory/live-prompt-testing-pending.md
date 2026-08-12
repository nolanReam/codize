# Live adversarial prompt testing — COMPLETED in Milestone 9 (2026-07-02)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

The spec's required live adversarial testing of the system prompts ran at the
start of M9 via `scripts/live_adversarial_tests.py` (re-runnable) against
Gemini `gemini-2.5-flash-lite` through `llm_service` — all 10 required cases
plus extra probes defended after two prompt strengthenings; full record in
`docs/prebuild/adversarial_tests.md`.

Still LIVE PENDING: only the `phase_explanation.md` gate-question-leak probe
(M1 table case 9) — that prompt is deliberately not wired up at runtime yet;
test it in the milestone that wires it. Also still live-unverified: the
OpenRouter fallback path (Gemini never failed during any probe).

Provider decision stands (M7, user-directed): Gemini primary, OpenRouter
fallback — **Anthropic is intentionally not supported**; never reintroduce
`ANTHROPIC_API_KEY` unless the user explicitly decides to. Never ask the user
to paste a key into chat. Re-run the adversarial suite after any gate-prompt
edit (see [[gate-conventions]] via .claude/memory/gate-conventions.md).
