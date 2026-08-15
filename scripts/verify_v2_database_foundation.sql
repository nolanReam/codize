-- Codize V2.2 database-foundation verification.
--
-- Run after all migrations on an isolated PostgreSQL 17 / local Supabase
-- database. The script is self-cleaning: every fixture and mutation is inside
-- one transaction and the final statement rolls it back. Any failed assertion
-- aborts the batch. It intentionally does not inspect or mutate V1 rows.

begin;

-- ---------------------------------------------------------------------------
-- Catalog and exposure contract.
-- ---------------------------------------------------------------------------
do $$
declare
  v_tables constant text[] := array[
    'v2_projects', 'v2_plan_items', 'v2_current_changes',
    'v2_prompt_versions', 'v2_checks', 'v2_project_facts', 'v2_build_turns',
    'v2_generation_attempts', 'v2_recovery_cases', 'v2_learner_evidence',
    'v2_user_preferences'
  ];
begin
  if (
    select count(*) from pg_catalog.pg_class as c
    where c.relnamespace = 'public'::regnamespace
      and c.relkind = 'r' and c.relname = any (v_tables)
  ) <> 11 then
    raise exception 'expected exactly eleven V2 tables';
  end if;
  if exists (
    select 1 from pg_catalog.pg_class as c
    where c.relnamespace = 'public'::regnamespace
      and c.relname = any (v_tables) and not c.relrowsecurity
  ) then
    raise exception 'every V2 table must have RLS enabled';
  end if;
  if exists (
    select 1 from pg_catalog.pg_policy as p
    join pg_catalog.pg_class as c on c.oid = p.polrelid
    where c.relnamespace = 'public'::regnamespace and c.relname = any (v_tables)
  ) then
    raise exception 'V2 browser policy set must remain empty/default-deny';
  end if;
  if exists (
    select 1 from pg_catalog.pg_class as c
    cross join (values ('anon'), ('authenticated')) as role_name(name)
    where c.relnamespace = 'public'::regnamespace and c.relname = any (v_tables)
      and (
        pg_catalog.has_table_privilege(role_name.name, c.oid, 'SELECT')
        or pg_catalog.has_table_privilege(role_name.name, c.oid, 'INSERT')
        or pg_catalog.has_table_privilege(role_name.name, c.oid, 'UPDATE')
        or pg_catalog.has_table_privilege(role_name.name, c.oid, 'DELETE')
        or pg_catalog.has_table_privilege(role_name.name, c.oid, 'TRUNCATE')
      )
  ) then
    raise exception 'browser role has a forbidden V2 table privilege';
  end if;
  if exists (
    select 1 from pg_catalog.pg_proc as p
    where p.pronamespace = 'public'::regnamespace
      and (
        p.proname like 'v2\_%' escape '\'
        or p.proname in (
          'mutate_v2_plan', 'accept_v2_prompt_version',
          'handoff_v2_prompt_version', 'resume_v2_recovery_handoff',
          'open_v2_recovery_case',
          'transition_v2_recovery_case',
          'complete_v2_current_change', 'purge_v2_project'
        )
      )
      and (
        not (p.proconfig @> array['search_path=""'])
        or pg_catalog.pg_get_userbyid(p.proowner) in ('anon', 'authenticated', 'service_role')
        or pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
        or pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
      )
  ) then
    raise exception 'V2 function security mode, search_path, or browser grant is unsafe';
  end if;
  if (
    select count(*) from pg_catalog.pg_proc as p
    where p.pronamespace = 'public'::regnamespace
      and p.proname in (
        'mutate_v2_plan', 'accept_v2_prompt_version',
        'handoff_v2_prompt_version', 'resume_v2_recovery_handoff',
        'open_v2_recovery_case',
        'transition_v2_recovery_case',
        'complete_v2_current_change', 'purge_v2_project'
      )
      and not p.prosecdef
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
  ) <> 8 then
    raise exception 'service_role does not have exactly eight public invoker RPC wrappers';
  end if;
  if (
    select count(*) from pg_catalog.pg_proc as p
    where p.pronamespace = 'codize_v2_internal'::regnamespace
      and p.proname in (
        'mutate_v2_plan', 'accept_v2_prompt_version',
        'handoff_v2_prompt_version', 'resume_v2_recovery_handoff',
        'open_v2_recovery_case', 'transition_v2_recovery_case',
        'complete_v2_current_change', 'purge_v2_project'
      )
      and p.prosecdef
      and p.proconfig @> array['search_path=""']
      and pg_catalog.pg_get_userbyid(p.proowner) = 'codize_v2_executor'
      and pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      and not pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
  ) <> 8 then
    raise exception 'private V2 definer functions are not exactly owned and granted';
  end if;
  if pg_catalog.has_sequence_privilege(
       'anon', 'public.v2_build_turns_sequence_no_seq', 'USAGE'
     ) or pg_catalog.has_sequence_privilege(
       'authenticated', 'public.v2_build_turns_sequence_no_seq', 'USAGE'
     ) or pg_catalog.has_sequence_privilege(
       'service_role', 'public.v2_build_turns_sequence_no_seq', 'USAGE'
     ) then
    raise exception 'V2 Build Turn identity sequence grants are unsafe';
  end if;
  if pg_catalog.has_schema_privilege('anon', 'codize_v2_internal', 'USAGE')
     or pg_catalog.has_schema_privilege('authenticated', 'codize_v2_internal', 'USAGE')
     or not pg_catalog.has_schema_privilege('service_role', 'codize_v2_internal', 'USAGE') then
    raise exception 'private V2 execution schema grants are unsafe';
  end if;
  if not exists (
    select 1 from pg_catalog.pg_roles as r
    where r.rolname = 'codize_v2_executor'
      and not r.rolcanlogin and not r.rolinherit and not r.rolsuper
      and not r.rolcreatedb and not r.rolcreaterole and not r.rolreplication
      and r.rolbypassrls
  ) or exists (
    select 1 from pg_catalog.pg_auth_members as m
    where m.roleid = (
      select oid from pg_catalog.pg_roles where rolname = 'codize_v2_executor'
    )
  ) or pg_catalog.has_schema_privilege('codize_v2_executor', 'public', 'CREATE')
     or pg_catalog.has_schema_privilege(
       'codize_v2_executor', 'codize_v2_internal', 'CREATE'
     ) then
    raise exception 'private V2 executor role attributes or membership are unsafe';
  end if;
  if exists (
    select 1
    from pg_catalog.pg_constraint as con
    join pg_catalog.pg_class as child on child.oid = con.conrelid
    join pg_catalog.pg_class as parent on parent.oid = con.confrelid
    join pg_catalog.pg_namespace as parent_ns on parent_ns.oid = parent.relnamespace
    where con.contype = 'f'
      and child.relnamespace = 'public'::regnamespace
      and child.relname = any (v_tables)
      and parent_ns.nspname = 'public'
      and parent.relname not like 'v2\_%' escape '\'
  ) then
    raise exception 'a V2 table depends on a V1 public table';
  end if;
  if exists (
    select 1
    from pg_catalog.pg_default_acl as d
    cross join lateral pg_catalog.aclexplode(coalesce(d.defaclacl, '{}'::aclitem[])) as acl
    where d.defaclnamespace in (
        0, 'public'::regnamespace, 'codize_v2_internal'::regnamespace
      )
      and d.defaclrole in (
        (select oid from pg_catalog.pg_roles where rolname = current_user),
        (select oid from pg_catalog.pg_roles where rolname = 'codize_v2_executor')
      )
      and d.defaclobjtype in ('r', 'S', 'f')
      and (acl.grantee = 0
        or pg_catalog.pg_get_userbyid(acl.grantee) in ('anon', 'authenticated', 'service_role'))
      and acl.privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'USAGE', 'EXECUTE')
  ) then
    raise exception 'pg_default_acl permits a forbidden future-object grant';
  end if;
  if (
    select count(*)
    from pg_catalog.pg_default_acl as d
    where d.defaclnamespace = 0
      and d.defaclobjtype = 'f'
      and d.defaclrole in (
        (select oid from pg_catalog.pg_roles where rolname = current_user),
        (select oid from pg_catalog.pg_roles where rolname = 'codize_v2_executor')
      )
  ) <> 2 then
    raise exception 'global function default ACL hardening is missing for an execution role';
  end if;
  if not exists (
    select 1 from pg_catalog.pg_class as c
    join pg_catalog.pg_index as i on i.indexrelid = c.oid
    where c.relnamespace = 'public'::regnamespace
      and c.relname = 'v2_current_changes_one_nonterminal_per_project_key'
      and i.indisunique and i.indpred is not null
  ) or not exists (
    select 1 from pg_catalog.pg_class as c
    join pg_catalog.pg_index as i on i.indexrelid = c.oid
    where c.relnamespace = 'public'::regnamespace
      and c.relname = 'v2_recovery_cases_one_open_per_change_key'
      and i.indisunique and i.indpred is not null
  ) then
    raise exception 'required partial uniqueness indexes are absent';
  end if;
end
$$;

