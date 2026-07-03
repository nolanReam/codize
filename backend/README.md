# Codize backend (FastAPI)

Async FastAPI service. Architecture rule: **Frontend → this backend → external
services (Supabase, LLM providers)** — the frontend never calls external
services directly except Supabase Auth. Route handlers stay thin; product logic lives in
`app/services/` (from Milestone 5 on).

## Layout

```
app/
├── main.py        app factory + CORS + error handlers
├── core/
│   ├── config.py    centralized settings (SecretStr for server-only values)
│   ├── errors.py    consistent JSON error shape, no internal detail leaks
│   └── security.py  Supabase JWT verification (JWKS / ES256)
├── deps/auth.py   require_user dependency → 401 on missing/invalid token
├── routers/       thin route handlers (health; archetypes — auth-required, read-only;
│                  intake — auth-required five-question flow, M6;
│                  roadmap — auth-required generation + read, M7;
│                  phases — auth-required phase workspace, M8;
│                  gate — auth-required Interrogation Gate, M9;
│                  unlocks — auth-required earned-unlock listing, M10)
├── services/      product logic (template_service.py: archetype template engine, M5;
│                  intake_service.py + project_repository.py: intake engine, M6
│                  — project_repository.py also holds the gate_sessions
│                  repository since M9;
│                  llm_service.py + roadmap_service.py: provider-agnostic LLM
│                  layer and roadmap generation with fail-closed validation, M7;
│                  phase_service.py: phase workspace over the stored roadmap, M8;
│                  gate_service.py: 3-turn Interrogation Gate + evaluator, M9;
│                  unlock_service.py: hidden-threshold functional unlocks, M10)
├── schemas/       request/response models (intake.py, phases.py, gate.py)
├── templates/     the three archetype JSON templates (Milestone 1)
└── prompts/       the six system prompts (Milestone 1)
tests/             pytest suite
```

## Setup & run

From `backend/`:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # (Windows; use .venv/bin/pip elsewhere)
.venv\Scripts\uvicorn app.main:app --reload
```

Configuration comes from environment variables or a `.env` file in the working
directory — see the repo-root `.env.example` for the contract. Never commit a
real `.env`; server-only values (`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`,
`OPENROUTER_API_KEY`) exist only in the backend environment.

## LLM providers (M7)

All LLM calls go through `services/llm_service.py`. Provider order: Gemini
primary (`GEMINI_API_KEY`, `GEMINI_MODEL`), OpenRouter fallback
(`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`), deterministic stub when no live key
is configured (tests and local no-key mode only — never a silent fallback for a
failing live provider). `LLM_PROVIDER` names the primary. Anthropic is
intentionally not supported. Whatever the provider, a generated roadmap is
validated against the source archetype template and discarded on any
structural drift.

## Phase workspace (M8)

`services/phase_service.py` serves phases straight from the stored roadmap
JSONB (the personalized content generated in M7) — no LLM call; the
`phase_explanation.md` prose call is deliberately not wired up yet. Eligibility
is intake complete + archetype + roadmap + status `active`. Task completion is
tracked per phase in the separate `projects.task_progress` column as
`{"<phase>": ["ai-1", "human-2", …]}` (1-based index into the phase's task
lists), so marking tasks complete can never mutate the fixed roadmap
structure. `current_phase` is advanced by the Interrogation Gate (M9), never
by ticking tasks. Routes: `GET /phases`, `GET /phases/current`,
`GET /phases/{n}`, `PATCH /phases/{n}/tasks/{task_id}` (body
`{"completed": bool}`); workspace not ready → 409, unknown phase/task → 404.

## Interrogation Gate (M9)

`services/gate_service.py` runs the spec's 3-turn gate for the student's
current phase. Flow: `POST /gate/start` (eligibility: active project + roadmap
+ current phase; 30-minute cooldown after a failed attempt, derived from
`gate_sessions.failed_at`) → `POST /gate/{id}/turn1` (body
`{"anchor_statement"}`; a deterministic server check plus model re-validation
reject anchors with no concrete implementation element — the gate never starts
without an anchor) → `POST /gate/{id}/turn2` and `/turn3` (body `{"answer"}`;
each stores the previous answer and returns the next question in one write, so
LLM failures are retryable with nothing lost) → `POST /gate/{id}/evaluate`
(separate temperature-0 call; strict fail-closed JSON parse). Turns run at
temperature 0.3, prompts from `app/prompts/gate_turn_*.md` /
`gate_evaluation.md`. On PASS: `passed_at` set, `projects.current_phase`
advances (never past the final phase), `gate_history_summary` appended. On
FAIL: `failed_at` set, cooldown starts, no advancement. `GET /gate/current`
reports the current phase's gate state (not started / in progress with
transcript / cooldown with remaining seconds / passed). The evaluator's 0–10
quality score is stored for the hidden unlock thresholds (consumed server-side
by M10's unlock service) and never appears in any response; the DB
additionally revokes the column from client roles.
Errors: not ready / in progress / already passed / out of order / cooldown →
409 (cooldown adds Retry-After), unknown session → 404, invalid anchor → 422,
LLM failure or malformed verdict → 502 with nothing stored.

## Functional unlocks (M10)

`services/unlock_service.py` implements the spec's variable-reward mechanic:
after every gate PASS (never a FAIL), the gate flow calls the unlock
evaluation, which recomputes earned unlocks from the project's passed-gate
history — the hidden rule is a quality score at the qualifying threshold on
two consecutive phases' passed gates (spec: ≥7; only the passing attempt's
score counts). Qualifying at phase N grants roadmap phase N's
`functional_unlock` reward (template content that skips configuration work or
provides a pre-built component). Grants are idempotent (recompute + the DB's
unique `(project_id, unlock_key)` with PostgREST ignore-duplicates) and
self-healing — an unlock storage error never fails the PASS response; the
next PASS backfills. Unlocks never mutate the roadmap and never advance
phases. Routes: `GET /unlocks` lists what the user earned on their current
project (safe fields only: id, unlock_key, phase, description, unlocked_at,
project_id); a PASS's `new_unlocks` appears in the evaluate response. The
threshold, the rule, and raw scores are server-only and appear in no response
(the `unlocks` table itself is owner read-only with client writes revoked).

## Tests

```bash
.venv\Scripts\python -m pytest
```

Auth tests sign tokens with a locally generated ES256 key and stub only the
JWKS fetch, so the full verification path runs offline. Live verification of a
real Supabase JWT additionally requires `SUPABASE_URL` (used to derive the
JWKS URL: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`).

## Auth model (docs/auth.md)

- Frontend sends `Authorization: Bearer <supabase access token>` on every request.
- `require_user` verifies the token server-side (signature via JWKS, `exp`,
  `aud == "authenticated"`) and exposes `CurrentUser` with `user_id = sub`.
- Missing/invalid token → **401**. Wrong-user resource → **403/404**, decided
  per endpoint in the service layer (the backend uses the service-role key,
  which bypasses RLS, so every user-scoped query must filter by
  `user_id == sub` itself).
- UI hiding is never security; every protected endpoint enforces this
  dependency.
