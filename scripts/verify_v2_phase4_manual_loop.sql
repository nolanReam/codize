-- Phase 4 verification for an isolated, freshly migrated PostgreSQL 17 database.
begin;

do $$
declare v_commands constant text[] := array[
  'establish_v2_manual_project', 'confirm_v2_manual_current_change',
  'record_v2_manual_return', 'record_v2_manual_check', 'update_v2_dialogue_sound'
];
begin
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace = 'public'::regnamespace and p.proname = any(v_commands)
        and not p.prosecdef and p.proconfig @> array['search_path=""']
        and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')) <> 5 then
    raise exception 'Phase 4 public wrappers are not safely granted';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace = 'codize_v2_internal'::regnamespace
        and p.proname = any(v_commands) and p.prosecdef
        and p.proconfig @> array['search_path=""']
        and pg_catalog.pg_get_userbyid(p.proowner) = 'codize_v2_executor'
        and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')) <> 5 then
    raise exception 'Phase 4 internal commands are not safely owned and granted';
  end if;
  if exists (select 1 from pg_catalog.pg_class as c
      where c.relnamespace = 'public'::regnamespace and c.relname like 'v2\_%' escape '\'
        and c.relkind = 'r' and not c.relrowsecurity) then
    raise exception 'a V2 table lost RLS';
  end if;
end $$;

insert into auth.users (id) values
  ('f4000000-0000-4000-8000-000000000001');

set local role service_role;
do $$
declare
  v_owner constant uuid := 'f4000000-0000-4000-8000-000000000001';
  v_item constant uuid := 'f4000000-0000-4000-8000-000000000201';
  v_check_one constant uuid := 'f4000000-0000-4000-8000-000000000301';
  v_check_two constant uuid := 'f4000000-0000-4000-8000-000000000302';
  v_check_three constant uuid := 'f4000000-0000-4000-8000-000000000303';
  v_project uuid;
  v_change uuid;
  v_prompt uuid;
  v_result jsonb;
  v_version bigint;
