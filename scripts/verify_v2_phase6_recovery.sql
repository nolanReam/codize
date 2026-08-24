-- Phase 6 Recovery verification for an isolated, freshly migrated PostgreSQL 17 database.
-- Covers cross-owner denial, stale writers, exact replay, agent_claimed provenance,
-- student-performed rechecks, atomic rollback, retry loops, and resolved completion.
begin;

do $$
declare v_commands constant text[] := array[
  'record_v2_recovery_symptom',
  'record_v2_recovery_investigation_return',
  'record_v2_recovery_correction_return',
  'record_v2_recovery_check'
];
begin
  if (select pg_catalog.count(*) from pg_catalog.pg_class as c
      where c.relnamespace='public'::regnamespace
        and c.relname like 'v2\_%' escape '\' and c.relkind='r') <> 11 then
    raise exception 'Phase 6 changed the canonical eleven-table boundary';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace='public'::regnamespace and p.proname=any(v_commands)
        and not p.prosecdef and p.proconfig @> array['search_path=""']
        and pg_catalog.has_function_privilege('service_role',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('anon',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated',p.oid,'EXECUTE')) <> 4 then
    raise exception 'Phase 6 public wrappers are not safely granted';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace='codize_v2_internal'::regnamespace
        and p.proname=any(v_commands) and p.prosecdef
        and p.proconfig @> array['search_path=""']
        and pg_catalog.pg_get_userbyid(p.proowner)='codize_v2_executor'
        and pg_catalog.has_function_privilege('service_role',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('anon',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated',p.oid,'EXECUTE')) <> 4 then
    raise exception 'Phase 6 internal commands are not safely owned and granted';
  end if;
end $$;

insert into auth.users(id) values
  ('f6000000-0000-4000-8000-000000000001'),
  ('f6000000-0000-4000-8000-000000000002');

set local role service_role;
do $$
declare
  v_owner constant uuid := 'f6000000-0000-4000-8000-000000000001';
  v_other constant uuid := 'f6000000-0000-4000-8000-000000000002';
  v_item constant uuid := 'f6000000-0000-4000-8000-000000000201';
  v_recovery constant uuid := 'f6000000-0000-4000-8000-000000000301';
  v_check constant uuid := 'f6000000-0000-4000-8000-000000000401';
  v_retry constant uuid := 'f6000000-0000-4000-8000-000000000402';
  v_open_command constant uuid := 'f6000000-0000-4000-8000-000000000501';
  v_rollback_command constant uuid := 'f6000000-0000-4000-8000-000000000502';
  v_feature constant text := 'Add a visible score control.';
  v_diagnostic constant text := 'INVESTIGATION ONLY. Inspect the score update path and do not edit files.';
  v_correction constant text := 'Make the smallest targeted score correction and preserve unrelated behavior.';
  v_goal constant text := 'Show a score control';
  v_done constant text := 'Adding a point visibly changes the score';
  v_project uuid;
  v_change uuid;
  v_prompt uuid;
  v_result jsonb;
  v_completed record;
  v_observed_at timestamptz;
begin
  v_result := public.create_v2_project(v_owner,pg_catalog.gen_random_uuid(),
    'Phase 6 verifier','new_idea',null,null);
  v_project := (v_result->'project'->>'id')::uuid;
  perform public.establish_v2_manual_project(v_owner,v_project,1,
    pg_catalog.gen_random_uuid(),'A small score tracker',v_item,
    v_goal,v_done);
  v_result := public.start_v2_current_change(v_owner,v_project,2,
    pg_catalog.gen_random_uuid(),v_item,'build','ignored');
  v_change := (v_result->'current_change'->>'id')::uuid;
  perform public.resolve_v2_current_change_policy(v_owner,v_project,v_change,1,
    pg_catalog.gen_random_uuid(),'skip',null,'no_intervention_required',
    'phase5-beta-teaching-v1','normal',null,'phase5-beta-risk-v1','required',null);
  perform public.update_v2_coding_agent(v_owner,v_project,v_change,2,2,'codex');
  perform public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,3,1,
    v_feature,v_done,array[]::text[],'normal',null,'phase5-beta-risk-v1',
    public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_feature));
  perform public.record_v2_effort_attempt(v_owner,v_project,v_change,4,
    pg_catalog.gen_random_uuid(),'standard','standard',true);
  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    v_owner,v_project,v_change,5,2,pg_catalog.gen_random_uuid(),'feature',null,
    v_feature,pg_catalog.encode(pg_catalog.sha256(
      pg_catalog.convert_to(v_feature,'UTF8')),'hex'),null,'codex','standard',null,null);
  perform public.handoff_v2_prompt_version(v_owner,v_project,v_change,v_prompt,null,6,1,
    pg_catalog.gen_random_uuid());
  v_result := public.record_v2_manual_return(v_owner,v_project,v_change,7,
    pg_catalog.gen_random_uuid(),'broken',null);
  if (v_result->'current_change'->>'resume_step')<>'recovery_symptom' then
    raise exception 'broken return did not enter contextual Recovery';
  end if;

  -- Cross-owner access must fail before revealing any aggregate state.
  begin
    perform public.record_v2_recovery_symptom(v_other,v_project,v_change,v_recovery,8,
      v_open_command,'Score remains zero','It worked before','yes',v_diagnostic,
      'normal',null,'phase5-beta-risk-v1',
      public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_diagnostic));
    raise exception 'cross-owner Recovery command unexpectedly passed';
  exception when no_data_found then null;
  end;

  v_result := public.record_v2_recovery_symptom(v_owner,v_project,v_change,v_recovery,8,
    v_open_command,'Score remains zero','It worked before','yes',v_diagnostic,
    'normal',null,'phase5-beta-risk-v1',
    public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_diagnostic));
  if (v_result->'recovery_case'->>'status')<>'investigating'
     or (v_result->'current_change'->>'version')::bigint<>9 then
    raise exception 'Recovery symptom was not stored atomically';
  end if;
  v_result := public.record_v2_recovery_symptom(v_owner,v_project,v_change,v_recovery,8,
    v_open_command,'Score remains zero','It worked before','yes',v_diagnostic,
    'normal',null,'phase5-beta-risk-v1',
    public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_diagnostic));
  if not (v_result->>'replayed')::boolean
     or (select version from public.v2_current_changes where id=v_change)<>9 then
    raise exception 'Recovery symptom replayed state was not stable';
  end if;
  begin
    perform public.record_v2_recovery_symptom(v_owner,v_project,v_change,
      pg_catalog.gen_random_uuid(),8,pg_catalog.gen_random_uuid(),'A stale symptom',null,
      'unsure',v_diagnostic,'normal',null,'phase5-beta-risk-v1',
      public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_diagnostic));
    raise exception 'stale Recovery writer unexpectedly passed';
  exception when unique_violation or serialization_failure then null;
  end;

  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    v_owner,v_project,v_change,9,3,pg_catalog.gen_random_uuid(),'diagnostic',v_recovery,
    v_diagnostic,pg_catalog.encode(pg_catalog.sha256(
      pg_catalog.convert_to(v_diagnostic,'UTF8')),'hex'),null,'codex','standard',null,null);
  perform public.handoff_v2_prompt_version(v_owner,v_project,v_change,v_prompt,v_recovery,
    10,1,pg_catalog.gen_random_uuid());
  v_result := public.record_v2_recovery_investigation_return(
    v_owner,v_project,v_change,v_recovery,11,pg_catalog.gen_random_uuid(),
    'The reducer returns the previous state in its increment branch.',
    'Correct only the increment branch.',v_correction,'normal',null,
    'phase5-beta-risk-v1',
    public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_correction));
  if (v_result->'recovery_case'->>'status')<>'correcting'
     or not exists(select 1 from public.v2_build_turns
       where recovery_case_id=v_recovery and turn_kind='return_report'
         and structured_payload->>'provenance'='agent_claimed') then
    raise exception 'investigation finding lost agent_claimed provenance';
  end if;

  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    v_owner,v_project,v_change,12,4,pg_catalog.gen_random_uuid(),'correction',v_recovery,
    v_correction,pg_catalog.encode(pg_catalog.sha256(
      pg_catalog.convert_to(v_correction,'UTF8')),'hex'),null,'codex','standard',null,null);
  perform public.handoff_v2_prompt_version(v_owner,v_project,v_change,v_prompt,v_recovery,
    13,1,pg_catalog.gen_random_uuid());
  v_result := public.record_v2_recovery_correction_return(
    v_owner,v_project,v_change,v_recovery,14,pg_catalog.gen_random_uuid(),v_check,v_done);
  if (v_result->'check'->>'status')<>'proposed'
     or (v_result->'recovery_case'->>'status')<>'rechecking' then
    raise exception 'correction return accepted an agent claim instead of proposing a recheck';
  end if;

  -- A late duplicate successor failure must roll back the performed Check and Build Turn.
  begin
    perform public.record_v2_recovery_check(v_owner,v_project,v_change,v_recovery,
      v_check,15,1,v_rollback_command,'unsure','I could not tell yet.',true,v_check,
      null,null,null,null,null);
    raise exception 'duplicate recheck successor unexpectedly passed';
  exception when check_violation then null;
  end;
  if not exists(select 1 from public.v2_checks where id=v_check and status='proposed' and version=1)
     or (select version from public.v2_current_changes where id=v_change)<>15
     or exists(select 1 from public.v2_build_turns where id=v_rollback_command) then
    raise exception 'student-performed recheck failure did not rollback atomically';
  end if;

  -- Exercise UNSURE and failed recheck semantics in a subtransaction, then restore
  -- the same ready-to-recheck fixture for the successful resolution path.
  begin
    v_result := public.record_v2_recovery_check(v_owner,v_project,v_change,v_recovery,
      v_check,15,1,pg_catalog.gen_random_uuid(),'unsure','The display changed too quickly.',
      true,v_retry,null,null,null,null,null);
    if (v_result->'next_check'->>'id')::uuid<>v_retry
       or (v_result->'recovery_case'->>'status')<>'rechecking' then
      raise exception 'UNSURE did not stay incomplete with one successor';
    end if;
    v_result := public.record_v2_recovery_check(v_owner,v_project,v_change,v_recovery,
      v_retry,16,1,pg_catalog.gen_random_uuid(),'did_not_work','Score remained zero.',
      true,null,v_diagnostic,'normal',null,'phase5-beta-risk-v1',
      public.v2_risk_input_fingerprint(v_goal,v_done,array[]::text[],v_diagnostic));
    if (v_result->'recovery_case'->>'status')<>'investigating'
       or (v_result->'current_change'->>'resume_step')<>'recovery_investigate' then
      raise exception 'failed recheck did not loop to investigation';
    end if;
    raise exception using errcode='P6001',message='rollback exercised retry branch';
  exception when sqlstate 'P6001' then null;
  end;

  v_result := public.record_v2_recovery_check(v_owner,v_project,v_change,v_recovery,
    v_check,15,1,pg_catalog.gen_random_uuid(),'worked',
    'I added a point and personally saw the score change from 0 to 1.',true,null,
    null,null,null,null,null);
  if (v_result->'check'->>'status')<>'performed'
     or (v_result->'check'->>'result')<>'worked'
     or (v_result->'recovery_case'->>'status')<>'rechecking' then
    raise exception 'student-performed successful recheck was not preserved for completion';
  end if;
  select performed_at into v_observed_at from public.v2_checks where id=v_check;
  select * into v_completed from public.complete_v2_current_change(
    v_owner,v_project,v_change,16,2,1,pg_catalog.gen_random_uuid(),true,
    'I added a point and personally saw the score change from 0 to 1.',null,
    pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object(
      'fact_type','known_working_behavior','subject_key','phase6/recheck',
      'value_kind','text','value','Score changed from 0 to 1',
      'source_kind','student_observed','source_record_type','check',
      'source_record_id',v_check,'observed_at',v_observed_at)),
    pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object(
      'competency_key','testing','observed_behavior','Performed the Recovery recheck.',
      'elicitation','taught','support_level','teach','context_key','recovery',
      'source_record_type','check','source_record_id',v_check,
      'observed_at',v_observed_at,'evidence_policy_version','phase5-beta-evidence-v1')));
  if v_completed.current_change_state<>'completed'
     or v_completed.recovery_case_status<>'resolved'
     or not exists(select 1 from public.v2_recovery_cases
       where id=v_recovery and status='resolved' and resolved_at is not null
         and resolution_summary like 'I added a point%') then
    raise exception 'Recovery and Current Change were not resolved atomically';
  end if;
end $$;
reset role;

set local role anon;
do $$ begin
  begin
    perform public.record_v2_recovery_symptom(
      'f6000000-0000-4000-8000-000000000001',pg_catalog.gen_random_uuid(),
      pg_catalog.gen_random_uuid(),pg_catalog.gen_random_uuid(),1,
      pg_catalog.gen_random_uuid(),'blocked',null,'unsure','blocked','normal',null,
      'phase5-beta-risk-v1','blocked');
    raise exception 'anon unexpectedly executed a Phase 6 RPC';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;

rollback;
