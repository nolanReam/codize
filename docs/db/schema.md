# Codize Database Schema (Milestone 2)

Supabase project: `tadkbymxkdncqahzshml` (Postgres 17). Applied migrations live in
`supabase/migrations/` and mirror what was applied via MCP on 2026-07-02.
Audit queries: `scripts/verify_rls.sql`.

Note: this project previously held an unrelated legacy schema (20 empty tables,
migrations 001–010 from 2026-06-16). It was dropped with owner approval in
`20260702070843_drop_legacy_schema.sql`, including its `on_auth_user_created`
trigger and `ensure_rls` event trigger.

## Design principles

- The frontend never talks to Supabase directly except for Auth; all data goes
  Frontend → FastAPI backend → Supabase using the **service role** (bypasses
  RLS). RLS policies exist as defense-in-depth against the public anon key.
- Every table has RLS enabled **in the same migration that creates it** and a
  `user_id` column with ownership policies `USING (auth.uid() = user_id)` —
  never mere login checks.
- Simplest schema that satisfies the spec: 4 tables. Things deliberately **not**
  tables:
  - **Cooldowns** — derived from `gate_sessions.failed_at` (roadmap-pinned:
    gate start checks `now() - failed_at > interval '30 minutes'`, else 429).
  - **Intake answers / archetype classification** — five fixed columns +
    `archetype_id` on `projects` (exactly five questions, exactly three
    archetypes; a join table would model flexibility the spec forbids).
  - **Phase progress** — `projects.current_phase` plus passed `gate_sessions`
    rows; phases themselves are fixed by the hardcoded archetype templates.
    Task checkboxes (M8) are `projects.task_progress` jsonb — kept outside the
    `roadmap` jsonb so ticking tasks can never mutate the fixed structure.
  - **Reconnection tracking** — `profiles.last_login_at` (modal fires on login
    when delta ≥ 72h; shows `projects.intake_purpose` verbatim). Semantics
    pinned in M11: the column means "last acknowledged presence" — set at
    signup by its `default now()`, thereafter written only by
    `POST /reconnection/acknowledge` (never by `GET /reconnection`, which is a
    pure read). No schema change was needed.
  - **Session/logging metadata** — not required by the spec MVP; add only when
    a milestone needs it.

## Tables

### `profiles` — one row per auth user
Auto-created by the `on_auth_user_created` trigger (`handle_new_user()`,
SECURITY DEFINER, `search_path = ''`, EXECUTE revoked from client roles).

| column | type | notes |
|---|---|---|
| `user_id` | uuid PK → `auth.users` | ownership key |
| `display_name` | text | |
| `last_login_at` | timestamptz | drives 72h reconnection modal |
| `created_at` / `updated_at` | timestamptz | `updated_at` via trigger |

Policies: owner select / insert / update. No delete (account deletion cascades
from `auth.users`).

### `projects` — one row per student project
| column | type | notes |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid → `auth.users` | ownership key |
| `intake_purpose` | text | verbatim Q1 answer; re-shown by reconnection modal |
| `intake_scope`, `intake_stack`, `intake_self_assessment`, `intake_timeline` | text | Q2–Q5, nullable while the conversational intake is in progress |
| `intake_completed_at` | timestamptz | set when all five answers stored |
| `archetype_id` | smallint ∈ {1,2,3} | temp-0 classification result |
| `stack_warning` | text | roadmap prompt's >30% language-gap warning |
| `roadmap` | jsonb | personalized roadmap (template structure, LLM wording) |
| `current_phase` | smallint 1–7 | advanced by gate passes (M9), never by task completion |
| `task_progress` | jsonb, default `{}` | M8 phase workspace: `{"<phase>": ["ai-1", "human-2", …]}` — completed task ids per phase, backend-written only |
| `workflow_artifacts` | jsonb, default `{}` | M13B workflow store: `{"<phase>": {"prompt_builder": {…}, "review_board": {…}, "evidence": {…}, "verification": {…}}}` — student-authored Build Loop artifacts, validated + size-capped by the backend |
| `gate_history_summary` | text | summarized transcripts; calibrates future gates |
| `status` | 'intake' \| 'active' \| 'completed' | |

Policies: owner select / insert / update / delete.

