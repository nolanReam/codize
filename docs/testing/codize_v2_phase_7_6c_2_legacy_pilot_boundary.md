# Phase 7.6C-2 — Legacy V1 Pilot Boundary

**Status:** Locally implemented and tested; not enabled or verified on any hosted deployment. No pilot launch authorization. Phase 7.6B remains locked.

## Starting repository state

Worktree: `C:/Users/purpl/Downloads/Codize/codize-v2-staging-fix`. Branch: `ox/v2-beta-staging`. Starting HEAD: `16484237a604ebe00d9a04e1d2db8ed386ae5083`. All three expectations matched and the worktree was clean. The separate main worktree was already dirty and was not edited, staged, reset, restored, cleaned, stashed, or switched. Its existing Python virtual environment was used only as a test interpreter.

Authority: current user-approved pilot defaults; AGENTS.md; local Spec Guardian, Security and Test, and Codize UI/UX skills; context authority, V2 Product Thesis, Exact UX, Technical Architecture (especially the separate-domain compatibility boundary), Schema Design, and the locked Phase 7.6B release-truth audit. Source and tests determine current implementation truth where older documentation still describes a pre-implementation stage.

## Route and dependency inventory

### Legacy frontend

`/app`, `/app/intake`, `/app/phase`, `/app/phase/prompt`, `/app/phase/import`, `/app/phase/change-map`, `/app/phase/review`, `/app/phase/verify`, `/app/phase/evidence`, `/app/gate`, `/app/report`. The phase root was already a compatibility redirect. The other legacy pages expose the V1 entry, intake, assignments/workflow, Defense, and report. The combined V2 project picker previously linked its maintained legacy project to `/app`.

### Legacy FastAPI routes

All ten legacy routers are omitted in pilot mode: **35 distinct paths, 38 method/path operations**.

| Router | Existing operations (all disabled in pilot mode) |
|---|---|
| archetypes | GET `/archetypes`, `/archetypes/{archetype_id}` |
| intake | GET `/intake/questions`, `/intake/entry-profile`, `/intake/status`; PUT `/intake/entry-profile`; POST `/intake/answers`, `/intake/complete` |
| roadmap | GET `/roadmap`; POST `/roadmap/generate` |
| phases | GET `/phases`, `/phases/current`, `/phases/current/assignment`, `/phases/{phase_number}`; PUT `/phases/current/assignment`; PATCH `/phases/{phase_number}/tasks/{task_id}` |
| report | GET `/report/{phase_number}` |
| gate | POST `/gate/start`; GET `/gate/context-summary`, `/gate/current`; POST `/gate/{gate_session_id}/turn1`, `/turn2`, `/turn3`, `/evaluate` |
| unlocks | GET `/unlocks` |
| reconnection | GET `/reconnection`; POST `/reconnection/acknowledge` |
| evaluation | GET `/evaluation` |
| workflow | GET `/workflow/{phase_number}`; POST `/workflow/{phase_number}/change-map/generate`, `/change-map/manual`, `/change-map/confirm`, `/review/from-change-map`, `/verification/from-review`; PUT `/workflow/{phase_number}/change-map`, `/workflow/{phase_number}/{section}`; GET and POST `/workflow/{phase_number}/evidence/from-verification` |

### Shared and retained

- `/health`, error handlers, explicit-origin CORS, development docs/OpenAPI behavior, settings, verified JWT/JWKS/`require_user`, Supabase Auth, and repository transport remain available.
- All **36 V2 API paths** under `/v2` remain registered: project creation/setup/drafts/references/detail/promotion/purge, plans, changes, teaching, prompt/agent/effort/handoff/return/check/completion, recovery, Learning/History/recent changes, and preferences.
- `/`, `/why-codize`, `/how-it-works`, `/login`, `/character`, `/settings`, `/app/projects`, `/app/project/[id]` and plan/build/learning/history children, `/app/character`, `/app/settings` remain outside the frontend legacy matcher.
- New public GET `/deployment-mode` returns only `{"pilot_v2_only": boolean}` with `Cache-Control: no-store`.

Two compatibility dependencies were confirmed rather than guessed: `/v2/project-refs` reads the legacy project repository for the combined picker; the client app layout performed a V1 reconnection GET/ack even on V2 routes. In pilot mode the picker now skips the legacy read and advertises only V2 references. The layout now performs reconnection only on legacy paths. Shared repository code and authentication are retained; V2 feature/state machinery has no V1 workflow dependency.

