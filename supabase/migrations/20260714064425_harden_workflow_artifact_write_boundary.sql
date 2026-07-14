-- M16S.1: Workflow Artifact Write-Boundary Hardening.
--
-- All Codize product writes are mediated by authenticated FastAPI routes. The
-- browser uses Supabase directly for Auth only, so authenticated Data API
-- clients need owner-scoped reads on projects but no table mutation rights.
-- RLS continues to decide which rows an authenticated owner may read; grants
-- independently make the table read-only to that role.
--
-- This closes direct INSERT, UPDATE/PATCH, UPSERT, DELETE, TRUNCATE, and other
-- table-level mutation paths, including complete or partial replacement of
-- projects.workflow_artifacts. The service_role ACL is intentionally untouched
-- so the owner-filtered FastAPI repository retains its existing write access.
revoke all privileges on table public.projects from authenticated;
grant select on table public.projects to authenticated;

-- anon already has no projects privileges and remains unchanged. Existing
-- owner write policies are intentionally retained as inert defense in depth:
-- PostgreSQL requires both an object privilege and an RLS policy, and the
-- authenticated role no longer has any object privilege that can mutate rows.
--
-- Rollback consideration: if a future product milestone introduces a genuine
-- direct browser write, add a new forward migration granting only the required
-- column(s) or a narrowly reviewed RPC. Do not restore broad table mutation.
