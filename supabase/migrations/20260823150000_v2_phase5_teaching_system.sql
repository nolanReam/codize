-- Codize V2 Phase 5: deterministic adaptive teaching inside the manual Build loop.
-- No new tables: durable interaction state uses Current Change, Build Turns,
-- Checks, and append-oriented Learner Evidence.

-- Existing private routines are owned by the NOLOGIN executor role. Retain
-- temporary ownership authority through the complete privilege setup below.
grant codize_v2_executor to current_user with set true;
grant create on schema codize_v2_internal to codize_v2_executor;

alter table public.v2_current_changes
  add column risk_input_fingerprint text;
alter table public.v2_current_changes
  add constraint v2_current_changes_risk_input_fingerprint_ck check (
    risk_input_fingerprint is null
    or risk_input_fingerprint ~ '^[0-9a-f]{32}$'
  );

create function public.v2_risk_input_fingerprint(
  p_goal text,p_done text,p_boundaries text[],p_prompt text
)
returns text language sql immutable parallel safe set search_path=''
as $$
  select pg_catalog.md5(
    'risk-v1|'
    || case when p_goal is null then 'N' else 'V'||pg_catalog.octet_length(p_goal)||':'||p_goal end || '|'
    || case when p_done is null then 'N' else 'V'||pg_catalog.octet_length(p_done)||':'||p_done end || '|'
    || 'A'||coalesce(pg_catalog.cardinality(p_boundaries),0)||':'
    || coalesce((
      select pg_catalog.string_agg(
        'V'||pg_catalog.octet_length(value)||':'||value,'' order by ordinal
      ) from pg_catalog.unnest(coalesce(p_boundaries,array[]::text[]))
        with ordinality as boundary(value,ordinal)
    ),'') || '|'
    || case when p_prompt is null then 'N' else 'V'||pg_catalog.octet_length(p_prompt)||':'||p_prompt end
  )
$$;

create function public.v2_qualifies_structured_response(p_target text,p_response text)
returns boolean language sql immutable parallel safe set search_path=''
as $$
  select pg_catalog.cardinality(pg_catalog.regexp_split_to_array(
      pg_catalog.btrim(p_response),'\s+'))>=4 and case p_target
    when 'define_done' then p_response ~* '\m(see|show|display|appear|receive|save|load|view|hear|visible|update|updates|change|changes|message|result)\M'
    when 'protect_working_behavior' then p_response ~* '\m(leave|keep|preserve|remain|unchanged|not change|do not change|must still|without changing)\M'
    when 'data_ownership' then
      p_response ~* '\m(allow|may|can|access|only the intended|owner)\M'
      and p_response ~* '\m(prevent|deny|cannot|can''t|must not|no other|only)\M'
    else false
  end
$$;

create function public.v2_qualifies_check_plan(p_check_plan text)
returns boolean language sql immutable parallel safe set search_path=''
as $$
  select pg_catalog.cardinality(pg_catalog.regexp_split_to_array(
       pg_catalog.btrim(p_check_plan),'\s+'))>=5
     and p_check_plan ~* '\m(add|click|type|enter|submit|open|select|save|load|refresh|run|try|visit|request)\M'
     and p_check_plan ~* '\m(see|show|display|appear|receive|observe|confirm|verify|expect|result|message|status|change|changes|remain|remains)\M'
$$;

-- Teaching/check policy remains immutable after resolution. Phase 5 risk is
-- the narrow exception: prompt-relevant state may refresh the risk decision,
-- but only with the exact current fingerprint and accepted beta version.
create or replace function public.v2_guard_policy_resolution()
returns trigger language plpgsql security invoker set search_path=''
as $$
declare
  v_teaching_changed boolean;
  v_risk_changed boolean;
  v_policy_changed boolean;