-- Data/API roles must fail at the privilege layer, independent of RLS.
set local role anon;
do $$
begin
  begin
    perform 1 from public.v2_projects;
    raise exception 'anonymous V2 read unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
  begin
    insert into public.v2_projects (
      owner_user_id, display_name, lifecycle_state, setup_resume_step,
      create_command_id
    ) values (
      'a2000000-0000-4000-8000-000000000001', 'forged', 'active', 'ready',
      'a2000000-0000-4000-8000-000000000099'
    );
    raise exception 'anonymous V2 write unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$$;

reset role;
set local role authenticated;
do $$
begin
  begin
    perform 1 from public.v2_projects;
    raise exception 'authenticated browser V2 read unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
  begin
    perform * from public.purge_v2_project(
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000011', 1, 'standard', '[]'
    );
    raise exception 'authenticated browser V2 RPC unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$$;

reset role;

-- Minimal Auth principals for same-owner composite-FK tests.
insert into auth.users (id) values
  ('a2000000-0000-4000-8000-000000000001'),
  ('b2000000-0000-4000-8000-000000000002');

set local role service_role;
do $$
begin
  perform pg_catalog.set_config('codize.v2_completion',
    'a2000000-0000-4000-8000-000000000031', true);
  begin
    update public.v2_current_changes
    set lifecycle_state = 'completed', version = version + 1
    where false;
    raise exception 'spoofed completion GUC bypassed direct-DML denial';
  exception when insufficient_privilege then null;
  end;

  perform pg_catalog.set_config('codize.v2_project_purge',
    'a2000000-0000-4000-8000-000000000011', true);
  begin
    delete from public.v2_projects where false;
    raise exception 'spoofed purge GUC bypassed direct-DML denial';
  exception when insufficient_privilege then null;
  end;

  begin
    update public.v2_plan_items set order_key = order_key + 1 where false;
    raise exception 'direct Plan DML bypassed plan-version semantics';
  exception when insufficient_privilege then null;
  end;
end
$$;
reset role;

-- ---------------------------------------------------------------------------
-- Standard build fixture: concurrency, state matrix, handoff, Check truth,
-- typed provenance, atomic completion, and replay idempotency.
-- ---------------------------------------------------------------------------
insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  coding_agent_key, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Atomic fixture', 'active', 'ready', 'cursor',
  'a2000000-0000-4000-8000-000000000012'
);

insert into public.v2_plan_items (
  id, project_id, owner_user_id, label, intended_outcome,
  scope_band, status, order_key
) values (
  'a2000000-0000-4000-8000-000000000021',
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Add persistence', 'State survives refresh', 'first_version', 'ready', 10
);

insert into public.v2_current_changes (
  id, project_id, owner_user_id, plan_item_id, change_kind,
  lifecycle_state, resume_step, goal_snapshot, done_condition_snapshot,
  boundary_snapshots, prompt_draft, coding_agent_key, effort_category,
  teaching_mode, teaching_reason_key, teaching_policy_version,
  risk, risk_policy_version, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000031',
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000021',
  'build', 'preparing', 'prompt', 'Persist the form', 'Refresh preserves it',
  array['Keep the change inside the local form state'],
  'Implement local persistence.', 'cursor', 'standard',
  'skip', 'policy_not_set', 'teaching-v1',
  'normal', 'risk-v1', 'a2000000-0000-4000-8000-000000000032'
);

do $$
begin
  begin
    insert into public.v2_current_changes (
      project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
      goal_snapshot, teaching_mode, teaching_reason_key,
      teaching_policy_version, risk, risk_policy_version, create_command_id
    ) values (
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000001',
      'build', 'preparing', 'confirm_change', 'A second active change',
      'skip', 'policy_not_set', 'teaching-v1', 'normal', 'risk-v1',
      'a2000000-0000-4000-8000-000000000033'
    );
    raise exception 'second nonterminal Current Change unexpectedly succeeded';
  exception when unique_violation then null;
  end;

  begin
    update public.v2_current_changes
    set lifecycle_state = 'awaiting_agent', resume_step = 'return_outcome',
        handoff_command_id = 'a2000000-0000-4000-8000-000000000073', version = 2
    where id = 'a2000000-0000-4000-8000-000000000031';
    raise exception 'AWAITING_AGENT without handed-off prompt unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

-- A backward-FK cleanup may not silently mutate a surviving versioned row.
-- The later populated-project purge proves the same cleanup is accepted when
-- both rows disappear in the transaction.
reset role;
do $$
begin
  begin
    delete from public.v2_plan_items
    where id = 'a2000000-0000-4000-8000-000000000021';
    set constraints all immediate;
    raise exception 'surviving Current Change accepted unversioned FK cleanup';
  exception when serialization_failure then null;
  end;
  if not exists (
    select 1 from public.v2_plan_items
    where id = 'a2000000-0000-4000-8000-000000000021'
  ) or not exists (
    select 1 from public.v2_current_changes
    where id = 'a2000000-0000-4000-8000-000000000031'
      and plan_item_id = 'a2000000-0000-4000-8000-000000000021'
      and version = 1
  ) then
    raise exception 'failed deferred cleanup was not rolled back';
  end if;
end
$$;
set local role service_role;

-- Wrong owner cannot use a backend transaction primitive against owner A.
do $$
begin
  begin
    perform public.mutate_v2_plan(
      'b2000000-0000-4000-8000-000000000002',
      'a2000000-0000-4000-8000-000000000011',
      1, 1, 'a2000000-0000-4000-8000-000000000081',
      jsonb_build_array(jsonb_build_object(
        'action', 'reorder',
        'plan_item_id', 'a2000000-0000-4000-8000-000000000021',
        'expected_version', 1, 'order_key', 10
      ))
    );
    raise exception 'wrong-owner backend plan mutation unexpectedly succeeded';
  exception when no_data_found then null;
  end;
end
$$;
reset role;

select * from public.accept_v2_prompt_version(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000031',
  1, 1, 'a2000000-0000-4000-8000-000000000072',
  'feature', null, 'Implement local persistence.',
  encode(sha256(convert_to('Implement local persistence.', 'UTF8')), 'hex'),
  null, 'cursor', 'standard', null, null
);

do $$
begin
  begin
    update public.v2_prompt_versions
    set handoff_command_id = 'a2000000-0000-4000-8000-000000000074',
        handed_off_at = now(), version = 2
    where id = (
      select latest_prompt_version_id from public.v2_current_changes
      where id = 'a2000000-0000-4000-8000-000000000031'
    );
    update public.v2_current_changes
    set lifecycle_state = 'awaiting_agent', resume_step = 'return_outcome',
        handoff_command_id = 'a2000000-0000-4000-8000-000000000075', version = 3
    where id = 'a2000000-0000-4000-8000-000000000031';
    raise exception 'mismatched Current Change / Prompt handoff command unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

select * from public.handoff_v2_prompt_version(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000031',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'a2000000-0000-4000-8000-000000000031'),
  null, 2, 1, 'a2000000-0000-4000-8000-000000000073'
);

update public.v2_current_changes
set lifecycle_state = 'reviewing', resume_step = 'check',
    student_return_outcome = 'worked', version = version + 1
where id = 'a2000000-0000-4000-8000-000000000031';

insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan,
  plan_source, status, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000051',
  'a2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000031',
  'Refresh and inspect the saved form', 'student', 'proposed',
  'a2000000-0000-4000-8000-000000000052'
);

do $$
begin
  begin
    update public.v2_checks set status = 'performed', version = 2
    where id = 'a2000000-0000-4000-8000-000000000051';
    raise exception 'performed Check without result unexpectedly succeeded';
  exception when check_violation then null;
  end;
  begin
    insert into public.v2_checks (
      project_id, owner_user_id, current_change_id, check_plan,
      plan_source, status, result, create_command_id
    ) values (
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000031',
      'A skipped check cannot have a result', 'codize', 'not_run', 'worked',
      'a2000000-0000-4000-8000-000000000053'
    );
    raise exception 'not-run Check with a result unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

update public.v2_checks
set status = 'performed', result = 'worked',
    student_observation = 'The saved value returned.', version = 2
where id = 'a2000000-0000-4000-8000-000000000051';

-- A valid source record cannot launder an arbitrary system-observed value.
-- The failure must roll back completion, Plan movement, Facts, and Evidence.
do $$
declare
  v_command_id constant uuid := 'a2000000-0000-4000-8000-000000000076';
