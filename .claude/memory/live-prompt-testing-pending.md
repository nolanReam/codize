# Live adversarial prompt testing is pending an API key

No `ANTHROPIC_API_KEY` was available in the build environment at Milestone 1 (2026-07-01). The six system prompts passed static adversarial verification (see `docs/prebuild/adversarial_tests.md`), but the spec's required live testing against a real model has NOT run yet.

Why it matters: the spec's pre-build gate requires manual adversarial testing before backend code; static analysis was the achievable substitute. Live runs (anchor-skip, textbook Turn 3, ill-fitting project, injection cases 4–10 in the log) must be executed and recorded before Milestone 9 (Interrogation Gate) at the latest — ask the user for the key at the start of Milestone 2.