begin
  if tg_op='INSERT' then
    if new.policy_resolution_command_id is not null then
      raise exception using errcode='23514', message='V2 policy provenance is written only by the resolution command';
    end if;
    return new;
  end if;
  v_teaching_changed := row(new.teaching_mode,new.teaching_target,
    new.teaching_reason_key,new.teaching_policy_version,new.check_requirement,
    new.check_waiver_reason_key) is distinct from row(old.teaching_mode,
    old.teaching_target,old.teaching_reason_key,old.teaching_policy_version,
    old.check_requirement,old.check_waiver_reason_key);
  v_risk_changed := row(new.risk,new.risk_reason_key,new.risk_policy_version,
    new.risk_input_fingerprint) is distinct from row(old.risk,old.risk_reason_key,
    old.risk_policy_version,old.risk_input_fingerprint);
  v_policy_changed := v_teaching_changed or v_risk_changed;
  if old.policy_resolution_command_id is not null
     and new.policy_resolution_command_id is distinct from old.policy_resolution_command_id then
    raise exception using errcode='23514', message='V2 policy resolution provenance is immutable';
  end if;
  if old.teaching_policy_version<>'unresolved-v0'
     and old.risk_policy_version<>'unresolved-v0' then
    if v_teaching_changed then
      raise exception using errcode='23514', message='resolved V2 teaching policy fields are immutable';
    end if;
    if v_risk_changed and (
         new.teaching_policy_version<>'phase5-beta-teaching-v1'
         or new.risk_policy_version<>'phase5-beta-risk-v1'
         or new.risk_input_fingerprint is distinct from
            public.v2_risk_input_fingerprint(new.goal_snapshot,
              new.done_condition_snapshot,new.boundary_snapshots,new.prompt_draft)
       ) then
      raise exception using errcode='23514', message='invalid Phase 5 risk refresh';
    end if;
  end if;
  if old.teaching_policy_version='unresolved-v0'
     or old.risk_policy_version='unresolved-v0' then
    if new.teaching_policy_version='unresolved-v0'
       or new.risk_policy_version='unresolved-v0' then
      if v_policy_changed
         or new.policy_resolution_command_id is distinct from old.policy_resolution_command_id then
        raise exception using errcode='23514', message='unresolved V2 policy fields cannot be partially rewritten';
      end if;
    elsif not v_policy_changed
       or old.policy_resolution_command_id is not null
       or new.policy_resolution_command_id is null then
      raise exception using errcode='23514', message='V2 policy resolution requires one atomic controlled replacement';
    end if;
  end if;
  return new;
end;
$$;

