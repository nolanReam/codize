-- Codize V2.3A backend-core database verification.
--
-- Run unchanged after all migrations on an isolated PostgreSQL 17 database.
-- Every fixture is transaction-local and rolled back. V1 rows are untouched.

begin;

do $$
declare
  v_commands constant text[] := array[
    'create_v2_project',
    'resolve_v2_current_change_policy',
    'promote_v2_temporary_project',
    'start_v2_current_change',
    'cancel_v2_current_change'
  ];
begin
  if (
    select pg_catalog.count(*)
    from pg_catalog.pg_proc as p
    where p.pronamespace = 'public'::regnamespace
      and p.proname = any (v_commands)
      and not p.prosecdef
      and p.proconfig @> array['search_path=""']
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
  ) <> 5 then
    raise exception 'V2.3A public command wrappers are not safely granted';
  end if;

  if (
    select pg_catalog.count(*)
    from pg_catalog.pg_proc as p
    where p.pronamespace = 'codize_v2_internal'::regnamespace
      and p.proname = any (v_commands)
      and p.prosecdef
      and p.proconfig @> array['search_path=""']
      and pg_catalog.pg_get_userbyid(p.proowner) = 'codize_v2_executor'
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
  ) <> 5 then
    raise exception 'V2.3A private command functions are not safely owned and granted';
  end if;
end
$$;

set local role anon;
do $$
begin
  begin
    perform public.create_v2_project(
      'c3000000-0000-4000-8000-000000000001',
      'c3000000-0000-4000-8000-000000000011',
      'Forbidden browser project', 'new_idea', null, null
    );
    raise exception 'anon unexpectedly executed a V2.3A command';
  exception when insufficient_privilege then null;
  end;
end
$$;
reset role;

insert into auth.users (id) values
  ('c3000000-0000-4000-8000-000000000001'),
  ('d3000000-0000-4000-8000-000000000002');

set local role service_role;
do $$
begin
  begin
    insert into public.v2_projects (
      owner_user_id, display_name, lifecycle_state, setup_resume_step,
      create_command_id
    ) values (
      'c3000000-0000-4000-8000-000000000001',
      'Forbidden direct write', 'active', 'ready',
      'c3000000-0000-4000-8000-000000000012'
    );
    raise exception 'service_role unexpectedly wrote a V2 Project directly';
  exception when insufficient_privilege then null;
  end;
end
$$;

-- Display-name-only creation must remain in truthful setup states.
do $$
declare
  v_result jsonb;
