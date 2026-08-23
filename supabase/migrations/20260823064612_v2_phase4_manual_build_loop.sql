-- Codize V2 Phase 4: deterministic manual setup, return, check, and preferences.
-- All writes remain backend-only through invoker wrappers over narrowly granted
-- SECURITY DEFINER implementations. Lock order is Project -> Current Change ->
-- Plan Item -> Check.

create function codize_v2_internal.establish_v2_manual_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid,
  p_project_context text,
  p_plan_item_id uuid,
  p_change_label text,
  p_done_condition text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_item public.v2_plan_items%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_command_id is null
     or p_plan_item_id is null
     or p_project_context is null or pg_catalog.btrim(p_project_context) = ''
     or pg_catalog.octet_length(p_project_context) > 8192
     or p_change_label is null or pg_catalog.btrim(p_change_label) = ''
     or pg_catalog.octet_length(p_change_label) > 200
     or p_done_condition is null or pg_catalog.btrim(p_done_condition) = ''
     or pg_catalog.octet_length(p_done_condition) > 4096 then
    raise exception using errcode = '22023', message = 'invalid manual Project setup command';
  end if;

  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  if v_project.last_plan_command_id = p_command_id then
    select * into v_item from public.v2_plan_items as pi
    where pi.id = p_plan_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id;
    if not found
       or v_project.setup_draft ->> 'project_context' <> pg_catalog.btrim(p_project_context)
       or v_item.label <> pg_catalog.btrim(p_change_label)
       or v_item.intended_outcome <> pg_catalog.btrim(p_done_condition) then
      raise exception using errcode = '23505', message = 'manual setup command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'project', pg_catalog.to_jsonb(v_project),
      'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', true
    );
  end if;

  -- A browser may lose the successful setup response and return with fresh
  -- in-memory command IDs. Recognize the one canonical initial setup by its
  -- durable Project state and payload; do not create a second Plan Item.
  if v_project.lifecycle_state = 'active'
     and v_project.setup_resume_step = 'ready'
     and v_project.version = 2
     and v_project.plan_version = 2
     and v_project.setup_draft = pg_catalog.jsonb_build_object(
       'project_context', pg_catalog.btrim(p_project_context),
       'source', 'student_setup'
     ) then
    select * into v_item from public.v2_plan_items as pi
    where pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id
      and pi.scope_band = 'first_version'
      and pi.status = 'ready'
      and pi.label = pg_catalog.btrim(p_change_label)
      and pi.intended_outcome = pg_catalog.btrim(p_done_condition);
    if found and (
      select pg_catalog.count(*) from public.v2_plan_items as pi
      where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id
    ) = 1 then
      return pg_catalog.jsonb_build_object(
        'project', pg_catalog.to_jsonb(v_project),
        'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', true
      );
    end if;
  end if;

  if v_project.version <> p_expected_project_version
     or v_project.lifecycle_state <> 'draft'
     or v_project.setup_resume_step not in ('idea_capture', 'existing_project_context') then
    raise exception using errcode = '40001', message = 'stale or ineligible manual Project setup';
  end if;
  if exists (select 1 from public.v2_plan_items as pi
             where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id) then
    raise exception using errcode = '23514', message = 'manual setup requires an empty plan';
  end if;

  insert into public.v2_plan_items (
    id, project_id, owner_user_id, label, intended_outcome,
    scope_band, status, order_key
  ) values (
    p_plan_item_id, p_project_id, p_owner_user_id,
    pg_catalog.btrim(p_change_label), pg_catalog.btrim(p_done_condition),
    'first_version', 'ready', 1024
  ) returning * into v_item;

  update public.v2_projects as p
  set lifecycle_state = 'active', setup_resume_step = 'ready',
      setup_draft = pg_catalog.jsonb_build_object(
        'project_context', pg_catalog.btrim(p_project_context),
        'source', 'student_setup'
      ),
      last_plan_command_id = p_command_id,
      plan_version = p.plan_version + 1,
      version = p.version + 1
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  returning * into v_project;

  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project),
    'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', false
  );
end;
$$;