create or replace function codize_v2_internal.resolve_v2_current_change_policy(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_command_id uuid,
  p_teaching_mode text, p_teaching_target text, p_teaching_reason_key text,
  p_teaching_policy_version text, p_risk text, p_risk_reason_key text,
  p_risk_policy_version text, p_check_requirement text,
  p_check_waiver_reason_key text
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_item public.v2_plan_items%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null or p_command_id is null
     or p_teaching_mode not in ('skip','ask','remind','teach')
     or (p_teaching_mode <> 'skip' and p_teaching_target is null)
     or p_teaching_target is not null and p_teaching_target not in (
       'first_version_scoping','define_done','protect_working_behavior',
       'effort_selection','inspect_changes','testing','debugging',
       'causal_explanation','functions','state','events','api','database',
       'authentication','client_server','persistence','async_work','validation',
       'error_handling','data_ownership','rendering','routing','dependencies',
       'version_control')
     or p_teaching_reason_key is null or pg_catalog.btrim(p_teaching_reason_key)=''
     or p_teaching_policy_version is null
     or pg_catalog.btrim(p_teaching_policy_version) in ('','unresolved-v0')
     or p_risk not in ('normal','slowdown')
     or (p_risk='slowdown') <> (p_risk_reason_key is not null)
     or p_risk_policy_version is null
     or pg_catalog.btrim(p_risk_policy_version) in ('','unresolved-v0')
     or p_check_requirement not in ('required','waived')
     or p_risk='slowdown' and p_check_requirement <> 'required' then
    raise exception using errcode='22023', message='invalid V2 Phase 5 policy resolution';
  end if;

  perform 1 from public.v2_projects as p
    where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;

  if v_change.policy_resolution_command_id=p_command_id then
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',true);
  end if;
  if v_change.policy_resolution_command_id is not null
     or v_change.teaching_policy_version<>'unresolved-v0'
     or v_change.risk_policy_version<>'unresolved-v0' then
    raise exception using errcode='23514', message='V2 Current Change policy is already resolved';
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'preparing' or v_change.resume_step<>'confirm_change' then
    raise exception using errcode='40001', message='stale or ineligible policy resolution';
  end if;

  if v_change.plan_item_id is not null then
    select * into v_item from public.v2_plan_items as pi
      where pi.id=v_change.plan_item_id and pi.project_id=p_project_id
        and pi.owner_user_id=p_owner_user_id for update;
    if not found then raise exception using errcode='P0002', message='v2 plan item not found'; end if;
  end if;

  update public.v2_current_changes as cc set
    teaching_mode=p_teaching_mode, teaching_target=p_teaching_target,
    teaching_reason_key=pg_catalog.btrim(p_teaching_reason_key),
    teaching_policy_version=pg_catalog.btrim(p_teaching_policy_version),
    risk=p_risk, risk_reason_key=p_risk_reason_key,
    risk_policy_version=pg_catalog.btrim(p_risk_policy_version),
    risk_input_fingerprint=public.v2_risk_input_fingerprint(
      cc.goal_snapshot,
      case when p_teaching_target='define_done' and p_teaching_mode<>'skip'
        then null else coalesce(cc.done_condition_snapshot,v_item.intended_outcome) end,
      cc.boundary_snapshots,cc.prompt_draft),
    check_requirement=p_check_requirement,
    check_waiver_reason_key=p_check_waiver_reason_key,
    policy_resolution_command_id=p_command_id,
    -- A confirmed Plan outcome is a safe fallback only when defining Done is
    -- skipped. Otherwise the student supplies the accepted snapshot.
    done_condition_snapshot=case
      when p_teaching_target='define_done' and p_teaching_mode<>'skip' then null
      else coalesce(cc.done_condition_snapshot,v_item.intended_outcome)
    end,
    help_context_key=case when p_teaching_mode='skip' then null else p_teaching_target end,
    support_level_disclosed='none',
    resume_step=case when p_teaching_mode='skip' then 'choose_agent' else 'intervention' end,
    version=cc.version+1
  where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',false);
end;
$$;

create function codize_v2_internal.disclose_v2_teaching_help(
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
  if p_context not in ('prebuild','verification','understanding')
     or p_command_id is null or p_expected_current_change_version is null then
    raise exception using errcode='22023', message='invalid teaching help command';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_request from public.v2_build_turns as bt where bt.id=p_command_id
    and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_request.project_id<>p_project_id
       or v_request.current_change_id<>p_current_change_id
       or v_request.turn_kind<>'student_decision'
       or v_request.speaker<>'student'
       or v_request.content<>'Need help'
       or v_request.structured_payload->>'context'<>p_context then
      raise exception using errcode='23505', message='teaching help command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or (p_context='prebuild' and not (v_change.lifecycle_state='preparing' and v_change.resume_step='intervention'))
     or (p_context='verification' and not (v_change.lifecycle_state='reviewing' and v_change.resume_step='check'))
     or (p_context='understanding' and not (v_change.lifecycle_state='reviewing' and v_change.resume_step='understand')) then
    raise exception using errcode='40001', message='stale or ineligible teaching help';
  end if;
  v_help_key := case p_context when 'prebuild' then v_change.teaching_target
    when 'verification' then 'testing' else 'causal_explanation' end;
  if v_change.help_context_key=v_help_key and v_change.support_level_disclosed='teach' then
    raise exception using errcode='23514', message='final teaching help is already disclosed';
  end if;
  v_support := case
    when v_change.help_context_key is distinct from v_help_key then 'nudge'
    when v_change.support_level_disclosed='none' then 'nudge'
    when v_change.support_level_disclosed='nudge' then 'clue'
    else 'teach' end;
  v_hint_kind := case v_support when 'nudge' then 'help_nudge'
    when 'clue' then 'help_clue' else 'help_teach' end;
  v_hint_text := case v_support
    when 'nudge' then 'Think about one concrete action or result in this project.'
    when 'clue' then 'Use the current change and name what someone would try, protect, or observe.'
    else 'Connect the answer to one specific action, boundary, or cause in this change.' end;

  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,help_context_key,support_level,
    policy_version,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,
    'student_decision','student','Need help',
    pg_catalog.jsonb_build_object('context',p_context,'support_level',v_support),
    v_help_key,v_support,'phase5-beta-teaching-v1','structured');
  insert into public.v2_build_turns(project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,help_context_key,support_level,
    policy_version,retention_class)
  values(p_project_id,p_owner_user_id,p_current_change_id,v_hint_kind,'codize',v_hint_text,
    pg_catalog.jsonb_build_object('context',p_context),v_help_key,v_support,
    'phase5-beta-teaching-v1','structured');
  insert into public.v2_learner_evidence(owner_user_id,source_project_id,
    source_current_change_id,competency_key,observed_behavior,elicitation,
    support_level,context_key,source_record_type,source_record_id,
    source_operation_id,observed_at,status,evidence_policy_version)
  values(p_owner_user_id,p_project_id,p_current_change_id,v_help_key,
    'Requested contextual support while working on this competency.',
    'after_hint',v_support,case when v_change.risk='slowdown' then 'slowdown_novel' else 'normal_novel' end,
    'build_turn',p_command_id,p_command_id,pg_catalog.now(),'active','phase5-beta-evidence-v1');
  update public.v2_current_changes as cc set help_context_key=v_help_key,
    support_level_disclosed=v_support,version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_teaching_response(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_command_id uuid,
  p_context text,p_response text,p_elicitation text,p_support_level text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_turn public.v2_build_turns%rowtype;
  v_target text;
  v_elicitation text;
  v_support text;
begin
  if p_context not in ('prebuild','understanding') or p_command_id is null
     or p_response is null or pg_catalog.btrim(p_response)=''
     or pg_catalog.octet_length(p_response)>8192
     or not ((p_elicitation in ('spontaneous','asked') and p_support_level='none')
       or (p_elicitation='after_hint' and p_support_level in ('nudge','clue'))
       or (p_elicitation='taught' and p_support_level='teach')) then
    raise exception using errcode='22023', message='invalid teaching response';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_turn from public.v2_build_turns as bt where bt.id=p_command_id
    and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id
       or v_turn.current_change_id<>p_current_change_id
       or v_turn.turn_kind<>'student_answer'
       or v_turn.speaker<>'student'
       or v_turn.content<>pg_catalog.btrim(p_response)
       or v_turn.support_level<>p_support_level
       or v_turn.structured_payload->>'context'<>p_context then
      raise exception using errcode='23505', message='teaching response command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or (p_context='prebuild' and not (v_change.lifecycle_state='preparing' and v_change.resume_step='intervention'))
     or (p_context='understanding' and not (v_change.lifecycle_state='reviewing' and v_change.resume_step='understand')) then
    raise exception using errcode='40001', message='stale or ineligible teaching response';
  end if;
  if pg_catalog.lower(pg_catalog.btrim(p_response))='continue'
     and not (p_context='prebuild' and v_change.teaching_mode='remind') then
    raise exception using errcode='23514', message='continue is valid only for a reminder';
  end if;
  if pg_catalog.lower(pg_catalog.btrim(p_response))<>'continue'
     and (pg_catalog.octet_length(pg_catalog.btrim(p_response))<8
       or pg_catalog.cardinality(pg_catalog.regexp_split_to_array(
          pg_catalog.btrim(p_response),'\s+'))<2
       or pg_catalog.lower(pg_catalog.btrim(p_response)) in
          ('i don''t know','i dont know','not sure','no idea')) then
    raise exception using errcode='23514', message='teaching response is not actionable';
  end if;
  v_target := case when p_context='prebuild' then v_change.teaching_target else 'causal_explanation' end;
  if p_elicitation='after_hint'
     and (v_change.help_context_key is distinct from v_target
       or v_change.support_level_disclosed is distinct from p_support_level) then
    raise exception using errcode='23514', message='teaching support belongs to another interaction';
  end if;
  v_support := p_support_level;
  v_elicitation := p_elicitation;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,help_context_key,support_level,
    policy_version,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,
    'student_answer','student',pg_catalog.btrim(p_response),
    pg_catalog.jsonb_build_object('context',p_context,'competency_key',v_target),
    v_target,v_support,'phase5-beta-teaching-v1','structured');
  -- A REMIND acknowledgement is navigation, not competency evidence.
  -- Free text remains a Build Turn. Evidence is emitted only for a narrow,
  -- objectively constrained prebuild decision; causal prose is not graded.
  if p_context='prebuild'
     and not (v_change.teaching_mode='remind'
              and pg_catalog.lower(pg_catalog.btrim(p_response))='continue')
     and public.v2_qualifies_structured_response(v_target,pg_catalog.btrim(p_response)) then
    insert into public.v2_learner_evidence(owner_user_id,source_project_id,
      source_current_change_id,competency_key,observed_behavior,elicitation,
      support_level,context_key,source_record_type,source_record_id,
      source_operation_id,observed_at,status,evidence_policy_version)
    values(p_owner_user_id,p_project_id,p_current_change_id,v_target,
      case v_target
        when 'define_done' then 'Defined an observable outcome for the current change.'
        when 'protect_working_behavior' then 'Named a working behavior to protect.'
        when 'data_ownership' then 'Described an access boundary for a consequential change.'
        when 'causal_explanation' then 'Explained an important causal relationship in the current change.'
        else 'Responded to a contextual competency question.' end,
      v_elicitation,v_support,case when v_change.risk='slowdown' then 'slowdown_novel' else 'build' end,
      'build_turn',p_command_id,p_command_id,pg_catalog.now(),'active','phase5-beta-evidence-v1');
  end if;
  update public.v2_current_changes as cc set
    done_condition_snapshot=case when p_context='prebuild' and v_target='define_done'
      then pg_catalog.btrim(p_response) else cc.done_condition_snapshot end,
    boundary_snapshots=case when p_context='prebuild' and v_target in ('protect_working_behavior','data_ownership')
      then array[pg_catalog.btrim(p_response)]::text[] else cc.boundary_snapshots end,
    resume_step=case when p_context='prebuild' then 'choose_agent' else 'understand' end,
    help_context_key=case when p_context='prebuild' then null else 'understanding_complete' end,
    support_level_disclosed='none',version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_effort_attempt(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_command_id uuid,
  p_selected text,p_recommended text,p_appropriate boolean
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_turn public.v2_build_turns%rowtype;
  v_attempts integer;
  v_retry boolean;
  v_revealed boolean;
  v_message text;
  v_support text;
begin
  if p_selected not in ('quick','standard','deep') or p_recommended not in ('quick','standard','deep')
     or p_appropriate is null or p_command_id is null then
    raise exception using errcode='22023', message='invalid effort attempt';
  end if;
  if p_appropriate <> (p_selected=p_recommended) then
    raise exception using errcode='23514', message='effort appropriateness must match deterministic recommendation';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_turn from public.v2_build_turns as bt where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id
       or v_turn.current_change_id<>p_current_change_id
       or v_turn.turn_kind<>'student_decision'
       or v_turn.speaker<>'student'
       or v_turn.structured_payload->>'context'<>'effort'
       or v_turn.structured_payload->>'selected'<>p_selected
       or (v_turn.structured_payload->'feedback'->>'appropriate')::boolean <> p_appropriate
       or (v_turn.structured_payload->>'recommended') is distinct from
          (case when (v_turn.structured_payload->'feedback'->>'revealed')::boolean
                 or (v_turn.structured_payload->'feedback'->>'appropriate')::boolean
               then p_recommended else null end) then
      raise exception using errcode='23505', message='effort command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
      'feedback',v_turn.structured_payload->'feedback','replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'preparing' or v_change.resume_step<>'effort'
     or v_change.coding_agent_key is null or v_change.prompt_draft is null
     or v_change.effort_category is not null then
    raise exception using errcode='40001', message='stale or ineligible effort attempt';
  end if;
  select pg_catalog.count(*)::integer into v_attempts from public.v2_build_turns as bt
    where bt.current_change_id=p_current_change_id and bt.project_id=p_project_id
      and bt.owner_user_id=p_owner_user_id and bt.turn_kind='student_decision'
      and bt.structured_payload->>'context'='effort';
  v_retry := not p_appropriate and v_attempts=0;
  v_revealed := not p_appropriate and v_attempts>=1;
  -- A correct second answer still follows the nudge disclosed by the first
  -- mismatch; correctness does not erase support already used.
  v_support := case
    when p_appropriate and v_attempts=0 then 'none'
    when p_appropriate or v_retry then 'nudge'
    else 'teach'
  end;
  v_message := case when p_appropriate then
      pg_catalog.initcap(p_selected)||' fits the size and consequence of this change.'
    when v_retry then 'Look at how many connected pieces and how much risk this change has, then try once more.'
    else pg_catalog.initcap(p_recommended)||' is the recommended level for this change.' end;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,help_context_key,support_level,
    policy_version,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,'student_decision','student',
    p_selected,pg_catalog.jsonb_build_object('context','effort','selected',p_selected,
      'recommended',case when v_revealed or p_appropriate then p_recommended else null end,
      'message',v_message,'feedback',pg_catalog.jsonb_build_object(
        'selected',p_selected,'recommended',case when v_revealed or p_appropriate then p_recommended else null end,
        'appropriate',p_appropriate,'retry_allowed',v_retry,'revealed',v_revealed,'message',v_message)),
    'effort_selection',v_support,'phase5-beta-teaching-v1','structured');
  insert into public.v2_learner_evidence(owner_user_id,source_project_id,
    source_current_change_id,competency_key,observed_behavior,elicitation,support_level,
    context_key,source_record_type,source_record_id,source_operation_id,observed_at,
    status,evidence_policy_version)
  values(p_owner_user_id,p_project_id,p_current_change_id,'effort_selection',
    case when p_appropriate then 'Selected an appropriate effort level for the current change.'
      else 'Needed support matching effort to the current change.' end,
    case
      when p_appropriate and v_attempts=0 then 'asked'
      when p_appropriate or v_retry then 'after_hint'
      else 'taught'
    end,
    v_support,case when v_change.risk='slowdown' then 'slowdown_novel' else 'build' end,
    'build_turn',p_command_id,p_command_id,pg_catalog.now(),'active','phase5-beta-evidence-v1');
  update public.v2_current_changes as cc set
    effort_category=case when p_appropriate then p_selected when v_revealed then p_recommended else null end,
    resume_step=case when p_appropriate or v_revealed then 'prompt' else 'effort' end,
    help_context_key='effort_selection',support_level_disclosed=v_support,
    version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),
    'feedback',pg_catalog.jsonb_build_object('selected',p_selected,
      'recommended',case when v_revealed or p_appropriate then p_recommended else null end,
      'appropriate',p_appropriate,'retry_allowed',v_retry,'revealed',v_revealed,'message',v_message),
    'replayed',false);