begin
  v_result := public.create_v2_project(
    v_owner, 'f4000000-0000-4000-8000-000000000101',
    'Phase 4 verifier', 'new_idea', null, null);
  v_project := (v_result -> 'project' ->> 'id')::uuid;

  v_result := public.establish_v2_manual_project(
    v_owner, v_project, 1, 'f4000000-0000-4000-8000-000000000102',
    'A resumable student project', v_item, 'Add one visible score',
    'Adding a point visibly changes the score');
  if (v_result ->> 'replayed')::boolean
     or (v_result -> 'project' ->> 'version')::bigint <> 2 then
    raise exception 'manual setup did not establish one canonical Project';
  end if;

  -- Simulate response loss plus a new browser process: both command-owned IDs
  -- are fresh, while the submitted setup payload and explicit Project are the
  -- same. The durable state must win without adding a second item/version.
  v_result := public.establish_v2_manual_project(
    v_owner, v_project, 1, 'f4000000-0000-4000-8000-000000000103',
    'A resumable student project', 'f4000000-0000-4000-8000-000000000202',
    'Add one visible score', 'Adding a point visibly changes the score');
  if not (v_result ->> 'replayed')::boolean
     or (v_result -> 'plan_item' ->> 'id')::uuid <> v_item
     or (select pg_catalog.count(*) from public.v2_plan_items
         where project_id = v_project) <> 1
     or (select pg_catalog.count(*) from public.v2_projects
         where owner_user_id = v_owner) <> 1
     or (select version from public.v2_projects where id = v_project) <> 2
     or (select plan_version from public.v2_projects where id = v_project) <> 2 then
    raise exception 'fresh-session setup replay duplicated or advanced canonical state';
  end if;

  v_result := public.start_v2_current_change(
    v_owner, v_project, 2, 'f4000000-0000-4000-8000-000000000104',
    v_item, 'build', 'client supplied text is ignored for linked items');
  v_change := (v_result -> 'current_change' ->> 'id')::uuid;
  perform public.confirm_v2_manual_current_change(
    v_owner, v_project, v_change, 1,
    'f4000000-0000-4000-8000-000000000105');
  perform public.update_v2_coding_agent(v_owner, v_project, v_change, 2, 2, 'codex');
  perform public.update_v2_prompt_draft(
    v_owner, v_project, v_change, 3, 1,
    'Add a score control and preserve current behavior.',
    'Adding a point visibly changes the score',
    array['Keep the existing score display']);
  perform public.update_v2_effort(v_owner, v_project, v_change, 4, 'standard');

  select prompt_version_id into v_prompt
  from public.accept_v2_prompt_version(
    v_owner, v_project, v_change, 5, 2,
    'f4000000-0000-4000-8000-000000000106', 'feature', null,
    'Add a score control and preserve current behavior.',
    pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
      'Add a score control and preserve current behavior.', 'UTF8')), 'hex'),
    null, 'codex', 'standard', null, null);
  perform public.handoff_v2_prompt_version(
    v_owner, v_project, v_change, v_prompt, null, 6, 1,
    'f4000000-0000-4000-8000-000000000107');

  v_result := public.record_v2_manual_return(
    v_owner, v_project, v_change, 7,
    'f4000000-0000-4000-8000-000000000108', 'unsure', v_check_one);
  if (v_result -> 'check' ->> 'status') <> 'proposed'
     or (v_result -> 'current_change' ->> 'version')::bigint <> 8 then
    raise exception 'UNSURE return did not establish the first proposed Check';
  end if;

  v_result := public.record_v2_manual_check(
    v_owner, v_project, v_change, v_check_one, 8, 1,
    'f4000000-0000-4000-8000-000000000109', 'unsure',
    'I could not tell whether the score refreshed.', true, v_check_two);
  if (v_result -> 'check' ->> 'status') <> 'performed'
     or (v_result -> 'next_check' ->> 'id')::uuid <> v_check_two
     or (v_result -> 'current_change' ->> 'version')::bigint <> 9
     or (v_result -> 'current_change' ->> 'resume_step') <> 'check'
     or (v_result -> 'current_change' ->> 'unresolved_uncertainty_summary')
        not like '%' || v_check_one::text || '%' then
    raise exception 'first UNSURE Check did not atomically persist its observation and successor';
  end if;

  -- Exact command replay must not duplicate the successor or advance either
  -- aggregate version.
  v_result := public.record_v2_manual_check(
    v_owner, v_project, v_change, v_check_one, 8, 1,
    'f4000000-0000-4000-8000-000000000109', 'unsure',
    'I could not tell whether the score refreshed.', true, v_check_two);
  if not (v_result ->> 'replayed')::boolean
     or (v_result -> 'current_change' ->> 'version')::bigint <> 9
     or (select pg_catalog.count(*) from public.v2_checks
         where current_change_id = v_change) <> 2 then
    raise exception 'UNSURE Check replay duplicated state or advanced a version';
  end if;

  v_result := public.record_v2_manual_check(
    v_owner, v_project, v_change, v_check_two, 9, 1,
    'f4000000-0000-4000-8000-000000000110', 'unsure',
    'The second check still leaves the result unclear.', true, v_check_three);
  if (v_result -> 'next_check' ->> 'id')::uuid <> v_check_three
     or (v_result -> 'current_change' ->> 'version')::bigint <> 10
     or not exists (select 1 from public.v2_checks
       where id = v_check_one and status = 'performed' and result = 'unsure'
         and student_observation = 'I could not tell whether the score refreshed.'
         and version = 2)
     or not exists (select 1 from public.v2_checks
       where id = v_check_two and status = 'performed' and result = 'unsure'
         and student_observation = 'The second check still leaves the result unclear.'
         and supersedes_check_id = v_check_one and version = 2)
     or not exists (select 1 from public.v2_checks
       where id = v_check_three and status = 'proposed'
         and supersedes_check_id = v_check_two and version = 1)
     or (select pg_catalog.count(*) from public.v2_checks
         where current_change_id = v_change and status = 'performed') <> 2
     or (select pg_catalog.count(*) from public.v2_checks
         where current_change_id = v_change and status = 'proposed') <> 1 then
    raise exception 'multiple UNSURE attempts did not leave exactly one active successor';
  end if;

  -- Force a late successor insert failure after the function has attempted to
  -- mark the active Check performed. PostgreSQL must roll the whole statement
  -- back, leaving the old Check proposed and the Current Change unchanged.
  begin
    perform public.record_v2_manual_check(
      v_owner, v_project, v_change, v_check_three, 10, 1,
      'f4000000-0000-4000-8000-000000000112', 'unsure',
      'This statement must roll back atomically.', true, v_check_one);
    raise exception 'duplicate successor unexpectedly passed';
  exception when unique_violation then null;
  end;
  if not exists (select 1 from public.v2_checks
       where id = v_check_three and status = 'proposed' and version = 1)
     or (select version from public.v2_current_changes where id = v_change) <> 10
     or exists (select 1 from public.v2_build_turns
       where id = 'f4000000-0000-4000-8000-000000000112') then
    raise exception 'failed UNSURE successor insert did not roll back atomically';
  end if;

  begin
    perform public.complete_v2_current_change(
      v_owner, v_project, v_change, 10, 2, 1,
      'f4000000-0000-4000-8000-000000000111', true,
      'This must not complete',
      (select unresolved_uncertainty_summary from public.v2_current_changes where id = v_change),
      '[]'::jsonb, '[]'::jsonb);
    raise exception 'completion unexpectedly accepted an active UNSURE successor';
  exception when check_violation then null;
  end;

  select version into v_version from public.v2_current_changes where id = v_change;
  if v_version <> 10
     or not exists (select 1 from public.v2_current_changes
       where id = v_change and lifecycle_state = 'reviewing' and resume_step = 'check')
     or not exists (select 1 from public.v2_plan_items
       where id = v_item and status = 'ready' and version = 1) then
    raise exception 'failed completion changed the active UNSURE state';
  end if;
end $$;
reset role;

set local role anon;
do $$ begin
  begin
    perform public.update_v2_dialogue_sound(
      'f4000000-0000-4000-8000-000000000001', 0, false);
    raise exception 'anon unexpectedly executed a Phase 4 RPC';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;

rollback;
