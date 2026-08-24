-- Phase 5 adaptive-teaching verification for an isolated PostgreSQL 17 database.
begin;

do $$
declare v_commands constant text[] := array[
  'disclose_v2_teaching_help', 'record_v2_teaching_response',
  'record_v2_effort_attempt', 'create_v2_student_check_plan',
  'update_v2_prompt_draft_with_risk'
];
begin
  if (select pg_catalog.count(*) from pg_catalog.pg_class as c
      where c.relnamespace='public'::regnamespace and c.relname like 'v2\_%' escape '\'
        and c.relkind='r') <> 11 then
    raise exception 'Phase 5 changed the canonical eleven-table boundary';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace='public'::regnamespace and p.proname=any(v_commands)
        and not p.prosecdef and p.proconfig @> array['search_path=""']
        and pg_catalog.has_function_privilege('service_role',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('anon',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated',p.oid,'EXECUTE')) <> 5 then
    raise exception 'Phase 5 public wrappers are not safely granted';
  end if;
  if (select pg_catalog.count(*) from pg_catalog.pg_proc as p
      where p.pronamespace='codize_v2_internal'::regnamespace
        and p.proname=any(v_commands) and p.prosecdef
        and p.proconfig @> array['search_path=""']
        and pg_catalog.pg_get_userbyid(p.proowner)='codize_v2_executor'
        and pg_catalog.has_function_privilege('service_role',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('anon',p.oid,'EXECUTE')
        and not pg_catalog.has_function_privilege('authenticated',p.oid,'EXECUTE')) <> 5 then
    raise exception 'Phase 5 internal commands are not safely owned and granted';
  end if;
end $$;

insert into auth.users(id) values
  ('f5000000-0000-4000-8000-000000000001'),
  ('f5000000-0000-4000-8000-000000000002');

set local role service_role;
do $$
declare
  v_owner constant uuid := 'f5000000-0000-4000-8000-000000000001';
  v_other constant uuid := 'f5000000-0000-4000-8000-000000000002';
  v_item constant uuid := 'f5000000-0000-4000-8000-000000000201';
  v_check constant uuid := 'f5000000-0000-4000-8000-000000000301';
  v_project uuid;
  v_change uuid;
  v_prompt uuid;
  v_result jsonb;
begin
  v_result := public.create_v2_project(v_owner,
    'f5000000-0000-4000-8000-000000000101','Phase 5 verifier','new_idea',null,null);
  v_project := (v_result->'project'->>'id')::uuid;
  v_result := public.establish_v2_manual_project(v_owner,v_project,1,
    'f5000000-0000-4000-8000-000000000102','A small score tracker',v_item,
    'Show a score summary','The visible score summary updates after a point');
  v_result := public.start_v2_current_change(v_owner,v_project,2,
    'f5000000-0000-4000-8000-000000000103',v_item,'build','ignored');
  v_change := (v_result->'current_change'->>'id')::uuid;

  v_result := public.resolve_v2_current_change_policy(v_owner,v_project,v_change,1,
    'f5000000-0000-4000-8000-000000000104','teach','protect_working_behavior',
    'working_boundary_not_supplied','phase5-beta-teaching-v1','normal',null,
    'phase5-beta-risk-v1','required',null);
  if (v_result->'current_change'->>'teaching_policy_version')='unresolved-v0'
     or (v_result->'current_change'->>'risk_policy_version')='unresolved-v0'
     or (v_result->'current_change'->>'resume_step')<>'intervention' then
    raise exception 'deterministic policy did not resolve atomically';
  end if;
  v_result := public.resolve_v2_current_change_policy(v_owner,v_project,v_change,1,
    'f5000000-0000-4000-8000-000000000104','teach','protect_working_behavior',
    'working_boundary_not_supplied','phase5-beta-teaching-v1','normal',null,
    'phase5-beta-risk-v1','required',null);
  if not (v_result->>'replayed')::boolean then
    raise exception 'policy command did not replay';
  end if;

  begin
    perform public.update_v2_coding_agent(v_owner,v_project,v_change,2,2,'codex');
    raise exception 'agent selection bypassed the intervention';
  exception when check_violation then null;
  end;

  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,2,
    'f5000000-0000-4000-8000-000000000105','prebuild');
  if (v_result->'current_change'->>'support_level_disclosed')<>'nudge' then
    raise exception 'first help did not disclose a nudge';
  end if;
  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,3,
    'f5000000-0000-4000-8000-000000000106','prebuild');
  if (v_result->'current_change'->>'support_level_disclosed')<>'clue' then
    raise exception 'second help did not disclose a clue';
  end if;
  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,4,
    'f5000000-0000-4000-8000-000000000107','prebuild');
  if (v_result->'current_change'->>'support_level_disclosed')<>'teach' then
    raise exception 'final help did not disclose direct teaching';
  end if;
  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,4,
    'f5000000-0000-4000-8000-000000000107','prebuild');
  if not (v_result->>'replayed')::boolean
     or (select pg_catalog.count(*) from public.v2_learner_evidence
         where source_current_change_id=v_change and competency_key='protect_working_behavior')<>3 then
    raise exception 'help replay duplicated evidence';
  end if;

  begin
    perform public.disclose_v2_teaching_help(v_other,v_project,v_change,5,
      'f5000000-0000-4000-8000-000000000108','prebuild');
    raise exception 'cross-owner help unexpectedly succeeded';
  exception when no_data_found then null;
  end;

  v_result := public.record_v2_teaching_response(v_owner,v_project,v_change,5,
    'f5000000-0000-4000-8000-000000000109','prebuild',
    'Keep the existing point controls working','taught','teach');
  if (v_result->'current_change'->>'resume_step')<>'choose_agent'
     or not ((v_result->'current_change'->'boundary_snapshots') ? 'Keep the existing point controls working') then
    raise exception 'teaching response did not persist its structured boundary';
  end if;

  perform public.update_v2_coding_agent(v_owner,v_project,v_change,2,6,'codex');
  perform public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,7,1,
    'Add the score summary and preserve the point controls.',
    'The visible score summary updates after a point',
    array['Keep the existing point controls working'],'normal',null,
    'phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Show a score summary','The visible score summary updates after a point',
      array['Keep the existing point controls working'],
      'Add the score summary and preserve the point controls.'));
  begin
    perform public.update_v2_effort(v_owner,v_project,v_change,8,'deep');
    raise exception 'legacy effort mutation bypassed Phase 5 teaching';
  exception when check_violation then null;
  end;
  v_result := public.record_v2_effort_attempt(v_owner,v_project,v_change,8,
    'f5000000-0000-4000-8000-000000000110','quick','standard',false);
  if not (v_result->'feedback'->>'retry_allowed')::boolean
     or (v_result->'feedback'->>'recommended') is not null
     or (v_result->'current_change'->>'effort_category') is not null
     or not exists(select 1 from public.v2_learner_evidence
       where source_operation_id='f5000000-0000-4000-8000-000000000110'
         and elicitation='after_hint' and support_level='nudge') then
    raise exception 'first effort mismatch did not preserve student retry';
  end if;
  v_result := public.record_v2_effort_attempt(v_owner,v_project,v_change,9,
    'f5000000-0000-4000-8000-000000000111','deep','standard',false);
  if not (v_result->'feedback'->>'revealed')::boolean
     or (v_result->'feedback'->>'recommended')<>'standard'
     or (v_result->'current_change'->>'effort_category')<>'standard'
     or not exists(select 1 from public.v2_learner_evidence
       where source_operation_id='f5000000-0000-4000-8000-000000000111'
         and elicitation='taught' and support_level='teach') then
    raise exception 'second effort mismatch did not reveal and apply the recommendation';
  end if;

  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    v_owner,v_project,v_change,10,2,'f5000000-0000-4000-8000-000000000112',
    'feature',null,'Add the score summary and preserve the point controls.',
    pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
      'Add the score summary and preserve the point controls.','UTF8')),'hex'),
    null,'codex','standard',null,null);
  perform public.handoff_v2_prompt_version(v_owner,v_project,v_change,v_prompt,null,11,1,
    'f5000000-0000-4000-8000-000000000113');
  v_result := public.record_v2_manual_return(v_owner,v_project,v_change,12,
    'f5000000-0000-4000-8000-000000000114','worked',null);
  if (v_result->>'check') is not null
     or (v_result->'current_change'->>'resume_step')<>'check' then
    raise exception 'adaptive return did not preserve the student Check-planning seam';
  end if;

  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,13,
    'f5000000-0000-4000-8000-000000000116','verification');
  if (v_result->'current_change'->>'support_level_disclosed')<>'nudge'
     or (v_result->'current_change'->>'help_context_key')<>'testing' then
    raise exception 'verification help did not start in its own context';
  end if;

  -- Exercise student-authored verification without manufacturing a result.
  v_result := public.create_v2_student_check_plan(v_owner,v_project,v_change,14,
    'f5000000-0000-4000-8000-000000000115',v_check,
    'Add one point and observe the visible score summary increase',
    'after_hint','nudge');
  if (v_result->'check'->>'plan_source')<>'student'
     or (v_result->'check'->>'status')<>'proposed'
     or (v_result->'check'->>'result') is not null
     or (v_result->'check'->>'version')::bigint<>1
     or not exists(select 1 from public.v2_learner_evidence
       where source_operation_id='f5000000-0000-4000-8000-000000000115'
          and competency_key='testing' and elicitation='after_hint'
          and support_level='nudge') then
    raise exception 'verification teaching manufactured or rewrote a Check result';
  end if;
  v_result := public.record_v2_manual_check(v_owner,v_project,v_change,v_check,15,1,
    'f5000000-0000-4000-8000-000000000117','worked',
    'I added one point and saw the summary increase',true,null);
  begin
    perform public.record_v2_teaching_response(v_owner,v_project,v_change,16,
      'f5000000-0000-4000-8000-000000000120','understanding',
      'The point action updates the visible summary','after_hint','clue');
    raise exception 'verification clue leaked into understanding response support';
  exception when check_violation then null;
  end;
  v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,16,
    'f5000000-0000-4000-8000-000000000118','understanding');
  if (v_result->'current_change'->>'support_level_disclosed')<>'nudge'
     or (v_result->'current_change'->>'help_context_key')<>'causal_explanation' then
    raise exception 'understanding help leaked the verification help level';
  end if;
  v_result := public.record_v2_teaching_response(v_owner,v_project,v_change,17,
    'f5000000-0000-4000-8000-000000000119','understanding',
    'Looks good','after_hint','nudge');
  if exists(select 1 from public.v2_learner_evidence
      where source_operation_id='f5000000-0000-4000-8000-000000000119') then
    raise exception 'generic understanding prose created strong evidence';
  end if;
