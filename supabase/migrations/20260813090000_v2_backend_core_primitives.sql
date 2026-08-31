-- Codize V2.3A: backend application command primitives and fail-closed
-- unresolved-policy enforcement.
--
-- This migration preserves the eleven-table V2 entity cut and every V1
-- object. Two operation-local command IDs are added to existing aggregates so
-- policy resolution and temporary-Project promotion have exact retry
-- provenance rather than inferring replay from ordinary domain state.

alter table public.v2_projects
  add column promotion_command_id uuid;

create unique index v2_projects_promotion_command_key
  on public.v2_projects (owner_user_id, promotion_command_id)
  where promotion_command_id is not null;

create function public.v2_guard_promotion_provenance()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.promotion_command_id is not null then
      raise exception using errcode = '23514',
        message = 'V2 promotion provenance is written only by promotion';
    end if;
    return new;
  end if;
  if old.promotion_command_id is not null
     and new.promotion_command_id is distinct from old.promotion_command_id then
    raise exception using errcode = '23514',
      message = 'V2 promotion provenance is immutable';
  end if;
  if old.promotion_command_id is null
     and new.promotion_command_id is not null
     and not (
       old.lifecycle_state = 'temporary_recovery'
       and new.lifecycle_state = 'active'
       and new.setup_resume_step = 'existing_project_context'
     ) then
    raise exception using errcode = '23514',
      message = 'V2 promotion provenance requires the canonical transition';
  end if;
  return new;
end;
$$;

create trigger v2_05_projects_promotion_provenance
  before insert or update on public.v2_projects
  for each row execute function public.v2_guard_promotion_provenance();

revoke execute on function public.v2_guard_promotion_provenance()
  from public, anon, authenticated, service_role;

alter table public.v2_current_changes
  add column policy_resolution_command_id uuid;

create unique index v2_current_changes_policy_resolution_command_key
  on public.v2_current_changes (owner_user_id, policy_resolution_command_id)
  where policy_resolution_command_id is not null;

alter table public.v2_current_changes
  add constraint v2_current_changes_unresolved_policy_state_check
  check (
    (
      teaching_policy_version <> 'unresolved-v0'
      and risk_policy_version <> 'unresolved-v0'
    )
    or lifecycle_state = 'cancelled'
    or (
      lifecycle_state = 'preparing'
      and resume_step = 'confirm_change'
      and done_condition_snapshot is null
      and pg_catalog.cardinality(boundary_snapshots) = 0
      and prompt_draft is null
      and coding_agent_key is null
      and effort_category is null
      and latest_prompt_version_id is null
      and handoff_command_id is null
      and completion_command_id is null
      and student_return_outcome is null
      and accepted_outcome_summary is null
      and unresolved_uncertainty_summary is null
    )
  );

create function public.v2_guard_policy_resolution()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_policy_changed boolean;
begin
  if tg_op = 'INSERT' then
    if new.policy_resolution_command_id is not null then
      raise exception using errcode = '23514',
        message = 'V2 policy provenance is written only by the resolution command';
    end if;
    return new;
  end if;

  v_policy_changed := row(
    new.teaching_mode,
    new.teaching_target,
    new.teaching_reason_key,
    new.teaching_policy_version,
    new.risk,
    new.risk_reason_key,
    new.risk_policy_version,
    new.check_requirement,
    new.check_waiver_reason_key
  ) is distinct from row(
    old.teaching_mode,
    old.teaching_target,
    old.teaching_reason_key,
    old.teaching_policy_version,
    old.risk,
    old.risk_reason_key,
    old.risk_policy_version,
    old.check_requirement,
    old.check_waiver_reason_key
  );

  if old.policy_resolution_command_id is not null
     and new.policy_resolution_command_id is distinct from old.policy_resolution_command_id then
    raise exception using errcode = '23514',
      message = 'V2 policy resolution provenance is immutable';
  end if;

  if old.teaching_policy_version <> 'unresolved-v0'
     and old.risk_policy_version <> 'unresolved-v0'
     and v_policy_changed then
    raise exception using errcode = '23514',
      message = 'resolved V2 policy fields are immutable for a Current Change';
  end if;

  if old.teaching_policy_version = 'unresolved-v0'
     or old.risk_policy_version = 'unresolved-v0' then
    if new.teaching_policy_version = 'unresolved-v0'
       or new.risk_policy_version = 'unresolved-v0' then
      if v_policy_changed
         or new.policy_resolution_command_id is distinct from old.policy_resolution_command_id then
        raise exception using errcode = '23514',
          message = 'unresolved V2 policy fields cannot be partially rewritten';
      end if;
    elsif not v_policy_changed
       or old.policy_resolution_command_id is not null
       or new.policy_resolution_command_id is null then
      raise exception using errcode = '23514',
        message = 'V2 policy resolution requires one atomic controlled replacement';
    end if;
  end if;

  return new;
