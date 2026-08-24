-- Codize V2 Phase 6: contextual Observe -> Investigate -> Correct -> Recheck.
-- Uses the accepted eleven-table domain; no browser role receives V2 DML.

begin;

create function codize_v2_internal.record_v2_recovery_symptom(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_recovery_case_id uuid, p_expected_current_change_version bigint,
  p_command_id uuid, p_observed_symptom text,
  p_last_known_working_statement text, p_last_known_working_certainty text,
  p_investigation_prompt text, p_risk text, p_risk_reason_key text,
  p_risk_policy_version text, p_risk_input_fingerprint text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_expected_fingerprint text;
begin
  if p_recovery_case_id is null or p_command_id is null
     or p_observed_symptom is null or pg_catalog.btrim(p_observed_symptom)=''
     or pg_catalog.octet_length(p_observed_symptom)>16384
     or p_last_known_working_certainty not in ('yes','no','unsure')
     or (p_last_known_working_statement is not null and (
       pg_catalog.btrim(p_last_known_working_statement)=''
       or pg_catalog.octet_length(p_last_known_working_statement)>16384))
     or p_investigation_prompt is null or pg_catalog.btrim(p_investigation_prompt)=''
     or pg_catalog.octet_length(p_investigation_prompt)>65536
     or p_risk not in ('normal','slowdown')
     or (p_risk='slowdown')<>(p_risk_reason_key is not null)
     or p_risk_policy_version is null
     or pg_catalog.btrim(p_risk_policy_version) in ('','unresolved-v0') then
    raise exception using errcode='22023', message='invalid bounded Recovery symptom command';
  end if;

  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id
    and p.lifecycle_state not in ('archived','deletion_pending') for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;

  select * into v_recovery from public.v2_recovery_cases as rc
    where rc.owner_user_id=p_owner_user_id and rc.open_command_id=p_command_id for update;
  if found then
    if v_recovery.id<>p_recovery_case_id
       or v_recovery.current_change_id<>p_current_change_id
       or v_recovery.observed_symptom<>pg_catalog.btrim(p_observed_symptom)
       or v_recovery.last_known_working_statement is distinct from
          (case when p_last_known_working_statement is null then null
                else pg_catalog.btrim(p_last_known_working_statement) end)
       or v_recovery.last_known_working_certainty<>p_last_known_working_certainty then
      raise exception using errcode='23505', message='Recovery symptom command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
      'recovery_case',pg_catalog.to_jsonb(v_recovery),'replayed',true);
  end if;

  if exists(select 1 from public.v2_recovery_cases as rc
      where rc.current_change_id=p_current_change_id
        and rc.status in ('open','investigating','correcting','rechecking')) then
    raise exception using errcode='23505', message='Current Change already has an active Recovery Case';
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'recovering'
     or v_change.resume_step<>'recovery_symptom'
     or v_change.coding_agent_key is null
     or v_change.teaching_policy_version='unresolved-v0' then
    raise exception using errcode='40001', message='stale or ineligible Recovery symptom';
  end if;
  v_expected_fingerprint:=public.v2_risk_input_fingerprint(
    v_change.goal_snapshot,v_change.done_condition_snapshot,
    v_change.boundary_snapshots,p_investigation_prompt);
  if p_risk_input_fingerprint is distinct from v_expected_fingerprint then
    raise exception using errcode='23514', message='Recovery investigation risk fingerprint mismatch';
  end if;

  update public.v2_current_changes as cc set
    lifecycle_state='recovering',resume_step='recovery_investigate',
    prompt_draft=p_investigation_prompt,
    prompt_draft_version=cc.prompt_draft_version+1,
    risk=p_risk,risk_reason_key=p_risk_reason_key,
    risk_policy_version=p_risk_policy_version,
    risk_input_fingerprint=v_expected_fingerprint,
    help_context_key=null,support_level_disclosed='none',
    version=cc.version+1
    where cc.id=v_change.id returning * into v_change;

  insert into public.v2_recovery_cases(
    id,project_id,owner_user_id,current_change_id,status,intended_behavior,
    observed_symptom,last_known_working_statement,last_known_working_certainty,
    candidate_change_summary,open_command_id
  ) values(
    p_recovery_case_id,p_project_id,p_owner_user_id,p_current_change_id,'investigating',
    coalesce(v_change.done_condition_snapshot,v_change.goal_snapshot),
    pg_catalog.btrim(p_observed_symptom),
    case when p_last_known_working_statement is null then null
         else pg_catalog.btrim(p_last_known_working_statement) end,
    p_last_known_working_certainty,v_change.goal_snapshot,p_command_id
  ) returning * into v_recovery;

  insert into public.v2_build_turns(
    id,project_id,owner_user_id,current_change_id,recovery_case_id,
    turn_kind,speaker,content,structured_payload,related_record_type,
    related_record_id,retention_class
  ) values(
    p_command_id,p_project_id,p_owner_user_id,p_current_change_id,p_recovery_case_id,
    'recovery_observation','student',pg_catalog.btrim(p_observed_symptom),
    pg_catalog.jsonb_build_object('context','recovery_symptom',
      'last_known_working_certainty',p_last_known_working_certainty),
    'recovery_case',p_recovery_case_id,'structured'
  );
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
    'recovery_case',pg_catalog.to_jsonb(v_recovery),'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_recovery_investigation_return(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_recovery_case_id uuid, p_expected_current_change_version bigint,
  p_command_id uuid, p_finding text, p_correction_summary text,
  p_correction_prompt text, p_risk text, p_risk_reason_key text,
  p_risk_policy_version text, p_risk_input_fingerprint text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_prompt public.v2_prompt_versions%rowtype;
  v_turn public.v2_build_turns%rowtype;
  v_expected_fingerprint text;
