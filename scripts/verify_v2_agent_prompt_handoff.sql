-- Codize V2.3B database verification for isolated PostgreSQL 17.
-- All fixtures and assertions are transaction-local.

begin;

do $$
declare v_commands constant text[] := array[
  'update_v2_coding_agent', 'update_v2_prompt_draft', 'update_v2_effort',
  'start_v2_generation_attempt', 'finish_v2_generation_attempt',
  'apply_v2_generated_prompt_draft'
];
begin
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace = 'public'::regnamespace
        and p.proname = any(v_commands) and not p.prosecdef
        and p.proconfig @> array['search_path=""']
        and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')) <> 6 then
    raise exception 'V2.3B public wrappers are not safely granted';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace = 'codize_v2_internal'::regnamespace
        and p.proname = any(v_commands) and p.prosecdef
        and p.proconfig @> array['search_path=""']
        and pg_catalog.pg_get_userbyid(p.proowner) = 'codize_v2_executor'
        and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')) <> 6 then
    raise exception 'V2.3B internal commands are not safely owned and granted';
  end if;
  if exists (select 1 from pg_catalog.pg_class as c
      where c.relnamespace = 'public'::regnamespace
        and c.relname like 'v2\_%' escape '\' and c.relkind = 'r'
        and not c.relrowsecurity) then
    raise exception 'V2 table lost RLS';
  end if;
end
$$;

set local role anon;
do $$ begin
  begin
    perform public.update_v2_effort(
      'b3000000-0000-4000-8000-000000000001',
      'b3000000-0000-4000-8000-000000000010',
      'b3000000-0000-4000-8000-000000000020', 1, 'quick');
    raise exception 'anon unexpectedly executed V2.3B RPC';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;

insert into auth.users (id) values
  ('b3000000-0000-4000-8000-000000000001'),
  ('b3000000-0000-4000-8000-000000000002');

set local role service_role;
select public.create_v2_project(
  'b3000000-0000-4000-8000-000000000001',
  'b3000000-0000-4000-8000-000000000101',
  'V2.3B fixture', 'new_idea', null, null);
reset role;

-- Accepted setup is a later command; establish its canonical result directly.
update public.v2_projects set lifecycle_state = 'active', setup_resume_step = 'ready',
  version = version + 1
where create_command_id = 'b3000000-0000-4000-8000-000000000101';

set local role service_role;
select public.start_v2_current_change(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  2, 'b3000000-0000-4000-8000-000000000102', null, 'build', 'Add player totals');

do $$
declare v_project uuid; v_change uuid;
begin
  select id into v_project from public.v2_projects
    where create_command_id = 'b3000000-0000-4000-8000-000000000101';
  select id into v_change from public.v2_current_changes
    where create_command_id = 'b3000000-0000-4000-8000-000000000102';
  begin
    perform public.update_v2_coding_agent(
      'b3000000-0000-4000-8000-000000000001', v_project, v_change, 2, 1, 'codex');
    raise exception 'unresolved policy unexpectedly allowed an agent';
  exception when check_violation then null;
  end;
  begin
    perform public.update_v2_coding_agent(
      'b3000000-0000-4000-8000-000000000001', v_project, v_change, 2, 1, 'help_me_choose');
    raise exception 'Help me choose persisted as an agent';
  exception when check_violation then null;
  end;
  begin
    perform public.update_v2_coding_agent(
      'b3000000-0000-4000-8000-000000000002', v_project, v_change, 2, 1, 'codex');
    raise exception 'cross-owner agent update unexpectedly succeeded';
  exception when sqlstate 'P0002' then null;
  end;
end $$;

select public.resolve_v2_current_change_policy(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  1, 'b3000000-0000-4000-8000-000000000103',
  'skip', null, 'no_intervention_required', 'teaching-v1',
  'normal', null, 'risk-v1', 'required', null);

select public.update_v2_coding_agent(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  2, 2, 'other');

select public.update_v2_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  3, 1, 'Use exactly this student-edited prompt.', 'Totals update correctly',
  array['Keep existing scoring behavior']);

