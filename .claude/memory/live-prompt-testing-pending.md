# Live adversarial prompt testing is pending a provider key

No live LLM provider key was available in the build environment at Milestones 1–7. **Since M8 (2026-07-02) `GEMINI_API_KEY` and `OPENROUTER_API_KEY` exist in the repo-root `.env` (gitignored)** — the blocker is gone, and the M8 live roadmap smoke test proved the Gemini path works. The six system prompts passed static adversarial verification (see `docs/prebuild/adversarial_tests.md`), but the spec's required live adversarial testing of the six prompts has still NOT run — it was out of M8's scope. **Run it at the start of Milestone 9 (Interrogation Gate), before building gate runtime logic.**

Provider decision (M7, user-directed): Gemini primary, OpenRouter fallback — **Anthropic is intentionally not supported**; never reintroduce `ANTHROPIC_API_KEY` unless the user explicitly decides to. Live runs can be satisfied with `GEMINI_API_KEY` or `OPENROUTER_API_KEY` through `backend/app/services/llm_service.py`.

Why it matters: the spec's pre-build gate requires manual adversarial testing before backend code; static analysis was the achievable substitute. Live runs (anchor-skip, textbook Turn 3, ill-fitting project, injection cases 4–10 in the log) must be executed and recorded before Milestone 9 (Interrogation Gate) at the latest. Never ask the user to paste a key into chat.
