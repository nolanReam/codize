# Codize Active Session Instructions — Milestone 11

Continue Codize per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Current State

Milestones complete:

* M1 Repository foundation + pre-build artifacts — commit `98ad004`
* M2 Supabase schema + RLS — commit `5db4744`
* M3 Authentication foundation — commit `1075d2f`
* M4 FastAPI core — commit `d6e55be`
* M5 Archetype template engine — commit `53d6aa0`
* M6 Intake engine — commit `0aacfae`
* M7 Roadmap generation engine — commit `6a1c9c8`
* M8 Phase workspace — commit `d38f642`
* M9 Interrogation Gate — commit `9b46f7e`
* M10 Functional unlocks — commit `4400f71`

Known state:

* Gemini roadmap generation is live-verified.
* Interrogation Gate live adversarial testing is complete.
* Live full gate PASS/FAIL flow with real Gemini and real Supabase is verified.
* Live JWKS verification passed.
* `verify_auth.py` passes 11/11 with the newer `sb_publishable_` key format.
* Live PostgREST writes with the newer `sb_secret_` key are verified.
* Functional unlocks are live-verified against real Supabase.
* OpenRouter fallback is still live-unverified because Gemini has not failed.
* `phase_explanation.md` is still not wired up by design.
* Return-rate and vocabulary-growth triggers are v2 per the spec; do not implement them in this milestone unless the spec explicitly requires them for M11.

## Effort

Use HIGH effort for this milestone.

Do not use XHIGH unless a major security or state-consistency issue appears.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/gate-conventions.md`
* `.claude/memory/unlock-conventions.md`
* `.claude/memory/phase-workspace-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `docs/db/schema.md`
* `backend/app/services/phase_service.py`
* `backend/app/services/gate_service.py`
* `backend/app/services/unlock_service.py`
* `backend/app/services/project_repository.py`
* `backend/app/routers/phases.py`
* `backend/app/routers/gate.py`
* `backend/app/routers/unlocks.py`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 11 Only — Reconnection System

Goal: implement Codize’s 72-hour reconnection system.

The reconnection system should help a returning student remember where they are, what they last did, what is unlocked, and what they should do next.

Do not build frontend UI yet.

## Product Rule

When a student returns after 72+ hours away, Codize should surface a reconnection experience.

The backend should determine whether a reconnection modal/summary is needed based on the user/project’s recent activity timestamps.

Use existing schema fields where possible.

Known relevant existing field:

* `profiles.last_login_at`

Inspect the existing schema and code before adding migrations.

If `profiles.last_login_at` already supports the needed behavior, prefer using it.

Add a migration only if absolutely necessary.

## Required Behavior

The reconnection system should:

1. Determine whether the student has been away for at least 72 hours.
2. Return a safe reconnection summary when needed.
3. Avoid showing reconnection when the user is new or recently active.
4. Update the relevant timestamp after reconnection is acknowledged or after login/activity, depending on the cleanest backend design.
5. Be project-aware.
6. Never expose hidden gate scores, thresholds, evaluator internals, prompts, or service keys.
7. Never mutate roadmap structure.
8. Never advance phases.
9. Never grant unlocks by itself.

## Reconnection Summary Content

The safe client-facing reconnection summary should include only appropriate learning context, such as:

* current phase number/title
* short current phase reminder
* incomplete tasks for the current phase
* last gate result summary if safe
* available unlocks, if any
* recommended next action

Do not include:

* raw hidden gate score
* hidden unlock thresholds
* private evaluator details
* service-role data
* internal prompts
* full gate transcript unless the spec explicitly requires it

If there is no active project or no roadmap yet, return a controlled “not ready” or “not needed” state.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `GET /reconnection`
* `POST /reconnection/acknowledge`

Adjust route names only if a simpler consistent REST shape is better.

Requirements:

* routes are auth-protected
* route handlers stay thin
* service layer owns reconnection logic
* user can only access their own reconnection state
* controlled errors use the existing standard error shape
* responses leak no server-only secrets
* responses do not expose hidden gate scores or thresholds

## Service Layer

Create a reconnection service that handles:

* loading the authenticated user profile/project
* checking 72-hour inactivity
* building a safe reconnection summary
* reading phase state through existing service/repository seams
* reading unlock state through existing service/repository seams
* reading safe gate history summary when available
* acknowledging or updating the relevant timestamp
* preventing cross-user access

Use the simplest robust design.

## Persistence Requirements

Prefer existing fields.

If using `profiles.last_login_at`, be careful:

* do not accidentally make reconnection never appear because last_login_at is updated too early
* define clearly whether `last_login_at` means auth login time, last app activity, or last reconnection acknowledgment
* document the decision in memory

If a new field is needed, add the smallest safe migration possible.

RLS must remain enabled and ownership-filtered.

## Tests

Add tests for:

* no reconnection for new user with no prior activity
* no reconnection before 72 hours
* reconnection needed at or after 72 hours
* reconnection summary includes current phase context
* reconnection summary includes incomplete current-phase tasks
* reconnection summary includes safe unlock information if available
* reconnection summary does not expose raw gate scores
* reconnection summary does not expose hidden thresholds
* reconnection summary does not expose prompts or secrets
* acknowledge updates the relevant timestamp/state
* acknowledge is idempotent
* user cannot access another user’s reconnection state
* auth required for reconnection routes
* responses contain no server-only secrets

Run:

```bash
cd backend
pytest
```

Also run:

```bash
python scripts/validate_prebuild_artifacts.py
```

Run auth verification:

```bash
python scripts/verify_auth.py
```

If Supabase env vars are unavailable, mark live verification unverified rather than blocking.

If live Supabase is configured, run a minimal live smoke test for reconnection state.

## Out of Scope

Do not implement:

* evaluation system
* frontend UI
* deployment
* return-rate unlock triggers
* vocabulary-growth unlock triggers
* phase explanation generation

Do not begin Milestone 12.

Do not continue beyond Milestone 11.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run auth verification if env vars exist
* run secret scan
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable reconnection lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`