create or replace function codize_v2_internal.start_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_create_command_id uuid,
  p_plan_item_id uuid,
  p_change_kind text,
  p_goal_snapshot text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_plan_item public.v2_plan_items%rowtype;
  v_change public.v2_current_changes%rowtype;
  v_goal text;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_create_command_id is null
     or p_change_kind not in ('build', 'recovery')
     or p_goal_snapshot is null or pg_catalog.btrim(p_goal_snapshot) = ''
     or pg_catalog.octet_length(p_goal_snapshot) > 4096 then
    raise exception using errcode = '22023', message = 'invalid V2 Current Change start command';
  end if;

  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;

  if p_plan_item_id is not null then
    select * into v_plan_item from public.v2_plan_items as pi
    where pi.id = p_plan_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id for update;
    if not found then raise exception using errcode = 'P0002', message = 'v2 plan item not found'; end if;
    if v_plan_item.status in ('done', 'removed') then
      raise exception using errcode = '23514', message = 'terminal V2 Plan Item cannot start a Current Change';
    end if;
    v_goal := v_plan_item.label;
  else
    v_goal := pg_catalog.btrim(p_goal_snapshot);
  end if;

  select * into v_change from public.v2_current_changes as cc
  where cc.owner_user_id = p_owner_user_id and cc.create_command_id = p_create_command_id
  for update;
  if found then
    if v_change.project_id <> p_project_id or v_change.change_kind <> p_change_kind
       or v_change.plan_item_id is distinct from p_plan_item_id
       or v_change.goal_snapshot <> v_goal then
      raise exception using errcode = '23505', message = 'V2 Current Change command id already used';
    end if;
    return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change), 'replayed', true);
  end if;

  if v_project.version <> p_expected_project_version
     or v_project.lifecycle_state not in ('active', 'temporary_recovery') then
    raise exception using errcode = '40001', message = 'stale or ineligible V2 Project';
  end if;
  if v_project.lifecycle_state = 'temporary_recovery' and p_change_kind <> 'recovery' then
    raise exception using errcode = '23514', message = 'temporary Project requires Recovery';
  end if;
  if exists (select 1 from public.v2_current_changes as cc
    where cc.project_id = p_project_id and cc.owner_user_id = p_owner_user_id
      and cc.lifecycle_state in ('preparing','awaiting_agent','reviewing','recovering')) then
    raise exception using errcode = '23505', message = 'V2 Project already has a nonterminal Current Change';
  end if;

  insert into public.v2_current_changes (
    project_id, owner_user_id, plan_item_id, change_kind, lifecycle_state,
    resume_step, goal_snapshot, teaching_mode, teaching_reason_key,
    teaching_policy_version, risk, risk_policy_version, check_requirement,
    create_command_id
  ) values (
    p_project_id, p_owner_user_id, p_plan_item_id, p_change_kind, 'preparing',
    'confirm_change', v_goal, 'skip', 'policy_not_evaluated', 'unresolved-v0',
    'normal', 'unresolved-v0', 'required', p_create_command_id
  ) returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change), 'replayed', false);
end;
$$;

create function codize_v2_internal.confirm_v2_manual_current_change(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_command_id uuid
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_item public.v2_plan_items%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null or p_command_id is null then
    raise exception using errcode = '22023', message = 'invalid manual confirmation command';
  end if;
  perform 1 from public.v2_projects as p where p.id = p_project_id
    and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id = p_current_change_id and cc.project_id = p_project_id
      and cc.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 current change not found'; end if;
  if v_change.policy_resolution_command_id = p_command_id then
    return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change), 'replayed', true);
  end if;
  if v_change.version <> p_expected_current_change_version
     or v_change.lifecycle_state <> 'preparing' or v_change.resume_step <> 'confirm_change'
     or v_change.policy_resolution_command_id is not null then
    raise exception using errcode = '40001', message = 'stale or ineligible manual confirmation';
  end if;
  if v_change.plan_item_id is null then
    raise exception using errcode = '23514', message = 'manual Build requires a linked Plan Item';
  end if;
  select * into v_item from public.v2_plan_items as pi
    where pi.id = v_change.plan_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 plan item not found'; end if;

  update public.v2_current_changes as cc
  set done_condition_snapshot = v_item.intended_outcome,
      teaching_mode = 'skip', teaching_target = null,
      teaching_reason_key = 'phase4_manual_loop',
      teaching_policy_version = 'phase4-mechanical-v1',
      risk = 'normal', risk_reason_key = null,
      risk_policy_version = 'phase4-mechanical-v1',
      check_requirement = 'required', check_waiver_reason_key = null,
      policy_resolution_command_id = p_command_id,
      resume_step = 'choose_agent', version = cc.version + 1
  where cc.id = v_change.id returning * into v_change;
  return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change), 'replayed', false);
end;
$$;

