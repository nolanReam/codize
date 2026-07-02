# Codize Active Session Instructions — Milestone 5

Continue Codize per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Current State

Milestones complete:

* M1 Repository foundation + pre-build artifacts — commit `98ad004`
* M2 Supabase schema + RLS — commit `5db4744`
* M3 Authentication foundation — commit `1075d2f`
* M4 FastAPI core — commit `d6e55be`

Known pending items:

* Live adversarial prompt testing is still pending because no `ANTHROPIC_API_KEY` is available. Required before Milestone 9.
* Live JWKS verification of a real Supabase JWT is pending backend env vars.
* `scripts/verify_auth.py` was skipped in M4 because `SUPABASE_URL` / `SUPABASE_ANON_KEY` were absent from the session env.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/prebuild-artifact-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `backend/app/templates/*.json`
* `backend/app/prompts/README.md`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 5 Only — Archetype Template Engine

Goal: implement the backend engine that loads, validates, and serves the three hardcoded archetype JSON templates.

This milestone does not call any LLMs.

## Implement

Create the simplest robust template engine inside the FastAPI backend.

Required behavior:

* Load the three archetype JSON templates from `backend/app/templates/`.
* Validate the template structure at startup or service initialization.
* Expose a service layer for future milestones to retrieve templates by archetype id.
* Preserve the rule that template structure is fixed.
* Do not allow runtime mutation of templates.
* Do not allow adding a fourth archetype.
* Provide deterministic classification helper logic if appropriate, but do not call an LLM yet.

Required service behavior:

* `list_archetypes()` returns metadata for exactly three archetypes.
* `get_template(archetype_id)` returns the matching template.
* Invalid archetype ids return a controlled error.
* Validation confirms:

  * exactly three templates
  * ids are 1, 2, 3
  * required top-level fields exist
  * phases are sequential
  * each phase has required fields
  * each phase has 3–5 gate targets
  * final phase is the Pre-Deployment Security Checklist
  * fixed security constraints are present
  * templates do not contain unexpected archetype ids

API routes are allowed only if they are thin and foundation-level.

Allowed routes:

* `GET /archetypes`
* `GET /archetypes/{archetype_id}`

If created, these routes must:

* be read-only
* expose no secrets
* use the service layer
* return controlled errors for invalid ids

## Tests

Add tests for:

* all three templates load
* `list_archetypes()` returns exactly three
* `get_template(1)`, `get_template(2)`, and `get_template(3)` work
* invalid id returns controlled error
* templates are immutable from caller perspective
* template validation catches missing fields
* API routes work if created
* no fourth archetype can be introduced silently

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

* intake API routes
* roadmap generation runtime
* LLM calls
* phase workspace
* Interrogation Gate runtime
* unlock system
* reconnection system
* frontend UI
* deployment

Do not begin Milestone 6.

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