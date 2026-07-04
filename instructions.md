# Codize M13C.2B — Gate Question Cleanliness Hotfix

Fix the user-facing gate-question cleanliness issue found during the M13C.2 browser smoke test.

This is a narrow backend/UI-quality hotfix.

Do not start M14.

Do not add new product features.

Do not implement evidence-aware gate prompts.

Do not change gate pass/fail logic.

Do not weaken gate validation.

Do not modify evaluator scoring.

Do not create migrations.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, analytics dashboard, hosted coding runtime, or gamification.

## Current State

Relevant commits:

- M13B workflow artifact backend: `de42d5b`
- M13C.1 frontend foundation: `03e3c1f`
- M13C.1 live smoke pass: `3cb6275`
- M13C.1B roadmap reliability hotfix: `6eb7e57`
- M13C.2 Gate UI + Project Defense Report: `8161dce`

M13C.2 implemented:

- live `/app/gate` turn-by-turn Project Defense UI
- full `/app/report` client-assembled Project Defense Report
- Markdown copy/export
- pilot polish
- favicon

The M13C.2 browser smoke test found one known issue:

Gemini `flash-lite` occasionally leaks a phrase like “valid anchor…” or similar meta-preamble into the Turn 1 question text. The frontend correctly renders what the backend returns, so this should be fixed at the gate-question generation/cleanliness layer.

## Goal

Ensure all user-facing gate questions are clean, direct, and free of internal/meta/prompt artifacts.

The gate should still be strict.

The evaluator should remain unchanged.

The frontend should not hide backend bugs by blindly accepting unsafe text.

## Read First

Read:

- `CLAUDE.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/product-vision-v3.md`
- backend gate router/service/schemas
- backend gate prompt construction
- backend gate tests
- frontend `/app/gate` page only if needed

Do not read `conversations.json` unless genuinely needed.

## Problem To Solve

Sometimes the generated Turn 1 question includes meta text or prompt-instruction leakage such as:

- “valid anchor…”
- “Here is a valid question…”
- “The anchor is valid because…”
- rubric/internal language
- instruction-following preambles
- anything that sounds like the model is explaining the prompt instead of asking the student a question

This hurts pilot readiness because the Project Defense flow should feel polished and serious.

## Allowed Fixes

Choose the smallest safe fix after inspecting the backend.

Allowed options:

1. Tighten the gate-question generation prompt so it requires question-only output.
2. Add a small output-normalization/sanitization layer for user-facing gate questions.
3. Add validation that rejects or retries obviously meta/preamble-style question text.
4. Use an existing retry/fallback pattern if already present.

Prefer a deterministic guard if possible.

Do not overbuild.

## Required Behavior

User-facing gate questions should:

- be direct questions
- be implementation-specific
- not include model preambles
- not include rubric language
- not include internal prompt text
- not include evaluator reasoning
- not include hidden score/threshold language
- not expose system instructions
- remain connected to the phase/gate target

Examples of acceptable question style:

- “Explain how your current implementation handles user ownership.”
- “What would break if this route returned the wrong response shape?”
- “Why does this phase require the database policy before the frontend depends on it?”

Examples of unacceptable style:

- “Valid anchor: this answer should…”
- “Here is a question that satisfies the rubric…”
- “The student must demonstrate…”
- “According to the evaluator criteria…”
- “I will now ask…”

## Boundaries

Do not make the gate evidence-aware.

Do not send workflow artifacts into the evaluator.

Do not change pass/fail thresholds.

Do not expose raw scores.

Do not expose evaluator private reasoning.

Do not alter cooldown behavior.

Do not alter phase advancement behavior.

Do not alter unlock logic.

Do not change the frontend report except if it has to display the cleaned gate text safely.

## Tests Required

Add or update tests covering:

1. Clean gate question output remains unchanged.
2. Preamble/meta text is removed or rejected/retried.
3. “valid anchor” style leakage does not reach the user-facing response.
4. Rubric/evaluator language does not reach the user-facing response.
5. Internal prompt fragments do not reach the user-facing response.
6. Gate pass/fail evaluator behavior remains unchanged.
7. Existing gate tests still pass.
8. Frontend gate UI still typechecks/builds if frontend types are touched.

If the fix is prompt-only, still add a deterministic unit test around the output-cleanliness helper or response validator.

## Verification Commands

Run:

```bash
cd backend
pytest