end;
$$;

create function codize_v2_internal.create_v2_student_check_plan(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_command_id uuid,p_check_id uuid,
  p_check_plan text,p_elicitation text,p_support_level text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare v_change public.v2_current_changes%rowtype; v_check public.v2_checks%rowtype; v_turn public.v2_build_turns%rowtype;
begin
  if p_command_id is null or p_check_id is null or p_check_plan is null
     or pg_catalog.btrim(p_check_plan)='' or pg_catalog.octet_length(p_check_plan)>8192
     or not ((p_elicitation in ('spontaneous','asked') and p_support_level='none')
       or (p_elicitation='after_hint' and p_support_level in ('nudge','clue'))
       or (p_elicitation='taught' and p_support_level='teach')) then
    raise exception using errcode='22023', message='invalid student Check plan';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_turn from public.v2_build_turns as bt where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.project_id<>p_project_id
       or v_turn.current_change_id<>p_current_change_id
       or v_turn.turn_kind<>'student_answer'
       or v_turn.speaker<>'student'
       or v_turn.content<>pg_catalog.btrim(p_check_plan)
       or v_turn.support_level<>p_support_level
       or v_turn.structured_payload->>'context'<>'verification'
       or v_turn.related_record_type<>'check'
       or v_turn.related_record_id<>p_check_id then
      raise exception using errcode='23505', message='student Check command id already used';
    end if;
    select * into v_check from public.v2_checks where id=p_check_id and owner_user_id=p_owner_user_id;
    if not found then
      raise exception using errcode='23503', message='student Check replay source is missing';
    end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'reviewing' or v_change.resume_step<>'check'
     or exists(select 1 from public.v2_checks where current_change_id=p_current_change_id and status='proposed') then
    raise exception using errcode='40001', message='stale or ineligible student Check plan';
  end if;
  if p_elicitation='after_hint'
     and (v_change.help_context_key is distinct from 'testing'
       or v_change.support_level_disclosed is distinct from p_support_level) then
    raise exception using errcode='23514', message='Check support belongs to another interaction';
  end if;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,related_record_type,related_record_id,
    help_context_key,support_level,policy_version,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,'student_answer','student',
    pg_catalog.btrim(p_check_plan),pg_catalog.jsonb_build_object('context','verification','competency_key','testing'),
    'check',p_check_id,'testing',p_support_level,'phase5-beta-teaching-v1','structured');
  insert into public.v2_checks(id,project_id,owner_user_id,current_change_id,
    check_plan,plan_source,status,source_build_turn_id,create_command_id)
  values(p_check_id,p_project_id,p_owner_user_id,p_current_change_id,
    pg_catalog.btrim(p_check_plan),'student','proposed',p_command_id,p_command_id)
  returning * into v_check;
  if public.v2_qualifies_check_plan(pg_catalog.btrim(p_check_plan)) then
    insert into public.v2_learner_evidence(owner_user_id,source_project_id,source_current_change_id,
      competency_key,observed_behavior,elicitation,support_level,context_key,
      source_record_type,source_record_id,source_operation_id,observed_at,status,evidence_policy_version)
    values(p_owner_user_id,p_project_id,p_current_change_id,'testing','Proposed a contextual Check for the current change.',
      p_elicitation,p_support_level,'build','build_turn',p_command_id,p_command_id,
      pg_catalog.now(),'active','phase5-beta-evidence-v1');
  end if;
  update public.v2_current_changes as cc set help_context_key='testing_complete',
    support_level_disclosed='none',version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'replayed',false);