begin
  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000031',
      4, 1, 1, v_command_id, true,
      'This invalid Fact must roll back.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'boundary', 'subject_key', 'current_change_boundaries',
        'value_kind', 'text_list', 'value', jsonb_build_array('Invented boundary'),
        'source_kind', 'system_observed', 'source_record_type', 'current_change',
        'source_record_id', 'a2000000-0000-4000-8000-000000000031',
        'observed_at', now()
      )),
      jsonb_build_array(jsonb_build_object(
        'competency_key', 'testing',
        'observed_behavior', 'This Evidence must roll back with the invalid Fact.',
        'elicitation', 'asked', 'support_level', 'none',
        'context_key', 'normal_novel', 'source_record_type', 'check',
        'source_record_id', 'a2000000-0000-4000-8000-000000000051',
        'observed_at', now(), 'evidence_policy_version', 'qualification-v1'
      ))
    );
    raise exception 'Current Change source accepted an unsupported system-observed value';
  exception when check_violation then null;
  end;

  if not exists (
       select 1 from public.v2_current_changes
       where id = 'a2000000-0000-4000-8000-000000000031'
         and lifecycle_state = 'reviewing' and version = 4
     ) or not exists (
       select 1 from public.v2_plan_items
       where id = 'a2000000-0000-4000-8000-000000000021'
         and status = 'ready' and version = 1
     ) or not exists (
       select 1 from public.v2_projects
       where id = 'a2000000-0000-4000-8000-000000000011'
         and plan_version = 1 and version = 1
     ) or exists (
       select 1 from public.v2_project_facts where source_operation_id = v_command_id
     ) or exists (
       select 1 from public.v2_learner_evidence where source_operation_id = v_command_id
     ) then
    raise exception 'invalid system-observed Fact did not roll back completion atomically';
  end if;
end
$$;

do $$
declare
  v_prompt_id uuid;
begin
  select latest_prompt_version_id into strict v_prompt_id
  from public.v2_current_changes
  where id = 'a2000000-0000-4000-8000-000000000031';

  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000031',
      4, 1, 1, 'a2000000-0000-4000-8000-000000000077', true,
      'Prompt mismatch must fail.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'tool', 'subject_key', 'selected_coding_agent',
        'value_kind', 'text', 'value', 'invented-agent',
        'source_kind', 'system_observed', 'source_record_type', 'prompt_version',
        'source_record_id', v_prompt_id, 'observed_at', now()
      )), '[]'
    );
    raise exception 'Prompt Version source accepted an unsupported system-observed value';
  exception when check_violation then null;
  end;

  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000031',
      4, 1, 1, 'a2000000-0000-4000-8000-000000000078', true,
      'Unsupported pairing must fail.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'boundary', 'subject_key', 'current_change_boundaries',
        'value_kind', 'text_list',
        'value', jsonb_build_array('Keep the change inside the local form state'),
        'source_kind', 'system_observed', 'source_record_type', 'prompt_version',
        'source_record_id', v_prompt_id, 'observed_at', now()
      )), '[]'
    );
    raise exception 'legitimate source accepted an unsupported system-observed Fact combination';
  exception when check_violation then null;
  end;

  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000011',
      'a2000000-0000-4000-8000-000000000031',
      4, 1, 1, 'a2000000-0000-4000-8000-000000000079', true,
      'Unsupported Check mapping must fail.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'known_working_behavior', 'subject_key', 'persistence_refresh',
        'value_kind', 'boolean', 'value', true,
        'source_kind', 'system_observed', 'source_record_type', 'check',
        'source_record_id', 'a2000000-0000-4000-8000-000000000051',
        'observed_at', now()
      )), '[]'
    );
    raise exception 'performed Check without a deterministic system mapping created a Fact';
  exception when check_violation then null;
  end;
end
$$;

do $$
declare
  v_result record;
  v_fact_count bigint;
  v_evidence_count bigint;
begin
  select * into v_result from public.complete_v2_current_change(
    'a2000000-0000-4000-8000-000000000001',
    'a2000000-0000-4000-8000-000000000011',
    'a2000000-0000-4000-8000-000000000031',
    4, 1, 1, 'a2000000-0000-4000-8000-000000000071', true,
    'The form state survived a refresh.', null,
    jsonb_build_array(
      jsonb_build_object(
        'fact_type', 'known_working_behavior', 'subject_key', 'persistence_refresh',
        'value_kind', 'boolean', 'value', true,
        'source_kind', 'student_observed', 'source_record_type', 'check',
        'source_record_id', 'a2000000-0000-4000-8000-000000000051',
        'observed_at', now()
      ),
      jsonb_build_object(
        'fact_type', 'boundary', 'subject_key', 'current_change_boundaries',
        'value_kind', 'text_list',
        'value', jsonb_build_array('Keep the change inside the local form state'),
        'source_kind', 'system_observed', 'source_record_type', 'current_change',
        'source_record_id', 'a2000000-0000-4000-8000-000000000031',
        'observed_at', now()
      ),
      jsonb_build_object(
        'fact_type', 'tool', 'subject_key', 'selected_coding_agent',
        'value_kind', 'text', 'value', 'cursor',
        'source_kind', 'system_observed', 'source_record_type', 'prompt_version',
        'source_record_id', (
          select latest_prompt_version_id from public.v2_current_changes
          where id = 'a2000000-0000-4000-8000-000000000031'
        ),
        'observed_at', now()
      )
    ),
    jsonb_build_array(jsonb_build_object(
      'competency_key', 'testing',
      'observed_behavior', 'Ran the planned refresh check and reported the result.',
      'elicitation', 'asked', 'support_level', 'none',
      'context_key', 'normal_novel', 'source_record_type', 'check',
      'source_record_id', 'a2000000-0000-4000-8000-000000000051',
      'observed_at', now(), 'evidence_policy_version', 'qualification-v1'
    ))
  );
  if v_result.replayed or v_result.current_change_version <> 5
     or v_result.plan_item_version <> 2 or v_result.plan_version <> 2
     or v_result.project_version <> 2 or v_result.current_change_state <> 'completed'
     or v_result.plan_item_status <> 'done' then
    raise exception 'atomic completion did not increment exact versions/state';
  end if;

  select count(*) into v_fact_count from public.v2_project_facts
  where source_operation_id = 'a2000000-0000-4000-8000-000000000071';
  select count(*) into v_evidence_count from public.v2_learner_evidence
  where source_operation_id = 'a2000000-0000-4000-8000-000000000071';
  if v_fact_count <> 3 or v_evidence_count <> 1 then
    raise exception 'atomic completion did not write three Facts and one Evidence row';
  end if;
  if not exists (
       select 1 from public.v2_project_facts
       where source_operation_id = 'a2000000-0000-4000-8000-000000000071'
         and fact_type = 'boundary'
         and subject_key = 'current_change_boundaries'
         and value_text_list = array['Keep the change inside the local form state']
         and source_kind = 'system_observed'
         and source_record_type = 'current_change'
         and source_record_id = 'a2000000-0000-4000-8000-000000000031'
     ) or not exists (
       select 1 from public.v2_project_facts as pf
       join public.v2_prompt_versions as pv on pv.id = pf.source_record_id
       where pf.source_operation_id = 'a2000000-0000-4000-8000-000000000071'
         and pf.fact_type = 'tool'
         and pf.subject_key = 'selected_coding_agent'
         and pf.value_text = pv.coding_agent_key
         and pf.source_kind = 'system_observed'
         and pf.source_record_type = 'prompt_version'
     ) then
    raise exception 'matching Current Change or Prompt Version system Fact was not persisted exactly';
  end if;

  select * into v_result from public.complete_v2_current_change(
    'a2000000-0000-4000-8000-000000000001',
    'a2000000-0000-4000-8000-000000000011',
    'a2000000-0000-4000-8000-000000000031',
    4, 1, 1, 'a2000000-0000-4000-8000-000000000071', true,
    'Ignored replay body', null, '[]', '[]'
  );
  if not v_result.replayed or v_result.current_change_version <> 5
     or v_result.project_version <> 2 or v_result.plan_version <> 2 then
    raise exception 'completion replay did not return current canonical state';
  end if;
  if (select count(*) from public.v2_project_facts
      where source_operation_id = 'a2000000-0000-4000-8000-000000000071') <> 3
     or (select count(*) from public.v2_learner_evidence
      where source_operation_id = 'a2000000-0000-4000-8000-000000000071') <> 1 then
    raise exception 'completion replay duplicated Fact or Evidence writes';
  end if;
end
$$;

-- Completion policy is persisted explicitly. Leaf failed/unsure Checks block;
-- a later performed superseding success can qualify.
create function pg_temp.prepare_v2_review_fixture(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_check_requirement text,
  p_risk text
)
returns void
language plpgsql
as $$
declare
  v_prompt_id uuid;
begin
  insert into public.v2_projects (
    id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
    create_command_id
  ) values (
    p_project_id, p_owner_user_id, 'Completion policy fixture', 'active', 'ready',
    gen_random_uuid()
  );
  insert into public.v2_current_changes (
    id, project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
    goal_snapshot, done_condition_snapshot, prompt_draft, coding_agent_key,
    effort_category, teaching_mode, teaching_reason_key,
    teaching_policy_version, risk, risk_reason_key, risk_policy_version,
    check_requirement, check_waiver_reason_key, create_command_id
  ) values (
    p_current_change_id, p_project_id, p_owner_user_id, 'build', 'preparing',
    'prompt', 'Exercise completion eligibility', 'The eligibility rule holds',
    'Apply the isolated change.', 'test-agent', 'standard', 'skip',
    'policy_not_set', 'teaching-v1', p_risk,
    case when p_risk = 'slowdown' then 'high_risk_change' else null end,
    'risk-v1', p_check_requirement,
    case when p_check_requirement = 'waived' then 'policy_redundant' else null end,
    gen_random_uuid()
  );
  perform * from public.accept_v2_prompt_version(
    p_owner_user_id, p_project_id, p_current_change_id, 1, 1,
    gen_random_uuid(), 'feature', null, 'Apply the isolated change.',
    encode(sha256(convert_to('Apply the isolated change.', 'UTF8')), 'hex'),
    null, 'test-agent', 'standard', null, null
  );
  select latest_prompt_version_id into strict v_prompt_id
  from public.v2_current_changes where id = p_current_change_id;
  perform * from public.handoff_v2_prompt_version(
    p_owner_user_id, p_project_id, p_current_change_id, v_prompt_id, null,
    2, 1, gen_random_uuid()
  );
  update public.v2_current_changes
  set lifecycle_state = 'reviewing', resume_step = 'check',
      student_return_outcome = 'worked', version = 4
  where id = p_current_change_id;
