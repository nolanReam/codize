-- Codize V2.3B: deterministic agent, prompt, effort, handoff, and generation lifecycle.
-- Additive only: the accepted eleven-table V2 entity cut is unchanged.

create function public.v2_valid_coding_agent_key(p_key text)
returns boolean
language sql
immutable
strict
parallel safe
security invoker
set search_path = ''
as $$
  select p_key in ('codex', 'claude_code', 'cursor', 'chatgpt', 'replit', 'other');
$$;

revoke execute on function public.v2_valid_coding_agent_key(text)
  from public, anon, authenticated, service_role;

-- V2.2 retained the aggregate input version but did not snapshot every
-- structured feature-prompt input. These nullable columns preserve upgrade
-- compatibility: pre-V2.3B feature rows remain unreadable as current and fail
-- closed at handoff, while every new feature acceptance receives exact values
-- from the locked Current Change in the trigger below.
alter table public.v2_prompt_versions
  add column input_goal_snapshot text,
  add column input_done_condition_snapshot text,
  add column input_boundary_snapshots text[];

-- The accepted feature snapshot must be exactly the durable Build inputs.
-- Aggregate Current Change version remains provenance/concurrency data, not a
-- freshness token: DETACH and other unrelated aggregate writes may increment it.
create function public.v2_guard_feature_prompt_snapshot()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
begin
  if tg_op = 'UPDATE' and (
    new.input_goal_snapshot is distinct from old.input_goal_snapshot
    or new.input_done_condition_snapshot is distinct from old.input_done_condition_snapshot
    or new.input_boundary_snapshots is distinct from old.input_boundary_snapshots
  ) then
    raise exception using errcode = '23514',
      message = 'feature prompt input snapshots are immutable';
  end if;
  if new.purpose <> 'feature' then
    return new;
  end if;
  if tg_op = 'UPDATE'
     and not (old.handoff_command_id is null and new.handoff_command_id is not null) then
    return new;
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = new.current_change_id
    and cc.project_id = new.project_id
    and cc.owner_user_id = new.owner_user_id;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;
  if tg_op = 'INSERT' then
    new.input_goal_snapshot := v_change.goal_snapshot;
    new.input_done_condition_snapshot := v_change.done_condition_snapshot;
    new.input_boundary_snapshots := v_change.boundary_snapshots;
  end if;
  if v_change.lifecycle_state <> 'preparing'
     or v_change.resume_step not in ('prompt', 'effort')
     or v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0'
     or v_change.prompt_draft is null
     or v_change.coding_agent_key is null
     or v_change.effort_category is null
     or new.content is distinct from v_change.prompt_draft
     or new.coding_agent_key is distinct from v_change.coding_agent_key
     or new.effort_category is distinct from v_change.effort_category
     or new.input_goal_snapshot is distinct from v_change.goal_snapshot
     or new.input_done_condition_snapshot is distinct from v_change.done_condition_snapshot
     or new.input_boundary_snapshots is distinct from v_change.boundary_snapshots
     or (tg_op = 'INSERT' and new.input_current_change_version <> v_change.version)
     or (tg_op = 'UPDATE' and (
       v_change.latest_prompt_version_id <> new.id
     )) then
    raise exception using errcode = '23514',
      message = 'feature prompt snapshot does not match the current Build state';
  end if;
  return new;
end;
$$;

revoke execute on function public.v2_guard_feature_prompt_snapshot()
  from public, anon, authenticated, service_role;
create trigger v2_09_feature_prompt_snapshot
  before insert or update on public.v2_prompt_versions
  for each row execute function public.v2_guard_feature_prompt_snapshot();

grant codize_v2_executor to current_user with set true;
grant create on schema codize_v2_internal to codize_v2_executor;

