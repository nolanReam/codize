# Codize Active Session Instructions — Milestone 7

Continue Codize per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Current State

Milestones complete:

* M1 Repository foundation + pre-build artifacts — commit `98ad004`
* M2 Supabase schema + RLS — commit `5db4744`
* M3 Authentication foundation — commit `1075d2f`
* M4 FastAPI core — commit `d6e55be`
* M5 Archetype template engine — commit `53d6aa0`
* M6 Intake engine — commit `0aacfae`

Known pending items:

* Live PostgREST reads/writes are unverified because backend env vars have not been available.
* Live JWKS verification of a real Supabase JWT is pending env vars.
* Live adversarial prompt testing is still pending until at least one live LLM provider is configured. Gemini or OpenRouter may satisfy this. Anthropic is intentionally not required for this project.
* M6 decision: completing intake sets `intake_completed_at` and `archetype_id` but leaves `projects.status = 'intake'`. M7 should flip status to `active` after roadmap generation succeeds.

## Read First

Read only these before implementation:

* `CLAUDE.md`
* `.claude/skills/spec-guardian/SKILL.md`
* `.claude/skills/security-test/SKILL.md`
* `.claude/skills/milestone-handoff/SKILL.md`
* `.claude/memory/prebuild-artifact-conventions.md`
* `.claude/memory/intake-engine-conventions.md`
* `.claude/memory/auth-milestone-todos.md`
* `backend/README.md`
* `backend/app/services/template_service.py`
* `backend/app/services/intake_service.py`
* `backend/app/services/project_repository.py`
* `backend/app/prompts/roadmap_generation.md`
* `backend/app/prompts/README.md`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 7 Only — Roadmap Generation

Goal: implement the backend roadmap generation engine.

Roadmap generation must use the selected archetype’s hardcoded JSON template as the structural source of truth.

The LLM may personalize language and examples, but it must never:

* add phases
* remove phases
* reorder phases
* change task classifications
* alter gate targets
* alter gate depth
* alter unlock conditions
* alter functional unlock rewards
* add a fourth archetype

## Required Behavior

After intake is complete and an `archetype_id` exists, roadmap generation should:

1. Load the matching archetype template.
2. Inject the full template and the student’s intake answers into the roadmap generation prompt.
3. Generate or prepare a personalized roadmap.
4. Preserve the template structure exactly.
5. Store the generated roadmap on the project record.
6. Flip `projects.status` from `intake` to `active` only after roadmap generation succeeds.
7. Return the generated roadmap to the caller.

## LLM Handling

Build a provider-agnostic LLM service.

Provider order for development:

1. Gemini primary
2. OpenRouter fallback
3. Stub provider for tests/no-key mode

Do not require Anthropic.

Do not add `ANTHROPIC_API_KEY` to `.env.example` unless the user explicitly decides to support Anthropic later.

Use these environment variables:

* `LLM_PROVIDER`
* `GEMINI_API_KEY`
* `GEMINI_MODEL`
* `OPENROUTER_API_KEY`
* `OPENROUTER_MODEL`

Default development config:

* `LLM_PROVIDER=gemini`
* `GEMINI_MODEL=gemini-2.5-flash-lite`
* `OPENROUTER_MODEL=cohere/north-mini-code:free`

Roadmap generation must call the generic LLM service, not provider-specific code directly.

If Gemini is configured:

* use Gemini for live roadmap generation
* use the correct temperature from `backend/app/prompts/README.md`
* validate the returned roadmap against the source template
* fail closed if structure drifts

If Gemini fails due to rate limit, provider error, or unavailable model, and OpenRouter is configured:

* fall back to OpenRouter
* use `OPENROUTER_MODEL`
* validate the returned roadmap against the source template
* fail closed if structure drifts

If no live provider key is configured:

* implement the provider interface
* use a deterministic stub provider for tests and local no-key mode
* mark live LLM generation as unverified
* do not block the milestone

The stub provider must be deterministic and used only for tests/local no-key mode.

Regardless of provider, validate the returned roadmap against the source archetype template and fail closed if structure drifts.

Do not ask the user to paste secrets into chat.

## Service Layer

Create or update services so that roadmap generation logic lives outside route handlers.

Likely service responsibilities:

* load roadmap generation prompt
* prepare prompt inputs
* call generic LLM service
* call Gemini provider when configured
* call OpenRouter provider as fallback when configured
* use stub provider for tests/no-key mode
* validate generated roadmap against source template
* persist roadmap JSONB
* update project status to `active`

Use the simplest robust design.

## Environment Documentation

Update `.env.example` and backend docs if needed.

Document variables without values:

* `LLM_PROVIDER`
* `GEMINI_API_KEY`
* `GEMINI_MODEL`
* `OPENROUTER_API_KEY`
* `OPENROUTER_MODEL`

Do not document Anthropic variables unless the user explicitly decides to support Anthropic later.

Never commit real secrets.

## API Routes

Create thin protected routes if appropriate.

Allowed routes:

* `POST /roadmap/generate`
* `GET /roadmap`

Adjust route names only if a simpler consistent REST shape is better.

Requirements:

* routes are auth-protected
* users can only generate/read their own roadmap
* route handlers stay thin
* service layer owns roadmap logic
* controlled errors use the existing standard error shape
* responses leak no server-only secrets

## Roadmap Structure Validation

Add validation that catches:

* missing phases
* extra phases
* reordered phases
* changed phase numbers
* changed gate targets
* changed gate depth
* changed unlock conditions
* changed functional unlocks
* changed AI/human task labels
* added fourth archetype or wrong archetype id

The validator should compare generated roadmap output against the original template.

## Tests

Add tests for:

* cannot generate roadmap before intake completion
* cannot generate roadmap without archetype id
* loads correct template for archetype id
* generated roadmap preserves phase count/order
* generated roadmap preserves fixed gate targets
* generated roadmap preserves AI/human task classifications
* generated roadmap preserves unlock conditions
* generated roadmap preserves final security checklist phase
* successful generation stores roadmap and flips status to `active`
* generation failure does not flip status to `active`
* Gemini provider path can be unit-tested without real API calls
* OpenRouter fallback path can be unit-tested without real API calls
* stub provider is deterministic
* user cannot read or generate another user’s roadmap
* auth required for roadmap routes
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

## Out of Scope

Do not implement:

* phase workspace
* Interrogation Gate runtime
* gate evaluation runtime
* unlock system
* reconnection system
* frontend UI
* deployment

Do not begin Milestone 8.

Do not continue beyond Milestone 7.

## End Requirements

At the end:

* run backend tests
* run prebuild validator
* run secret scan
* commit changes
* update `CLAUDE.md` with new commands/routes if relevant
* update `.claude/memory/` with durable roadmap/LLM lessons
* output `MILESTONE COMPLETE`
* tell the user to run `/compact`