No existing deployment-level V2-only/compatibility flag was found. The existing typed Settings/env mechanism was reused.

## Chosen architecture and backend enforcement

One typed server setting, `codize_pilot_v2_only: bool = False`, controls router registration at application creation. The startup-selected boolean is retained in application state for mode reporting and project-reference filtering. Pilot requests never enter legacy handlers or their dependencies: absent routes return the normal safe 404. This avoids per-endpoint guards and introduces no roles or membership storage.

Queries, bodies, headers, method-override headers, and even a signed JWT carrying `pilot_v2_only=false` cannot register a missing route or change the application's mode. Ordinary CORS preflight remains infrastructure: it can return 200 for an allowed origin but cannot dispatch a missing legacy operation.

## Frontend handling

Next.js middleware matches only the legacy app root/segments. It fetches `/deployment-mode` from the existing configured API origin without cookies, authorization, or browser-supplied mode values, with no-store caching and a five-second timeout. Pilot mode gives a temporary 307 redirect to `/app/projects`, discarding legacy query parameters. Redirects are also no-store.

False mode passes the request through. Missing configuration, non-200 responses, network failures/timeouts, and malformed mode responses give a plain temporary-unavailable 503 on legacy URLs. Public and V2 paths require no mode lookup. Existing login/session checking still owns authentication on V2 destinations.

The backend-filtered picker removes V1 entry links. V2 layouts do not mount legacy navigation or invoke reconnection. No public design, copy, animation, or navigation architecture changed; no second frontend mode flag or server secret was added to public environment variables.

## Gemini/OpenRouter reachability

Source inspection found provider dispatch only in `llm_service.py`. Application completion callers are roadmap generation, gate completion/follow-up/evaluation, and change-map extraction. Reachable provider-capable endpoints are POST `/roadmap/generate`, POST `/gate/{gate_session_id}/turn1`, `/turn2`, `/turn3`, `/evaluate`, and POST `/workflow/{phase_number}/change-map/generate`.

All belong to omitted legacy routers. No current V2 route or its called application service invokes the legacy LLM service. V2's internal generation-attempt lifecycle stores attempt/result metadata and has no live provider adapter or public generation endpoint. Coding-agent metadata and manual handoff are not provider requests.

Tests set fake Gemini and OpenRouter keys and install failure sentinels on `LLMService.complete`, both provider `complete` methods, and provider HTTP dispatch. None were called. **Legacy provider calls are unreachable through this application's APIs in V2-only mode.** No live or paid provider call was made. Existing provider code/credentials were not deleted or changed.

## Configuration

On the designated pilot **backend**, set `CODIZE_PILOT_V2_ONLY=true` and restart every backend instance. Absent/false preserves ordinary V1 router registration and the combined picker. Invalid boolean configuration fails validation at startup.

No additional frontend pilot setting is needed. The existing `NEXT_PUBLIC_API_BASE_URL` must target that same designated backend and be reachable from both browser and Next.js middleware. It is already a public, build-time API origin; changes require a frontend rebuild. The mode endpoint discloses only the nonsecret boolean, never a Settings dump.

## Tests

Backend commands use `C:/Users/purpl/Downloads/Codize/codize/backend/.venv/Scripts/python.exe`, with the staging worktree's `backend/` as working directory. Its FastAPI installation uses deferred router registration; tests inventory the generated OpenAPI rather than assuming flattened `app.routes`.

| Command/check | Verified result |
|---|---|
| `python -m pytest tests/test_pilot_boundary.py tests/test_config.py tests/test_health.py -q` | **17 passed**, including both modes and invalid/absent configuration. Pilot checks issue 560 requests: 35 legacy paths × 8 methods × 2 slash forms, with client overrides; all 404; provider sentinels untouched. |
| `python -m pytest -q` (ordinary mode) | **1,244 passed, 2 failed**. Both failures reproduced in an untouched archive of starting HEAD; see below. |
| `CODIZE_PILOT_V2_ONLY=true`; `python -m pytest tests/test_v2_backend_routes.py tests/test_v2_phase6_recovery_routes.py tests/test_v2_api_error_boundary.py tests/test_v2_generation_lifecycle.py -k 'not test_v1_and_v2_refs_remain_distinct_and_only_one_legacy_row_is_advertised' -q` | **92 passed, 1 failed, 1 deselected**. Same baseline teaching-mode failure. The deselected test requires ordinary mixed V1/V2 references; the new boundary tests cover picker behavior in both modes. |
| `npm test` | **482 passed in 55 files**; includes 41 middleware and 10 rendered isolation tests. |
| `npm run typecheck` | Passed. |
| `npm run lint` | Passed; existing `next lint` deprecation notice. |
| `npm run build` | Passed with Next.js 15.5.20, 24 static pages and middleware output. |
| `python -m compileall -q ../backend/app` from frontend directory | Passed. No configured backend static linter/type checker was found. |
| `git diff --check` | Passed before local commit. |