create function codize_v2_internal.update_v2_coding_agent(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_project_version bigint,
  p_expected_current_change_version bigint,
  p_coding_agent_key text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
begin
  if not public.v2_valid_coding_agent_key(p_coding_agent_key) then
    raise exception using errcode = '23514', message = 'unsupported coding agent';
  end if;
  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 current change not found'; end if;
  if v_project.version <> p_expected_project_version
     or v_change.version <> p_expected_current_change_version then
    raise exception using errcode = '40001', message = 'stale Build state';
  end if;
  if v_change.lifecycle_state <> 'preparing' or v_change.handoff_command_id is not null
     or v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514', message = 'coding agent cannot change in this state';
  end if;
  if v_project.coding_agent_key is distinct from p_coding_agent_key then
    update public.v2_projects as p set coding_agent_key = p_coding_agent_key,
      version = p.version + 1 where p.id = v_project.id returning * into v_project;
  end if;
  if v_change.coding_agent_key is distinct from p_coding_agent_key then
    update public.v2_current_changes as cc set coding_agent_key = p_coding_agent_key,
      resume_step = 'prompt', version = cc.version + 1
    where cc.id = v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project), 'current_change', pg_catalog.to_jsonb(v_change));
end;
$$;

create function codize_v2_internal.update_v2_prompt_draft(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint,
  p_prompt_draft text,
  p_done_condition_snapshot text,
  p_boundary_snapshots text[]
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
begin
  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 current change not found'; end if;
  if v_change.version <> p_expected_current_change_version
     or v_change.prompt_draft_version <> p_expected_prompt_draft_version then
    raise exception using errcode = '40001', message = 'stale prompt draft';
  end if;
  if v_change.lifecycle_state <> 'preparing' or v_change.handoff_command_id is not null
     or v_change.coding_agent_key is null
     or v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514', message = 'prompt draft cannot change in this state';
  end if;
  if p_prompt_draft is null or pg_catalog.btrim(p_prompt_draft) = ''
     or pg_catalog.octet_length(p_prompt_draft) > 65536
     or (p_done_condition_snapshot is not null and (
       pg_catalog.btrim(p_done_condition_snapshot) = ''
       or pg_catalog.octet_length(p_done_condition_snapshot) > 8192))
     or not public.v2_valid_text_array(p_boundary_snapshots, 32, 8192, 256, true) then
    raise exception using errcode = '23514', message = 'invalid bounded prompt draft';
  end if;
  if v_change.prompt_draft is distinct from p_prompt_draft
     or v_change.done_condition_snapshot is distinct from p_done_condition_snapshot
     or v_change.boundary_snapshots is distinct from p_boundary_snapshots then
    update public.v2_current_changes as cc
    set prompt_draft = p_prompt_draft,
        prompt_draft_version = cc.prompt_draft_version
          + case when cc.prompt_draft is distinct from p_prompt_draft then 1 else 0 end,
        done_condition_snapshot = p_done_condition_snapshot,
        boundary_snapshots = p_boundary_snapshots,
        resume_step = case when cc.effort_category is null then 'effort' else 'prompt' end,
        version = cc.version + 1
    where cc.id = v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change));
end;
$$;