begin
  v_result := public.create_v2_project(
    'c3000000-0000-4000-8000-000000000001',
    'c3000000-0000-4000-8000-000000000101',
    'New idea fixture', 'new_idea', null, null
  );
  if v_result #>> '{project,lifecycle_state}' <> 'draft'
     or v_result #>> '{project,setup_resume_step}' <> 'idea_capture' then
    raise exception 'new idea did not begin in canonical draft setup';
  end if;

  begin
    perform public.promote_v2_temporary_project(
      'd3000000-0000-4000-8000-000000000002',
      (v_result #>> '{project,id}')::uuid, 1,
      'c3000000-0000-4000-8000-000000000105'
    );
    raise exception 'cross-owner V2 Project mutation unexpectedly succeeded';
  exception when sqlstate 'P0002' then null;
  end;

  v_result := public.create_v2_project(
    'c3000000-0000-4000-8000-000000000001',
    'c3000000-0000-4000-8000-000000000102',
    'Already building fixture', 'already_building', null, null
  );
  if v_result #>> '{project,lifecycle_state}' <> 'draft'
     or v_result #>> '{project,setup_resume_step}' <> 'existing_project_context' then
    raise exception 'already-building entry claimed readiness prematurely';
  end if;

  begin
    perform public.create_v2_project(
      'c3000000-0000-4000-8000-000000000001',
      'c3000000-0000-4000-8000-000000000103',
      'Context-free Recovery', 'recovery_first', null,
      'c3000000-0000-4000-8000-000000000104'
    );
    raise exception 'Recovery-first Project creation accepted missing context';
  exception when invalid_parameter_value then null;
  end;
end
$$;
reset role;

-- The later accepted setup command is outside V2.3A. Establish its canonical
-- result directly so this verifier can probe Current Change commands.
update public.v2_projects
set lifecycle_state = 'active', setup_resume_step = 'ready', version = version + 1
where create_command_id = 'c3000000-0000-4000-8000-000000000101';

set local role service_role;
select public.start_v2_current_change(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000101'),
  2, 'c3000000-0000-4000-8000-000000000111', null, 'build',
  'Add player totals'
);

-- Every V2.2 command that could progress an unresolved change must fail with
-- the policy-specific rejection before ordinary step eligibility is considered.
do $$
declare
  v_project_id uuid;
  v_change_id uuid;
begin
  select id into v_project_id from public.v2_projects
  where create_command_id = 'c3000000-0000-4000-8000-000000000101';
  select id into v_change_id from public.v2_current_changes
  where create_command_id = 'c3000000-0000-4000-8000-000000000111';

  begin
    perform * from public.accept_v2_prompt_version(
      'c3000000-0000-4000-8000-000000000001', v_project_id, v_change_id,
      1, 1, 'c3000000-0000-4000-8000-000000000112', 'feature', null,
      'Never accepted',
      pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to('Never accepted', 'UTF8')), 'hex'),
      null, 'cursor', 'standard', null, null
    );
    raise exception 'unresolved policy prompt acceptance unexpectedly succeeded';
  exception when check_violation then
    if sqlerrm not like '%requires resolved V2 policy%' then raise; end if;
  end;

  begin
    perform * from public.handoff_v2_prompt_version(
      'c3000000-0000-4000-8000-000000000001', v_project_id, v_change_id,
      'c3000000-0000-4000-8000-000000000113', null, 1, 1,
      'c3000000-0000-4000-8000-000000000114'
    );
    raise exception 'unresolved policy prompt handoff unexpectedly succeeded';
  exception when check_violation then
    if sqlerrm not like '%requires resolved V2 policy%' then raise; end if;
  end;

  begin
    perform * from public.complete_v2_current_change(
      'c3000000-0000-4000-8000-000000000001', v_project_id, v_change_id,
      1, null, null, 'c3000000-0000-4000-8000-000000000115', false,
      'Never complete.', null, '[]'::jsonb, '[]'::jsonb
    );
    raise exception 'unresolved policy completion unexpectedly succeeded';
  exception when check_violation then
    if sqlerrm not like '%requires resolved V2 policy%' then raise; end if;
  end;
end
$$;
reset role;

do $$
declare
  v_change_id uuid;
begin
  select id into v_change_id from public.v2_current_changes
  where create_command_id = 'c3000000-0000-4000-8000-000000000111';

  begin
    update public.v2_current_changes
    set lifecycle_state = 'reviewing', resume_step = 'check', version = version + 1
    where id = v_change_id;
    raise exception 'unresolved policy later lifecycle transition unexpectedly succeeded';
  exception when check_violation then null;
  end;

  begin
    update public.v2_current_changes
    set teaching_policy_version = 'teaching-v1', version = version + 1
    where id = v_change_id;
    raise exception 'partial V2 policy resolution unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

set local role service_role;
do $$
declare
  v_result jsonb;