end;
$$;

create trigger v2_05_current_changes_policy_resolution
  before insert or update on public.v2_current_changes
  for each row execute function public.v2_guard_policy_resolution();

create function public.v2_reject_prompt_while_policy_unresolved()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if exists (
    select 1
    from public.v2_current_changes as cc
    where cc.id = new.current_change_id
      and cc.project_id = new.project_id
      and cc.owner_user_id = new.owner_user_id
      and (
        cc.teaching_policy_version = 'unresolved-v0'
        or cc.risk_policy_version = 'unresolved-v0'
      )
  ) then
    raise exception using errcode = '23514',
      message = 'V2 prompt acceptance and handoff require resolved policy';
  end if;
  return new;
end;
$$;

create trigger v2_05_prompt_policy_on_accept
  before insert on public.v2_prompt_versions
  for each row execute function public.v2_reject_prompt_while_policy_unresolved();

create trigger v2_05_prompt_policy_on_handoff
  before update of handoff_command_id, handed_off_at on public.v2_prompt_versions
  for each row execute function public.v2_reject_prompt_while_policy_unresolved();

revoke execute on function
  public.v2_guard_policy_resolution(),
  public.v2_reject_prompt_while_policy_unresolved()
from public, anon, authenticated, service_role;

grant codize_v2_executor to current_user with set true;
grant create on schema codize_v2_internal to codize_v2_executor;