create function codize_v2_internal.update_v2_effort(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_effort_category text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare v_change public.v2_current_changes%rowtype;
begin
  if p_effort_category not in ('quick', 'standard', 'deep') then
    raise exception using errcode = '23514', message = 'unsupported effort category';
  end if;
  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_change from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 current change not found'; end if;
  if v_change.version <> p_expected_current_change_version then
    raise exception using errcode = '40001', message = 'stale Build state';
  end if;
  if v_change.lifecycle_state <> 'preparing' or v_change.handoff_command_id is not null
     or v_change.coding_agent_key is null or v_change.prompt_draft is null
     or v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514', message = 'effort cannot change in this state';
  end if;
  if v_change.effort_category is distinct from p_effort_category then
    update public.v2_current_changes as cc set effort_category = p_effort_category,
      resume_step = 'effort', version = cc.version + 1
    where cc.id = v_change.id returning * into v_change;
  end if;
  return pg_catalog.jsonb_build_object('current_change', pg_catalog.to_jsonb(v_change));
end;
$$;

create function codize_v2_internal.start_v2_generation_attempt(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_command_id uuid,
  p_target_current_change_id uuid,
  p_target_recovery_case_id uuid,
  p_purpose text,
  p_target_aggregate_version bigint,
  p_policy_version text,
  p_config_version text,
  p_provider_key text,
  p_model_key text,
  p_input_sha256 text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_attempt public.v2_generation_attempts%rowtype;
  v_actual_version bigint;
begin
  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_attempt from public.v2_generation_attempts as ga
  where ga.owner_user_id = p_owner_user_id and ga.attempt_command_id = p_command_id for update;
  if found then
    if v_attempt.project_id <> p_project_id or v_attempt.purpose <> p_purpose
       or v_attempt.target_current_change_id is distinct from p_target_current_change_id
       or v_attempt.target_recovery_case_id is distinct from p_target_recovery_case_id
       or v_attempt.target_aggregate_version <> p_target_aggregate_version
       or v_attempt.policy_version is distinct from p_policy_version
       or v_attempt.config_version <> p_config_version
       or v_attempt.provider_key <> p_provider_key
       or v_attempt.model_key <> p_model_key
       or v_attempt.input_sha256 <> p_input_sha256 then
      raise exception using errcode = '23505', message = 'generation command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'generation_attempt', pg_catalog.to_jsonb(v_attempt), 'replayed', true);
  end if;
  if p_target_current_change_id is not null then
    select * into v_change from public.v2_current_changes as cc
    where cc.id = p_target_current_change_id and cc.project_id = p_project_id
      and cc.owner_user_id = p_owner_user_id for update;
    if not found then raise exception using errcode = 'P0002', message = 'generation target not found'; end if;
    v_actual_version := v_change.version;
  elsif p_target_recovery_case_id is not null then
    select * into v_recovery from public.v2_recovery_cases as rc
    where rc.id = p_target_recovery_case_id and rc.project_id = p_project_id
      and rc.owner_user_id = p_owner_user_id for update;
    if not found then raise exception using errcode = 'P0002', message = 'generation target not found'; end if;
    v_actual_version := v_recovery.version;
  else
    v_actual_version := v_project.version;
  end if;
  if v_actual_version <> p_target_aggregate_version then
    raise exception using errcode = '40001', message = 'stale generation target';
  end if;
  insert into public.v2_generation_attempts (
    project_id, owner_user_id, target_current_change_id, target_recovery_case_id,
    purpose, target_aggregate_version, policy_version, config_version, status,
    provider_key, model_key, input_sha256, attempt_command_id
  ) values (
    p_project_id, p_owner_user_id, p_target_current_change_id, p_target_recovery_case_id,
    p_purpose, p_target_aggregate_version, p_policy_version, p_config_version, 'pending',
    p_provider_key, p_model_key, p_input_sha256, p_command_id
  ) returning * into v_attempt;
  return pg_catalog.jsonb_build_object(
    'generation_attempt', pg_catalog.to_jsonb(v_attempt), 'replayed', false);
end;
$$;

create function codize_v2_internal.finish_v2_generation_attempt(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_generation_attempt_id uuid,
  p_expected_attempt_version bigint,
  p_status text,
  p_safe_error_category text,
  p_retryable boolean,
  p_result_record_type text,
  p_result_record_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_attempt public.v2_generation_attempts%rowtype;
  v_actual_version bigint;
  v_final_status text;
begin
  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'v2 project not found'; end if;
  select * into v_attempt from public.v2_generation_attempts as ga
  where ga.id = p_generation_attempt_id and ga.project_id = p_project_id
    and ga.owner_user_id = p_owner_user_id for update;
  if not found then raise exception using errcode = 'P0002', message = 'generation attempt not found'; end if;
  if v_attempt.version <> p_expected_attempt_version or v_attempt.status <> 'pending' then
    raise exception using errcode = '40001', message = 'stale generation attempt';
  end if;
  if p_status not in ('succeeded', 'failed')
     or (p_status = 'failed' and (p_safe_error_category is null or p_retryable is null
       or p_result_record_type is not null or p_result_record_id is not null))
     or (p_status = 'succeeded' and (p_safe_error_category is not null or p_retryable is not null
       or p_result_record_type not in ('prompt_version', 'build_turn')
       or p_result_record_id is null)) then
    raise exception using errcode = '23514', message = 'invalid generation completion';
  end if;
  if v_attempt.target_current_change_id is not null then
    select * into v_change from public.v2_current_changes as cc
    where cc.id = v_attempt.target_current_change_id and cc.project_id = p_project_id
      and cc.owner_user_id = p_owner_user_id;
    v_actual_version := v_change.version;
  elsif v_attempt.target_recovery_case_id is not null then
    select * into v_recovery from public.v2_recovery_cases as rc
    where rc.id = v_attempt.target_recovery_case_id and rc.project_id = p_project_id
      and rc.owner_user_id = p_owner_user_id;
    v_actual_version := v_recovery.version;
  else
    v_actual_version := v_project.version;
  end if;
  v_final_status := case
    when p_status = 'succeeded' and v_actual_version is distinct from v_attempt.target_aggregate_version
      then 'superseded' else p_status end;
  if v_final_status = 'succeeded' and not (
    (p_result_record_type = 'prompt_version' and exists (
      select 1 from public.v2_prompt_versions as pv where pv.id = p_result_record_id
        and pv.project_id = p_project_id and pv.owner_user_id = p_owner_user_id
        and pv.current_change_id is not distinct from v_attempt.target_current_change_id))
    or (p_result_record_type = 'build_turn' and exists (
      select 1 from public.v2_build_turns as bt where bt.id = p_result_record_id
        and bt.project_id = p_project_id and bt.owner_user_id = p_owner_user_id))
  ) then
    raise exception using errcode = '23514', message = 'generation result record is not accepted durable output';
  end if;
  update public.v2_generation_attempts as ga
  set status = v_final_status,
      safe_error_category = case when v_final_status = 'failed' then p_safe_error_category end,
      retryable = case when v_final_status = 'failed' then p_retryable end,
      result_record_type = case when v_final_status = 'succeeded' then p_result_record_type end,
      result_record_id = case when v_final_status = 'succeeded' then p_result_record_id end,
      version = ga.version + 1
  where ga.id = v_attempt.id returning * into v_attempt;
  return pg_catalog.jsonb_build_object('generation_attempt', pg_catalog.to_jsonb(v_attempt));
end;
$$;

create function codize_v2_internal.apply_v2_generated_prompt_draft(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_generation_attempt_id uuid,
  p_expected_attempt_version bigint,
  p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint,
  p_prompt_draft text,
  p_done_condition_snapshot text,
  p_boundary_snapshots text[]
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_attempt public.v2_generation_attempts%rowtype;
  v_change public.v2_current_changes%rowtype;
begin
  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_attempt from public.v2_generation_attempts as ga
  where ga.id = p_generation_attempt_id and ga.project_id = p_project_id
    and ga.owner_user_id = p_owner_user_id for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'generation attempt not found';
  end if;
  if v_attempt.purpose <> 'prompt_draft'
     or v_attempt.target_current_change_id is null
     or v_attempt.target_recovery_case_id is not null then
    raise exception using errcode = '23514',
      message = 'generation attempt does not target a prompt draft';
  end if;

  select * into v_change from public.v2_current_changes as cc
  where cc.id = v_attempt.target_current_change_id
    and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'generation target not found';
  end if;

  if v_attempt.status = 'succeeded' then
    if v_attempt.result_record_type <> 'prompt_draft'
       or v_attempt.result_record_id <> v_change.id then
      raise exception using errcode = '23514',
        message = 'generation completion does not match its prompt target';
    end if;
    return pg_catalog.jsonb_build_object(
      'generation_attempt', pg_catalog.to_jsonb(v_attempt),
      'current_change', pg_catalog.to_jsonb(v_change),
      'applied', true, 'replayed', true);
  elsif v_attempt.status = 'superseded' then
    return pg_catalog.jsonb_build_object(
      'generation_attempt', pg_catalog.to_jsonb(v_attempt),
      'current_change', pg_catalog.to_jsonb(v_change),
      'applied', false, 'replayed', true);
  elsif v_attempt.status <> 'pending' then
    raise exception using errcode = '40001', message = 'generation attempt is already terminal';
  end if;

  if v_attempt.version <> p_expected_attempt_version then
    raise exception using errcode = '40001', message = 'stale generation attempt';
  end if;
  if v_change.version <> v_attempt.target_aggregate_version then
    update public.v2_generation_attempts as ga
    set status = 'superseded',
        safe_error_category = null,
        retryable = null,
        result_record_type = null,
        result_record_id = null,
        version = ga.version + 1
    where ga.id = v_attempt.id
    returning * into v_attempt;
    return pg_catalog.jsonb_build_object(
      'generation_attempt', pg_catalog.to_jsonb(v_attempt),
      'current_change', pg_catalog.to_jsonb(v_change),
      'applied', false, 'replayed', false);
  end if;
  if v_change.version <> p_expected_current_change_version
     or v_change.prompt_draft_version <> p_expected_prompt_draft_version then
    raise exception using errcode = '40001', message = 'stale prompt application command';
  end if;
  if v_change.lifecycle_state <> 'preparing'
     or v_change.handoff_command_id is not null
     or v_change.coding_agent_key is null
     or v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514',
      message = 'generated prompt cannot be applied in this state';
  end if;
  if p_prompt_draft is null or pg_catalog.btrim(p_prompt_draft) = ''
     or pg_catalog.octet_length(p_prompt_draft) > 65536
     or (p_done_condition_snapshot is not null and (
       pg_catalog.btrim(p_done_condition_snapshot) = ''
       or pg_catalog.octet_length(p_done_condition_snapshot) > 8192))
     or not public.v2_valid_text_array(p_boundary_snapshots, 32, 8192, 256, true) then
    raise exception using errcode = '23514', message = 'invalid bounded generated prompt';
  end if;
  if v_change.prompt_draft is not distinct from p_prompt_draft
     and v_change.done_condition_snapshot is not distinct from p_done_condition_snapshot
     and v_change.boundary_snapshots is not distinct from p_boundary_snapshots then
    raise exception using errcode = '23514',
      message = 'generated prompt application must change the durable draft';
  end if;

  update public.v2_current_changes as cc
  set prompt_draft = p_prompt_draft,
      prompt_draft_version = cc.prompt_draft_version
        + case when cc.prompt_draft is distinct from p_prompt_draft then 1 else 0 end,
      done_condition_snapshot = p_done_condition_snapshot,
      boundary_snapshots = p_boundary_snapshots,
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  update public.v2_generation_attempts as ga
  set status = 'succeeded',
      safe_error_category = null,
      retryable = null,
      result_record_type = 'prompt_draft',
      result_record_id = v_change.id,
      version = ga.version + 1
  where ga.id = v_attempt.id
  returning * into v_attempt;

  return pg_catalog.jsonb_build_object(
    'generation_attempt', pg_catalog.to_jsonb(v_attempt),
    'current_change', pg_catalog.to_jsonb(v_change),
    'applied', true, 'replayed', false);
end;
$$;

create function public.update_v2_coding_agent(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_project_version bigint, p_expected_current_change_version bigint,
  p_coding_agent_key text)
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.update_v2_coding_agent($1,$2,$3,$4,$5,$6); $$;
create function public.update_v2_prompt_draft(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_expected_prompt_draft_version bigint,
  p_prompt_draft text, p_done_condition_snapshot text, p_boundary_snapshots text[])
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.update_v2_prompt_draft($1,$2,$3,$4,$5,$6,$7,$8); $$;
create function public.update_v2_effort(
  p_owner_user_id uuid, p_project_id uuid, p_current_change_id uuid,
  p_expected_current_change_version bigint, p_effort_category text)
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.update_v2_effort($1,$2,$3,$4,$5); $$;
create function public.start_v2_generation_attempt(
  p_owner_user_id uuid, p_project_id uuid, p_command_id uuid,
  p_target_current_change_id uuid, p_target_recovery_case_id uuid,
  p_purpose text, p_target_aggregate_version bigint, p_policy_version text,
  p_config_version text, p_provider_key text, p_model_key text, p_input_sha256 text)
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.start_v2_generation_attempt($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12); $$;
create function public.finish_v2_generation_attempt(
  p_owner_user_id uuid, p_project_id uuid, p_generation_attempt_id uuid,
  p_expected_attempt_version bigint, p_status text, p_safe_error_category text,
  p_retryable boolean, p_result_record_type text, p_result_record_id uuid)
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.finish_v2_generation_attempt($1,$2,$3,$4,$5,$6,$7,$8,$9); $$;
create function public.apply_v2_generated_prompt_draft(
  p_owner_user_id uuid, p_project_id uuid, p_generation_attempt_id uuid,
  p_expected_attempt_version bigint, p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint, p_prompt_draft text,
  p_done_condition_snapshot text, p_boundary_snapshots text[])
returns jsonb language sql security invoker set search_path = ''
as $$ select codize_v2_internal.apply_v2_generated_prompt_draft($1,$2,$3,$4,$5,$6,$7,$8,$9); $$;

alter function codize_v2_internal.update_v2_coding_agent(uuid, uuid, uuid, bigint, bigint, text) owner to codize_v2_executor;
alter function codize_v2_internal.update_v2_prompt_draft(uuid, uuid, uuid, bigint, bigint, text, text, text[]) owner to codize_v2_executor;
alter function codize_v2_internal.update_v2_effort(uuid, uuid, uuid, bigint, text) owner to codize_v2_executor;
alter function codize_v2_internal.start_v2_generation_attempt(uuid, uuid, uuid, uuid, uuid, text, bigint, text, text, text, text, text) owner to codize_v2_executor;
alter function codize_v2_internal.finish_v2_generation_attempt(uuid, uuid, uuid, bigint, text, text, boolean, text, uuid) owner to codize_v2_executor;
alter function codize_v2_internal.apply_v2_generated_prompt_draft(uuid, uuid, uuid, bigint, bigint, bigint, text, text, text[]) owner to codize_v2_executor;

revoke execute on function
  public.v2_guard_feature_prompt_snapshot(),
  public.update_v2_coding_agent(uuid, uuid, uuid, bigint, bigint, text),
  public.update_v2_prompt_draft(uuid, uuid, uuid, bigint, bigint, text, text, text[]),
  public.update_v2_effort(uuid, uuid, uuid, bigint, text),
  public.start_v2_generation_attempt(uuid, uuid, uuid, uuid, uuid, text, bigint, text, text, text, text, text),
  public.finish_v2_generation_attempt(uuid, uuid, uuid, bigint, text, text, boolean, text, uuid),
  public.apply_v2_generated_prompt_draft(uuid, uuid, uuid, bigint, bigint, bigint, text, text, text[])
from public, anon, authenticated, service_role;
revoke execute on function
  codize_v2_internal.update_v2_coding_agent(uuid, uuid, uuid, bigint, bigint, text),
  codize_v2_internal.update_v2_prompt_draft(uuid, uuid, uuid, bigint, bigint, text, text, text[]),
  codize_v2_internal.update_v2_effort(uuid, uuid, uuid, bigint, text),
  codize_v2_internal.start_v2_generation_attempt(uuid, uuid, uuid, uuid, uuid, text, bigint, text, text, text, text, text),
  codize_v2_internal.finish_v2_generation_attempt(uuid, uuid, uuid, bigint, text, text, boolean, text, uuid),
  codize_v2_internal.apply_v2_generated_prompt_draft(uuid, uuid, uuid, bigint, bigint, bigint, text, text, text[])
from public, anon, authenticated, service_role;

grant execute on function public.v2_valid_coding_agent_key(text) to codize_v2_executor;
grant execute on function
  codize_v2_internal.update_v2_coding_agent(uuid, uuid, uuid, bigint, bigint, text),
  codize_v2_internal.update_v2_prompt_draft(uuid, uuid, uuid, bigint, bigint, text, text, text[]),
  codize_v2_internal.update_v2_effort(uuid, uuid, uuid, bigint, text),
  codize_v2_internal.start_v2_generation_attempt(uuid, uuid, uuid, uuid, uuid, text, bigint, text, text, text, text, text),
  codize_v2_internal.finish_v2_generation_attempt(uuid, uuid, uuid, bigint, text, text, boolean, text, uuid),
  codize_v2_internal.apply_v2_generated_prompt_draft(uuid, uuid, uuid, bigint, bigint, bigint, text, text, text[])
to service_role;
grant execute on function
  public.update_v2_coding_agent(uuid, uuid, uuid, bigint, bigint, text),
  public.update_v2_prompt_draft(uuid, uuid, uuid, bigint, bigint, text, text, text[]),
  public.update_v2_effort(uuid, uuid, uuid, bigint, text),
  public.start_v2_generation_attempt(uuid, uuid, uuid, uuid, uuid, text, bigint, text, text, text, text, text),
  public.finish_v2_generation_attempt(uuid, uuid, uuid, bigint, text, text, boolean, text, uuid),
  public.apply_v2_generated_prompt_draft(uuid, uuid, uuid, bigint, bigint, bigint, text, text, text[])
to service_role;

revoke create on schema codize_v2_internal from codize_v2_executor;
revoke codize_v2_executor from current_user;