begin
  if p_command_id is null or p_finding is null or pg_catalog.btrim(p_finding)=''
     or pg_catalog.octet_length(p_finding)>16384
     or p_correction_summary is null or pg_catalog.btrim(p_correction_summary)=''
     or pg_catalog.octet_length(p_correction_summary)>16384
     or p_correction_prompt is null or pg_catalog.btrim(p_correction_prompt)=''
     or pg_catalog.octet_length(p_correction_prompt)>65536
     or p_risk not in ('normal','slowdown')
     or (p_risk='slowdown')<>(p_risk_reason_key is not null)
     or p_risk_policy_version is null
     or pg_catalog.btrim(p_risk_policy_version) in ('','unresolved-v0') then
    raise exception using errcode='22023', message='invalid bounded Recovery investigation return';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_recovery from public.v2_recovery_cases as rc
    where rc.id=p_recovery_case_id and rc.current_change_id=p_current_change_id
      and rc.project_id=p_project_id and rc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 recovery case not found'; end if;
  select * into v_turn from public.v2_build_turns as bt
    where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id or v_turn.current_change_id<>p_current_change_id
       or v_turn.recovery_case_id<>p_recovery_case_id
       or v_turn.turn_kind<>'return_report' or v_turn.content<>pg_catalog.btrim(p_finding)
       or v_turn.structured_payload->>'context'<>'recovery_investigation' then
      raise exception using errcode='23505', message='Recovery investigation return command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
      'recovery_case',pg_catalog.to_jsonb(v_recovery),'replayed',true);
  end if;
  select * into v_prompt from public.v2_prompt_versions as pv
    where pv.id=v_change.latest_prompt_version_id and pv.current_change_id=p_current_change_id
      and pv.project_id=p_project_id and pv.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='Recovery diagnostic prompt not found'; end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'awaiting_agent' or v_change.resume_step<>'return_outcome'
     or v_recovery.status<>'investigating' or v_prompt.purpose<>'diagnostic'
     or v_prompt.handed_off_at is null
     or v_prompt.handoff_command_id is distinct from v_change.handoff_command_id then
    raise exception using errcode='40001', message='stale or ineligible Recovery investigation return';
  end if;
  v_expected_fingerprint:=public.v2_risk_input_fingerprint(
    v_change.goal_snapshot,v_change.done_condition_snapshot,
    v_change.boundary_snapshots,p_correction_prompt);
  if p_risk_input_fingerprint is distinct from v_expected_fingerprint then
    raise exception using errcode='23514', message='Recovery correction risk fingerprint mismatch';
  end if;

  update public.v2_current_changes as cc set
    lifecycle_state='recovering',resume_step='recovery_correct',
    prompt_draft=p_correction_prompt,prompt_draft_version=cc.prompt_draft_version+1,
    risk=p_risk,risk_reason_key=p_risk_reason_key,
    risk_policy_version=p_risk_policy_version,risk_input_fingerprint=v_expected_fingerprint,
    help_context_key=null,support_level_disclosed='none',version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  update public.v2_recovery_cases as rc set status='correcting',
    investigation_finding=pg_catalog.btrim(p_finding),
    correction_summary=pg_catalog.btrim(p_correction_summary),version=rc.version+1
    where rc.id=v_recovery.id returning * into v_recovery;
  insert into public.v2_build_turns(
    id,project_id,owner_user_id,current_change_id,recovery_case_id,
    turn_kind,speaker,content,structured_payload,related_record_type,
    related_record_id,retention_class
  ) values(
    p_command_id,p_project_id,p_owner_user_id,p_current_change_id,p_recovery_case_id,
    'return_report','student',pg_catalog.btrim(p_finding),
    pg_catalog.jsonb_build_object('context','recovery_investigation',
      'provenance','agent_claimed','prompt_version_id',v_prompt.id),
    'prompt_version',v_prompt.id,'structured'
  );
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
    'recovery_case',pg_catalog.to_jsonb(v_recovery),'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_recovery_correction_return(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_recovery_case_id uuid, p_expected_current_change_version bigint,
  p_command_id uuid, p_check_id uuid, p_check_plan text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_prompt public.v2_prompt_versions%rowtype;
  v_turn public.v2_build_turns%rowtype;
  v_check public.v2_checks%rowtype;
  v_superseded uuid;