create function codize_v2_internal.create_v2_project(
  p_owner_user_id uuid,
  p_create_command_id uuid,
  p_display_name text,
  p_creation_intent text,
  p_recovery_context jsonb,
  p_current_change_command_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
  v_lifecycle_state text;
  v_setup_resume_step text;
  v_setup_draft jsonb;
begin
  if p_owner_user_id is null or p_create_command_id is null
     or p_display_name is null or pg_catalog.btrim(p_display_name) = ''
     or pg_catalog.octet_length(p_display_name) > 120
     or p_creation_intent not in ('new_idea', 'already_building', 'recovery_first') then
    raise exception using errcode = '22023', message = 'invalid V2 Project creation command';
  end if;

  if p_creation_intent = 'new_idea' then
    v_lifecycle_state := 'draft';
    v_setup_resume_step := 'idea_capture';
  elsif p_creation_intent = 'already_building' then
    v_lifecycle_state := 'draft';
    v_setup_resume_step := 'existing_project_context';
  else
    v_lifecycle_state := 'temporary_recovery';
    v_setup_resume_step := 'recovery_context';
  end if;

  if p_creation_intent <> 'recovery_first' then
    if p_recovery_context is not null or p_current_change_command_id is not null then
      raise exception using errcode = '22023',
        message = 'Recovery context is legal only for Recovery-first creation';
    end if;
  elsif p_current_change_command_id is null
     or p_recovery_context is null
     or pg_catalog.jsonb_typeof(p_recovery_context) <> 'object'
     or p_recovery_context - array[
       'project_context', 'intended_behavior', 'observed_symptom',
       'last_known_working_statement', 'last_known_working_certainty',
       'candidate_change_summary'
     ] <> '{}'::jsonb
     or not (p_recovery_context ?& array[
       'project_context', 'intended_behavior', 'observed_symptom',
       'last_known_working_certainty', 'candidate_change_summary'
     ])
     or pg_catalog.btrim(p_recovery_context ->> 'project_context') = ''
     or pg_catalog.octet_length(p_recovery_context ->> 'project_context') > 16384
     or pg_catalog.btrim(p_recovery_context ->> 'intended_behavior') = ''
     or pg_catalog.octet_length(p_recovery_context ->> 'intended_behavior') > 16384
     or pg_catalog.btrim(p_recovery_context ->> 'observed_symptom') = ''
     or pg_catalog.octet_length(p_recovery_context ->> 'observed_symptom') > 16384
     or p_recovery_context ->> 'last_known_working_certainty' not in ('yes', 'no', 'unsure')
     or (
       p_recovery_context ? 'last_known_working_statement'
       and p_recovery_context ->> 'last_known_working_statement' is not null
       and (
         pg_catalog.btrim(p_recovery_context ->> 'last_known_working_statement') = ''
         or pg_catalog.octet_length(p_recovery_context ->> 'last_known_working_statement') > 16384
       )
     )
     or pg_catalog.btrim(p_recovery_context ->> 'candidate_change_summary') = ''
     or pg_catalog.octet_length(p_recovery_context ->> 'candidate_change_summary') > 8192
     or pg_catalog.octet_length(p_recovery_context::text) > 16384 then
    raise exception using errcode = '22023',
      message = 'Recovery-first creation requires bounded canonical Recovery context';
  else
    v_setup_draft := pg_catalog.jsonb_strip_nulls(pg_catalog.jsonb_build_object(
      'project_context', pg_catalog.btrim(p_recovery_context ->> 'project_context'),
      'intended_behavior', pg_catalog.btrim(p_recovery_context ->> 'intended_behavior'),
      'observed_symptom', pg_catalog.btrim(p_recovery_context ->> 'observed_symptom'),
      'last_known_working_statement', p_recovery_context ->> 'last_known_working_statement',
      'last_known_working_certainty', p_recovery_context ->> 'last_known_working_certainty',
      'candidate_change_summary', pg_catalog.btrim(p_recovery_context ->> 'candidate_change_summary')
    ));
  end if;

  insert into public.v2_projects (
    owner_user_id, display_name, lifecycle_state, setup_resume_step,
    setup_draft, create_command_id
  ) values (
    p_owner_user_id, pg_catalog.btrim(p_display_name), v_lifecycle_state,
    v_setup_resume_step, v_setup_draft, p_create_command_id
  )
  on conflict (owner_user_id, create_command_id) do nothing
  returning * into v_project;

  if not found then
    select * into v_project
    from public.v2_projects as p
    where p.owner_user_id = p_owner_user_id
      and p.create_command_id = p_create_command_id
    for update;
    if not found then
      raise exception using errcode = '23505', message = 'V2 Project command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'project', pg_catalog.to_jsonb(v_project), 'replayed', true
    );
  end if;

  if p_creation_intent = 'recovery_first' then
    insert into public.v2_current_changes (
      project_id, owner_user_id, change_kind, lifecycle_state, resume_step,
      goal_snapshot, teaching_mode, teaching_reason_key,
      teaching_policy_version, risk, risk_policy_version, check_requirement,
      create_command_id
    ) values (
      v_project.id, p_owner_user_id, 'recovery', 'preparing', 'confirm_change',
      pg_catalog.btrim(p_recovery_context ->> 'intended_behavior'),
      'skip', 'policy_not_evaluated', 'unresolved-v0',
      'normal', 'unresolved-v0', 'required', p_current_change_command_id
    ) returning * into v_change;
  end if;

  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project), 'replayed', false
  );
end;
$$;