end;
$$;

-- Adaptive return: experienced testers originate a Check before any Check row exists.
create or replace function codize_v2_internal.record_v2_manual_return(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_command_id uuid,p_outcome text,p_check_id uuid
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare v_change public.v2_current_changes%rowtype; v_check public.v2_checks%rowtype; v_turn public.v2_build_turns%rowtype;
begin
  if p_outcome not in ('worked','broken','unsure') or p_command_id is null
     or p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null
     or ((p_outcome='broken') and p_check_id is not null) then
    raise exception using errcode='22023', message='invalid manual return command';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_turn from public.v2_build_turns where id=p_command_id and owner_user_id=p_owner_user_id for update;
  if found then
    if v_turn.project_id<>p_project_id or v_turn.current_change_id<>p_current_change_id
       or v_turn.turn_kind<>'return_report' or v_turn.structured_payload->>'outcome'<>p_outcome
       or v_turn.related_record_id is distinct from p_check_id then
      raise exception using errcode='23505', message='manual return command id already used';
    end if;
    if p_check_id is not null then select * into v_check from public.v2_checks where id=p_check_id; end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.lifecycle_state<>'awaiting_agent' or v_change.resume_step<>'return_outcome'
     or v_change.latest_prompt_version_id is null or v_change.handoff_command_id is null then
    raise exception using errcode='40001', message='stale or ineligible manual return';
  end if;
  if p_outcome='broken' then
    update public.v2_current_changes as cc set student_return_outcome='broken',
      lifecycle_state='recovering',resume_step='recovery_symptom',version=cc.version+1
      where cc.id=v_change.id returning * into v_change;
  else
    if p_check_id is not null then
      insert into public.v2_checks(id,project_id,owner_user_id,current_change_id,
        check_plan,plan_source,status,create_command_id)
      values(p_check_id,p_project_id,p_owner_user_id,p_current_change_id,
        v_change.done_condition_snapshot,'codize','proposed',p_command_id) returning * into v_check;
    end if;
    update public.v2_current_changes as cc set student_return_outcome=p_outcome,
      lifecycle_state='reviewing',resume_step='check',help_context_key='testing',
      support_level_disclosed=case when p_check_id is null then 'none' else 'teach' end,
      unresolved_uncertainty_summary=case when p_outcome='unsure' then 'The student was unsure before checking.' else null end,
      version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  end if;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,structured_payload,related_record_type,related_record_id,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,'return_report','student',
    pg_catalog.jsonb_build_object('outcome',p_outcome),case when p_check_id is null then null else 'check' end,
    p_check_id,'structured');
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'replayed',false);
end;
$$;