begin
  if p_command_id is null or p_check_id is null or p_check_plan is null
     or pg_catalog.btrim(p_check_plan)='' or pg_catalog.octet_length(p_check_plan)>8192 then
    raise exception using errcode='22023', message='invalid Recovery correction return';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_recovery from public.v2_recovery_cases as rc
    where rc.id=p_recovery_case_id and rc.current_change_id=p_current_change_id
      and rc.project_id=p_project_id and rc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 recovery case not found'; end if;
  select * into v_turn from public.v2_build_turns as bt
    where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id or v_turn.current_change_id<>p_current_change_id
       or v_turn.recovery_case_id<>p_recovery_case_id
       or v_turn.structured_payload->>'context'<>'recovery_correction'
       or v_turn.related_record_id<>p_check_id then
      raise exception using errcode='23505', message='Recovery correction return command id already used';
    end if;
    select * into strict v_check from public.v2_checks where id=p_check_id;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
      'recovery_case',pg_catalog.to_jsonb(v_recovery),'check',pg_catalog.to_jsonb(v_check),
      'replayed',true);
  end if;
  select * into v_prompt from public.v2_prompt_versions as pv
    where pv.id=v_change.latest_prompt_version_id and pv.current_change_id=p_current_change_id
      and pv.project_id=p_project_id and pv.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='Recovery correction prompt not found'; end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'awaiting_agent' or v_change.resume_step<>'return_outcome'
     or v_recovery.status<>'correcting' or v_prompt.purpose<>'correction'
     or v_prompt.handed_off_at is null
     or v_prompt.handoff_command_id is distinct from v_change.handoff_command_id then
    raise exception using errcode='40001', message='stale or ineligible Recovery correction return';
  end if;
  select vc.id into v_superseded from public.v2_checks as vc
    where vc.current_change_id=p_current_change_id and vc.project_id=p_project_id
      and vc.owner_user_id=p_owner_user_id and vc.status='performed'
      and not exists(select 1 from public.v2_checks as successor
        where successor.supersedes_check_id=vc.id)
    order by vc.created_at desc,vc.id desc limit 1 for update;
  insert into public.v2_checks(
    id,project_id,owner_user_id,current_change_id,check_plan,plan_source,
    status,supersedes_check_id,create_command_id
  ) values(
    p_check_id,p_project_id,p_owner_user_id,p_current_change_id,
    pg_catalog.btrim(p_check_plan),'codize','proposed',v_superseded,p_command_id
  ) returning * into v_check;
  update public.v2_current_changes as cc set lifecycle_state='recovering',
    resume_step='recovery_recheck',help_context_key=null,
    support_level_disclosed='none',version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  update public.v2_recovery_cases as rc set status='rechecking',version=rc.version+1
    where rc.id=v_recovery.id returning * into v_recovery;
  insert into public.v2_build_turns(
    id,project_id,owner_user_id,current_change_id,recovery_case_id,
    turn_kind,speaker,content,structured_payload,related_record_type,
    related_record_id,retention_class
  ) values(
    p_command_id,p_project_id,p_owner_user_id,p_current_change_id,p_recovery_case_id,
    'student_decision','student','Returned after targeted correction',
    pg_catalog.jsonb_build_object('context','recovery_correction',
      'prompt_version_id',v_prompt.id,'claimed_working',false),
    'check',p_check_id,'structured'
  );
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
    'recovery_case',pg_catalog.to_jsonb(v_recovery),'check',pg_catalog.to_jsonb(v_check),
    'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_recovery_check(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_recovery_case_id uuid, p_check_id uuid,
  p_expected_current_change_version bigint, p_expected_check_version bigint,
  p_command_id uuid, p_result text, p_observation text,
  p_performed_by_student boolean, p_next_check_id uuid,
  p_investigation_prompt text, p_risk text, p_risk_reason_key text,
  p_risk_policy_version text, p_risk_input_fingerprint text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_check public.v2_checks%rowtype;
  v_next public.v2_checks%rowtype;
  v_turn public.v2_build_turns%rowtype;
  v_expected_fingerprint text;