create function codize_v2_internal.resolve_v2_current_change_policy(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_teaching_mode text,
  p_teaching_target text,
  p_teaching_reason_key text,
  p_teaching_policy_version text,
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_check_requirement text,
  p_check_waiver_reason_key text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null or p_command_id is null
     or p_teaching_mode not in ('skip', 'ask', 'remind', 'teach')
     or p_teaching_reason_key is null or pg_catalog.btrim(p_teaching_reason_key) = ''
     or p_teaching_policy_version is null
     or pg_catalog.btrim(p_teaching_policy_version) in ('', 'unresolved-v0')
     or p_risk not in ('normal', 'slowdown')
     or p_risk_policy_version is null
     or pg_catalog.btrim(p_risk_policy_version) in ('', 'unresolved-v0')
     or p_check_requirement not in ('required', 'waived') then
    raise exception using errcode = '22023', message = 'invalid V2 policy resolution command';
  end if;

  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id
    and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  if v_change.policy_resolution_command_id = p_command_id then
    return pg_catalog.jsonb_build_object(
      'current_change', pg_catalog.to_jsonb(v_change), 'replayed', true
    );
  end if;
  if v_change.policy_resolution_command_id is not null
     or (
       v_change.teaching_policy_version <> 'unresolved-v0'
       and v_change.risk_policy_version <> 'unresolved-v0'
     ) then
    raise exception using errcode = '23514', message = 'V2 Current Change policy is already resolved';
  end if;
  if v_change.version <> p_expected_current_change_version then
    raise exception using errcode = '40001', message = 'stale V2 Current Change version';
  end if;
  if v_change.lifecycle_state <> 'preparing' or v_change.resume_step <> 'confirm_change' then
    raise exception using errcode = '23514', message = 'V2 policy resolves only at initial preparation';
  end if;

  update public.v2_current_changes as cc
  set teaching_mode = p_teaching_mode,
      teaching_target = p_teaching_target,
      teaching_reason_key = pg_catalog.btrim(p_teaching_reason_key),
      teaching_policy_version = pg_catalog.btrim(p_teaching_policy_version),
      risk = p_risk,
      risk_reason_key = p_risk_reason_key,
      risk_policy_version = pg_catalog.btrim(p_risk_policy_version),
      check_requirement = p_check_requirement,
      check_waiver_reason_key = p_check_waiver_reason_key,
      policy_resolution_command_id = p_command_id,
      version = cc.version + 1
  where cc.id = v_change.id
    and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  returning * into v_change;

  return pg_catalog.jsonb_build_object(
    'current_change', pg_catalog.to_jsonb(v_change), 'replayed', false
  );
end;
$$;

create function codize_v2_internal.promote_v2_temporary_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_command_id is null then
    raise exception using errcode = '22023', message = 'invalid V2 Project promotion command';
  end if;

  select * into v_project
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  if v_project.promotion_command_id = p_command_id then
    return pg_catalog.jsonb_build_object(
      'project', pg_catalog.to_jsonb(v_project), 'replayed', true
    );
  end if;
  if v_project.lifecycle_state <> 'temporary_recovery' then
    raise exception using errcode = '23514',
      message = 'only a temporary Recovery Project can be promoted';
  end if;
  if v_project.version <> p_expected_project_version then
    raise exception using errcode = '40001', message = 'stale V2 Project version';
  end if;

  if not exists (
    select 1 from public.v2_current_changes as cc
    where cc.project_id = v_project.id
      and cc.owner_user_id = p_owner_user_id
      and cc.change_kind = 'recovery'
  ) or not exists (
    select 1
    from public.v2_recovery_cases as rc
    join public.v2_current_changes as cc
      on cc.id = rc.current_change_id
     and cc.project_id = rc.project_id
     and cc.owner_user_id = rc.owner_user_id
    where rc.project_id = v_project.id
      and rc.owner_user_id = p_owner_user_id
      and rc.status = 'resolved'
      and rc.resolved_at is not null
      and rc.resolution_summary is not null
      and cc.change_kind = 'recovery'
      and cc.lifecycle_state = 'completed'
      and cc.completed_at is not null
  ) or exists (
    select 1 from public.v2_current_changes as cc
    where cc.project_id = v_project.id
      and cc.owner_user_id = p_owner_user_id
      and cc.change_kind = 'recovery'
      and cc.lifecycle_state <> 'completed'
  ) or exists (
    select 1 from public.v2_recovery_cases as rc
    where rc.project_id = v_project.id
      and rc.owner_user_id = p_owner_user_id
      and rc.status <> 'resolved'
  ) or exists (
    select 1 from public.v2_current_changes as cc
    where cc.project_id = v_project.id
      and cc.owner_user_id = p_owner_user_id
      and cc.change_kind = 'recovery'
      and not exists (
        select 1 from public.v2_recovery_cases as rc
        where rc.current_change_id = cc.id
          and rc.project_id = cc.project_id
          and rc.owner_user_id = cc.owner_user_id
          and rc.status = 'resolved'
      )
  ) then
    raise exception using errcode = '23514',
      message = 'temporary Project promotion requires only completed, resolved Recovery flows';
  end if;

  update public.v2_projects as p
  set lifecycle_state = 'active',
      setup_resume_step = 'existing_project_context',
      setup_draft = null,
      promotion_command_id = p_command_id,
      version = p.version + 1
  where p.id = v_project.id and p.owner_user_id = p_owner_user_id
  returning * into v_project;

  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project), 'replayed', false
  );
end;
$$;