end;
$$;

select pg_temp.prepare_v2_review_fixture(
  'a2000000-0000-4000-8000-000000000001',
  'c2000000-0000-4000-8000-000000000011',
  'c2000000-0000-4000-8000-000000000031', 'required', 'normal'
);
do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'c2000000-0000-4000-8000-000000000011',
      'c2000000-0000-4000-8000-000000000031',
      4, null, null, gen_random_uuid(), false,
      'Missing Check must fail.', null, '[]', '[]'
    );
    raise exception 'required Check missing unexpectedly completed';
  exception when check_violation then null;
  end;
end
$$;

select pg_temp.prepare_v2_review_fixture(
  'a2000000-0000-4000-8000-000000000001',
  'd2000000-0000-4000-8000-000000000011',
  'd2000000-0000-4000-8000-000000000031', 'waived', 'normal'
);
do $$
declare
  v_result record;
begin
  select * into v_result from public.complete_v2_current_change(
    'a2000000-0000-4000-8000-000000000001',
    'd2000000-0000-4000-8000-000000000011',
    'd2000000-0000-4000-8000-000000000031',
    4, null, null, gen_random_uuid(), false,
    'The explicit waiver was honored.', null, '[]', '[]'
  );
  if v_result.current_change_state <> 'completed' then
    raise exception 'explicit Check waiver did not complete';
  end if;
end
$$;

select pg_temp.prepare_v2_review_fixture(
  'a2000000-0000-4000-8000-000000000001',
  'e2000000-0000-4000-8000-000000000011',
  'e2000000-0000-4000-8000-000000000031', 'required', 'slowdown'
);
do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'e2000000-0000-4000-8000-000000000011',
      'e2000000-0000-4000-8000-000000000031',
      4, null, null, gen_random_uuid(), false,
      'Slowdown requires checking.', null, '[]', '[]'
    );
    raise exception 'slowdown with missing Check unexpectedly completed';
  exception when check_violation then null;
  end;
end
$$;

select pg_temp.prepare_v2_review_fixture(
  'a2000000-0000-4000-8000-000000000001',
  'f2000000-0000-4000-8000-000000000011',
  'f2000000-0000-4000-8000-000000000031', 'required', 'normal'
);
insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan, plan_source,
  status, result, student_observation, create_command_id
) values
  ('f2000000-0000-4000-8000-000000000051',
   'f2000000-0000-4000-8000-000000000011',
   'a2000000-0000-4000-8000-000000000001',
   'f2000000-0000-4000-8000-000000000031', 'Old passing Check', 'student',
   'performed', 'worked', 'It first appeared to work.', gen_random_uuid()),
  ('f2000000-0000-4000-8000-000000000052',
   'f2000000-0000-4000-8000-000000000011',
   'a2000000-0000-4000-8000-000000000001',
   'f2000000-0000-4000-8000-000000000031', 'Later failing Check', 'student',
   'performed', 'did_not_work', 'The latest run failed.', gen_random_uuid());
do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'f2000000-0000-4000-8000-000000000011',
      'f2000000-0000-4000-8000-000000000031',
      4, null, null, gen_random_uuid(), false,
      'A failure must block.', null, '[]', '[]'
    );
    raise exception 'unresolved failed Check unexpectedly completed';
  exception when check_violation then null;
  end;
end
$$;
insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan, plan_source,
  status, result, student_observation, supersedes_check_id, create_command_id
) values (
  'f2000000-0000-4000-8000-000000000053',
  'f2000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'f2000000-0000-4000-8000-000000000031', 'Successful corrected Check',
  'student', 'performed', 'worked', 'The corrected run worked.',
  'f2000000-0000-4000-8000-000000000052', gen_random_uuid()
);
do $$
declare
  v_result record;
begin
  select * into v_result from public.complete_v2_current_change(
    'a2000000-0000-4000-8000-000000000001',
    'f2000000-0000-4000-8000-000000000011',
    'f2000000-0000-4000-8000-000000000031',
    4, null, null, gen_random_uuid(), false,
    'The corrected Check succeeded.', null, '[]', '[]'
  );
  if v_result.current_change_state <> 'completed' then
    raise exception 'superseding successful Check did not permit completion';
  end if;
end
$$;

select pg_temp.prepare_v2_review_fixture(
  'a2000000-0000-4000-8000-000000000001',
  'a3000000-0000-4000-8000-000000000011',
  'a3000000-0000-4000-8000-000000000031', 'required', 'normal'
);
insert into public.v2_checks (
  project_id, owner_user_id, current_change_id, check_plan, plan_source,
  status, result, student_observation, create_command_id
) values (
  'a3000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'a3000000-0000-4000-8000-000000000031', 'Uncertain latest Check',
  'student', 'performed', 'unsure', 'The result was unclear.', gen_random_uuid()
);
do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'a2000000-0000-4000-8000-000000000001',
      'a3000000-0000-4000-8000-000000000011',
      'a3000000-0000-4000-8000-000000000031',
      4, null, null, gen_random_uuid(), false,
      'Unsure must block.', null, '[]', '[]'
    );
    raise exception 'unresolved unsure Check unexpectedly completed';
  exception when check_violation then null;
  end;
end
$$;

-- Atomic multi-item Plan mutation, narrow retry, stale rejection, and the two
-- explicit linked-item removal choices.
insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  create_command_id
) values (
  'b4000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Atomic Plan fixture', 'active', 'ready', gen_random_uuid()
);
insert into public.v2_plan_items (
  id, project_id, owner_user_id, label, intended_outcome,
  scope_band, status, order_key
) values
  ('b4000000-0000-4000-8000-000000000021',
   'b4000000-0000-4000-8000-000000000011',
   'a2000000-0000-4000-8000-000000000001',
   'One', 'Outcome one', 'first_version', 'ready', 10),
  ('b4000000-0000-4000-8000-000000000022',
   'b4000000-0000-4000-8000-000000000011',
   'a2000000-0000-4000-8000-000000000001',
   'Two', 'Outcome two', 'first_version', 'ready', 20),
  ('b4000000-0000-4000-8000-000000000023',
   'b4000000-0000-4000-8000-000000000011',
   'a2000000-0000-4000-8000-000000000001',
   'Three', 'Outcome three', 'first_version', 'ready', 30);
insert into public.v2_current_changes (
  id, project_id, owner_user_id, plan_item_id, change_kind, lifecycle_state,
  resume_step, goal_snapshot, teaching_mode, teaching_reason_key,
  teaching_policy_version, risk, risk_policy_version, create_command_id
) values (
  'b4000000-0000-4000-8000-000000000031',
  'b4000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'b4000000-0000-4000-8000-000000000021',
  'build', 'preparing', 'confirm_change', 'Immutable active goal',
  'skip', 'policy_not_set', 'teaching-v1', 'normal', 'risk-v1',
  gen_random_uuid()
);
do $$
declare
  v_command_id uuid := gen_random_uuid();
  v_result jsonb;