begin
  if p_result not in ('worked','partly_worked','did_not_work','unsure')
     or p_performed_by_student is distinct from true
     or p_observation is null or pg_catalog.btrim(p_observation)=''
     or pg_catalog.octet_length(p_observation)>16384
     or ((p_result='unsure')<>(p_next_check_id is not null))
     or ((p_result in ('partly_worked','did_not_work'))<>(p_investigation_prompt is not null)) then
    raise exception using errcode='22023', message='student-performed Recovery recheck is required';
  end if;
  if p_investigation_prompt is not null and (
       pg_catalog.btrim(p_investigation_prompt)=''
       or pg_catalog.octet_length(p_investigation_prompt)>65536
       or p_risk not in ('normal','slowdown')
       or (p_risk='slowdown')<>(p_risk_reason_key is not null)
       or p_risk_policy_version is null
       or pg_catalog.btrim(p_risk_policy_version) in ('','unresolved-v0')) then
    raise exception using errcode='22023', message='invalid Recovery reinvestigation prompt';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_recovery from public.v2_recovery_cases as rc
    where rc.id=p_recovery_case_id and rc.current_change_id=p_current_change_id
      and rc.project_id=p_project_id and rc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 recovery case not found'; end if;
  select * into v_check from public.v2_checks as vc
    where vc.id=p_check_id and vc.current_change_id=p_current_change_id
      and vc.project_id=p_project_id and vc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 Recovery check not found'; end if;
  select * into v_turn from public.v2_build_turns as bt
    where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id or v_turn.current_change_id<>p_current_change_id
       or v_turn.recovery_case_id<>p_recovery_case_id
       or v_turn.related_record_id<>p_check_id
       or v_turn.content<>pg_catalog.btrim(p_observation)
       or v_turn.structured_payload->>'result'<>p_result
       or nullif(v_turn.structured_payload->>'next_check_id','')::uuid is distinct from p_next_check_id then
      raise exception using errcode='23505', message='Recovery recheck command id already used';
    end if;
    if p_next_check_id is not null then select * into v_next from public.v2_checks where id=p_next_check_id; end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
      'recovery_case',pg_catalog.to_jsonb(v_recovery),'check',pg_catalog.to_jsonb(v_check),
      'next_check',pg_catalog.to_jsonb(v_next),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_check.version<>p_expected_check_version or v_check.status<>'proposed'
     or v_change.lifecycle_state<>'recovering' or v_change.resume_step<>'recovery_recheck'
     or v_recovery.status<>'rechecking' then
    raise exception using errcode='40001', message='stale or ineligible Recovery recheck';
  end if;
  if p_investigation_prompt is not null then
    v_expected_fingerprint:=public.v2_risk_input_fingerprint(
      v_change.goal_snapshot,v_change.done_condition_snapshot,
      v_change.boundary_snapshots,p_investigation_prompt);
    if p_risk_input_fingerprint is distinct from v_expected_fingerprint then
      raise exception using errcode='23514', message='Recovery retry risk fingerprint mismatch';
    end if;
  end if;
  update public.v2_checks as vc set status='performed',result=p_result,
    student_observation=pg_catalog.btrim(p_observation),performed_at=pg_catalog.now(),
    version=vc.version+1 where vc.id=v_check.id returning * into v_check;
  if p_result='unsure' then
    insert into public.v2_checks(
      id,project_id,owner_user_id,current_change_id,check_plan,plan_source,
      status,supersedes_check_id,create_command_id
    ) values(
      p_next_check_id,p_project_id,p_owner_user_id,p_current_change_id,
      v_check.check_plan,'codize','proposed',v_check.id,p_command_id
    ) returning * into v_next;
  end if;
  update public.v2_current_changes as cc set
    lifecycle_state='recovering',
    resume_step=case when p_result in ('partly_worked','did_not_work')
      then 'recovery_investigate' else 'recovery_recheck' end,
    prompt_draft=case when p_investigation_prompt is not null
      then p_investigation_prompt else cc.prompt_draft end,
    prompt_draft_version=cc.prompt_draft_version+
      case when p_investigation_prompt is not null then 1 else 0 end,
    risk=coalesce(p_risk,cc.risk),risk_reason_key=case
      when p_investigation_prompt is not null then p_risk_reason_key else cc.risk_reason_key end,
    risk_policy_version=coalesce(p_risk_policy_version,cc.risk_policy_version),
    risk_input_fingerprint=coalesce(v_expected_fingerprint,cc.risk_input_fingerprint),
    unresolved_uncertainty_summary=case when p_result='unsure'
      then 'Student remains unsure after Recovery recheck '||v_check.id::text||'.'
      else cc.unresolved_uncertainty_summary end,
    help_context_key=null,support_level_disclosed='none',version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  if p_result in ('partly_worked','did_not_work') then
    update public.v2_recovery_cases as rc set status='investigating',
      proposed_first_check=v_check.check_plan,version=rc.version+1
      where rc.id=v_recovery.id returning * into v_recovery;
  end if;
  insert into public.v2_build_turns(
    id,project_id,owner_user_id,current_change_id,recovery_case_id,
    turn_kind,speaker,content,structured_payload,related_record_type,
    related_record_id,retention_class
  ) values(
    p_command_id,p_project_id,p_owner_user_id,p_current_change_id,p_recovery_case_id,
    'student_answer','student',pg_catalog.btrim(p_observation),
    pg_catalog.jsonb_build_object('context','recovery_recheck','result',p_result,
      'performed_by_student',true,'next_check_id',p_next_check_id),
    'check',p_check_id,'structured'
  );
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
    'recovery_case',pg_catalog.to_jsonb(v_recovery),'check',pg_catalog.to_jsonb(v_check),
    'next_check',pg_catalog.to_jsonb(v_next),'replayed',false);
