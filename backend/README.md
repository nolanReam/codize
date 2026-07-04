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
│                  unlocks — auth-required earned-unlock listing, M10;
│                  reconnection — auth-required 72h reconnection state, M11;
│                  evaluation — auth-required progress evaluation, M12;
│                  workflow — auth-required workflow artifact store, M13B)
├── services/      product logic (template_service.py: archetype template engine, M5;
│                  intake_service.py + project_repository.py: intake engine, M6
│                  — project_repository.py also holds the gate_sessions
│                  repository since M9;
│                  llm_service.py + roadmap_service.py: provider-agnostic LLM
│                  layer and roadmap generation with fail-closed validation, M7;
│                  phase_service.py: phase workspace over the stored roadmap, M8;
│                  gate_service.py: 3-turn Interrogation Gate + evaluator, M9;
│                  unlock_service.py: hidden-threshold functional unlocks, M10;
│                  reconnection_service.py: Yeager reconnection engine, M11;
│                  evaluation_service.py: deterministic progress evaluation, M12;
│                  workflow_service.py: workflow artifact store, M13B)
├── schemas/       request/response models (intake.py, phases.py, gate.py, workflow.py)
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

## Reconnection (M11)

`services/reconnection_service.py` implements the spec's Yeager reconnection
mechanic server-side (the modal itself is frontend work, M13). Timestamp
semantics: `profiles.last_login_at` means "last acknowledged presence" — it is
initialized by the signup trigger's `default now()` (so a brand-new user never
sees the modal) and thereafter written ONLY by
`POST /reconnection/acknowledge`. `GET /reconnection` is a pure read that
returns one of four controlled states: `new_user` (no profile/timestamp),
`recently_active` (away < 72h), `workspace_not_ready` (away 72h+ but no
active project/roadmap yet), or `reconnection` (away 72h+) with a safe,
deterministic summary — the verbatim intake purpose (spec requirement),
current phase number/title/concept reminder, the incomplete current-phase
tasks, the newest gate-history line (attempt counts only — never scores),
earned unlock views, and a recommended next action. No LLM call. Frontend
contract: GET first on every login, then acknowledge — immediately when
`reconnection_needed` is false, on the "Let's keep building" click when true
(acknowledging before the GET would suppress the modal). Reconnection never
mutates the roadmap, never advances phases, never grants unlocks, and its
responses carry no scores, thresholds, prompts, or server-only keys.

## Evaluation (M12)

`services/evaluation_service.py` produces a student-facing progress
evaluation for the caller's current project: `GET /evaluation` returns one
controlled 200 state — `not_started`, `intake_needed`, `roadmap_needed`,
`in_progress`, `gate_ready` (all tasks checked off, or a gate session
mid-flight), `cooldown` (with `cooldown_seconds_remaining`), or `complete`
(final phase's gate passed) — never an error. The evaluation is deterministic
and computed on read: no LLM call, no persistence, no schema change (the spec
defines no evaluation snapshot, and its tracking section forbids showing
process metrics as numbers or scores). Content is derived only from
client-visible state via the shared safe-view seams: the current phase view
(`phase_service.current_phase_view` / `incomplete_tasks`), phase/task counts,
the newest `gate_history_summary` line or the evaluator's one-sentence reason
as a `recent_gate` label (never a score), earned unlock views
(`unlock_service.unlock_views`), and a recommended `next_action`. Cooldown
state reuses the gate's own derivation (`gate_service.cooldown_remaining`).
Evaluation is a pure read — it never mutates the roadmap, task progress,
gates, or unlocks, never advances phases, and never touches reconnection's
`last_login_at`.

## Workflow artifacts (M13B)

`services/workflow_service.py` stores the four student-authored v3 Build Loop
sections — `prompt_builder`, `review_board`, `evidence`, `verification` —
phase-scoped, in the `projects.workflow_artifacts` JSONB column
(task_progress precedent: outside the roadmap jsonb, so storing artifacts can
never mutate the fixed structure). Storage only: no LLM call, no gate
involvement, no report generation — the Interrogation Gate does not read
these artifacts (wiring them into gate prompts is a future,
spec-guardian-reviewed change), and the M13C frontend assembles the Project
Defense Report client-side from this route plus the existing ones. Routes:
`GET /workflow/{phase}` (all four sections, `null` when unset) and
`PUT /workflow/{phase}/{section}` (idempotent full-section replace; payloads
validated fail-closed by `schemas/workflow.py` — extra fields forbidden,
strings/lists capped, URL and commit-hash evidence format-checked, free text
that looks like an API key rejected, 30 KB total-size cap; the server stamps
`saved_at`). Eligibility mirrors the phase workspace (active project +
roadmap; unknown phase/section → 404, workspace not ready → 409, invalid
payload → 422). A write touches exactly one column; unknown keys in stored
data are dropped on read.

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