create function codize_v2_internal.record_v2_manual_return(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_command_id uuid,
  p_outcome text, p_check_id uuid
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_check public.v2_checks%rowtype;
  v_turn public.v2_build_turns%rowtype;
begin
  if p_outcome not in ('worked','broken','unsure') or p_command_id is null
     or p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null
     or ((p_outcome in ('worked','unsure')) <> (p_check_id is not null)) then
    raise exception using errcode = '22023', message = 'invalid manual return command';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
    where cc.id=p_current_change_id and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_turn from public.v2_build_turns as bt where bt.id=p_command_id
    and bt.owner_user_id=p_owner_user_id for update;
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
      lifecycle_state='recovering', resume_step='recovery_symptom', version=cc.version+1
      where cc.id=v_change.id returning * into v_change;
  else
    insert into public.v2_checks(id,project_id,owner_user_id,current_change_id,
      check_plan,plan_source,status,create_command_id)
    values(p_check_id,p_project_id,p_owner_user_id,p_current_change_id,
      v_change.done_condition_snapshot,'codize','proposed',p_command_id)
    returning * into v_check;
    update public.v2_current_changes as cc set student_return_outcome=p_outcome,
      lifecycle_state='reviewing',resume_step='check',
      unresolved_uncertainty_summary=case when p_outcome='unsure' then 'The student was unsure before checking.' else null end,
      version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  end if;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,structured_payload,related_record_type,related_record_id,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,'return_report','student',
    pg_catalog.jsonb_build_object('outcome',p_outcome),
    case when p_check_id is null then null else 'check' end,p_check_id,'structured');
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'replayed',false);
end;
$$;

create function codize_v2_internal.record_v2_manual_check(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_check_id uuid, p_expected_current_change_version bigint,
  p_expected_check_version bigint, p_command_id uuid, p_result text,
  p_observation text, p_performed_by_student boolean, p_next_check_id uuid
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_check public.v2_checks%rowtype;
  v_next public.v2_checks%rowtype;
  v_turn public.v2_build_turns%rowtype;
begin
  if p_result not in ('worked','partly_worked','did_not_work','unsure')
     or p_performed_by_student is distinct from true
     or p_observation is null or pg_catalog.btrim(p_observation)=''
     or pg_catalog.octet_length(p_observation)>16384
     or ((p_result='unsure') <> (p_next_check_id is not null)) then
    raise exception using errcode='22023', message='a student-performed check and observation are required';
  end if;
  perform 1 from public.v2_projects as p where p.id=p_project_id and p.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc where cc.id=p_current_change_id
    and cc.project_id=p_project_id and cc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 current change not found'; end if;
  select * into v_check from public.v2_checks as vc where vc.id=p_check_id
    and vc.current_change_id=p_current_change_id and vc.project_id=p_project_id
    and vc.owner_user_id=p_owner_user_id for update;
  if not found then raise exception using errcode='P0002', message='v2 check not found'; end if;
  select * into v_turn from public.v2_build_turns as bt where bt.id=p_command_id and bt.owner_user_id=p_owner_user_id;
  if found then
    if v_turn.related_record_id<>p_check_id or v_turn.structured_payload->>'result'<>p_result
       or v_turn.content<>pg_catalog.btrim(p_observation)
       or nullif(v_turn.structured_payload->>'next_check_id','')::uuid is distinct from p_next_check_id then
      raise exception using errcode='23505', message='manual check command id already used';
    end if;
    if p_next_check_id is not null then select * into v_next from public.v2_checks where id=p_next_check_id; end if;
    return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'next_check',pg_catalog.to_jsonb(v_next),'replayed',true);
  end if;
  if v_change.version<>p_expected_current_change_version or v_check.version<>p_expected_check_version
     or v_change.lifecycle_state<>'reviewing' or v_change.resume_step<>'check'
     or v_check.status<>'proposed' then
    raise exception using errcode='40001', message='stale or ineligible manual check';
  end if;
  update public.v2_checks as vc set status='performed',result=p_result,
    student_observation=pg_catalog.btrim(p_observation),performed_at=pg_catalog.now(),
    version=vc.version+1 where vc.id=v_check.id returning * into v_check;
  if p_result='unsure' then
    insert into public.v2_checks(id,project_id,owner_user_id,current_change_id,
      check_plan,plan_source,status,supersedes_check_id,create_command_id)
    values(p_next_check_id,p_project_id,p_owner_user_id,p_current_change_id,
      v_check.check_plan,'codize','proposed',v_check.id,p_command_id) returning * into v_next;
  end if;
  update public.v2_current_changes as cc set
    lifecycle_state=case when p_result in ('did_not_work','partly_worked') then 'recovering' else 'reviewing' end,
    resume_step=case when p_result in ('did_not_work','partly_worked') then 'recovery_symptom'
                     when p_result='worked' then 'understand' else 'check' end,
    -- REVIEWING/check is already the canonical state on an UNSURE retry. Keep
    -- the guard intact by recording a real, bounded Current Change mutation
    -- whose check id advances on every attempt; the full observation remains
    -- provenance-preserved on the performed Check and Build Turn.
    unresolved_uncertainty_summary=case when p_result='unsure'
      then 'Student remains unsure after check ' || v_check.id::text || '.'
      else cc.unresolved_uncertainty_summary end,
    version=cc.version+1 where cc.id=v_change.id returning * into v_change;
  insert into public.v2_build_turns(id,project_id,owner_user_id,current_change_id,
    turn_kind,speaker,content,structured_payload,related_record_type,related_record_id,retention_class)
  values(p_command_id,p_project_id,p_owner_user_id,p_current_change_id,'student_answer','student',
    pg_catalog.btrim(p_observation),pg_catalog.jsonb_build_object(
      'result',p_result,'performed_by_student',true,'next_check_id',p_next_check_id),
    'check',p_check_id,'structured');
  return pg_catalog.jsonb_build_object('current_change',pg_catalog.to_jsonb(v_change),'check',pg_catalog.to_jsonb(v_check),'next_check',pg_catalog.to_jsonb(v_next),'replayed',false);