do $$ begin
  if exists (select 1 from public.v2_prompt_versions
      where current_change_id = (select id from public.v2_current_changes
        where create_command_id = 'b3000000-0000-4000-8000-000000000102')) then
    raise exception 'draft edit created an immutable Prompt Version';
  end if;
  begin
    perform public.update_v2_prompt_draft(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
      (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
      3, 1, 'Stale overwrite', null, '{}');
    raise exception 'stale prompt edit unexpectedly succeeded';
  exception when serialization_failure then null;
  end;
end $$;

select public.update_v2_effort(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  4, 'deep');

select * from public.accept_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  5, 2, 'b3000000-0000-4000-8000-000000000104', 'feature', null,
  'Use exactly this student-edited prompt.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Use exactly this student-edited prompt.', 'UTF8')), 'hex'),
  null, 'other', 'deep', null, null);

-- Same acceptance command is a read-only replay and cannot duplicate history.
select * from public.accept_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  5, 2, 'b3000000-0000-4000-8000-000000000104', 'feature', null,
  'Use exactly this student-edited prompt.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Use exactly this student-edited prompt.', 'UTF8')), 'hex'),
  null, 'other', 'deep', null, null);

do $$ begin
  if (select count(*) from public.v2_prompt_versions
      where current_change_id = (select id from public.v2_current_changes
        where create_command_id = 'b3000000-0000-4000-8000-000000000102')) <> 1 then
    raise exception 'acceptance retry duplicated Prompt Version';
  end if;
end $$;

-- Editing only the done condition invalidates the accepted input snapshot.
select public.update_v2_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  6, 2, 'Use exactly this student-edited prompt.', 'A newly edited done condition',
  array['Keep existing scoring behavior']);

do $$ begin
  begin
    perform public.handoff_v2_prompt_version(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
      (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
      (select id from public.v2_prompt_versions where acceptance_command_id = 'b3000000-0000-4000-8000-000000000104'),
      null, 7, 1, 'b3000000-0000-4000-8000-000000000109');
    raise exception 'done-condition edit left the old acceptance handoff-ready';
  exception when check_violation then null;
  end;
end $$;

select * from public.accept_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  7, 2, 'b3000000-0000-4000-8000-000000000107', 'feature', null,
  'Use exactly this student-edited prompt.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Use exactly this student-edited prompt.', 'UTF8')), 'hex'),
  null, 'other', 'deep', null, null);

-- Editing only the boundaries also invalidates the newly accepted snapshot.
select public.update_v2_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  8, 2, 'Use exactly this student-edited prompt.', 'A newly edited done condition',
  array['A newly edited boundary']);

do $$ begin
  begin
    perform public.handoff_v2_prompt_version(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
      (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
      (select id from public.v2_prompt_versions where acceptance_command_id = 'b3000000-0000-4000-8000-000000000107'),
      null, 9, 1, 'b3000000-0000-4000-8000-000000000110');
    raise exception 'boundary edit left the old acceptance handoff-ready';
  exception when check_violation then null;
  end;
end $$;

select * from public.accept_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  9, 2, 'b3000000-0000-4000-8000-000000000108', 'feature', null,
  'Use exactly this student-edited prompt.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Use exactly this student-edited prompt.', 'UTF8')), 'hex'),
  null, 'other', 'deep', null, null);

select * from public.handoff_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  (select latest_prompt_version_id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  null, 10, 1, 'b3000000-0000-4000-8000-000000000105');
select * from public.handoff_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  (select latest_prompt_version_id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
  null, 10, 1, 'b3000000-0000-4000-8000-000000000105');