begin
  v_result := public.resolve_v2_current_change_policy(
    'c3000000-0000-4000-8000-000000000001',
    (select id from public.v2_projects
     where create_command_id = 'c3000000-0000-4000-8000-000000000101'),
    (select id from public.v2_current_changes
     where create_command_id = 'c3000000-0000-4000-8000-000000000111'),
    1, 'c3000000-0000-4000-8000-000000000116',
    'skip', null, 'no_intervention_required', 'teaching-v1',
    'normal', null, 'risk-v1', 'required', null
  );
  if (v_result ->> 'replayed')::boolean
     or v_result #>> '{current_change,teaching_policy_version}' <> 'teaching-v1'
     or v_result #>> '{current_change,risk_policy_version}' <> 'risk-v1'
     or (v_result #>> '{current_change,version}')::bigint <> 2 then
    raise exception 'atomic V2 policy resolution returned the wrong state';
  end if;
end
$$;

-- Recovery-first creation atomically establishes the temporary Project and
-- its one unresolved recovery Current Change from bounded canonical context.
do $$
declare
  v_result jsonb;
begin
  v_result := public.create_v2_project(
    'c3000000-0000-4000-8000-000000000001',
    'c3000000-0000-4000-8000-000000000201',
    'Broken tracker', 'recovery_first',
    pg_catalog.jsonb_build_object(
      'project_context', 'A volleyball statistics tracker',
      'intended_behavior', 'Player totals update after each point',
      'observed_symptom', 'Player totals no longer change',
      'last_known_working_statement', 'Totals worked before the last AI edit',
      'last_known_working_certainty', 'yes',
      'candidate_change_summary', 'The AI changed the totals reducer'
    ),
    'c3000000-0000-4000-8000-000000000202'
  );
  if v_result #>> '{project,lifecycle_state}' <> 'temporary_recovery'
     or v_result #>> '{project,setup_resume_step}' <> 'recovery_context'
     or not exists (
       select 1 from public.v2_current_changes
       where create_command_id = 'c3000000-0000-4000-8000-000000000202'
         and change_kind = 'recovery'
         and lifecycle_state = 'preparing'
         and resume_step = 'confirm_change'
         and teaching_policy_version = 'unresolved-v0'
         and risk_policy_version = 'unresolved-v0'
     ) then
    raise exception 'Recovery-first creation did not establish truthful recovery work';
  end if;

  begin
    perform public.promote_v2_temporary_project(
      'c3000000-0000-4000-8000-000000000001',
      (v_result #>> '{project,id}')::uuid, 1,
      'c3000000-0000-4000-8000-000000000203'
    );
    raise exception 'zero-Recovery Project promotion unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

-- Cancelled recovery is terminal but is not successful Recovery proof.
select public.create_v2_project(
  'c3000000-0000-4000-8000-000000000001',
  'c3000000-0000-4000-8000-000000000211',
  'Cancelled recovery', 'recovery_first',
  pg_catalog.jsonb_build_object(
    'project_context', 'A notes app',
    'intended_behavior', 'Notes save',
    'observed_symptom', 'Save does nothing',
    'last_known_working_certainty', 'unsure',
    'candidate_change_summary', 'The AI changed the save handler'
  ),
  'c3000000-0000-4000-8000-000000000212'
);
select public.cancel_v2_current_change(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000211'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000212'),
  1, 'c3000000-0000-4000-8000-000000000213', 'student_cancelled'
);
do $$
begin
  begin
    perform public.promote_v2_temporary_project(
      'c3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects
       where create_command_id = 'c3000000-0000-4000-8000-000000000211'),
      1, 'c3000000-0000-4000-8000-000000000214'
    );
    raise exception 'cancelled Recovery Project promotion unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

-- Resolve policy for the main temporary fixture, then exercise the existing
-- V2.2 manual Build/Recovery primitives through a genuine resolved flow.
select public.resolve_v2_current_change_policy(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  1, 'c3000000-0000-4000-8000-000000000221',
  'skip', null, 'no_intervention_required', 'teaching-v1',
  'normal', null, 'risk-v1', 'required', null
);
reset role;

update public.v2_current_changes
set resume_step = 'prompt',
    done_condition_snapshot = 'Player totals update again',
    prompt_draft = 'Restore the totals reducer without changing other behavior.',
    prompt_draft_version = prompt_draft_version + 1,
    coding_agent_key = 'cursor', effort_category = 'standard',
    version = version + 1
where create_command_id = 'c3000000-0000-4000-8000-000000000202';

set local role service_role;
select * from public.accept_v2_prompt_version(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  3, 2, 'c3000000-0000-4000-8000-000000000222', 'feature', null,
  'Restore the totals reducer without changing other behavior.',
  pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
    'Restore the totals reducer without changing other behavior.', 'UTF8'
  )), 'hex'),
  null, 'cursor', 'standard', null, null
);
select * from public.handoff_v2_prompt_version(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  (select latest_prompt_version_id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  null, 4, 1, 'c3000000-0000-4000-8000-000000000223'
);
reset role;

update public.v2_current_changes
set lifecycle_state = 'reviewing', resume_step = 'check',
    student_return_outcome = 'broken', version = version + 1
where create_command_id = 'c3000000-0000-4000-8000-000000000202';

set local role service_role;
select * from public.open_v2_recovery_case(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  'c3000000-0000-4000-8000-000000000231', 6,
  'c3000000-0000-4000-8000-000000000232',
  'Player totals update after each point', 'Player totals no longer change',
  'Totals worked before the last AI edit', 'yes', null,
  'The AI changed the totals reducer'
);

do $$
begin
  begin
    perform public.promote_v2_temporary_project(
      'c3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects
       where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
      1, 'c3000000-0000-4000-8000-000000000233'
    );
    raise exception 'open Recovery Project promotion unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

select * from public.transition_v2_recovery_case(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  'c3000000-0000-4000-8000-000000000231',
  7, 1, 'investigating',
  '{"student_hypothesis":"The reducer no longer returns the new total."}'::jsonb
);
select * from public.transition_v2_recovery_case(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  'c3000000-0000-4000-8000-000000000231',
  8, 2, 'rechecking',
  '{"investigation_finding":"The reducer returned the old object.","correction_summary":"Return the updated total."}'::jsonb
);
reset role;

insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan,
  plan_source, status, result, student_observation, create_command_id
) values (
  'c3000000-0000-4000-8000-000000000241',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  'Add a point and inspect the displayed total', 'student',
  'performed', 'worked', 'The total increased by one.',
  'c3000000-0000-4000-8000-000000000242'
);

