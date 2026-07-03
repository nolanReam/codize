# Codize Active Session Instructions — Milestone 10

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

Known state:

* Gemini roadmap generation was live-verified.
* Live adversarial prompt testing for the Interrogation Gate was completed in M9.
* Live JWKS verification of a real Supabase JWT passed.
* `verify_auth.py` passed 11/11 using the newer `sb_publishable_` key format.
* Live PostgREST writes with the newer `sb_secret_` key were verified.
* Supabase repository writes for projects and gate_sessions are verified.
* OpenRouter fallback is still live-unverified because Gemini has not failed.
* `phase_explanation.md` is still not wired up by design.
* The gate now stores score data, pass/fail result, passed_at, failed_at, and gate history.
* Authenticated users can read every gate column except `score`, which is revoked from client roles.

## Effort

Use HIGH effort for this milestone.

Do not use XHIGH unless a major security or evaluator issue appears.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/gate-conventions.md`
* `.claude/memory/phase-workspace-conventions.md`
* `.claude/memory/roadmap-llm-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `docs/db/schema.md`
* `backend/app/services/gate_service.py`
* `backend/app/services/phase_service.py`
* `backend/app/services/project_repository.py`
* `backend/app/services/template_service.py`
* `backend/app/routers/gate.py`
* `backend/app/schemas/gate.py`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 10 Only — Functional Unlocks

Goal: implement Codize’s functional unlock system.

Functional unlocks should reward strong gate performance by unlocking optional helpful features without exposing hidden thresholds or encouraging students to game the evaluator.

Do not build frontend UI yet.

## Product Rule

Functional unlocks are based on hidden gate performance thresholds.

The expected baseline rule is:

* unlock when a student scores at least 7 across two consecutive passed gates

However, confirm the exact unlock design from the spec before implementation.

If the spec differs, follow the spec and document the difference.

## Required Behavior

After a gate PASS, the backend should evaluate whether the student earned any functional unlocks.

Unlock evaluation should consider:

* current user
* current project
* current phase
* recent gate results
* pass/fail status
* hidden score values
* consecutive qualifying passes

Functional unlocks must:

* never be awarded on FAIL
* never be awarded from a single high score if the rule requires consecutive gates
* never expose hidden score thresholds to the client
* never expose raw hidden score values to the student/client
* be idempotent
* persist to the existing `unlocks` table or existing schema design
* be owned by the correct user/project
* respect RLS/security design
* not mutate the roadmap structure
* not advance phases by themselves

## Unlock Examples

Use spec-defined unlock names/types if they exist.

Possible examples may include:

* enhanced hints
* deeper explanation mode
* extra project-context feedback
* debugging support
* reflection support

Do not invent flashy/gamified unlocks if the spec already defines them.

Keep unlocks functional and learning-focused.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `GET /unlocks`
* `GET /unlocks/available`

Adjust route names only if a simpler consistent REST shape is better.

Requirements:

* routes are auth-protected
* route handlers stay thin
* service layer owns unlock logic
* users can only read their own unlocks
* hidden score thresholds are not returned
* raw gate scores are not returned
* responses leak no server-only secrets

## Service Layer

Create an unlock service that handles:

* reading relevant gate outcomes
* applying hidden unlock rules
* determining newly earned unlocks
* persisting earned unlocks
* preventing duplicate unlock rows
* returning safe client-facing unlock data
* integrating with gate PASS flow

The gate service should call the unlock evaluation after PASS if appropriate.

Use the simplest robust design.

## Persistence Requirements

Use the existing schema if possible.

If a migration is needed, keep it minimal.

Before adding a migration, inspect the existing `unlocks` table and use it if it already supports:

* user_id
* project_id
* unlock type/name
* created_at / unlocked_at
* relevant metadata

If new columns are needed, add only what is necessary.

RLS must remain enabled and ownership-filtered.

## Security Requirements

Do not expose:

* hidden thresholds
* raw score values
* evaluator private reasoning
* service-role keys
* provider keys
* internal gate prompts
* internal unlock formulas

Client-facing unlock responses should include only safe fields like:

* unlock id
* unlock type/name
* title
* description
* unlocked_at
* project_id

## Tests

Add tests for:

* no unlock on failed gate
* no unlock after only one qualifying passed gate
* unlock after two consecutive qualifying passed gates if rule is score ≥7 across two consecutive gates
* no unlock when passes are not consecutive
* no unlock when one of the consecutive scores is below threshold
* unlock creation is idempotent
* duplicate unlock rows are not created
* unlock belongs to the correct user/project
* user cannot read another user’s unlocks
* unlock route requires auth
* unlock route does not expose scores
* unlock route does not expose hidden thresholds
* gate PASS flow triggers unlock evaluation
* gate FAIL flow does not trigger unlock evaluation
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

If live Supabase is configured, run a minimal live smoke test for unlock persistence.

## Out of Scope

Do not implement:

* reconnection system
* evaluation system
* frontend UI
* deployment

Do not begin Milestone 11.

Do not continue beyond Milestone 10.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run auth verification if env vars exist
* run secret scan
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable unlock lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`