begin
  v_result := public.mutate_v2_plan(
    'a2000000-0000-4000-8000-000000000001',
    'b4000000-0000-4000-8000-000000000011', 1, 1, v_command_id,
    '[
      {"action":"reorder","plan_item_id":"b4000000-0000-4000-8000-000000000021","expected_version":1,"order_key":30},
      {"action":"reorder","plan_item_id":"b4000000-0000-4000-8000-000000000022","expected_version":1,"order_key":10},
      {"action":"reorder","plan_item_id":"b4000000-0000-4000-8000-000000000023","expected_version":1,"order_key":20}
    ]'::jsonb
  );
  if v_result ->> 'replayed' <> 'false'
     or (v_result ->> 'project_version')::bigint <> 2
     or (v_result ->> 'plan_version')::bigint <> 2
     or not exists (
       select 1 from public.v2_plan_items
       where id = 'b4000000-0000-4000-8000-000000000021'
         and order_key = 30 and version = 2
     )
     or not exists (
       select 1 from public.v2_plan_items
       where id = 'b4000000-0000-4000-8000-000000000022'
         and order_key = 10 and version = 2
     )
     or not exists (
       select 1 from public.v2_plan_items
       where id = 'b4000000-0000-4000-8000-000000000023'
         and order_key = 20 and version = 2
     ) then
    raise exception 'atomic multi-item Plan reorder failed';
  end if;

  v_result := public.mutate_v2_plan(
    'a2000000-0000-4000-8000-000000000001',
    'b4000000-0000-4000-8000-000000000011', 1, 1, v_command_id,
    '[{"action":"reorder","plan_item_id":"b4000000-0000-4000-8000-000000000021","expected_version":1,"order_key":30}]'::jsonb
  );
  if v_result ->> 'replayed' <> 'true' then
    raise exception 'duplicate Plan retry was not idempotent';
  end if;

  begin
    perform public.mutate_v2_plan(
      'a2000000-0000-4000-8000-000000000001',
      'b4000000-0000-4000-8000-000000000011', 1, 1, gen_random_uuid(),
      '[{"action":"reorder","plan_item_id":"b4000000-0000-4000-8000-000000000022","expected_version":2,"order_key":20}]'::jsonb
    );
    raise exception 'stale Plan version unexpectedly succeeded';
  exception when serialization_failure then null;
  end;

  begin
    perform public.mutate_v2_plan(
      'a2000000-0000-4000-8000-000000000001',
      'b4000000-0000-4000-8000-000000000011', 2, 2, gen_random_uuid(),
      '[{"action":"remove","plan_item_id":"b4000000-0000-4000-8000-000000000021","expected_version":2}]'::jsonb
    );
    raise exception 'linked-item removal without explicit choice unexpectedly succeeded';
  exception when serialization_failure then null;
  end;

  v_result := public.mutate_v2_plan(
    'a2000000-0000-4000-8000-000000000001',
    'b4000000-0000-4000-8000-000000000011', 2, 2, gen_random_uuid(),
    '[{"action":"remove","plan_item_id":"b4000000-0000-4000-8000-000000000021","expected_version":2}]'::jsonb,
    1, 'detach', null, null
  );
  if not exists (
    select 1 from public.v2_current_changes
    where id = 'b4000000-0000-4000-8000-000000000031'
      and plan_item_id is null and lifecycle_state = 'preparing'
      and goal_snapshot = 'Immutable active goal' and version = 2
  ) or not exists (
    select 1 from public.v2_plan_items
    where id = 'b4000000-0000-4000-8000-000000000021'
      and status = 'removed' and order_key < 0 and version = 3
  ) then
    raise exception 'DETACH did not preserve the active Current Change snapshot';
  end if;
end
$$;

insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  create_command_id
) values (
  'b5000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Plan cancel fixture', 'active', 'ready', gen_random_uuid()
);
insert into public.v2_plan_items (
  id, project_id, owner_user_id, label, intended_outcome,
  scope_band, status, order_key
) values (
  'b5000000-0000-4000-8000-000000000021',
  'b5000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Cancel me', 'Cancel safely', 'first_version', 'ready', 10
);
insert into public.v2_current_changes (
  id, project_id, owner_user_id, plan_item_id, change_kind, lifecycle_state,
  resume_step, goal_snapshot, teaching_mode, teaching_reason_key,
  teaching_policy_version, risk, risk_policy_version, create_command_id
) values (
  'b5000000-0000-4000-8000-000000000031',
  'b5000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'b5000000-0000-4000-8000-000000000021',
  'build', 'preparing', 'confirm_change', 'Cancel this active change',
  'skip', 'policy_not_set', 'teaching-v1', 'normal', 'risk-v1',
  gen_random_uuid()
);
select public.mutate_v2_plan(
  'a2000000-0000-4000-8000-000000000001',
  'b5000000-0000-4000-8000-000000000011', 1, 1, gen_random_uuid(),
  '[{"action":"remove","plan_item_id":"b5000000-0000-4000-8000-000000000021","expected_version":1}]'::jsonb,
  1, 'cancel', gen_random_uuid(), 'student_removed_linked_item'
);
do $$
begin
  if not exists (
    select 1 from public.v2_current_changes
    where id = 'b5000000-0000-4000-8000-000000000031'
      and lifecycle_state = 'cancelled' and version = 2
  ) or not exists (
    select 1 from public.v2_plan_items
    where id = 'b5000000-0000-4000-8000-000000000021'
      and status = 'removed' and order_key < 0 and version = 2
  ) then
    raise exception 'CANCEL did not atomically cancel the change and remove the Plan Item';
  end if;
end
$$;

-- ---------------------------------------------------------------------------
-- Rollback, stale-token, recovery serialization, and recovery completion.
-- ---------------------------------------------------------------------------
insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  coding_agent_key, create_command_id
) values (
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'Rollback fixture', 'active', 'ready', 'cursor',
  'b2000000-0000-4000-8000-000000000012'
);
do $$
begin
  begin
    insert into public.v2_current_changes (
      project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
      goal_snapshot, teaching_mode, teaching_reason_key,
      teaching_policy_version, risk, risk_policy_version, create_command_id
    ) values (
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'build', 'preparing', 'return_outcome', 'Illegal resume pairing',
      'skip', 'policy_not_set', 'teaching-v1', 'normal', 'risk-v1',
      'b2000000-0000-4000-8000-000000000013'
    );
    raise exception 'illegal lifecycle/resume pairing unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;
insert into public.v2_current_changes (
  id, project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
  goal_snapshot, done_condition_snapshot, prompt_draft, coding_agent_key,
  effort_category, teaching_mode, teaching_reason_key,
  teaching_policy_version, risk, risk_policy_version, create_command_id
) values (
  'b2000000-0000-4000-8000-000000000031',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'recovery', 'preparing', 'prompt', 'Repair loading', 'Loading works again',
  'Repair the load path.', 'cursor', 'deep', 'skip', 'policy_not_set',
  'teaching-v1', 'normal', 'risk-v1',
  'b2000000-0000-4000-8000-000000000032'
);
select * from public.accept_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000031',
  1, 1, 'b2000000-0000-4000-8000-000000000072',
  'feature', null, 'Repair the load path.',
  encode(sha256(convert_to('Repair the load path.', 'UTF8')), 'hex'),
  null, 'cursor', 'deep', null, null
);
select * from public.handoff_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000031',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'b2000000-0000-4000-8000-000000000031'),
  null, 2, 1, 'b2000000-0000-4000-8000-000000000073'
);
update public.v2_current_changes
set lifecycle_state = 'reviewing', resume_step = 'check',
    student_return_outcome = 'worked', version = 4
where id = 'b2000000-0000-4000-8000-000000000031';

do $$
declare
  v_before bigint;
begin
  select version into v_before from public.v2_current_changes
  where id = 'b2000000-0000-4000-8000-000000000031';
  begin
    perform * from public.complete_v2_current_change(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      4, null, null, 'b2000000-0000-4000-8000-000000000071', false,
      'Would otherwise complete.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'not_an_allowed_fact', 'subject_key', 'rollback',
        'value_kind', 'boolean', 'value', true,
        'source_kind', 'system_observed', 'source_record_type', 'current_change',
        'source_record_id', 'b2000000-0000-4000-8000-000000000031',
        'observed_at', now()
      )), '[]'
    );
    raise exception 'completion with invalid Fact unexpectedly succeeded';
  exception when check_violation then null;
  end;
  if (select lifecycle_state from public.v2_current_changes
      where id = 'b2000000-0000-4000-8000-000000000031') <> 'reviewing'
     or (select version from public.v2_current_changes
      where id = 'b2000000-0000-4000-8000-000000000031') <> v_before
     or exists (select 1 from public.v2_project_facts
      where source_operation_id = 'b2000000-0000-4000-8000-000000000071') then
    raise exception 'invalid completion did not roll back atomically';
  end if;

  begin
    perform * from public.complete_v2_current_change(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      3, null, null, 'b2000000-0000-4000-8000-000000000074', false,
      'Stale completion.', null, '[]', '[]'
    );
    raise exception 'stale completion unexpectedly succeeded';
  exception when serialization_failure then null;
  end;
end
$$;

select * from public.open_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000031',
  'b2000000-0000-4000-8000-000000000061',
  4, 'b2000000-0000-4000-8000-000000000062',
  'Loading restores the form', 'The form loads empty', null, 'unsure',
  null, null
);

do $$
begin
  begin
    perform * from public.open_v2_recovery_case(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      'b2000000-0000-4000-8000-000000000064',
      5, 'b2000000-0000-4000-8000-000000000063',
      'duplicate', 'duplicate', null, 'no', null, null
    );
    raise exception 'second open Recovery Case unexpectedly succeeded';
  exception when unique_violation then null;
  end;
  begin
    perform * from public.transition_v2_recovery_case(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      'b2000000-0000-4000-8000-000000000061',
      4, 1, 'investigating', '{}'
    );
    raise exception 'stale recovery mutation unexpectedly succeeded';
  exception when serialization_failure then null;
  end;
  if (select version from public.v2_current_changes
      where id = 'b2000000-0000-4000-8000-000000000031') <> 5
     or (select version from public.v2_recovery_cases
      where id = 'b2000000-0000-4000-8000-000000000061') <> 1 then
    raise exception 'stale recovery mutation changed durable versions';
  end if;
end
$$;