end;
$$;

create function codize_v2_internal.update_v2_dialogue_sound(
  p_owner_user_id uuid, p_expected_version bigint, p_dialogue_sound_enabled boolean
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare v_pref public.v2_user_preferences%rowtype;
begin
  if p_owner_user_id is null or p_expected_version is null or p_expected_version < 0
     or p_dialogue_sound_enabled is null then
    raise exception using errcode='22023', message='invalid preference command';
  end if;
  select * into v_pref from public.v2_user_preferences where owner_user_id=p_owner_user_id for update;
  if not found then
    if p_expected_version<>0 then raise exception using errcode='40001', message='stale preference version'; end if;
    insert into public.v2_user_preferences(owner_user_id,dialogue_sound_enabled)
      values(p_owner_user_id,p_dialogue_sound_enabled) returning * into v_pref;
  else
    if v_pref.dialogue_sound_enabled = p_dialogue_sound_enabled then
      return pg_catalog.to_jsonb(v_pref);
    end if;
    if v_pref.version<>p_expected_version then raise exception using errcode='40001', message='stale preference version'; end if;
    update public.v2_user_preferences as up set dialogue_sound_enabled=p_dialogue_sound_enabled,
      version=up.version+1 where owner_user_id=p_owner_user_id returning * into v_pref;
  end if;
  return pg_catalog.to_jsonb(v_pref);
end;
$$;

create function public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.establish_v2_manual_project($1,$2,$3,$4,$5,$6,$7,$8) $$;
create function public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.confirm_v2_manual_current_change($1,$2,$3,$4,$5) $$;
create function public.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_manual_return($1,$2,$3,$4,$5,$6,$7) $$;
create function public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.record_v2_manual_check($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) $$;
create function public.update_v2_dialogue_sound(uuid,bigint,boolean)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.update_v2_dialogue_sound($1,$2,$3) $$;

alter function codize_v2_internal.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.start_v2_current_change(uuid,uuid,bigint,uuid,uuid,text,text) owner to codize_v2_executor;
alter function codize_v2_internal.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid) owner to codize_v2_executor;
alter function codize_v2_internal.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid) owner to codize_v2_executor;
alter function codize_v2_internal.update_v2_dialogue_sound(uuid,bigint,boolean) owner to codize_v2_executor;

revoke execute on function
  public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  public.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  public.update_v2_dialogue_sound(uuid,bigint,boolean)
from public, anon, authenticated;
revoke execute on function
  codize_v2_internal.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  codize_v2_internal.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  codize_v2_internal.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  codize_v2_internal.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  codize_v2_internal.update_v2_dialogue_sound(uuid,bigint,boolean)
from public, anon, authenticated, service_role;
grant execute on function
  codize_v2_internal.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  codize_v2_internal.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  codize_v2_internal.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  codize_v2_internal.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  codize_v2_internal.update_v2_dialogue_sound(uuid,bigint,boolean)
to service_role;
grant execute on function
  public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  public.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  public.update_v2_dialogue_sound(uuid,bigint,boolean)
to service_role;

comment on function public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text)
  is 'Backend-only first manual Project setup and first Plan Item creation.';
comment on function public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid)
  is 'Backend-only Phase 4 mechanical confirmation; no adaptive teaching inference.';
comment on function public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid)
  is 'Records only a student-performed check; agent claims cannot satisfy completion.';
