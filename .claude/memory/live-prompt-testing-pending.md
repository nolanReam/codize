# Live adversarial prompt testing is pending a provider key

No live LLM provider key was available in the build environment at Milestones 1–7 (as of 2026-07-02). The six system prompts passed static adversarial verification (see `docs/prebuild/adversarial_tests.md`), but the spec's required live testing against a real model has NOT run yet.

Provider decision (M7, user-directed): Gemini primary, OpenRouter fallback — **Anthropic is intentionally not supported**; never reintroduce `ANTHROPIC_API_KEY` unless the user explicitly decides to. Live runs can be satisfied with `GEMINI_API_KEY` or `OPENROUTER_API_KEY` through `backend/app/services/llm_service.py`.

Why it matters: the spec's pre-build gate requires manual adversarial testing before backend code; static analysis was the achievable substitute. Live runs (anchor-skip, textbook Turn 3, ill-fitting project, injection cases 4–10 in the log) must be executed and recorded before Milestone 9 (Interrogation Gate) at the latest. Never ask the user to paste a key into chat.