end $$;
reset role;

-- A committed Check-plan command must replay its persisted qualification even
-- though the successful write clears the mutable support state. Build a fresh
-- ready-to-check Current Change for every replay-matrix row so the cases remain
-- independent and the strict new-command guard is exercised separately.
create function pg_temp.prepare_phase5_check_replay_fixture(p_owner uuid,p_label text)
returns jsonb language plpgsql set search_path=''
as $$
declare
  v_item uuid := pg_catalog.gen_random_uuid();
  v_project uuid;
  v_change uuid;
  v_prompt uuid;
  v_result jsonb;
  v_prompt_text constant text := 'Add a visible score summary.';
begin
  v_result := public.create_v2_project(p_owner,pg_catalog.gen_random_uuid(),p_label,
    'new_idea',null,null);
  v_project := (v_result->'project'->>'id')::uuid;
  perform public.establish_v2_manual_project(p_owner,v_project,1,
    pg_catalog.gen_random_uuid(),'A small score tracker',v_item,
    'Show a score summary','The visible score summary updates after a point');
  v_result := public.start_v2_current_change(p_owner,v_project,2,
    pg_catalog.gen_random_uuid(),v_item,'build','ignored');
  v_change := (v_result->'current_change'->>'id')::uuid;
  perform public.resolve_v2_current_change_policy(p_owner,v_project,v_change,1,
    pg_catalog.gen_random_uuid(),'skip',null,'no_intervention_required',
    'phase5-beta-teaching-v1','normal',null,'phase5-beta-risk-v1','required',null);
  perform public.update_v2_coding_agent(p_owner,v_project,v_change,2,2,'codex');
  perform public.update_v2_prompt_draft_with_risk(p_owner,v_project,v_change,3,1,
    v_prompt_text,'The visible score summary updates after a point',array[]::text[],
    'normal',null,'phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Show a score summary','The visible score summary updates after a point',
      array[]::text[],v_prompt_text));
  perform public.record_v2_effort_attempt(p_owner,v_project,v_change,4,
    pg_catalog.gen_random_uuid(),'standard','standard',true);
  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    p_owner,v_project,v_change,5,2,pg_catalog.gen_random_uuid(),'feature',null,
    v_prompt_text,pg_catalog.encode(pg_catalog.sha256(
      pg_catalog.convert_to(v_prompt_text,'UTF8')),'hex'),
    null,'codex','standard',null,null);
  perform public.handoff_v2_prompt_version(p_owner,v_project,v_change,v_prompt,null,6,1,
    pg_catalog.gen_random_uuid());
  v_result := public.record_v2_manual_return(p_owner,v_project,v_change,7,
    pg_catalog.gen_random_uuid(),'worked',null);
  return pg_catalog.jsonb_build_object('project_id',v_project,'change_id',v_change,
    'current_change',v_result->'current_change');