### `gate_sessions` — one row per Interrogation Gate attempt
Shape pinned by the roadmap (`id, project_id, phase_id, user_id,
anchor_statement, turns jsonb, score 0–10, passed, failed_at, created_at`) plus
`reason` (the evaluator's one-sentence verdict reason the student is shown) and
`passed_at` (M9 migration `20260703040000_add_passed_at_to_gate_sessions.sql`;
granted to `authenticated` — `score` stays revoked). `turns` holds
`[{"turn": 1|2|3, "question", "answer"}, …]`, written only by the backend.

**Owner read-only by design.** Only the backend writes gate rows — students
must not author their own verdicts — so there are no insert/update/delete
policies. Additionally, **the `score` column is revoked from `anon` and
`authenticated`** (column-level grant lists every column except `score`):
functional-unlock thresholds must never be observable by the student.
`failed_at` drives the 30-minute cooldown.

### `unlocks` — functional unlocks granted by the backend
`id, user_id, project_id, phase_number 1–7, unlock_key, granted_at`, unique on
`(project_id, unlock_key)`.

**Owner read-only by design** — unlocks are triggered by hidden thresholds
(e.g. score ≥ 7 across two consecutive gates) computed server-side; students
can see what they earned but cannot insert/update/delete.

## Verification record (2026-07-02, via Supabase MCP)

- RLS enabled on all 4 tables; 9 policies, every expression exactly
  `(auth.uid() = user_id)` (structural dump).
- Behavioral two-user test: user A saw only their own rows in all tables
  (1/0/1/1/0), update of B's project affected 0 rows.
- `select score from gate_sessions` as authenticated → `42501 permission denied` ✓
- Insert into `gate_sessions` / `unlocks` as authenticated → `42501` ✓
- `select` as `anon` on `projects` → `42501` ✓
- Signup trigger auto-created both test profiles; test users deleted, cascade
  left zero rows.
- Security advisors: clean except **leaked-password protection disabled** — an
  Auth dashboard setting, to be enabled in Milestone 3 (Auth).

## Verification record (M9 session, 2026-07-02)

- `passed_at` added to `gate_sessions`; column grants re-dumped: `authenticated`
  can select every column **except `score`** (still revoked), `anon` none.
- Security advisors: clean (no lints).
- `scripts/verify_auth.py`: **11/11 PASS over the live Auth + PostgREST APIs**
  with the newer `sb_publishable_...` key (keys are opaque to the scripts and
  backend — no JWT-shape assumption anywhere).
- Live backend writes through PostgREST with the `sb_secret_...` key verified
  end-to-end: project create/update, roadmap JSONB + status flip, gate session
  create/update, `current_phase` advancement — all ownership-filtered.
- Live JWKS verification of a real Supabase JWT (ES256, `aud=authenticated`)
  through `app/core/security.py`: PASS.

## Verification record (M10 session, 2026-07-03)

No schema change — the M2 `unlocks` table carried M10 as designed. Live smoke
test (10/10) with the verify_auth.sql test users: unlock granted through
`unlock_service.evaluate_unlocks` after two consecutive qualifying passed
gates (scores 8, 7); re-evaluation idempotent; a duplicate insert ignored by
the unique `(project_id, unlock_key)` constraint via PostgREST
`resolution=ignore-duplicates` (returns no row); ownership filtering verified
at the repo layer; RLS verified through the client path (user A reads own
unlock with a real JWT + anon key, user B sees zero rows, and the row exposes
no score field). `scripts/verify_auth.py` re-run: 11/11 PASS (includes the
unlock-forgery 42501 check). Security advisors: clean. Test users deleted;
cascade left zero rows in all four tables.

## Verification record (M11 session, 2026-07-03)

No schema change — `profiles.last_login_at` (M2) carried M11 as designed. Live
smoke test (12/12) with the verify_auth.sql test users: signup-trigger profile
readable with a fresh timestamp → `recently_active`; backdated 100h without a
roadmap → controlled `workspace_not_ready`; with an active project →
`reconnection` with the safe summary (verbatim purpose, phase context,
incomplete tasks, gate-history line, unlock view; JSON contains no
score/threshold strings); double acknowledge idempotent and clears the state;
user B's state independent of A's; RLS client path with real JWTs + anon key
(each user reads exactly their own `profiles` row). `scripts/verify_auth.py`
re-run: 11/11 PASS. Security advisors: clean. Test users deleted; cascade left
zero rows in all four tables.

## Verification record (M12 session, 2026-07-03)

No schema change — the evaluation system (M12) is computed on read from
existing tables; nothing new is persisted. Live smoke test (12/12) with the
verify_auth.sql test users: readiness states tracked the full project
lifecycle (`not_started` → `intake_needed` → `roadmap_needed` →
`in_progress`); a live task tick reflected in the summary; two consecutive
qualifying passed gates (scores 8, 7) seeded through the real gate repo
granted an unlock the evaluation surfaced safely; a fresh FAIL produced the
`cooldown` state with a bounded retry window; evaluation JSON contained no
score/threshold strings; a before/after project-row comparison confirmed the
evaluation is a pure read; user B saw only their own state.
`scripts/verify_auth.py` re-run: 11/11 PASS. Security advisors: clean. Test
users deleted; cascade left zero rows in all four tables.

## Verification record (M13B session, 2026-07-03)

- Migration `20260703130000_add_workflow_artifacts_to_projects.sql` applied via
  MCP: `projects.workflow_artifacts jsonb not null default '{}'::jsonb`
  (task_progress precedent — table-level grants, existing owner RLS policies
  cover the column; no new policies needed).
- Live smoke 11/11 against the real project: pre-existing row picked up the
  `{}` default; all four sections round-trip through the real
  `SupabaseProjectRepository`; full-section replace + phase isolation;
  oversized/secret-marker/unknown-phase payloads rejected with nothing stored;
  live row diff after writes touched only `workflow_artifacts`; owner read the
  column through PostgREST with a real JWT; user A saw zero of user B's rows
  and vice versa; client payload leak-free.
- `verify_auth.py` 11/11 PASS (SETUP/CLEANUP via MCP; cleanup left zero rows
  in all four tables and zero test users).
- Security advisors after the migration: clean (`{"lints": []}`).
