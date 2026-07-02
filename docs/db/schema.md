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
  - **Reconnection tracking** — `profiles.last_login_at` (modal fires on login
    when delta > 72h; shows `projects.intake_purpose` verbatim).
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
| `current_phase` | smallint 1–7 | |
| `gate_history_summary` | text | summarized transcripts; calibrates future gates |
| `status` | 'intake' \| 'active' \| 'completed' | |

Policies: owner select / insert / update / delete.

### `gate_sessions` — one row per Interrogation Gate attempt
Shape pinned by the roadmap (`id, project_id, phase_id, user_id,
anchor_statement, turns jsonb, score 0–10, passed, failed_at, created_at`) plus
`reason` (the evaluator's one-sentence verdict reason the student is shown).

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