do $$ begin
  if not exists (select 1 from public.v2_current_changes
      where create_command_id = 'b3000000-0000-4000-8000-000000000102'
        and lifecycle_state = 'awaiting_agent' and resume_step = 'return_outcome') then
    raise exception 'handoff did not enter awaiting_agent / return_outcome';
  end if;
  begin
    perform public.update_v2_coding_agent(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000101'),
      (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000102'),
      3, 11, 'codex');
    raise exception 'agent silently changed after handoff';
  exception when check_violation then null;
  end;
end $$;

-- DETACH changes the aggregate version but preserves every feature-prompt input.
-- The accepted Prompt Version must therefore remain handoff-ready.
select public.create_v2_project(
  'b3000000-0000-4000-8000-000000000001',
  'b3000000-0000-4000-8000-000000000301',
  'Prompt freshness DETACH fixture', 'new_idea', null, null);
reset role;

update public.v2_projects set lifecycle_state = 'active', setup_resume_step = 'ready',
  version = version + 1
where create_command_id = 'b3000000-0000-4000-8000-000000000301';

set local role service_role;
select public.mutate_v2_plan(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  2, 1, 'b3000000-0000-4000-8000-000000000302',
  '[{"action":"add","plan_item_id":"b3000000-0000-4000-8000-000000000320","label":"Linked prompt item","intended_outcome":"Prompt inputs stay current","scope_band":"first_version","status":"ready","order_key":10}]'::jsonb);

select public.start_v2_current_change(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  3, 'b3000000-0000-4000-8000-000000000303',
  'b3000000-0000-4000-8000-000000000320', 'build', 'Keep the linked goal');

select public.resolve_v2_current_change_policy(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  1, 'b3000000-0000-4000-8000-000000000304',
  'skip', null, 'no_intervention_required', 'teaching-v1',
  'normal', null, 'risk-v1', 'required', null);

select public.update_v2_coding_agent(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  3, 2, 'codex');

select public.update_v2_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  3, 1, 'Keep this accepted DETACH prompt.', 'DETACH leaves the prompt valid',
  array['Preserve prompt-relevant snapshots']);

select public.update_v2_effort(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  4, 'standard');

select * from public.accept_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  5, 2, 'b3000000-0000-4000-8000-000000000305', 'feature', null,
  'Keep this accepted DETACH prompt.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Keep this accepted DETACH prompt.', 'UTF8')), 'hex'),
  null, 'codex', 'standard', null, null);

select public.mutate_v2_plan(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  4, 2, 'b3000000-0000-4000-8000-000000000306',
  '[{"action":"remove","plan_item_id":"b3000000-0000-4000-8000-000000000320","expected_version":1}]'::jsonb,
  6, 'detach', null, null);

do $$ begin
  if not exists (
    select 1
    from public.v2_current_changes as cc
    join public.v2_prompt_versions as pv on pv.id = cc.latest_prompt_version_id
    where cc.create_command_id = 'b3000000-0000-4000-8000-000000000303'
      and cc.plan_item_id is null and cc.version = 7
      and pv.input_current_change_version = 5
      and pv.input_goal_snapshot is not distinct from cc.goal_snapshot
      and pv.input_done_condition_snapshot is not distinct from cc.done_condition_snapshot
      and pv.input_boundary_snapshots is not distinct from cc.boundary_snapshots
  ) then
    raise exception 'DETACH invalidated or changed the accepted prompt inputs';
  end if;
end $$;

select * from public.handoff_v2_prompt_version(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000301'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  (select latest_prompt_version_id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000303'),
  null, 7, 1, 'b3000000-0000-4000-8000-000000000307');

do $$ begin
  if not exists (select 1 from public.v2_current_changes
      where create_command_id = 'b3000000-0000-4000-8000-000000000303'
        and lifecycle_state = 'awaiting_agent' and resume_step = 'return_outcome'
        and version = 8) then
    raise exception 'DETACH-preserved Prompt Version did not hand off';
  end if;
end $$;

-- A second fixture verifies one-command generated-draft application.
select public.create_v2_project(
  'b3000000-0000-4000-8000-000000000001',
  'b3000000-0000-4000-8000-000000000201',
  'Atomic generation fixture', 'new_idea', null, null);
reset role;

update public.v2_projects set lifecycle_state = 'active', setup_resume_step = 'ready',
  version = version + 1
where create_command_id = 'b3000000-0000-4000-8000-000000000201';

set local role service_role;
select public.start_v2_current_change(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  2, 'b3000000-0000-4000-8000-000000000202', null, 'build', 'Generate one draft');

select public.resolve_v2_current_change_policy(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  1, 'b3000000-0000-4000-8000-000000000203',
  'skip', null, 'no_intervention_required', 'teaching-v1',
  'normal', null, 'risk-v1', 'required', null);

select public.update_v2_coding_agent(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  2, 2, 'codex');

select public.start_v2_generation_attempt(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  'b3000000-0000-4000-8000-000000000204',
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  null, 'prompt_draft', 3, 'teaching-v1', 'config-v1',
  'stub-provider', 'stub-model', repeat('b', 64));

