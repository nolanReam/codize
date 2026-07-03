# Codize Active Session Instructions — Milestone 12

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
* M11 Reconnection system — commit `9012a52`

Known state:

* Gemini roadmap generation is live-verified.
* Interrogation Gate live adversarial testing is complete.
* Live full gate PASS/FAIL flow with real Gemini and real Supabase is verified.
* Live JWKS verification passed.
* `verify_auth.py` passes 11/11 with the newer `sb_publishable_` key format.
* Live PostgREST writes with the newer `sb_secret_` key are verified.
* Functional unlocks are live-verified against real Supabase.
* Reconnection is live-verified against real Supabase.
* OpenRouter fallback is still live-unverified because Gemini has not failed.
* `phase_explanation.md` is still not wired up by design.
* Return-rate and vocabulary-growth triggers are v2 per the spec and should not be implemented unless the spec explicitly requires them in M12.
* The M13 frontend contract for reconnection is documented: GET first on login, then acknowledge.

## Effort

Use XHIGH effort for this milestone.

This milestone implements the backend evaluation system, which should be careful, safe, and spec-aligned.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/gate-conventions.md`
* `.claude/memory/unlock-conventions.md`
* `.claude/memory/reconnection-conventions.md`
* `.claude/memory/phase-workspace-conventions.md`
* `.claude/memory/roadmap-llm-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `docs/db/schema.md`
* `backend/app/services/gate_service.py`
* `backend/app/services/phase_service.py`
* `backend/app/services/unlock_service.py`
* `backend/app/services/reconnection_service.py`
* `backend/app/services/project_repository.py`
* `backend/app/routers/gate.py`
* `backend/app/routers/phases.py`
* `backend/app/routers/unlocks.py`
* `backend/app/routers/reconnection.py`

Then consult `docs/context/codize_master_spec_v2.1.md` specifically for the Evaluation system requirements.

Do not read `conversations.json` unless needed.

## Milestone 12 Only — Evaluation System

Goal: implement Codize’s backend evaluation system.

The evaluation system should help the student understand their learning progress and next best action without exposing hidden scores, hidden thresholds, evaluator internals, private prompts, or raw gate mechanics.

Do not build frontend UI yet.

## Product Rule

Confirm the exact evaluation design from the spec before implementation.

If the spec defines specific evaluation fields, states, labels, or route names, follow the spec.

If the spec does not require persistent evaluation snapshots, prefer a deterministic computed evaluation over adding new tables.

Document any design decision in memory.

## Required Behavior

The evaluation system should produce a safe, student-facing evaluation summary for the authenticated user’s current project.

It should consider existing backend signals such as:

* intake completion
* roadmap generation status
* current phase
* phase/task progress
* gate pass/fail history
* safe gate-history summaries
* earned unlocks
* reconnection state if relevant
* project status

The evaluation should help answer:

1. Where am I in the roadmap?
2. What have I completed?
3. What is incomplete?
4. What did my recent gate outcomes suggest in safe, non-hidden language?
5. What should I do next?

The evaluation system must not:

* expose raw gate scores
* expose hidden unlock thresholds
* expose evaluator private reasoning
* expose prompt text
* expose provider keys or service-role data
* mutate the roadmap
* advance phases
* grant unlocks
* update reconnection timestamps
* change gate outcomes

## Student-Facing Evaluation Content

Safe fields may include:

* project status
* roadmap status
* current phase number/title
* completed phase count
* total phase count
* current phase task completion summary
* incomplete current-phase tasks
* recent gate outcome label, without raw score
* earned unlock summaries
* recommended next action
* readiness state such as `not_started`, `intake_needed`, `roadmap_needed`, `in_progress`, `gate_ready`, `cooldown`, or `complete` if supported by the spec

Do not include:

* numeric hidden gate score
* hidden unlock formula
* “score >= 7”
* evaluator private rubric text
* full internal gate transcript unless the spec explicitly requires it
* internal prompt names or prompt bodies
* service-role data

## LLM Use

Do not add a new LLM dependency unless the spec explicitly requires it.

Prefer deterministic evaluation derived from existing stored state.

If the spec requires LLM-generated evaluation language:

* use the provider-agnostic LLM service only
* Gemini primary
* OpenRouter fallback
* stub for tests/no-key mode
* validate output so it cannot reveal hidden scores, thresholds, prompts, or private evaluator reasoning
* mark live LLM evaluation unverified if no live provider call is made

Do not require Anthropic.

Do not add Anthropic env vars.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `GET /evaluation`
* `GET /evaluation/summary`

Use one route if that is simpler.

Adjust route names only if the spec or existing backend style clearly suggests a better shape.

Requirements:

* routes are auth-protected
* route handlers stay thin
* service layer owns evaluation logic
* user can only access their own evaluation state
* controlled errors use the existing standard error shape
* responses leak no server-only secrets
* responses do not expose hidden scores or thresholds

## Service Layer

Create an evaluation service that handles:

* loading the authenticated user’s current project
* determining project/evaluation readiness state
* reading phase/task progress safely
* reading safe gate outcome summaries
* reading unlock views
* producing recommended next action
* preventing cross-user access
* producing safe client-facing response models

Use existing service/repository seams where appropriate.

Avoid duplicating phase/unlock/reconnection logic if public safe view helpers already exist.

## Persistence Requirements

Prefer no new migration.

If the spec requires persistent evaluation records, add the smallest safe migration possible.

If adding persistence:

* RLS must remain enabled
* ownership must be enforced
* hidden scores and thresholds must not be client-readable
* service-role writes must still filter by `user_id`

If evaluation is computed on read, document that decision in memory.

## Tests

Add tests for:

* evaluation returns correct state when user has no project
* evaluation returns intake-needed state before intake completion
* evaluation returns roadmap-needed state before roadmap generation
* evaluation returns active in-progress state after roadmap generation
* evaluation includes current phase number/title
* evaluation includes task completion summary
* evaluation includes incomplete current-phase tasks
* evaluation includes safe earned unlock summaries
* evaluation includes safe recent gate outcome label/summary
* evaluation recommends next action before gate
* evaluation recommends next action during cooldown
* evaluation recommends next action after gate pass
* evaluation handles completed/final phase if applicable
* evaluation does not expose raw gate scores
* evaluation does not expose hidden thresholds
* evaluation does not expose internal prompts
* evaluation does not expose provider or service-role secrets
* evaluation does not mutate roadmap, task progress, unlocks, gates, or reconnection timestamps
* user cannot access another user’s evaluation
* auth required for evaluation routes
* responses contain no server-only secrets

Run:

```bash id="5hmv3p"
cd backend
pytest
```

Also run:

```bash id="8fpu6o"
python scripts/validate_prebuild_artifacts.py
```

Run auth verification:

```bash id="r8byw4"
python scripts/verify_auth.py
```

If Supabase env vars are unavailable, mark live verification unverified rather than blocking.

If live Supabase is configured, run a minimal live smoke test for evaluation summary.

## Out of Scope

Do not implement:

* frontend UI
* deployment
* return-rate unlock triggers
* vocabulary-growth unlock triggers
* phase explanation generation
* new roadmap generation behavior
* new gate scoring behavior
* new unlock rules unless the spec explicitly requires them for M12

Do not begin Milestone 13.

Do not continue beyond Milestone 12.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run auth verification if env vars exist
* run secret scan
* run live Supabase smoke test if env vars exist
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable evaluation lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`