end;
$$;

-- Public security-invoker wrappers remain the only PostgREST surface.
create function public.record_v2_recovery_symptom(
  uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text
) returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_recovery_symptom(
  $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) $$;
create function public.record_v2_recovery_investigation_return(
  uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text
) returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_recovery_investigation_return(
  $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) $$;
create function public.record_v2_recovery_correction_return(
  uuid,uuid,uuid,uuid,bigint,uuid,uuid,text
) returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_recovery_correction_return(
  $1,$2,$3,$4,$5,$6,$7,$8) $$;
create function public.record_v2_recovery_check(
  uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text
) returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_recovery_check(
  $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17) $$;

alter function codize_v2_internal.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text) owner to codize_v2_executor;

revoke all on function public.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text) from public,anon,authenticated;
revoke all on function public.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text) from public,anon,authenticated;
revoke all on function public.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text) from public,anon,authenticated;
revoke all on function codize_v2_internal.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text) from public,anon,authenticated,service_role;
revoke all on function codize_v2_internal.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text) from public,anon,authenticated,service_role;
revoke all on function codize_v2_internal.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text) from public,anon,authenticated,service_role;
revoke all on function codize_v2_internal.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text) from public,anon,authenticated,service_role;
grant execute on function codize_v2_internal.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text) to service_role;
grant execute on function codize_v2_internal.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text) to service_role;
grant execute on function codize_v2_internal.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text) to service_role;
grant execute on function codize_v2_internal.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text) to service_role;
grant execute on function public.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text) to service_role;
grant execute on function public.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text) to service_role;
grant execute on function public.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text) to service_role;
grant execute on function public.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text) to service_role;

