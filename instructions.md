# Codize Active Session Instructions — Milestone 6

Continue Codize per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Current State

Milestones complete:

* M1 Repository foundation + pre-build artifacts — commit `98ad004`
* M2 Supabase schema + RLS — commit `5db4744`
* M3 Authentication foundation — commit `1075d2f`
* M4 FastAPI core — commit `d6e55be`
* M5 Archetype template engine — commit `53d6aa0`

Known pending items:

* Live adversarial prompt testing is still pending because no `ANTHROPIC_API_KEY` is available. Required before Milestone 9.
* Live JWKS verification of a real Supabase JWT is pending backend env vars.
* `scripts/verify_auth.py` may be skipped if `SUPABASE_URL` / `SUPABASE_ANON_KEY` are absent.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/prebuild-artifact-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `docs/db/schema.md`
* `docs/auth.md`
* `backend/app/services/template_service.py`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 6 Only — Intake Engine

Goal: implement the backend intake engine for Codize’s five mandatory conversational intake questions.

This milestone should create the backend logic and API foundation for intake. Do not build frontend UI yet.

## Required Intake Behavior

The intake flow has exactly five mandatory sequential questions.

Question 1 must be exactly:

"What problem do you want to solve, and who does solving it help?"

The five answers must capture:

1. purpose
2. project description / scope
3. stack preference
4. self-assessed AI-code understanding
5. deadline / timeline

Rules:

* Questions must be answered sequentially.
* Question 1 cannot be skipped.
* Intake must not complete until all five answers exist.
* Store answers in the existing Supabase-backed project model/schema design.
* Do not add a sixth question.
* Do not replace the purpose question with “What do you want to build?”
* Signup should eventually go straight to question 1, but frontend work is out of scope here.

## Archetype Classification

After all five intake answers are complete, classify the project into exactly one of:

1. AI-Powered App
2. REST API Backend
3. Full-Stack Web App

Use the existing `resolve_archetype()` deterministic tiebreaker from the template service if appropriate.

If an `ANTHROPIC_API_KEY` is available and the LLM service already exists, classification may use a temperature-0 LLM call. However, do not build a full LLM service in this milestone if that belongs later.

If no Anthropic key is available, implement the clean seam for future LLM classification and use the deterministic fallback/helper for now. Document what remains unverified.

Classification must never return a fourth archetype.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `GET /intake/questions`
* `GET /intake/status`
* `POST /intake/answers`
* `POST /intake/complete`

Adjust route names if a simpler REST shape is better, but preserve behavior.

Requirements:

* all intake routes are auth-protected
* route handlers stay thin
* service layer owns intake logic
* missing/invalid auth returns 401 through existing dependency
* users can only access/update their own project/intake state
* controlled errors use the existing standard error shape

## Service Layer

Create an intake service that handles:

* question definitions
* sequential answer validation
* answer normalization
* completion detection
* archetype classification
* project/intake state update interface

Use the simplest robust structure.

If real Supabase writes cannot run because env vars are unavailable, create repository/service seams and test the business rules with fakes. Clearly mark live DB writes as unverified.

## Tests

Add tests for:

* exactly five questions
* first question text is exact
* questions are sequential
* cannot complete with missing answers
* can complete with all five answers
* answer 1 / purpose is required
* invalid question index/order is rejected
* classification returns only ids 1, 2, or 3
* LLM-core projects classify as Archetype 1
* frontend/database projects classify as Archetype 3
* backend/API-only projects classify as Archetype 2
* auth required for intake routes
* route responses contain no server-only secrets

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

## Out of Scope

Do not implement:

* roadmap generation runtime
* phase workspace
* Interrogation Gate runtime
* unlock system
* reconnection system
* frontend UI
* deployment

Do not begin Milestone 7.

Do not continue beyond Milestone 6.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run secret scan
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`