end;
$$;
grant execute on function pg_temp.prepare_phase5_check_replay_fixture(uuid,text)
  to service_role;

set local role service_role;
do $$
declare
  v_owner constant uuid := 'f5000000-0000-4000-8000-000000000001';
  v_case record;
  v_fixture jsonb;
  v_project uuid;
  v_change uuid;
  v_command uuid;
  v_check uuid;
  v_version bigint;
  v_post_version bigint;
  v_result jsonb;
  v_original jsonb;
  v_i integer;
begin
  for v_case in
    select * from (values
      ('none',0,'asked','none'),
      ('nudge',1,'after_hint','nudge'),
      ('clue',2,'after_hint','clue'),
      ('teach',3,'taught','teach')
    ) as cases(label,help_count,elicitation,support)
  loop
    v_fixture := pg_temp.prepare_phase5_check_replay_fixture(
      v_owner,'Check replay ' || v_case.label);
    v_project := (v_fixture->>'project_id')::uuid;
    v_change := (v_fixture->>'change_id')::uuid;
    v_version := (v_fixture->'current_change'->>'version')::bigint;

    for v_i in 1..v_case.help_count loop
      v_result := public.disclose_v2_teaching_help(v_owner,v_project,v_change,v_version,
        pg_catalog.gen_random_uuid(),'verification');
      v_version := (v_result->'current_change'->>'version')::bigint;
    end loop;

    v_command := pg_catalog.gen_random_uuid();
    v_check := pg_catalog.gen_random_uuid();
    v_original := public.create_v2_student_check_plan(
      v_owner,v_project,v_change,v_version,v_command,v_check,
      'Add one point and observe the visible score summary increase',
      v_case.elicitation,v_case.support);
    v_post_version := (v_original->'current_change'->>'version')::bigint;
    if (v_original->>'replayed')::boolean
       or (v_original->'current_change'->>'support_level_disclosed')<>'none' then
      raise exception 'Check replay % first write was not canonical',v_case.label;
    end if;

    -- This is the response-loss retry for every help depth, especially Clue:
    -- the caller ignores the committed response and retries its original ID.
    v_result := public.create_v2_student_check_plan(
      v_owner,v_project,v_change,v_version,v_command,v_check,
      'Add one point and observe the visible score summary increase',
      v_case.elicitation,v_case.support);
    if not (v_result->>'replayed')::boolean
       or v_result->'current_change' is distinct from v_original->'current_change'
       or v_result->'check' is distinct from v_original->'check'
       or (v_result->'current_change'->>'version')::bigint<>v_post_version
       or (select pg_catalog.count(*) from public.v2_checks where id=v_check)<>1
       or (select pg_catalog.count(*) from public.v2_learner_evidence
           where source_operation_id=v_command)<>1
       or not exists(select 1 from public.v2_learner_evidence
           where source_operation_id=v_command
             and elicitation=v_case.elicitation and support_level=v_case.support) then
      raise exception 'Check replay % changed or duplicated its canonical result',v_case.label;
    end if;

    begin
      perform public.create_v2_student_check_plan(
        v_owner,v_project,v_change,v_version,v_command,v_check,
        'Observe a materially different result',v_case.elicitation,v_case.support);
      raise exception 'Check replay % accepted a mismatched payload',v_case.label;
    exception when unique_violation then null;
    end;

    -- A new command cannot inherit the historical Clue after success cleared
    -- support. The proposed Check also makes a second plan ineligible.
    begin
      perform public.create_v2_student_check_plan(
        v_owner,v_project,v_change,v_post_version,pg_catalog.gen_random_uuid(),
        pg_catalog.gen_random_uuid(),'Claim historical Clue support',
        'after_hint','clue');
      raise exception 'Check replay % accepted a dishonest new command',v_case.label;
    exception when serialization_failure or check_violation then null;
    end;
  end loop;

  -- Isolate the SQL context guard from the existing-proposed-Check state guard.
  v_fixture := pg_temp.prepare_phase5_check_replay_fixture(
    v_owner,'Check replay strict support guard');
  v_project := (v_fixture->>'project_id')::uuid;
  v_change := (v_fixture->>'change_id')::uuid;
  v_version := (v_fixture->'current_change'->>'version')::bigint;
  begin
    perform public.create_v2_student_check_plan(
      v_owner,v_project,v_change,v_version,pg_catalog.gen_random_uuid(),
      pg_catalog.gen_random_uuid(),'Claim Clue without current support',
      'after_hint','clue');
    raise exception 'strict Check support context guard accepted a dishonest command';
  exception when check_violation then null;
  end;

  -- With that unchanged current state, a new honest no-help operation succeeds.
  v_command := pg_catalog.gen_random_uuid();
  v_check := pg_catalog.gen_random_uuid();
  v_result := public.create_v2_student_check_plan(
    v_owner,v_project,v_change,v_version,v_command,v_check,
    'Add one point and observe the visible score summary increase','asked','none');
  if (v_result->>'replayed')::boolean
     or not exists(select 1 from public.v2_learner_evidence
       where source_operation_id=v_command and elicitation='asked' and support_level='none') then
    raise exception 'honest new Check command did not use current support truth';
  end if;
