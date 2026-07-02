# Codize Active Session Instructions — Milestone 4

Continue Codize per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Current State

Milestones complete:

- M1 Repository foundation + pre-build artifacts — commit `98ad004`
- M2 Supabase schema + RLS — commit `5db4744`
- M3 Authentication foundation — commit `1075d2f`

Live adversarial prompt testing is still pending because no `ANTHROPIC_API_KEY` is available. Do not block M4 on this.

## Read First

Read only these before implementation:

- `CLAUDE.md`
- `.claude/skills/spec-guardian/SKILL.md`
- `.claude/skills/security-test/SKILL.md`
- `.claude/skills/milestone-handoff/SKILL.md`
- `docs/auth.md`
- `.claude/memory/auth-milestone-todos.md`

If product behavior is unclear, consult `docs/context/codize_master_spec_v2.1.md`. Do not read `conversations.json` unless needed.

## Milestone 4 Only — FastAPI Core

Goal: create the FastAPI backend foundation only.

Implement:

- backend package structure
- FastAPI app entrypoint
- `GET /health`
- centralized config/settings
- safe CORS config
- consistent error response structure
- Supabase JWT auth dependency foundation
- backend test setup
- backend README or docs

Auth dependency should prepare future protected routes to use something like:

`current_user = Depends(require_user)`

It should:

- read `Authorization: Bearer <jwt>`
- reject missing token with 401
- reject invalid token with 401
- avoid trusting user IDs from request bodies
- avoid exposing secrets in logs or responses

Use the simplest robust approach. If live JWT verification is limited by missing env/network state, create the clean seam, test the error paths, and document what remains unverified.

## Tests

Add and run tests for:

- health route works
- app imports successfully
- settings load safely
- missing bearer token returns 401
- malformed bearer token returns 401
- no response leaks server-only env values

Run:

```bash
pytest
python scripts/validate_prebuild_artifacts.py