set local role service_role;
select * from public.complete_v2_current_change(
  'c3000000-0000-4000-8000-000000000001',
  (select id from public.v2_projects
   where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
  (select id from public.v2_current_changes
   where create_command_id = 'c3000000-0000-4000-8000-000000000202'),
  9, null, null, 'c3000000-0000-4000-8000-000000000243', false,
  'Player totals update again after the reducer correction.', null,
  '[]'::jsonb, '[]'::jsonb
);

do $$
declare
  v_result jsonb;
begin
  v_result := public.promote_v2_temporary_project(
    'c3000000-0000-4000-8000-000000000001',
    (select id from public.v2_projects
     where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
    1, 'c3000000-0000-4000-8000-000000000244'
  );
  if (v_result ->> 'replayed')::boolean
     or v_result #>> '{project,lifecycle_state}' <> 'active'
     or v_result #>> '{project,setup_resume_step}' <> 'existing_project_context'
     or v_result #>> '{project,promotion_command_id}' <>
       'c3000000-0000-4000-8000-000000000244' then
    raise exception 'valid resolved Recovery promotion returned the wrong state';
  end if;

  v_result := public.promote_v2_temporary_project(
    'c3000000-0000-4000-8000-000000000001',
    (select id from public.v2_projects
     where create_command_id = 'c3000000-0000-4000-8000-000000000201'),
    1, 'c3000000-0000-4000-8000-000000000244'
  );
  if not (v_result ->> 'replayed')::boolean then
    raise exception 'genuine duplicate promotion replay was not safe';
  end if;

  begin
    perform public.promote_v2_temporary_project(
      'c3000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects
       where create_command_id = 'c3000000-0000-4000-8000-000000000101'),
      2, 'c3000000-0000-4000-8000-000000000245'
    );
    raise exception 'unrelated active Project was treated as a promotion replay';
  exception when check_violation then null;
  end;
end
$$;

-- The purge mutation and the post-purge existence assertion are intentionally
-- separate sequential PL/pgSQL statements.
select public.create_v2_project(
  'c3000000-0000-4000-8000-000000000001',
  'c3000000-0000-4000-8000-000000000251',
  'Discard fixture', 'recovery_first',
  pg_catalog.jsonb_build_object(
    'project_context', 'A disposable timer',
    'intended_behavior', 'The timer starts',
    'observed_symptom', 'The button does nothing',
    'last_known_working_certainty', 'no',
    'candidate_change_summary', 'The AI replaced the click handler'
  ),
  'c3000000-0000-4000-8000-000000000252'
);
do $$
declare
  v_project_id uuid;
  v_purged boolean;
begin
  select id into v_project_id from public.v2_projects
  where create_command_id = 'c3000000-0000-4000-8000-000000000251';

  v_purged := public.purge_v2_project(
    'c3000000-0000-4000-8000-000000000001', v_project_id, 1,
    'temporary_recovery', '[]'::jsonb
  );
  if not v_purged then
    raise exception 'temporary Recovery Project purge did not return success';
  end if;
  if exists (
    select 1 from public.v2_projects
    where id = v_project_id
      and owner_user_id = 'c3000000-0000-4000-8000-000000000001'
  ) then
    raise exception 'temporary Recovery Project was not purged';
  end if;
end
$$;

reset role;
rollback;

select 'Codize V2.3A backend core database verification passed' as result;