-- Prompt edits are the one student-facing mutation of risk-relevant state.
-- Risk and its freshness identity move in the same transaction. A changed
-- fingerprint also reopens effort selection because consequence may differ.
create function codize_v2_internal.update_v2_prompt_draft_with_risk(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_expected_prompt_draft_version bigint,
  p_prompt_draft text,p_done_condition_snapshot text,p_boundary_snapshots text[],
  p_risk text,p_risk_reason_key text,p_risk_policy_version text,
  p_risk_input_fingerprint text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_expected_fingerprint text;
  v_risk_changed boolean;
begin
  if p_risk not in ('normal','slowdown')
     or (p_risk='slowdown') <> (p_risk_reason_key is not null)
     or p_risk_policy_version is null
     or pg_catalog.btrim(p_risk_policy_version) in ('','unresolved-v0') then
    raise exception using errcode='22023', message='invalid prompt risk decision';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  if v_change.version<>p_expected_current_change_version
     or v_change.prompt_draft_version<>p_expected_prompt_draft_version then
    raise exception using errcode='40001', message='stale prompt draft';
  end if;
  if v_change.lifecycle_state<>'preparing' or v_change.handoff_command_id is not null
     or v_change.coding_agent_key is null
     or v_change.teaching_policy_version<>'phase5-beta-teaching-v1' then
    raise exception using errcode='23514', message='prompt draft cannot change in this state';
  end if;
  if p_prompt_draft is null or pg_catalog.btrim(p_prompt_draft)=''
     or pg_catalog.octet_length(p_prompt_draft)>65536
     or (p_done_condition_snapshot is not null and (
       pg_catalog.btrim(p_done_condition_snapshot)=''
       or pg_catalog.octet_length(p_done_condition_snapshot)>8192))
     or not public.v2_valid_text_array(p_boundary_snapshots,32,8192,256,true) then
    raise exception using errcode='23514', message='invalid bounded prompt draft';
  end if;
  v_expected_fingerprint := public.v2_risk_input_fingerprint(
    v_change.goal_snapshot,p_done_condition_snapshot,p_boundary_snapshots,p_prompt_draft);
  if p_risk_input_fingerprint is distinct from v_expected_fingerprint then
    raise exception using errcode='23514', message='risk input fingerprint mismatch';
  end if;
  v_risk_changed := v_change.risk is distinct from p_risk
    or v_change.risk_reason_key is distinct from p_risk_reason_key;
  if v_change.prompt_draft is distinct from p_prompt_draft
     or v_change.done_condition_snapshot is distinct from p_done_condition_snapshot
     or v_change.boundary_snapshots is distinct from p_boundary_snapshots
     or v_change.risk is distinct from p_risk
     or v_change.risk_reason_key is distinct from p_risk_reason_key
     or v_change.risk_policy_version is distinct from p_risk_policy_version
     or v_risk_changed then
    update public.v2_current_changes as cc set
      prompt_draft=p_prompt_draft,
      prompt_draft_version=cc.prompt_draft_version
        + case when cc.prompt_draft is distinct from p_prompt_draft then 1 else 0 end,
      done_condition_snapshot=p_done_condition_snapshot,
      boundary_snapshots=p_boundary_snapshots,
      risk=p_risk,risk_reason_key=p_risk_reason_key,
      risk_policy_version=pg_catalog.btrim(p_risk_policy_version),
      risk_input_fingerprint=v_expected_fingerprint,
      effort_category=case when v_risk_changed then null else cc.effort_category end,
      resume_step=case when v_risk_changed or cc.effort_category is null then 'effort' else 'prompt' end,
      version=cc.version+1
    where cc.id=v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change));
