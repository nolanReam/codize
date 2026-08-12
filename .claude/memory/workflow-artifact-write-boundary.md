# Workflow artifact write boundary (Milestone 16S.1)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

## The discovered integrity issue

Ownership RLS and write integrity are separate controls. The existing
`projects_update_own` policy correctly kept users out of one another's rows,
but live ACL inspection showed that `authenticated` also held table-level
`INSERT`, `UPDATE`, and `DELETE` (plus the broad default table privileges) on
`public.projects`. An owner could therefore use Supabase/PostgREST directly to
replace the owner's `workflow_artifacts` JSONB and bypass FastAPI validation.
This was not a cross-user disclosure; it was an integrity failure inside the
owner's row.

The bypass could forge server timestamps, Change Map origin/source bindings,
deterministic ids, confirmation state, linked Review/Verification provenance,
staleness inputs, protected snapshots, and arbitrarily shaped section data.
FastAPI validation alone was insufficient while another database path could
write the same column.

## Actual architecture and complete project-write inventory

The frontend Supabase client is Auth-only. Repository-wide search found no
frontend `.from(...)`, direct `/rest/v1/`, `.insert`, `.update`, `.upsert`,
`.delete`, or `.rpc` product-data call. Every product write uses an
authenticated FastAPI route, then `SupabaseProjectRepository` with the trusted
server credential and both `id` and JWT-derived `user_id` filters:

- intake creates the project on Q1 and updates five answers;
- intake completion writes `archetype_id` and `intake_completed_at`;
- roadmap writes `roadmap`, optional `stack_warning`, and `status`;
- phase tasks write `task_progress`;
- gate PASS writes `current_phase` and `gate_history_summary`;
- workflow routes write `workflow_artifacts` for Prompt Builder,
  Implementation Import, Change Map, Review, Evidence, and Verification;
- database defaults/trigger manage `id`, `created_at`, and `updated_at`.

There is no FastAPI project-delete route and no frontend delete behavior.
Before M16S.1 only direct authenticated PostgREST deletion existed; it was
unused and could cascade-destroy workflow state. M16S.1 removes it.

## Column authority

All project columns remain readable to their owner. No project column is
intentionally client-writable.

- **Backend-only writable:** `user_id`; the five intake fields;
  `intake_completed_at`; `archetype_id`; `stack_warning`; `roadmap`;
  `current_phase`; `task_progress`; `workflow_artifacts`;
  `gate_history_summary`; `status`.
- **System-managed:** `id`, `created_at`, `updated_at`.
- **Client-writable:** none.

## Selected enforcement

Forward migration
`20260714064425_harden_workflow_artifact_write_boundary.sql` does exactly:

1. `REVOKE ALL PRIVILEGES ON TABLE public.projects FROM authenticated`;
2. `GRANT SELECT ON TABLE public.projects TO authenticated`.

RLS stays enabled and all existing owner policies remain. The write policies
are inert defense in depth because Postgres requires both a table/column
privilege and an RLS policy. `anon` remains without access. `service_role`,
table ownership, triggers, functions, data, and schema shape are untouched.
The backend continues to enforce semantic ownership itself because its trusted
credential bypasses RLS.

Column grants were considered but rejected because the inventory found zero
legitimate browser-writable project columns. A protective trigger, separate
table, or RPC would add machinery without preserving any required client write.
Read-only authenticated table access is the smallest correct mechanism.

## Alternate paths

Live inspection found no `public`/`api` views. The only public functions are
`handle_new_user()` and `set_updated_at()`; both have `EXECUTE` revoked from
`PUBLIC`, `anon`, and `authenticated`. The only project trigger invokes
`set_updated_at()` and changes only the system-managed timestamp. No exposed
RPC, writable view, SECURITY DEFINER project function, or other table rewrites
projects/workflow artifacts. PostgREST CRUD therefore follows the projects ACL
directly.

## Verification and deployment

- `scripts/verify_workflow_artifact_write_boundary.sql` is a rollback-only
  effective-role test for owner reads; full/partial/concat/mixed JSONB writes;
  insert/upsert/delete; cross-user and anonymous isolation; trusted writes;
  sibling preservation; RLS; views/functions; and cleanup.
- `scripts/verify_workflow_artifact_write_boundary.py` exercises real Auth,
  PostgREST, trusted backend access, and a FastAPI Prompt Builder save with
  temporary users deleted in `finally`.
- Backend workflow route/service tests cover Prompt Builder, Import, Change
  Map, Review, Verification, phase/owner isolation, Evidence, Defense, and
  roadmap compatibility. Frontend checks confirm no UI/API compatibility
  change.

The linked `Codize` Supabase project is the shared hosted friend-pilot database
with existing users/projects, not a known-safe development/test branch. M16S.1
was not applied remotely during implementation. Until a deliberate deployment
and passing effective checks, the live vulnerability remains. After deployment:

1. run the SQL verifier as one batch;
2. run the authenticated HTTP/FastAPI smoke against the same environment;
3. run the existing auth/RLS tools and security advisors;
4. confirm temporary rows/users are zero.

Rollback is another forward migration. Never restore broad table DML. If a
future feature genuinely needs direct Supabase product-data writes, document
the caller and ownership first, then grant only the required column or add a
narrow reviewed RPC with explicit authorization.

Permanent rule: **New server-owned workflow fields must be protected at both
the FastAPI semantic layer and the database authorization boundary.**