select * from public.transition_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000031',
  'b2000000-0000-4000-8000-000000000061',
  5, 1, 'investigating', '{"student_hypothesis":"The load key may differ."}'
);
do $$
begin
  begin
    perform * from public.transition_v2_recovery_case(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      'b2000000-0000-4000-8000-000000000061',
      6, 2, 'resolved', '{"resolution_summary":"Too early."}'
    );
    raise exception 'Recovery investigating-to-resolved bypass unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;
select * from public.transition_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000031',
  'b2000000-0000-4000-8000-000000000061',
  6, 2, 'rechecking', '{"investigation_finding":"The load key differed.","correction_summary":"Use the saved key."}'
);
do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      7, null, null, gen_random_uuid(), false,
      'Recovery still needs a recheck.', null, '[]', '[]'
    );
    raise exception 'Recovery without post-Recovery recheck unexpectedly completed';
  exception when check_violation then null;
  end;
end
$$;
insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan,
  plan_source, status, result, student_observation, create_command_id
) values (
  'b2000000-0000-4000-8000-000000000051',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000031',
  'Reload after correcting the key', 'student', 'performed', 'worked',
  'The saved form returned.', 'b2000000-0000-4000-8000-000000000052'
);

do $$
begin
  begin
    perform * from public.complete_v2_current_change(
      'b2000000-0000-4000-8000-000000000002',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000031',
      7, null, null, 'b2000000-0000-4000-8000-000000000076', false,
      'Recovery mismatch must fail.', null,
      jsonb_build_array(jsonb_build_object(
        'fact_type', 'unresolved_behavior',
        'subject_key', 'recovery_observed_symptom',
        'value_kind', 'text', 'value', 'An invented recovery symptom',
        'source_kind', 'system_observed', 'source_record_type', 'recovery_case',
        'source_record_id', 'b2000000-0000-4000-8000-000000000061',
        'observed_at', now()
      )), '[]'
    );
    raise exception 'Recovery Case source accepted an unsupported system-observed value';
  exception when check_violation then null;
  end;
  if not exists (
    select 1 from public.v2_current_changes
    where id = 'b2000000-0000-4000-8000-000000000031'
      and lifecycle_state = 'recovering' and version = 7
  ) or exists (
    select 1 from public.v2_project_facts
    where source_operation_id = 'b2000000-0000-4000-8000-000000000076'
  ) then
    raise exception 'invalid Recovery Fact did not roll back atomically';
  end if;
end
$$;

do $$
declare
  v_result record;
begin
  select * into v_result from public.complete_v2_current_change(
    'b2000000-0000-4000-8000-000000000002',
    'b2000000-0000-4000-8000-000000000011',
    'b2000000-0000-4000-8000-000000000031',
    7, null, null, 'b2000000-0000-4000-8000-000000000075', false,
    'Loading works after using the saved key.', null,
    jsonb_build_array(jsonb_build_object(
      'fact_type', 'unresolved_behavior',
      'subject_key', 'recovery_observed_symptom',
      'value_kind', 'text', 'value', 'The form loads empty',
      'source_kind', 'system_observed', 'source_record_type', 'recovery_case',
      'source_record_id', 'b2000000-0000-4000-8000-000000000061',
      'observed_at', now()
    )),
    jsonb_build_array(jsonb_build_object(
      'competency_key', 'debugging',
      'observed_behavior', 'Formed a hypothesis and rechecked the correction.',
      'elicitation', 'asked', 'support_level', 'nudge',
      'context_key', 'recovery', 'source_record_type', 'recovery_case',
      'source_record_id', 'b2000000-0000-4000-8000-000000000061',
      'observed_at', now(), 'evidence_policy_version', 'qualification-v1'
    ))
  );
  if v_result.current_change_version <> 8
     or v_result.recovery_case_version <> 4
     or v_result.recovery_case_status <> 'resolved' then
    raise exception 'recovery completion did not atomically resolve both aggregates';
  end if;
  if not exists (
    select 1 from public.v2_project_facts
    where source_operation_id = 'b2000000-0000-4000-8000-000000000075'
      and fact_type = 'unresolved_behavior'
      and subject_key = 'recovery_observed_symptom'
      and value_text = 'The form loads empty'
      and source_kind = 'system_observed'
      and source_record_type = 'recovery_case'
      and source_record_id = 'b2000000-0000-4000-8000-000000000061'
  ) then
    raise exception 'matching Recovery Case system Fact was not persisted exactly';
  end if;
end
$$;

-- Recovery diagnostic and correction prompts reuse immutable Prompt Versions,
-- retain the exact Recovery Case, and resume the canonical Recovery step.
select pg_temp.prepare_v2_review_fixture(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031', 'required', 'normal'
);
select * from public.open_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  'b3000000-0000-4000-8000-000000000061', 4, gen_random_uuid(),
  'The isolated behavior works', 'The isolated behavior failed', null, 'unsure',
  null, null
);
select * from public.transition_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  'b3000000-0000-4000-8000-000000000061',
  5, 1, 'investigating', '{"proposed_first_check":"Inspect the runtime value."}'
);
update public.v2_current_changes
set prompt_draft = 'Run the bounded diagnostic.', prompt_draft_version = 2,
    version = 7
where id = 'b3000000-0000-4000-8000-000000000031';
select * from public.accept_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  7, 2, gen_random_uuid(), 'diagnostic',
  'b3000000-0000-4000-8000-000000000061',
  'Run the bounded diagnostic.',
  encode(sha256(convert_to('Run the bounded diagnostic.', 'UTF8')), 'hex'),
  null, 'test-agent', 'standard', null, null
);
select * from public.handoff_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'b3000000-0000-4000-8000-000000000031'),
  'b3000000-0000-4000-8000-000000000061', 8, 1, gen_random_uuid()
);
select * from public.resume_v2_recovery_handoff(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  'b3000000-0000-4000-8000-000000000061',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'b3000000-0000-4000-8000-000000000031'),
  9, 2, 2
);
do $$
begin
  if not exists (
    select 1 from public.v2_current_changes as cc
    join public.v2_recovery_cases as rc on rc.current_change_id = cc.id
    where cc.id = 'b3000000-0000-4000-8000-000000000031'
      and cc.lifecycle_state = 'recovering'
      and cc.resume_step = 'recovery_investigate'
      and cc.version = 10
      and rc.id = 'b3000000-0000-4000-8000-000000000061'
      and rc.status = 'investigating' and rc.version = 2
  ) then
    raise exception 'Recovery diagnostic handoff did not resume investigating';
  end if;
end
$$;

select * from public.transition_v2_recovery_case(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  'b3000000-0000-4000-8000-000000000061',
  10, 2, 'correcting', '{"investigation_finding":"The runtime value was stale."}'
);
update public.v2_current_changes
set prompt_draft = 'Apply the bounded correction.', prompt_draft_version = 3,
    version = 12
where id = 'b3000000-0000-4000-8000-000000000031';
select * from public.accept_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  12, 3, gen_random_uuid(), 'correction',
  'b3000000-0000-4000-8000-000000000061',
  'Apply the bounded correction.',
  encode(sha256(convert_to('Apply the bounded correction.', 'UTF8')), 'hex'),
  null, 'test-agent', 'standard', null, null
);
select * from public.handoff_v2_prompt_version(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'b3000000-0000-4000-8000-000000000031'),
  'b3000000-0000-4000-8000-000000000061', 13, 1, gen_random_uuid()
);
select * from public.resume_v2_recovery_handoff(
  'b2000000-0000-4000-8000-000000000002',
  'b3000000-0000-4000-8000-000000000011',
  'b3000000-0000-4000-8000-000000000031',
  'b3000000-0000-4000-8000-000000000061',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'b3000000-0000-4000-8000-000000000031'),
  14, 3, 2
);
do $$
begin
  if not exists (
    select 1 from public.v2_current_changes as cc
    join public.v2_recovery_cases as rc on rc.current_change_id = cc.id
    where cc.id = 'b3000000-0000-4000-8000-000000000031'
      and cc.lifecycle_state = 'recovering'
      and cc.resume_step = 'recovery_recheck'
      and cc.version = 15
      and rc.id = 'b3000000-0000-4000-8000-000000000061'
      and rc.status = 'rechecking' and rc.version = 4
  ) then
    raise exception 'Recovery correction handoff did not resume rechecking';
  end if;
end
$$;