end $$;
reset role;

-- A correct second effort answer remains assisted by the first-attempt nudge.
set local role service_role;
do $$
declare
  v_owner constant uuid := 'f5000000-0000-4000-8000-000000000001';
  v_item constant uuid := 'f5000000-0000-4000-8000-000000000321';
  v_project uuid; v_change uuid; v_result jsonb;
begin
  v_result := public.create_v2_project(v_owner,
    'f5000000-0000-4000-8000-000000000322','Effort support verifier','new_idea',null,null);
  v_project := (v_result->'project'->>'id')::uuid;
  v_result := public.establish_v2_manual_project(v_owner,v_project,1,
    'f5000000-0000-4000-8000-000000000323','A score tracker',v_item,
    'Show player totals','The visible player total updates after a point');
  v_result := public.start_v2_current_change(v_owner,v_project,2,
    'f5000000-0000-4000-8000-000000000324',v_item,'build','ignored');
  v_change := (v_result->'current_change'->>'id')::uuid;
  v_result := public.resolve_v2_current_change_policy(v_owner,v_project,v_change,1,
    'f5000000-0000-4000-8000-000000000325','skip',null,
    'no_intervention_required','phase5-beta-teaching-v1','normal',null,
    'phase5-beta-risk-v1','required',null);
  perform public.update_v2_coding_agent(v_owner,v_project,v_change,2,2,'codex');
  perform public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,3,1,
    'Add a visible player total.','The visible player total updates after a point',
    array[]::text[],'normal',null,'phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Show player totals','The visible player total updates after a point',
      array[]::text[],'Add a visible player total.'));
  perform public.record_v2_effort_attempt(v_owner,v_project,v_change,4,
    'f5000000-0000-4000-8000-000000000326','quick','standard',false);
  v_result := public.record_v2_effort_attempt(v_owner,v_project,v_change,5,
    'f5000000-0000-4000-8000-000000000327','standard','standard',true);
  if not (v_result->'feedback'->>'appropriate')::boolean
     or (v_result->'current_change'->>'support_level_disclosed')<>'nudge'
     or not exists(select 1 from public.v2_learner_evidence
       where source_operation_id='f5000000-0000-4000-8000-000000000327'
         and elicitation='after_hint' and support_level='nudge') then
    raise exception 'hinted correct second effort answer was classified as independent';
  end if;
  v_result := public.record_v2_effort_attempt(v_owner,v_project,v_change,5,
    'f5000000-0000-4000-8000-000000000327','standard','standard',true);
  if not (v_result->>'replayed')::boolean
     or (select pg_catalog.count(*) from public.v2_learner_evidence
       where source_operation_id='f5000000-0000-4000-8000-000000000327')<>1 then
    raise exception 'hinted second effort replay duplicated evidence';
  end if;