end;
$$;

-- Phase 4's direct effort helper remains only for pre-Phase-5 compatibility.
-- A Phase 5 Current Change must use record_v2_effort_attempt.
create or replace function codize_v2_internal.update_v2_effort(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_current_change_version bigint,p_effort_category text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare v_change public.v2_current_changes%rowtype;
begin
  if p_effort_category not in ('quick','standard','deep') then
    raise exception using errcode='23514', message='unsupported effort category';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id
    and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  if v_change.teaching_policy_version like 'phase5-%' then
    raise exception using errcode='23514', message='Phase 5 effort requires the teaching-aware command';
  end if;
  if v_change.version<>p_expected_current_change_version then
    raise exception using errcode='40001', message='stale Build state';
  end if;
  if v_change.lifecycle_state<>'preparing' or v_change.handoff_command_id is not null
     or v_change.coding_agent_key is null or v_change.prompt_draft is null
     or v_change.teaching_policy_version='unresolved-v0'
     or v_change.risk_policy_version='unresolved-v0' then
    raise exception using errcode='23514', message='effort cannot change in this state';
  end if;
  if v_change.effort_category is distinct from p_effort_category then
    update public.v2_current_changes as cc set effort_category=p_effort_category,
      resume_step='effort',version=cc.version+1
      where cc.id=v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change));
end;
$$;

