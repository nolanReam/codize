# Codize Active Session Instructions — Milestone 8

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

Known pending items:

* Live Gemini/OpenRouter calls were unverified in M7 because no live LLM provider key was available in that session.
* Live adversarial prompt testing is still pending until at least one live LLM provider is configured. Gemini or OpenRouter may satisfy this. Required before Milestone 9.
* Live PostgREST reads/writes remain unverified because backend Supabase env vars have not been available.
* Live JWKS verification of a real Supabase JWT is pending env vars.
* M7 closed the M6 status decision: intake completion leaves status `intake`; successful roadmap generation stores a valid roadmap and flips status to `active` in the same write.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/intake-engine-conventions.md`
* `.claude/memory/roadmap-llm-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `backend/app/services/template_service.py`
* `backend/app/services/intake_service.py`
* `backend/app/services/roadmap_service.py`
* `backend/app/services/project_repository.py`
* `backend/app/prompts/phase_explanation.md`
* `backend/app/prompts/README.md`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 8 Only — Phase Workspace

Goal: implement the backend phase workspace foundation.

The phase workspace should let an authenticated user view the current roadmap phase, see its personalized content/tasks/resources/gate targets, mark phase tasks complete, and persist phase progress.

Do not build frontend UI yet.

## Required Behavior

The phase workspace must use the stored roadmap as the source of truth.

A project is eligible for phase workspace only if:

* intake is complete
* archetype_id exists
* roadmap exists
* project status is `active`

The workspace should support:

1. Listing roadmap phases.
2. Reading one phase by phase number.
3. Reading the current phase.
4. Reading task completion state for the current user/project.
5. Marking individual tasks complete/incomplete.
6. Persisting phase progress on the project record or existing schema structure.
7. Preventing access to another user’s project.
8. Returning controlled errors for missing roadmap, invalid phase number, or inactive project.

Use the simplest robust persistence strategy supported by the existing schema.

Do not create new tables unless absolutely necessary. Prefer existing JSONB/progress fields if they already exist and are appropriate.

## Phase Explanation

The prompt file `backend/app/prompts/phase_explanation.md` exists, but this milestone should not overbuild LLM behavior.

If the roadmap already contains personalized phase content, use it.

If a phase explanation generation seam is needed:

* call the generic LLM service only through the provider-agnostic layer
* use Gemini primary, OpenRouter fallback, stub for tests/no-key mode
* use the correct temperature from `backend/app/prompts/README.md`
* validate that returned explanation does not alter phase structure

If no live provider key is configured, use deterministic stub behavior in tests and mark live explanation generation as unverified.

Do not require Anthropic.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `GET /phases`
* `GET /phases/current`
* `GET /phases/{phase_number}`
* `PATCH /phases/{phase_number}/tasks/{task_id}`

Adjust route names only if a simpler consistent REST shape is better.

Requirements:

* routes are auth-protected
* route handlers stay thin
* service layer owns phase workspace logic
* user can access only their own project state
* invalid phase numbers return controlled errors
* responses use the existing standard error shape
* responses leak no server-only secrets

## Service Layer

Create a phase workspace service that handles:

* loading the user’s active project
* reading stored roadmap JSON
* validating phase numbers
* returning phase workspace data
* updating task completion state
* preserving roadmap structure
* preventing phase progress corruption
* preparing future Interrogation Gate integration

Use the simplest robust design.

## Tests

Add tests for:

* cannot access phases before roadmap exists
* cannot access phases if project is not active
* can list phases from stored roadmap
* can read current phase
* can read phase by valid phase number
* invalid phase number returns controlled error
* task completion can be marked true
* task completion can be marked false
* task completion persists
* task updates do not mutate fixed roadmap structure
* user cannot access or mutate another user’s phase state
* auth required for phase routes
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

Run auth verification only if env vars are available:

```bash
python scripts/verify_auth.py
```

If env vars are unavailable, mark it unverified rather than blocking.

If Gemini/OpenRouter env vars are available, run one live roadmap or phase-explanation smoke test if the service supports it. If unavailable, mark live LLM behavior unverified.

## Out of Scope

Do not implement:

* Interrogation Gate runtime
* gate evaluation runtime
* unlock system
* reconnection system
* frontend UI
* deployment

Do not begin Milestone 9.

Do not continue beyond Milestone 8.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run secret scan
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable phase-workspace lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`