end $$;
reset role;

-- Risk freshness: safe -> stale risky edit -> fail closed -> current risky
-- decision -> safe removal. This fixture also re-proves legacy effort rejection.
set local role service_role;
do $$
declare
  v_owner constant uuid := 'f5000000-0000-4000-8000-000000000001';
  v_item constant uuid := 'f5000000-0000-4000-8000-000000000401';
  v_project uuid; v_change uuid; v_prompt uuid; v_result jsonb;
  v_safe constant text := 'Add a profile settings panel';
  v_risky constant text := 'Change authentication logic and rotate login session tokens';
begin
  v_result := public.create_v2_project(v_owner,
    'f5000000-0000-4000-8000-000000000402','Phase 5 risk freshness','new_idea',null,null);
  v_project := (v_result->'project'->>'id')::uuid;
  perform public.establish_v2_manual_project(v_owner,v_project,1,
    'f5000000-0000-4000-8000-000000000403','A profile app',v_item,
    'Add profile settings','Click Save and see updated settings');
  v_result := public.start_v2_current_change(v_owner,v_project,2,
    'f5000000-0000-4000-8000-000000000404',v_item,'build','Add profile settings');
  v_change := (v_result->'current_change'->>'id')::uuid;
  perform public.resolve_v2_current_change_policy(v_owner,v_project,v_change,1,
    'f5000000-0000-4000-8000-000000000405','skip',null,'familiar_safe_change',
    'phase5-beta-teaching-v1','normal',null,'phase5-beta-risk-v1','required',null);
  perform public.update_v2_coding_agent(v_owner,v_project,v_change,2,2,'codex');
  perform public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,3,1,
    v_safe,'Click Save and see updated settings',array['Keep profile display unchanged'],
    'normal',null,'phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Add profile settings','Click Save and see updated settings',
      array['Keep profile display unchanged'],v_safe));

  -- Simulate a stale older writer. The acceptance trigger must reject its old NORMAL decision.
  perform public.update_v2_prompt_draft(v_owner,v_project,v_change,4,2,
    v_risky,'Click Sign in and see the private profile',array['Keep styling unchanged']);
  perform public.record_v2_effort_attempt(v_owner,v_project,v_change,5,
    'f5000000-0000-4000-8000-000000000406','deep','deep',true);
  begin
    perform public.accept_v2_prompt_version(v_owner,v_project,v_change,6,3,
      'f5000000-0000-4000-8000-000000000407','feature',null,v_risky,
      pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(v_risky,'UTF8')),'hex'),
      null,'codex','deep',null,null);
    raise exception 'stale NORMAL risk decision was accepted';
  exception when check_violation then null;
  end;

  v_result := public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,6,3,
    v_risky,'Click Sign in and see the private profile',array['Keep styling unchanged'],
    'slowdown','authentication','phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Add profile settings','Click Sign in and see the private profile',
      array['Keep styling unchanged'],v_risky));
  if (v_result->'current_change'->>'risk')<>'slowdown'
     or (v_result->'current_change'->>'effort_category') is not null then
    raise exception 'risk re-resolution did not enforce slowdown and reopen effort';
  end if;
  perform public.record_v2_effort_attempt(v_owner,v_project,v_change,7,
    'f5000000-0000-4000-8000-000000000408','deep','deep',true);
  select prompt_version_id into v_prompt from public.accept_v2_prompt_version(
    v_owner,v_project,v_change,8,3,'f5000000-0000-4000-8000-000000000409',
    'feature',null,v_risky,
    pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(v_risky,'UTF8')),'hex'),
    null,'codex','deep',null,null);

  v_result := public.update_v2_prompt_draft_with_risk(v_owner,v_project,v_change,9,3,
    v_safe,'Click Save and see updated settings',array['Keep profile display unchanged'],
    'normal',null,'phase5-beta-risk-v1',public.v2_risk_input_fingerprint(
      'Add profile settings','Click Save and see updated settings',
      array['Keep profile display unchanged'],v_safe));
  if (v_result->'current_change'->>'risk')<>'normal'
     or (v_result->'current_change'->>'risk_reason_key') is not null then
    raise exception 'removing risky work did not refresh risk to NORMAL';
  end if;
  begin
    perform public.handoff_v2_prompt_version(v_owner,v_project,v_change,v_prompt,null,10,1,
      'f5000000-0000-4000-8000-000000000410');
    raise exception 'old risky Prompt Version handed off after risk-relevant edit';
  exception when serialization_failure or check_violation then null;
  end;
end $$;
reset role;

-- Generation Attempts are intentionally not a valid learner-evidence source.
do $$ begin
  begin
    insert into public.v2_learner_evidence(
      owner_user_id,source_project_id,competency_key,observed_behavior,
      elicitation,support_level,context_key,source_record_type,source_record_id,
      observed_at,status,evidence_policy_version)
    values('f5000000-0000-4000-8000-000000000001',
      (select id from public.v2_projects where display_name='Phase 5 verifier'),
      'testing','A generated attempt must not count as student behavior.',
      'asked','none','build','generation_attempt',
      'f5000000-0000-4000-8000-000000000199',pg_catalog.now(),'active',
      'phase5-beta-evidence-v1');
    raise exception 'Generation Attempt unexpectedly became learner evidence';
  exception when check_violation then null;
  end;
end $$;

set local role anon;
do $$ begin
  begin
    perform public.disclose_v2_teaching_help(
      'f5000000-0000-4000-8000-000000000001',
      'f5000000-0000-4000-8000-000000000099',
      'f5000000-0000-4000-8000-000000000098',1,
      'f5000000-0000-4000-8000-000000000097','prebuild');
    raise exception 'anon unexpectedly executed Phase 5 teaching';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;

rollback;