comment on function public.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text)
  is 'Backend-only retry-safe Recovery symptom capture and deterministic investigation preparation.';
comment on function public.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text)
  is 'Backend-only agent-claim finding capture and targeted correction preparation.';
comment on function public.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text)
  is 'Backend-only Recovery correction return that creates a personal recheck without accepting agent success claims.';
comment on function public.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text)
  is 'Backend-only student-performed Recovery recheck with PASS/failure/UNSURE retry semantics.';

-- Phase 5 Need Help remains the single tutoring mechanism. Recovery adds only
-- interaction contexts; it does not add competencies or a second evidence engine.
create or replace function codize_v2_internal.disclose_v2_teaching_help(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_command_id uuid, p_context text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_request public.v2_build_turns%rowtype;
  v_support text;
  v_help_key text;
  v_hint_kind text;
  v_hint_text text;
begin
  if p_context not in (
       'prebuild','verification','understanding','recovery_symptom',
       'recovery_investigate','recovery_correct','recovery_recheck'
     ) or p_command_id is null or p_expected_current_change_version is null then
    raise exception using errcode='22023', message='invalid teaching help command';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_request from public.v2_build_turns as bt where bt.id=p_command_id
    and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_request.project_id<>p_project_id
       or v_request.current_change_id<>p_current_change_id
       or v_request.turn_kind<>'student_decision'
       or v_request.speaker<>'student' or v_request.content<>'Need help'
       or v_request.structured_payload->>'context'<>p_context then
      raise exception using errcode='23505', message='teaching help command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or (p_context='prebuild' and not (
       v_change.lifecycle_state='preparing' and v_change.resume_step='intervention'))
     or (p_context='verification' and not (
       v_change.lifecycle_state='reviewing' and v_change.resume_step='check'))
     or (p_context='understanding' and not (
       v_change.lifecycle_state='reviewing' and v_change.resume_step='understand'))
     or (p_context='recovery_symptom' and not (
       v_change.lifecycle_state='recovering' and v_change.resume_step='recovery_symptom'))
     or (p_context='recovery_investigate' and not (
       v_change.lifecycle_state='recovering' and v_change.resume_step='recovery_investigate'))
     or (p_context='recovery_correct' and not (
       v_change.lifecycle_state='recovering' and v_change.resume_step='recovery_correct'))
     or (p_context='recovery_recheck' and not (
       v_change.lifecycle_state='recovering' and v_change.resume_step='recovery_recheck')) then
    raise exception using errcode='40001', message='stale or ineligible teaching help';
  end if;
  v_help_key:=case
    when p_context='prebuild' then v_change.teaching_target
    when p_context in ('verification','recovery_recheck') then 'testing'
    when p_context like 'recovery_%' then 'debugging'
    else 'causal_explanation' end;
  if v_change.help_context_key=v_help_key and v_change.support_level_disclosed='teach' then
    raise exception using errcode='23514', message='final teaching help is already disclosed';
  end if;
  v_support:=case
    when v_change.help_context_key is distinct from v_help_key then 'nudge'
    when v_change.support_level_disclosed='none' then 'nudge'
    when v_change.support_level_disclosed='nudge' then 'clue'
    else 'teach' end;
  v_hint_kind:=case v_support when 'nudge' then 'help_nudge'
    when 'clue' then 'help_clue' else 'help_teach' end;
  v_hint_text:=case
    when p_context like 'recovery_%' and v_support='nudge'
      then 'Name the first visible thing that differed from what you expected.'
    when p_context like 'recovery_%' and v_support='clue'
      then 'Keep three labels separate: what you observed, what the coding AI suggested, and what you personally rechecked.'
    when p_context like 'recovery_%'
      then 'A symptom is the behavior you saw. A diagnosis is still a hypothesis until code or a performed check supports it.'
    when v_support='nudge' then 'Think about one concrete action or result in this project.'
    when v_support='clue' then 'Use the current change and name what someone would try, protect, or observe.'
    else 'Connect the answer to one specific action, boundary, or cause in this change.' end;
  insert into public.v2_build_turns(
    id,project_id,owner_user_id,current_change_id,turn_kind,speaker,content,
    structured_payload,help_context_key,support_level,policy_version,retention_class
  ) values(
    p_command_id,p_project_id,p_owner_user_id,p_current_change_id,
    'student_decision','student','Need help',
    pg_catalog.jsonb_build_object('context',p_context,'support_level',v_support),
    v_help_key,v_support,'phase5-beta-teaching-v1','structured'
  );
  insert into public.v2_build_turns(
    project_id,owner_user_id,current_change_id,turn_kind,speaker,content,
    structured_payload,help_context_key,support_level,policy_version,retention_class
  ) values(
    p_project_id,p_owner_user_id,p_current_change_id,v_hint_kind,'codize',v_hint_text,
    pg_catalog.jsonb_build_object('context',p_context),v_help_key,v_support,
    'phase5-beta-teaching-v1','structured'
  );
  insert into public.v2_learner_evidence(
    owner_user_id,source_project_id,source_current_change_id,competency_key,
    observed_behavior,elicitation,support_level,context_key,source_record_type,
    source_record_id,source_operation_id,observed_at,status,evidence_policy_version
  ) values(
    p_owner_user_id,p_project_id,p_current_change_id,v_help_key,
    'Requested contextual support while working on this competency.',
    'after_hint',v_support,case when v_change.risk='slowdown'
      then 'slowdown_novel' else 'normal_novel' end,
    'build_turn',p_command_id,p_command_id,pg_catalog.now(),'active','phase5-beta-evidence-v1'
  );
  update public.v2_current_changes as cc set help_context_key=v_help_key,
    support_level_disclosed=v_support,version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',false);
end;
$$;

commit;