select public.apply_v2_generated_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_generation_attempts where attempt_command_id = 'b3000000-0000-4000-8000-000000000204'),
  1, 3, 1, 'Generated draft candidate', 'Generated behavior is observable',
  array['Keep existing behavior']);

-- A retry with the original command inputs is a read-only replay.
select public.apply_v2_generated_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_generation_attempts where attempt_command_id = 'b3000000-0000-4000-8000-000000000204'),
  1, 3, 1, 'Generated draft candidate', 'Generated behavior is observable',
  array['Keep existing behavior']);

-- Invalid provider output rolls the whole application command back.
select public.start_v2_generation_attempt(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  'b3000000-0000-4000-8000-000000000205',
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  null, 'prompt_draft', 4, 'teaching-v1', 'config-v1',
  'stub-provider', 'stub-model', repeat('c', 64));

do $$ begin
  begin
    perform public.apply_v2_generated_prompt_draft(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
      (select id from public.v2_generation_attempts where attempt_command_id = 'b3000000-0000-4000-8000-000000000205'),
      1, 4, 2, '   ', null, '{}');
    raise exception 'invalid provider output unexpectedly applied';
  exception when check_violation then null;
  end;
  begin
    perform public.finish_v2_generation_attempt(
      'b3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
      (select id from public.v2_generation_attempts where attempt_command_id = 'b3000000-0000-4000-8000-000000000205'),
      1, 'succeeded', null, null, 'prompt_draft',
      (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'));
    raise exception 'generic completion accepted a separately applied prompt draft';
  exception when check_violation then null;
  end;
end $$;

-- A late provider result is superseded without touching the student edit.
select public.start_v2_generation_attempt(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  'b3000000-0000-4000-8000-000000000206',
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  null, 'prompt_draft', 4, 'teaching-v1', 'config-v1',
  'stub-provider', 'stub-model', repeat('d', 64));

select public.update_v2_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes where create_command_id = 'b3000000-0000-4000-8000-000000000202'),
  4, 2, 'Independent student edit', 'Student-owned done condition',
  array['Student-owned boundary']);

select public.apply_v2_generated_prompt_draft(
  'b3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects where create_command_id = 'b3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_generation_attempts where attempt_command_id = 'b3000000-0000-4000-8000-000000000206'),
  1, 4, 2, 'Late provider result', null, '{}');

do $$ begin
  if not exists (select 1 from public.v2_current_changes
      where create_command_id = 'b3000000-0000-4000-8000-000000000202'
        and version = 5 and prompt_draft_version = 3
        and prompt_draft = 'Independent student edit'
        and lifecycle_state = 'preparing' and resume_step = 'effort'
        and latest_prompt_version_id is null) then
    raise exception 'atomic application or stale rejection corrupted Current Change';
  end if;
  if not exists (select 1 from public.v2_generation_attempts
      where attempt_command_id = 'b3000000-0000-4000-8000-000000000204'
        and status = 'succeeded' and version = 2
        and result_record_type = 'prompt_draft'
        and result_record_id = (select id from public.v2_current_changes
          where create_command_id = 'b3000000-0000-4000-8000-000000000202')) then
    raise exception 'generated draft and successful attempt were not applied atomically';
  end if;
  if not exists (select 1 from public.v2_generation_attempts
      where attempt_command_id = 'b3000000-0000-4000-8000-000000000205'
        and status = 'pending' and version = 1 and result_record_id is null) then
    raise exception 'invalid generated result did not roll back cleanly';
  end if;
  if not exists (select 1 from public.v2_generation_attempts
      where attempt_command_id = 'b3000000-0000-4000-8000-000000000206'
        and status = 'superseded' and version = 2 and result_record_id is null) then
    raise exception 'stale generation result was not superseded safely';
  end if;
  if exists (select 1 from public.v2_project_facts where owner_user_id = 'b3000000-0000-4000-8000-000000000001')
     or exists (select 1 from public.v2_learner_evidence where owner_user_id = 'b3000000-0000-4000-8000-000000000001') then
    raise exception 'Generation Attempt became Project Fact or learner evidence provenance';
  end if;
  if not exists (select 1 from public.v2_current_changes
      where create_command_id = 'b3000000-0000-4000-8000-000000000102'
        and lifecycle_state = 'awaiting_agent' and version = 11) then
    raise exception 'provider completion changed Current Change workflow truth';
  end if;
end $$;

rollback;
