# Pre-build artifact conventions (Milestone 1)

`{{DOUBLE_BRACES}}` in prompt files = backend fills at call time (llm_service). `[SINGLE_BRACKETS]` in template JSON = the LLM fills during personalization. `NOTE:` sentences in template tasks = verbatim security constraints; the roadmap/phase prompts explicitly instruct the model to preserve them word for word, and the validator checks them.

Why it matters: mixing these up (backend substituting `[PROJECT_PURPOSE]`, or the LLM being allowed to rewrite `NOTE:` text) silently breaks the spec's security encoding. All three archetypes have exactly 7 phases, the final one always "Pre-Deployment Security Checklist" with exactly 9 human-required items — the validator (`scripts/validate_prebuild_artifacts.py`) enforces all of this; run it after any template or prompt edit.

Since M5, the runtime engine (`backend/app/services/template_service.py`) re-validates a subset of these invariants at app startup (exactly three archetypes, ids 1–3, sequential phases, 3–5 gate targets, checklist final phase, verbatim RLS-first + auth-middleware constraints) and rejects any fourth archetype. Any structural change to templates must keep BOTH validators in sync. Templates are served as deep copies — never add a mutation path to the store.