create function codize_v2_internal.start_v2_current_change(
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
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_create_command_id is null
     or p_change_kind not in ('build', 'recovery')
     or p_goal_snapshot is null or pg_catalog.btrim(p_goal_snapshot) = ''
     or pg_catalog.octet_length(p_goal_snapshot) > 4096 then
    raise exception using errcode = '22023', message = 'invalid V2 Current Change start command';
  end if;

  select * into v_project
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.owner_user_id = p_owner_user_id
    and cc.create_command_id = p_create_command_id
  for update;
  if found then
    if v_change.project_id <> p_project_id
       or v_change.change_kind <> p_change_kind
       or v_change.goal_snapshot <> pg_catalog.btrim(p_goal_snapshot) then
      raise exception using errcode = '23505', message = 'V2 Current Change command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'current_change', pg_catalog.to_jsonb(v_change), 'replayed', true
    );
  end if;

  if v_project.version <> p_expected_project_version then
    raise exception using errcode = '40001', message = 'stale V2 Project version';
  end if;
  if v_project.lifecycle_state not in ('active', 'temporary_recovery') then
    raise exception using errcode = '23514', message = 'V2 Project cannot start a Current Change';
  end if;
  if v_project.lifecycle_state = 'temporary_recovery' and p_change_kind <> 'recovery' then
    raise exception using errcode = '23514', message = 'temporary Project requires a Recovery Current Change';
  end if;

  if p_plan_item_id is not null then
    select * into v_plan_item
    from public.v2_plan_items as pi
    where pi.id = p_plan_item_id
      and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id
    for update;
    if not found then
      raise exception using errcode = 'P0002', message = 'v2 plan item not found';
    end if;
    if v_plan_item.status in ('done', 'removed') then
      raise exception using errcode = '23514', message = 'terminal V2 Plan Item cannot start a Current Change';
    end if;
  end if;

  if exists (
    select 1 from public.v2_current_changes as cc
    where cc.project_id = p_project_id
      and cc.owner_user_id = p_owner_user_id
      and cc.lifecycle_state in ('preparing', 'awaiting_agent', 'reviewing', 'recovering')
  ) then
    raise exception using errcode = '23505', message = 'V2 Project already has a nonterminal Current Change';
  end if;

  insert into public.v2_current_changes (
    project_id, owner_user_id, plan_item_id, change_kind, lifecycle_state,
    resume_step, goal_snapshot, teaching_mode, teaching_reason_key,
    teaching_policy_version, risk, risk_policy_version, check_requirement,
    create_command_id
  ) values (
    p_project_id, p_owner_user_id, p_plan_item_id, p_change_kind, 'preparing',
    'confirm_change', pg_catalog.btrim(p_goal_snapshot),
    'skip', 'policy_not_evaluated', 'unresolved-v0',
    'normal', 'unresolved-v0', 'required', p_create_command_id
  ) returning * into v_change;

  return pg_catalog.jsonb_build_object(
    'current_change', pg_catalog.to_jsonb(v_change), 'replayed', false
  );
end;
$$;

create function codize_v2_internal.cancel_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_cancellation_command_id uuid,
  p_cancellation_reason_key text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_current_change_id is null
     or p_expected_current_change_version is null
     or p_cancellation_command_id is null
     or p_cancellation_reason_key is null
     or pg_catalog.btrim(p_cancellation_reason_key) = ''
     or pg_catalog.octet_length(p_cancellation_reason_key) > 256 then
    raise exception using errcode = '22023', message = 'invalid V2 Current Change cancellation command';
  end if;

  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id
    and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  if v_change.lifecycle_state = 'cancelled'
     and v_change.cancellation_command_id = p_cancellation_command_id then
    return pg_catalog.jsonb_build_object(
      'current_change', pg_catalog.to_jsonb(v_change), 'replayed', true
    );
  end if;
  if v_change.lifecycle_state in ('completed', 'cancelled') then
    raise exception using errcode = '23514', message = 'terminal V2 Current Change cannot be cancelled';
  end if;
  if v_change.version <> p_expected_current_change_version then
    raise exception using errcode = '40001', message = 'stale V2 Current Change version';
  end if;

  update public.v2_current_changes as cc
  set lifecycle_state = 'cancelled', resume_step = null,
      cancellation_command_id = p_cancellation_command_id,
      cancellation_reason_key = pg_catalog.btrim(p_cancellation_reason_key),
      cancelled_at = pg_catalog.now(), version = cc.version + 1
  where cc.id = v_change.id
    and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  returning * into v_change;

  return pg_catalog.jsonb_build_object(
    'current_change', pg_catalog.to_jsonb(v_change), 'replayed', false
  );
end;
$$;

alter function codize_v2_internal.create_v2_project(uuid, uuid, text, text, jsonb, uuid)
  owner to codize_v2_executor;
alter function codize_v2_internal.resolve_v2_current_change_policy(
  uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
) owner to codize_v2_executor;
alter function codize_v2_internal.promote_v2_temporary_project(uuid, uuid, bigint, uuid)
  owner to codize_v2_executor;