Pre-existing failures, reproduced without our source changes:

1. `test_phase5_recently_independent_learner_originates_check`: expects teaching `skip`, receives `ask`.
2. `test_rls_verifier_cleanup_instructions_match_numbered_sections`: existing CLAUDE.md text does not satisfy the asserted documentation string.

No teaching or historical documentation fix was folded into this boundary change.

Local Uvicorn runtime (pilot=true, stub provider, no credentials used): `/health` 200, `/deployment-mode` 200 with true, `/intake/questions` 404, `/roadmap/generate` 404, `/v2/project-refs` 401 without auth. Signed-JWT authenticated V2 operations, ownership, complete Build loop and Recovery were verified through TestClient/fake repositories, not a hosted database.

Automatic approval review rejected the local frontend production-server start command with “blocked by policy” and supplied no more specific reason. Production frontend HTTP/browser verification could not be completed; middleware execution, rendered component tests and optimized build passed. No hosted behavior or accessibility conformance is claimed.

## Files changed

- `.env.example`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/routers/v2_projects.py`
- `backend/app/services/v2_project_service.py`
- `backend/tests/test_pilot_boundary.py`
- `frontend/app/app/layout.tsx`
- `frontend/app/app/pilot-boundary.test.tsx`
- `frontend/lib/app-routes.ts`
- `frontend/middleware.ts`
- `frontend/middleware.test.ts`
- This internal implementation/verification record.

## Scope integrity

No landing narrative/animation, informational-page copy/design, statistics, public header/footer, signup/login behavior, schema, migration, retention, deletion, age/consent/school screens, legal pages, new AI functionality, or Phase 11 work changed. No Phase 7.6C-3 work began. This implements only deployment-level feature isolation; the other approved defaults and adult/school/legal prerequisites are not implemented or satisfied by it.

## Remaining demonstrated risks and activation requirements

1. Nothing hosted has been enabled or verified. A later separately authorized staging deployment must ship this backend and frontend, set the backend flag, restart all instances, verify the deployed SHA and `/deployment-mode`, and check every legacy endpoint/provider path and frontend URL against the actual host. Verify V2 authenticated Build/Recovery, project-picker filtering, public pages, login/signup, and allowed-origin CORS there. Do not enroll students based only on this local record.
2. This is deployment-wide: enabling it disables V1 for every account on that backend, including non-pilot testers. Such testers need an ordinary deployment. It does not ban an account from separate non-pilot backends or implement a global account permission system.
3. Frontend middleware needs a reachable backend mode endpoint. An older backend lacking it, an outage, or an incorrect API origin yields 503 only for legacy frontend routes. Release coordination is required even on ordinary deployments. V2/API security does not depend on the frontend lookup.
4. An already-open V1 browser tab may retain its old interface until navigation/reload, but its backend requests are still blocked after all backend instances restart in pilot mode. Existing V1 data is neither removed nor migrated.
5. Resolve the demonstrated baseline test failures separately. Future router/provider additions require maintaining and reviewing this explicit legacy/V2 classification. Provider-blocking tests protect the current HTTP boundary, not arbitrary future background workers.
6. Real enrollment still requires the adult/school/legal approvals and other readiness work specified by the user. WCAG 2.2 AA remains a development target, not a conformance claim.

## Commit and production isolation

One focused local commit is required; its SHA is reported in the implementation chat after creation. Nothing is pushed or deployed. No hosted configuration, provider setting, production service, database or account was changed.

**Production mutations were ZERO.**

## Ready for independent security-focused review

**YES** — focused boundary checks pass; baseline failures and runtime/hosted verification limits are explicitly recorded. This is readiness for review, not authorization to deploy or launch.
