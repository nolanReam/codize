-- Focused beta setup-draft verification for an isolated, fully migrated PostgreSQL 17 database.
begin;

do $$
begin
  if not exists (
    select 1 from pg_catalog.pg_proc as p
    where p.pronamespace = 'public'::regnamespace
      and p.proname = 'save_v2_setup_draft'
      and not p.prosecdef
      and p.proconfig @> array['search_path=""']
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
  ) then
    raise exception 'setup draft public wrapper is not safely granted';
  end if;
  if not exists (
    select 1 from pg_catalog.pg_proc as p
    where p.pronamespace = 'codize_v2_internal'::regnamespace
      and p.proname = 'save_v2_setup_draft'
      and p.prosecdef
      and p.proconfig @> array['search_path=""']
      and pg_catalog.pg_get_userbyid(p.proowner) = 'codize_v2_executor'
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
  ) then
    raise exception 'setup draft private command is not safely owned and granted';
  end if;
end $$;

insert into auth.users (id) values
  ('fa000000-0000-4000-8000-000000000001'),
  ('fa000000-0000-4000-8000-000000000002');

set local role service_role;
do $$
declare
  v_owner constant uuid := 'fa000000-0000-4000-8000-000000000001';
  v_other constant uuid := 'fa000000-0000-4000-8000-000000000002';
  v_project uuid;
  v_existing uuid;
  v_item constant uuid := 'fa000000-0000-4000-8000-000000000201';
  v_result jsonb;
begin
  v_result := public.create_v2_project(
    v_owner, 'fa000000-0000-4000-8000-000000000101',
    'Draft idea', 'new_idea', null, null);
  v_project := (v_result -> 'project' ->> 'id')::uuid;

  v_result := public.save_v2_setup_draft(
    v_owner, v_project, 1, 'fa000000-0000-4000-8000-000000000102',
    'A score tracker', 'Show one score', '');
  if (v_result ->> 'replayed')::boolean
     or (v_result -> 'project' ->> 'version')::bigint <> 2
     or v_result -> 'project' -> 'setup_draft' ->> 'project_context' <> 'A score tracker' then
    raise exception 'new-idea partial setup was not saved canonically';
  end if;

  v_result := public.save_v2_setup_draft(
    v_owner, v_project, 1, 'fa000000-0000-4000-8000-000000000102',
    'A score tracker', 'Show one score', '');
  if not (v_result ->> 'replayed')::boolean
     or (v_result -> 'project' ->> 'version')::bigint <> 2 then
    raise exception 'exact setup draft retry advanced Project state';
  end if;

  begin
    perform public.save_v2_setup_draft(
      v_owner, v_project, 1, 'fa000000-0000-4000-8000-000000000103',
      'Stale overwrite', 'Show one score', '');
    raise exception 'stale setup draft was accepted';
  exception when sqlstate '40001' then null;
  end;
  if (select setup_draft ->> 'project_context' from public.v2_projects where id = v_project)
     <> 'A score tracker' then
    raise exception 'stale setup draft changed durable answers';
  end if;

  begin
    perform public.save_v2_setup_draft(
      v_other, v_project, 2, 'fa000000-0000-4000-8000-000000000104',
      'Other owner', '', '');
    raise exception 'other owner reached setup draft';
  exception when sqlstate 'P0002' then null;
  end;

  v_result := public.establish_v2_manual_project(
    v_owner, v_project, 2, 'fa000000-0000-4000-8000-000000000105',
    'A score tracker', v_item, 'Show one score', 'The score changes visibly');
  if (v_result ->> 'replayed')::boolean
     or (v_result -> 'project' ->> 'version')::bigint <> 3
     or (select pg_catalog.count(*) from public.v2_plan_items where project_id = v_project) <> 1 then
    raise exception 'final setup did not create exactly one Plan Item';
  end if;

  v_result := public.establish_v2_manual_project(
    v_owner, v_project, 2, 'fa000000-0000-4000-8000-000000000106',
    'A score tracker', 'fa000000-0000-4000-8000-000000000202',
    'Show one score', 'The score changes visibly');
  if not (v_result ->> 'replayed')::boolean
     or (v_result -> 'plan_item' ->> 'id')::uuid <> v_item
     or (select pg_catalog.count(*) from public.v2_plan_items where project_id = v_project) <> 1 then
    raise exception 'final setup fresh-session retry duplicated the Plan Item';
  end if;

  v_result := public.create_v2_project(
    v_owner, 'fa000000-0000-4000-8000-000000000107',
    'Existing app', 'already_building', null, null);
  v_existing := (v_result -> 'project' ->> 'id')::uuid;
  v_result := public.save_v2_setup_draft(
    v_owner, v_existing, 1, 'fa000000-0000-4000-8000-000000000108',
    'An existing student app', '', 'Keep current behavior working');
  if v_result -> 'project' ->> 'setup_resume_step' <> 'existing_project_context'
     or v_result -> 'project' -> 'setup_draft' ->> 'done_condition'
        <> 'Keep current behavior working' then
    raise exception 'already-building partial setup did not resume canonically';
  end if;
end $$;

rollback;
