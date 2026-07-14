-- Codize RLS audit — run via the Supabase MCP (execute_sql) or SQL editor.
-- Re-run after ANY schema change. Expected results are stated per section;
-- anything else is a security regression.
--
-- Sections 4-9 are the behavioral tests. They simulate PostgREST roles with
-- `set local role` + request.jwt.claims. Sections 6-9 EXPECT a permission
-- error, so run each section as its own statement batch (an expected error
-- aborts the batch it runs in).

-- ---------------------------------------------------------------------------
-- 1. Every public table must have RLS enabled (expect: zero rows)
-- ---------------------------------------------------------------------------
select c.relname as table_without_rls
from pg_class c
join pg_namespace n on c.relnamespace = n.oid
where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;

-- ---------------------------------------------------------------------------
-- 2. Every policy must check ownership, not just login
--    (expect: every row's using/with_check expr is exactly (auth.uid() = user_id))
-- ---------------------------------------------------------------------------
select c.relname as table_name, p.polname as policy, p.polcmd as cmd,
       pg_get_expr(p.polqual, p.polrelid) as using_expr,
       pg_get_expr(p.polwithcheck, p.polrelid) as with_check_expr
from pg_class c
join pg_namespace n on c.relnamespace = n.oid
join pg_policy p on p.polrelid = c.oid
where n.nspname = 'public'
order by c.relname, p.polname;

-- ---------------------------------------------------------------------------
-- 3. gate_sessions.score must not be readable by client roles
--    (expect: zero rows — no column grant on score for anon/authenticated)
-- ---------------------------------------------------------------------------
select grantee, privilege_type
from information_schema.column_privileges
where table_schema = 'public' and table_name = 'gate_sessions'
  and column_name = 'score' and grantee in ('anon', 'authenticated');

-- ---------------------------------------------------------------------------
-- 4. Behavioral setup: two throwaway users + one project and gate row each.
--    The signup trigger must auto-create both profiles (expect: 2).
--    ALWAYS run section 10 afterwards to clean up.
-- ---------------------------------------------------------------------------
insert into auth.users (instance_id, id, aud, role, email, encrypted_password,
                        email_confirmed_at, created_at, updated_at,
                        raw_app_meta_data, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-000000000000', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
   'authenticated', 'authenticated', 'rls-test-a@example.com', '', now(), now(), now(),
   '{"provider":"email","providers":["email"]}', '{}'),
  ('00000000-0000-0000-0000-000000000000', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
   'authenticated', 'authenticated', 'rls-test-b@example.com', '', now(), now(), now(),
   '{"provider":"email","providers":["email"]}', '{}');

insert into public.projects (id, user_id, intake_purpose)
values
  ('aaaaaaaa-0000-4000-8000-000000000001', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'test purpose A'),
  ('bbbbbbbb-0000-4000-8000-000000000001', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'test purpose B');

insert into public.gate_sessions (project_id, phase_id, user_id, score, passed, reason)
values
  ('aaaaaaaa-0000-4000-8000-000000000001', 1, 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 8, true, 'test A'),
  ('bbbbbbbb-0000-4000-8000-000000000001', 1, 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 3, false, 'test B');

select count(*) as profiles_auto_created  -- expect 2
from public.profiles
where user_id in ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');

-- ---------------------------------------------------------------------------
-- 5. Wrong-user isolation as user A
--    (expect: 1, 0, 1, 1, 0 — A sees only own rows)
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","role":"authenticated"}', true);

select
  (select count(*) from public.projects)                     as projects_visible,       -- 1
  (select count(*) from public.projects
     where user_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') as b_projects_visible,     -- 0
  (select count(*) from public.profiles)                     as profiles_visible,       -- 1
  (select count(*) from public.gate_sessions)                as gate_sessions_visible,  -- 1
  (select count(*) from public.unlocks)                      as unlocks_visible;        -- 0

-- ---------------------------------------------------------------------------
-- 6. EXPECT ERROR 42501: project rows are owner-readable but browser read-only
--    after M16S.1. This blocks own-row workflow replacement and all project
--    updates before RLS row filtering is considered.
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","role":"authenticated"}', true);
update public.projects
set workflow_artifacts = '{"forged":true}'::jsonb
where id = 'aaaaaaaa-0000-4000-8000-000000000001';

-- ---------------------------------------------------------------------------
-- 7. EXPECT ERROR 42501: student must never read gate scores
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","role":"authenticated"}', true);
select score from public.gate_sessions;

-- ---------------------------------------------------------------------------
-- 8. EXPECT ERROR 42501: student cannot write gate verdicts or forge unlocks
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","role":"authenticated"}', true);
insert into public.gate_sessions (project_id, phase_id, user_id, passed)
values ('aaaaaaaa-0000-4000-8000-000000000001', 2, 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', true);
-- and separately:
-- insert into public.unlocks (user_id, project_id, phase_number, unlock_key)
-- values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'aaaaaaaa-0000-4000-8000-000000000001', 1, 'forged');

-- ---------------------------------------------------------------------------
-- 9. EXPECT ERROR 42501: anon gets nothing
-- ---------------------------------------------------------------------------
set local role anon;
select count(*) from public.projects;

-- ---------------------------------------------------------------------------
-- 10. Cleanup (cascades to profiles/projects/gate_sessions). Expect all zeros.
-- ---------------------------------------------------------------------------
delete from auth.users
where id in ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');

select
  (select count(*) from public.profiles)      as profiles_left,
  (select count(*) from public.projects)      as projects_left,
  (select count(*) from public.gate_sessions) as gate_sessions_left,
  (select count(*) from public.unlocks)       as unlocks_left,
  (select count(*) from auth.users where email like 'rls-test-%') as test_users_left;