-- ---------------------------------------------------------------------------
-- Fact matrix/bounds and one-way Build Turn/Evidence mutation.
-- ---------------------------------------------------------------------------
insert into public.v2_build_turns (
  id, project_id, owner_user_id, current_change_id, turn_kind, speaker,
  content, retention_class
) values (
  'b2000000-0000-4000-8000-000000000081',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000031',
  'student_answer', 'student', 'The key was wrong.', 'structured'
);
do $$
begin
  begin
    insert into public.v2_project_facts (
      project_id, owner_user_id, fact_type, subject_key, value_kind, value_text,
      source_kind, source_record_type, source_record_id, status, observed_at
    ) values (
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'constraint', 'bad_matrix', 'text', 'bad', 'student_stated', 'check',
      'b2000000-0000-4000-8000-000000000051', 'active', now()
    );
    raise exception 'illegal Fact source matrix unexpectedly succeeded';
  exception when check_violation then null;
  end;
  begin
    insert into public.v2_project_facts (
      project_id, owner_user_id, fact_type, subject_key, value_kind, value_text,
      source_kind, source_record_type, source_record_id, status, observed_at
    ) values (
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'constraint', 'generation_source', 'text', 'bad', 'system_observed',
      'generation_attempt', 'b2000000-0000-4000-8000-000000000091',
      'active', now()
    );
    raise exception 'Generation Attempt became durable Fact provenance';
  exception when check_violation then null;
  end;
  begin
    insert into public.v2_project_facts (
      project_id, owner_user_id, fact_type, subject_key, value_kind,
      value_text_list, source_kind, source_record_type, source_record_id,
      status, observed_at
    ) values (
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'tool', 'bad_list', 'text_list', array['ok', '  '],
      'student_stated', 'build_turn',
      'b2000000-0000-4000-8000-000000000081', 'active', now()
    );
    raise exception 'Fact text-list with blank member unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan, plan_source,
  status, result, student_observation, create_command_id
) values (
  'b2000000-0000-4000-8000-000000000054',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'b2000000-0000-4000-8000-000000000031',
  'A later deliberately failing source-strength Check', 'student',
  'performed', 'did_not_work', 'It did not work.', gen_random_uuid()
);
do $$
begin
  begin
    insert into public.v2_project_facts (
      project_id, owner_user_id, fact_type, subject_key, value_kind,
      value_boolean, source_kind, source_record_type, source_record_id,
      status, observed_at
    ) values (
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'known_working_behavior', 'overstated_failed_check', 'boolean', true,
      'student_observed', 'check',
      'b2000000-0000-4000-8000-000000000054', 'active', now()
    );
    raise exception 'failed Check created an active known-working Fact';
  exception when check_violation then null;
  end;

  insert into public.v2_project_facts (
    project_id, owner_user_id, fact_type, subject_key, value_kind,
    value_boolean, source_kind, source_record_type, source_record_id,
    status, observed_at
  ) values (
    'b2000000-0000-4000-8000-000000000011',
    'b2000000-0000-4000-8000-000000000002',
    'known_working_behavior', 'valid_worked_check', 'boolean', true,
    'student_observed', 'check',
    'b2000000-0000-4000-8000-000000000051', 'active', now()
  );
end
$$;

insert into public.v2_project_facts (
  id, project_id, owner_user_id, fact_type, subject_key, value_kind, value_text,
  source_kind, source_record_type, source_record_id, status, observed_at
) values (
  'b2000000-0000-4000-8000-000000000091',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'constraint', 'supersession_fixture', 'text', 'Original constraint',
  'student_stated', 'build_turn',
  'b2000000-0000-4000-8000-000000000081', 'active', now()
);
insert into public.v2_project_facts (
  id, project_id, owner_user_id, fact_type, subject_key, value_kind, value_text,
  source_kind, source_record_type, source_record_id, status, observed_at,
  supersedes_fact_id
) values (
  'b2000000-0000-4000-8000-000000000092',
  'b2000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'constraint', 'supersession_fixture', 'text', 'Corrected constraint',
  'student_stated', 'build_turn',
  'b2000000-0000-4000-8000-000000000081', 'active', now(),
  'b2000000-0000-4000-8000-000000000091'
);
update public.v2_project_facts
set status = 'superseded', version = 2
where id = 'b2000000-0000-4000-8000-000000000091';
set constraints v2_80_project_facts_reciprocal immediate;
do $$
begin
  begin
    update public.v2_project_facts
    set supersedes_fact_id = null, version = 2
    where id = 'b2000000-0000-4000-8000-000000000092';
    raise exception 'clearing a Fact successor left a stranded predecessor';
  exception when check_violation then null;
  end;
  begin
    insert into public.v2_project_facts (
      id, project_id, owner_user_id, fact_type, subject_key, value_kind,
      value_text, source_kind, source_record_type, source_record_id, status,
      observed_at, supersedes_fact_id
    ) values (
      'b2000000-0000-4000-8000-000000000093',
      'b2000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'constraint', 'supersession_fixture', 'text', 'Conflicting successor',
      'student_stated', 'build_turn',
      'b2000000-0000-4000-8000-000000000081', 'active', now(),
      'b2000000-0000-4000-8000-000000000091'
    );
    raise exception 'conflicting Fact supersession unexpectedly succeeded';
  exception when unique_violation then null;
  end;
end
$$;

do $$
begin
  begin
    update public.v2_build_turns
    set content = null, structured_payload = null, redacted_at = now(),
        content_sha256 = repeat('0', 64)
    where id = 'b2000000-0000-4000-8000-000000000081';
    raise exception 'arbitrary replacement Build Turn hash unexpectedly succeeded';
  exception when check_violation then null;
  end;
  begin
    update public.v2_build_turns set redacted_at = now()
    where id = 'b2000000-0000-4000-8000-000000000081';
    raise exception 'raw Build Turn content survived a redaction transition';
  exception when check_violation then null;
  end;
end
$$;

update public.v2_build_turns
set content = null, structured_payload = null, redacted_at = now()
where id = 'b2000000-0000-4000-8000-000000000081';
do $$
begin
  if not exists (
    select 1 from public.v2_build_turns
    where id = 'b2000000-0000-4000-8000-000000000081'
      and content is null and structured_payload is null and redacted_at is not null
      and content_sha256 = encode(
        sha256(convert_to('The key was wrong.', 'UTF8')), 'hex'
      )
  ) then
    raise exception 'Build Turn redaction changed the original content hash';
  end if;
  begin
    update public.v2_build_turns set content = 'restored'
    where id = 'b2000000-0000-4000-8000-000000000081';
    raise exception 'Build Turn redaction unexpectedly reversed';
  exception when check_violation then null;
  end;
end
$$;

-- Canonical competency vocabulary and byte-oriented key bounds.
insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  create_command_id
) values (
  'c3000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'Teaching allowlist fixture', 'active', 'ready', gen_random_uuid()
);
do $$
begin
  begin
    insert into public.v2_current_changes (
      project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
      goal_snapshot, teaching_mode, teaching_target, teaching_reason_key,
      teaching_policy_version, risk, risk_policy_version, create_command_id
    ) values (
      'c3000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'build', 'preparing', 'intervention', 'Reject arbitrary competencies',
      'ask', 'invented_mastery_skill', 'policy_target', 'policy-v1',
      'normal', 'risk-v1', gen_random_uuid()
    );
    raise exception 'arbitrary teaching_target unexpectedly succeeded';
  exception when check_violation then null;
  end;

  begin
    insert into public.v2_current_changes (
      project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
      goal_snapshot, teaching_mode, teaching_target, teaching_reason_key,
      teaching_policy_version, risk, risk_policy_version, create_command_id
    ) values (
      'c3000000-0000-4000-8000-000000000011',
      'b2000000-0000-4000-8000-000000000002',
      'build', 'preparing', 'intervention', 'Reject oversized UTF-8 reason',
      'ask', 'testing', repeat('€', 86), 'policy-v1',
      'normal', 'risk-v1', gen_random_uuid()
    );
    raise exception 'multibyte reason exceeded the 256-byte bound';
  exception when check_violation then null;
  end;
end
$$;
insert into public.v2_current_changes (
  project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
  goal_snapshot, teaching_mode, teaching_target, teaching_reason_key,
  teaching_policy_version, risk, risk_policy_version, create_command_id
) values (
  'c3000000-0000-4000-8000-000000000011',
  'b2000000-0000-4000-8000-000000000002',
  'build', 'preparing', 'intervention', 'Accept canonical competency',
  'ask', 'testing', 'policy_target', 'policy-v1',
  'normal', 'risk-v1', gen_random_uuid()
);