create function public.v2_guard_fresh_prompt_risk()
returns trigger language plpgsql set search_path=''
as $$
declare v_change public.v2_current_changes%rowtype;
begin
  if new.purpose='feature' and (
       tg_op='INSERT'
       or (old.handed_off_at is null and new.handed_off_at is not null)
     ) then
    select * into v_change from public.v2_current_changes as cc
      where cc.id=new.current_change_id and cc.project_id=new.project_id
        and cc.owner_user_id=new.owner_user_id;
    if not found or (
       v_change.teaching_policy_version like 'phase5-%' and (
         v_change.risk_policy_version<>'phase5-beta-risk-v1'
         or v_change.risk_input_fingerprint is null
         or v_change.risk_input_fingerprint is distinct from
            public.v2_risk_input_fingerprint(v_change.goal_snapshot,
              v_change.done_condition_snapshot,v_change.boundary_snapshots,v_change.prompt_draft)
       )) then
      raise exception using errcode='23514', message='prompt risk decision is stale';
    end if;
  end if;
  return new;
end;
$$;

create trigger v2_prompt_versions_fresh_risk_trg
before insert or update of handed_off_at on public.v2_prompt_versions
for each row execute function public.v2_guard_fresh_prompt_risk();

-- Close the Phase 4 compatibility seam that otherwise allowed an agent
-- selection to skip a persisted Phase 5 intervention.
create or replace function codize_v2_internal.update_v2_coding_agent(
  p_owner_user_id uuid,p_project_id uuid,p_current_change_id uuid,
  p_expected_project_version bigint,p_expected_current_change_version bigint,
  p_coding_agent_key text
)
returns jsonb language plpgsql security definer set search_path=''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
begin
  if not public.v2_valid_coding_agent_key(p_coding_agent_key) then
    raise exception using errcode='23514', message='unsupported coding agent';
  end if;
  select * into v_project from public.v2_projects as p
    where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id
      and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  if v_project.version<>p_expected_project_version
     or v_change.version<>p_expected_current_change_version then
    raise exception using errcode='40001', message='stale Build state';
  end if;
  if v_change.lifecycle_state<>'preparing'
     or v_change.resume_step not in ('choose_agent','prompt','effort')
     or v_change.handoff_command_id is not null
     or v_change.teaching_policy_version='unresolved-v0'
     or v_change.risk_policy_version='unresolved-v0' then
    raise exception using errcode='23514', message='coding agent cannot change in this state';
  end if;
  if v_project.coding_agent_key is distinct from p_coding_agent_key then
    update public.v2_projects as p set coding_agent_key=p_coding_agent_key,
      version=p.version+1 where p.id=v_project.id returning * into v_project;
  end if;
  if v_change.coding_agent_key is distinct from p_coding_agent_key then
    update public.v2_current_changes as cc set coding_agent_key=p_coding_agent_key,
      resume_step='prompt',version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object('project',pg_catalog.to_jsonb(v_project),
    'current_change',pg_catalog.to_jsonb(v_change));
end;
$$;

-- Public wrappers.
create function public.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.disclose_v2_teaching_help($1,$2,$3,$4,$5,$6) $$;
create function public.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_teaching_response($1,$2,$3,$4,$5,$6,$7,$8,$9) $$;
create function public.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_effort_attempt($1,$2,$3,$4,$5,$6,$7,$8) $$;
create function public.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.create_v2_student_check_plan($1,$2,$3,$4,$5,$6,$7,$8,$9) $$;
create function public.update_v2_prompt_draft_with_risk(
  uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text
)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.update_v2_prompt_draft_with_risk(
  $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) $$;

alter function codize_v2_internal.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean) owner to codize_v2_executor;
alter function codize_v2_internal.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text) owner to codize_v2_executor;

revoke execute on function
  public.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  public.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  public.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  public.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  public.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text),
  public.v2_risk_input_fingerprint(text,text,text[],text),
  public.v2_qualifies_structured_response(text,text),
  public.v2_qualifies_check_plan(text),
  public.v2_guard_fresh_prompt_risk()
from public,anon,authenticated;
revoke execute on function
  codize_v2_internal.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  codize_v2_internal.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  codize_v2_internal.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  codize_v2_internal.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  codize_v2_internal.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text)
from public,anon,authenticated,service_role;
grant execute on function
  codize_v2_internal.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  codize_v2_internal.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  codize_v2_internal.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  codize_v2_internal.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  codize_v2_internal.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text)
to service_role;
grant execute on function
  public.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  public.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  public.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  public.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  public.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text),
  public.v2_risk_input_fingerprint(text,text,text[],text),
  public.v2_qualifies_structured_response(text,text),
  public.v2_qualifies_check_plan(text)
to service_role;
grant execute on function
  public.v2_risk_input_fingerprint(text,text,text[],text),
  public.v2_qualifies_structured_response(text,text),
  public.v2_qualifies_check_plan(text)
to codize_v2_executor;

revoke create on schema codize_v2_internal from codize_v2_executor;
revoke codize_v2_executor from current_user;

comment on function public.resolve_v2_current_change_policy(uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text,text)
  is 'Atomically persists Phase 5 deterministic teaching/risk/check policy and the next durable resume step.';