alter function codize_v2_internal.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text)
  owner to codize_v2_executor;
alter function codize_v2_internal.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text)
  owner to codize_v2_executor;

create function public.create_v2_project(
  p_owner_user_id uuid,
  p_create_command_id uuid,
  p_display_name text,
  p_creation_intent text,
  p_recovery_context jsonb,
  p_current_change_command_id uuid
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.create_v2_project(
    p_owner_user_id, p_create_command_id, p_display_name, p_creation_intent,
    p_recovery_context, p_current_change_command_id
  );
$wrapper$;

create function public.resolve_v2_current_change_policy(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_teaching_mode text,
  p_teaching_target text,
  p_teaching_reason_key text,
  p_teaching_policy_version text,
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_check_requirement text,
  p_check_waiver_reason_key text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.resolve_v2_current_change_policy(
    p_owner_user_id, p_project_id, p_current_change_id,
    p_expected_current_change_version, p_command_id,
    p_teaching_mode, p_teaching_target, p_teaching_reason_key,
    p_teaching_policy_version, p_risk, p_risk_reason_key,
    p_risk_policy_version, p_check_requirement, p_check_waiver_reason_key
  );
$wrapper$;

create function public.promote_v2_temporary_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.promote_v2_temporary_project(
    p_owner_user_id, p_project_id, p_expected_project_version, p_command_id
  );
$wrapper$;

create function public.start_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_create_command_id uuid,
  p_plan_item_id uuid,
  p_change_kind text,
  p_goal_snapshot text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.start_v2_current_change(
    p_owner_user_id, p_project_id, p_expected_project_version,
    p_create_command_id, p_plan_item_id, p_change_kind, p_goal_snapshot
  );
$wrapper$;

create function public.cancel_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_cancellation_command_id uuid,
  p_cancellation_reason_key text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.cancel_v2_current_change(
    p_owner_user_id, p_project_id, p_current_change_id,
    p_expected_current_change_version, p_cancellation_command_id,
    p_cancellation_reason_key
  );
$wrapper$;

revoke execute on function
  public.create_v2_project(uuid, uuid, text, text, jsonb, uuid),
  public.resolve_v2_current_change_policy(
    uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
  ),
  public.promote_v2_temporary_project(uuid, uuid, bigint, uuid),
  public.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text),
  public.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text)
from public, anon, authenticated;

revoke execute on function
  codize_v2_internal.create_v2_project(uuid, uuid, text, text, jsonb, uuid),
  codize_v2_internal.resolve_v2_current_change_policy(
    uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
  ),
  codize_v2_internal.promote_v2_temporary_project(uuid, uuid, bigint, uuid),
  codize_v2_internal.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text),
  codize_v2_internal.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text)
from public, anon, authenticated, service_role;

grant execute on function
  codize_v2_internal.create_v2_project(uuid, uuid, text, text, jsonb, uuid),
  codize_v2_internal.resolve_v2_current_change_policy(
    uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
  ),
  codize_v2_internal.promote_v2_temporary_project(uuid, uuid, bigint, uuid),
  codize_v2_internal.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text),
  codize_v2_internal.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text)
to service_role;

grant execute on function
  public.create_v2_project(uuid, uuid, text, text, jsonb, uuid),
  public.resolve_v2_current_change_policy(
    uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
  ),
  public.promote_v2_temporary_project(uuid, uuid, bigint, uuid),
  public.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text),
  public.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text)
to service_role;

revoke create on schema codize_v2_internal from codize_v2_executor;
revoke codize_v2_executor from current_user;

comment on function public.create_v2_project(uuid, uuid, text, text, jsonb, uuid) is
  'Backend-only explicit-intent V2 Project creation command; Recovery-first also starts unresolved recovery work.';
comment on function public.resolve_v2_current_change_policy(
  uuid, uuid, uuid, bigint, uuid, text, text, text, text, text, text, text, text, text
) is 'Backend-only atomic replacement of unresolved Current Change policy fields.';
comment on function public.promote_v2_temporary_project(uuid, uuid, bigint, uuid) is
  'Backend-only, provenance-bound promotion after durable resolved Recovery.';
comment on function public.start_v2_current_change(uuid, uuid, bigint, uuid, uuid, text, text) is
  'Backend-only, owner-scoped V2 Current Change start command.';
comment on function public.cancel_v2_current_change(uuid, uuid, uuid, bigint, uuid, text) is
  'Backend-only, owner-scoped V2 Current Change cancellation command.';