-- ---------------------------------------------------------------------------
-- Fully populated permanent-project purge: every project-scoped table has a
-- row; evidence is minimized/deleted; the preference survives and versions.
-- ---------------------------------------------------------------------------
insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  coding_agent_key, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'Purple Dragon private project', 'active', 'ready', 'cursor',
  'a2000000-0000-4000-8000-000000000112'
);
insert into public.v2_plan_items (
  id, project_id, owner_user_id, label, intended_outcome,
  scope_band, status, order_key
) values (
  'a2000000-0000-4000-8000-000000000121',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'Private plan label', 'Private plan outcome', 'first_version', 'ready', 10
);
insert into public.v2_current_changes (
  id, project_id, owner_user_id, plan_item_id, change_kind,
  lifecycle_state, resume_step, goal_snapshot, done_condition_snapshot,
  prompt_draft, coding_agent_key, effort_category,
  teaching_mode, teaching_reason_key, teaching_policy_version,
  risk, risk_policy_version, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000131',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000121',
  'recovery', 'preparing', 'prompt', 'Private recovery goal', 'Private done',
  'Private correction prompt.', 'cursor', 'deep',
  'skip', 'policy_not_set', 'teaching-v1',
  'normal', 'risk-v1', 'a2000000-0000-4000-8000-000000000132'
);
insert into public.v2_generation_attempts (
  id, project_id, owner_user_id, target_current_change_id, purpose,
  target_aggregate_version, config_version, status, provider_key, model_key,
  input_sha256, attempt_command_id
) values (
  'a2000000-0000-4000-8000-000000000141',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000131', 'prompt_draft', 1,
  'config-v1', 'pending', 'provider', 'model', repeat('a', 64),
  'a2000000-0000-4000-8000-000000000142'
);
select * from public.accept_v2_prompt_version(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000131',
  1, 1, 'a2000000-0000-4000-8000-000000000151',
  'feature', null, 'Private correction prompt.',
  encode(sha256(convert_to('Private correction prompt.', 'UTF8')), 'hex'),
  null, 'cursor', 'deep', null, null
);
select * from public.handoff_v2_prompt_version(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000131',
  (select latest_prompt_version_id from public.v2_current_changes
    where id = 'a2000000-0000-4000-8000-000000000131'),
  null, 2, 1, 'a2000000-0000-4000-8000-000000000152'
);
select * from public.open_v2_recovery_case(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000131',
  'a2000000-0000-4000-8000-000000000161',
  3, 'a2000000-0000-4000-8000-000000000162',
  'Private intended behavior', 'Private symptom', null, 'no', null, null
);
insert into public.v2_build_turns (
  id, project_id, owner_user_id, current_change_id, recovery_case_id,
  turn_kind, speaker, content, retention_class
) values (
  'a2000000-0000-4000-8000-000000000171',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000131',
  'a2000000-0000-4000-8000-000000000161',
  'student_answer', 'student', 'Purple Dragon repository uses secret-name.ts.',
  'sensitive_short'
);
insert into public.v2_checks (
  id, project_id, owner_user_id, current_change_id, check_plan,
  plan_source, status, create_command_id
) values (
  'a2000000-0000-4000-8000-000000000181',
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000131',
  'Private check plan', 'codize', 'not_run',
  'a2000000-0000-4000-8000-000000000182'
);
insert into public.v2_project_facts (
  project_id, owner_user_id, fact_type, subject_key, value_kind, value_text,
  source_kind, source_record_type, source_record_id, status, observed_at
) values (
  'a2000000-0000-4000-8000-000000000111',
  'a2000000-0000-4000-8000-000000000001',
  'constraint', 'private_repo_detail', 'text', 'secret-name.ts',
  'student_stated', 'build_turn', 'a2000000-0000-4000-8000-000000000171',
  'active', now()
);
insert into public.v2_learner_evidence (
  id, owner_user_id, source_project_id, source_current_change_id,
  competency_key, observed_behavior, elicitation, support_level, context_key,
  source_record_type, source_record_id, source_operation_id, observed_at,
  status, evidence_policy_version
) values
  (
    'a2000000-0000-4000-8000-000000000191',
    'a2000000-0000-4000-8000-000000000001',
    'a2000000-0000-4000-8000-000000000111',
    'a2000000-0000-4000-8000-000000000131',
    'debugging', 'Found Purple Dragon bug in secret-name.ts.',
    'asked', 'nudge', 'recovery', 'build_turn',
    'a2000000-0000-4000-8000-000000000171',
    'a2000000-0000-4000-8000-000000000192', now(), 'active',
    'qualification-v1'
  ),
  (
    'a2000000-0000-4000-8000-000000000193',
    'a2000000-0000-4000-8000-000000000001',
    'a2000000-0000-4000-8000-000000000111',
    'a2000000-0000-4000-8000-000000000131',
    'testing', 'Tested Purple Dragon private repository.',
    'asked', 'none', 'recovery', 'build_turn',
    'a2000000-0000-4000-8000-000000000171',
    'a2000000-0000-4000-8000-000000000194', now(), 'active',
    'qualification-v1'
  );
insert into public.v2_user_preferences (
  owner_user_id, active_v2_project_id
) values (
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111'
);

do $$
begin
  begin
    update public.v2_learner_evidence
    set observed_behavior = 'Arbitrarily rewritten', version = 2
    where id = 'a2000000-0000-4000-8000-000000000191';
    raise exception 'ordinary learner Evidence rewrite unexpectedly succeeded';
  exception when check_violation then null;
  end;
end
$$;

update public.v2_projects
set lifecycle_state = 'deletion_pending',
    deletion_requested_at = now() - interval '2 minutes',
    purge_after = now() - interval '1 minute',
    deletion_command_id = 'a2000000-0000-4000-8000-000000000113',
    version = 2
where id = 'a2000000-0000-4000-8000-000000000111';

do $$
begin
  begin
    delete from public.v2_projects
    where id = 'a2000000-0000-4000-8000-000000000111';
    raise exception 'direct backend Project delete bypassed the purge transaction';
  exception when check_violation then null;
  end;
  if not exists (
    select 1 from public.v2_projects
    where id = 'a2000000-0000-4000-8000-000000000111'
  ) then
    raise exception 'blocked direct Project delete was not rolled back';
  end if;
end
$$;

select public.purge_v2_project(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111', 2, 'standard',
  '[
    {"evidence_id":"a2000000-0000-4000-8000-000000000191","expected_version":1,"action":"minimize"}
  ]'
);

do $$
begin
  if exists (select 1 from public.v2_projects
      where id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_plan_items
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_current_changes
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_prompt_versions
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_checks
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_project_facts
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_build_turns
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_generation_attempts
      where project_id = 'a2000000-0000-4000-8000-000000000111')
     or exists (select 1 from public.v2_recovery_cases
      where project_id = 'a2000000-0000-4000-8000-000000000111') then
    raise exception 'fully populated V2 Project did not cascade-purge cleanly';
  end if;
  if not exists (
    select 1 from public.v2_user_preferences
    where owner_user_id = 'a2000000-0000-4000-8000-000000000001'
      and active_v2_project_id is null and version = 2
  ) then
    raise exception 'preference did not survive purge with exact +1 detach';
  end if;
  if not exists (
    select 1 from public.v2_learner_evidence
    where id = 'a2000000-0000-4000-8000-000000000191'
      and source_project_id is null and source_current_change_id is null
      and source_record_type = 'minimized' and source_record_id is null
      and source_operation_id is null and source_minimized_at is not null
      and version = 2
      and observed_behavior =
        'Observed this competency in a prior project without retained project details.'
      and observed_behavior not ilike '%Purple Dragon%'
      and observed_behavior not ilike '%secret-name%'
  ) or exists (
    select 1 from public.v2_learner_evidence
    where id = 'a2000000-0000-4000-8000-000000000193'
  ) then
    raise exception 'learner Evidence purge minimization/deletion was incomplete';
  end if;
end
$$;

-- Safe absence replay does not disclose whether the project existed.
select public.purge_v2_project(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000111', 1, 'standard', '[]'
);

insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  create_command_id
) values (
  'a2000000-0000-4000-8000-000000000211',
  'a2000000-0000-4000-8000-000000000001',
  'Temporary recovery discard fixture', 'temporary_recovery', 'ready',
  'a2000000-0000-4000-8000-000000000212'
);
select public.purge_v2_project(
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000211', 1,
  'temporary_recovery', '[]'
);

insert into public.v2_projects (
  id, owner_user_id, display_name, lifecycle_state, setup_resume_step,
  create_command_id
) values (
  'a4000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'Bulk purge fixture', 'temporary_recovery', 'ready', gen_random_uuid()
);
insert into public.v2_build_turns (
  id, project_id, owner_user_id, turn_kind, speaker, content, retention_class
) values (
  'a4000000-0000-4000-8000-000000000081',
  'a4000000-0000-4000-8000-000000000011',
  'a2000000-0000-4000-8000-000000000001',
  'student_answer', 'student', 'Private bulk evidence source.', 'sensitive_short'
);
insert into public.v2_learner_evidence (
  owner_user_id, source_project_id, competency_key, observed_behavior,
  elicitation, support_level, context_key, source_record_type,
  source_record_id, source_operation_id, observed_at, status,
  evidence_policy_version
)
select
  'a2000000-0000-4000-8000-000000000001'::uuid,
  'a4000000-0000-4000-8000-000000000011'::uuid,
  'testing', 'Private bulk evidence row ' || series.n,
  'asked', 'none', 'transfer', 'build_turn',
  'a4000000-0000-4000-8000-000000000081'::uuid,
  gen_random_uuid(), now(), 'active', 'qualification-v1'
from generate_series(1, 300) as series(n);
select public.purge_v2_project(
  'a2000000-0000-4000-8000-000000000001',
  'a4000000-0000-4000-8000-000000000011', 1,
  'temporary_recovery', '[]'
);
do $$
begin
  if exists (
    select 1 from public.v2_projects
    where id = 'a4000000-0000-4000-8000-000000000011'
  ) or exists (
    select 1 from public.v2_learner_evidence
    where source_project_id = 'a4000000-0000-4000-8000-000000000011'
  ) then
    raise exception 'Project with more than 256 Evidence rows did not purge';
  end if;
end
$$;

reset role;
rollback;

select 'Codize V2.2 database foundation verification passed' as result;
