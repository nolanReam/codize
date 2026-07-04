# Codize M13C.1B — Roadmap Generation Reliability Hotfix

Fix the roadmap-generation reliability blocker found during the M13C.1 live smoke pass.

This is a narrow backend/product-flow reliability milestone.

Do not start M13C.2.

Do not implement Gate UI.

Do not implement full Project Defense Report.

Do not make the gate evidence-aware.

Do not modify evaluator logic.

Do not create frontend features except tiny error-message fixes if absolutely necessary.

Do not add GitHub OAuth, AI news, browser IDE, community, marketplace, hosted runtime, or analytics dashboard.

## Current State

Relevant commits:

- M13B workflow artifact backend: `de42d5b`
- M13C.1 frontend foundation: `03e3c1f`
- M13C.1 live smoke pass: `3cb6275`

The live smoke pass verified the frontend flow in a real browser against live FastAPI + Supabase.

However, roadmap generation failed three times in a row with 502 due to LLM roadmap drift using the current Gemini config. The validator correctly failed closed, and the frontend handled the error, but this blocks real testers from reaching the workspace unless a valid roadmap is manually seeded.

## Goal

Make roadmap generation reliable enough for pilot users.

A user who completes intake should not be blocked by LLM structure drift if a valid archetype template exists.

The solution must preserve safety:

- Do not accept malformed LLM roadmaps.
- Do not weaken validation.
- Do not store invalid structures.
- Do not hide real unexpected failures.
- Do not require manual DB seeding.

## Read First

Read:

- `CLAUDE.md`
- `docs/context/context_authority.md`
- `docs/context/codize_product_vision_v3.md`
- `docs/context/m13_ai_workflow_workspace_plan.md`
- `docs/context/codize_master_spec_v2.1.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/frontend-conventions.md`
- backend roadmap routes/services/schemas
- archetype template engine/service
- roadmap validation logic
- LLM provider layer
- tests around roadmap generation
- M13C.1 live smoke notes in memory/docs if present

Do not read `conversations.json` unless genuinely needed.

## Problem To Solve

Current behavior appears to be:

1. User completes intake.
2. Backend calls LLM for roadmap generation.
3. LLM returns a roadmap that drifts from the required template structure.
4. Validator rejects it.
5. Backend returns 502.
6. User can retry, but repeated drift can block onboarding.

This is fail-closed, which is good for safety, but it is not good enough for pilot usability.

## Required Product Behavior

If LLM output is invalid but a valid hardcoded archetype template exists, Codize should still be able to create a valid roadmap.

Preferred behavior:

1. Try LLM personalization.
2. Validate output strictly.
3. If valid, store and return it.
4. If invalid after the allowed attempts, fall back to a deterministic template-backed roadmap.
5. Store only the valid fallback roadmap.
6. Do not expose internal validation details to the user.
7. Log or record that personalization fell back, if the existing logging/docs pattern supports it.

The fallback should be structurally valid and based on the existing archetype template.

The fallback may be less personalized, but it should still let the student enter the AI Workflow Workspace.

## Important Principle

The LLM should personalize language.

The hardcoded archetype template should protect structure.

If the LLM cannot preserve structure, the product should prefer a valid template-backed roadmap over blocking the user.

## Possible Implementation Options

Inspect the existing code and choose the smallest safe fix.

Acceptable options include:

- deterministic fallback roadmap generated from the selected archetype template
- stricter/lower-temperature roadmap generation config if already configurable
- retry prompt tightening if small and testable
- clearer frontend error message only as a supplement, not the main fix

Do not solve this by:

- weakening validation
- accepting partially invalid LLM output
- making the frontend manually seed roadmaps
- hardcoding a single user/project workaround
- adding a large new roadmap system
- adding paid-model-specific assumptions
- requiring a new external service

## Model Configuration Boundary

Do not hardcode a paid model as the only path.

If a stronger roadmap-generation model is recommended, document it as an environment/config option only.

The code should remain provider-agnostic.

The reliability fix should work even when the LLM returns invalid output or errors.

## Fallback Requirements

The fallback roadmap must:

- use the correct archetype template
- include valid phases/tasks according to existing schema
- pass existing roadmap validation
- produce a project status that lets the user continue
- preserve the intake purpose/scope/stack where safely possible
- avoid hallucinated unsupported requirements
- avoid exposing internal fallback/debug text in user-facing fields unless intentionally phrased

User-facing language may say something like:

“Codize created a structured starter roadmap from the verified template.”

But do not overcomplicate the UX.

## Tests Required

Add or update backend tests covering:

1. Valid LLM roadmap still succeeds.
2. Invalid/drifting LLM output does not store invalid data.
3. Invalid/drifting LLM output falls back to a valid template-backed roadmap when a template exists.
4. LLM provider error falls back to a valid template-backed roadmap when a template exists.
5. If no template exists or the archetype is unsupported, behavior remains safely failed.
6. Fallback roadmap passes existing validation.
7. Project becomes usable/active after fallback.
8. Frontend-facing error details do not leak internal validator prompts or stack traces.
9. Existing roadmap tests still pass.
10. No unrelated gate/workflow/evaluation behavior changes.

If there is already a test pattern for fake/stub LLM providers, use it.

## Optional Tiny Frontend Fix

Only if needed:

- make the intake retry message clearer
- make it obvious that no data was lost
- do not create new frontend features

If the backend fallback eliminates the blocker, frontend changes may not be needed.

## Verification Commands

Run:

```bash
cd backend
pytest