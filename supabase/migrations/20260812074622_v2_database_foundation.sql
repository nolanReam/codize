-- Codize V2.2: additive V2 database foundation.
--
-- V2 is a separate backend-mediated domain. This migration does not alter,
-- read, backfill, or reinterpret any V1 product table.

-- ---------------------------------------------------------------------------
-- Bounded-value helpers used by row-local CHECK constraints.
-- ---------------------------------------------------------------------------
create function public.v2_valid_text_array(
  p_value text[],
  p_max_entries integer,
  p_max_total_bytes integer,
  p_max_element_bytes integer,
  p_allow_empty boolean
)
returns boolean
language plpgsql
immutable
security invoker
set search_path = ''
as $$
declare
  v_item text;
begin
  if p_value is null then
    return false;
  end if;

  if pg_catalog.cardinality(p_value) > p_max_entries
     or (not p_allow_empty and pg_catalog.cardinality(p_value) = 0)
     or pg_catalog.octet_length(pg_catalog.array_to_string(p_value, '')) > p_max_total_bytes then
    return false;
  end if;

  foreach v_item in array p_value loop
    if v_item is null
       or pg_catalog.btrim(v_item) = ''
       or pg_catalog.octet_length(v_item) > p_max_element_bytes then
      return false;
    end if;
  end loop;

  return true;
end;
$$;

revoke execute on function public.v2_valid_text_array(text[], integer, integer, integer, boolean)
  from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- Eleven canonical V2 MVP tables.
-- ---------------------------------------------------------------------------
create table public.v2_projects (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null,
  workflow_version text not null default 'v2',
  display_name varchar(120) not null,
  lifecycle_state varchar(32) not null,
  setup_resume_step varchar(40) not null,
  setup_draft jsonb,
  coding_agent_key varchar(64),
  plan_version bigint not null default 1,
  last_plan_command_id uuid,
  first_version_completed_at timestamptz,
  deletion_requested_at timestamptz,
  purge_after timestamptz,
  create_command_id uuid not null,
  deletion_command_id uuid,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_projects_owner_user_fk
    foreign key (owner_user_id) references auth.users (id) on delete restrict,
  constraint v2_projects_owned_key unique (id, owner_user_id),
  constraint v2_projects_workflow_version_check
    check (workflow_version = 'v2'),
  constraint v2_projects_display_name_check
    check (pg_catalog.btrim(display_name) <> '' and pg_catalog.octet_length(display_name) <= 256),
  constraint v2_projects_lifecycle_state_check
    check (lifecycle_state in ('draft', 'temporary_recovery', 'active', 'archived', 'deletion_pending')),
  constraint v2_projects_setup_resume_step_check
    check (setup_resume_step in (
      'idea_capture', 'first_version_shaping', 'guided_resistance',
      'plan_proposal', 'existing_project_context', 'recovery_context', 'ready'
    )),
  constraint v2_projects_setup_draft_check
    check (
      setup_draft is null
      or (
        pg_catalog.jsonb_typeof(setup_draft) = 'object'
        and pg_catalog.octet_length(setup_draft::text) <= 16384
      )
    ),
  constraint v2_projects_coding_agent_key_check
    check (
      coding_agent_key is null
      or (pg_catalog.btrim(coding_agent_key) <> '' and pg_catalog.octet_length(coding_agent_key) <= 256)
    ),
  constraint v2_projects_versions_check
    check (plan_version > 0 and version > 0),
  constraint v2_projects_deletion_state_check
    check (
      (
        lifecycle_state = 'deletion_pending'
        and deletion_requested_at is not null
        and purge_after is not null
        and deletion_command_id is not null
        and purge_after >= deletion_requested_at
      )
      or (
        lifecycle_state <> 'deletion_pending'
        and deletion_requested_at is null
        and purge_after is null
        and deletion_command_id is null
      )
    ),
  constraint v2_projects_temporary_completion_check
    check (lifecycle_state <> 'temporary_recovery' or first_version_completed_at is null)
);

create unique index v2_projects_create_command_key
  on public.v2_projects (owner_user_id, create_command_id);
create unique index v2_projects_deletion_command_key
  on public.v2_projects (owner_user_id, deletion_command_id)
  where deletion_command_id is not null;
create unique index v2_projects_last_plan_command_key
  on public.v2_projects (owner_user_id, last_plan_command_id)
  where last_plan_command_id is not null;
create index v2_projects_owner_lifecycle_updated_idx
  on public.v2_projects (owner_user_id, lifecycle_state, updated_at desc);

create table public.v2_plan_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  label varchar(200) not null,
  intended_outcome text not null,
  scope_band varchar(24) not null,
  status varchar(16) not null,
  order_key bigint not null,
  completed_at timestamptz,
  terminal_current_change_id uuid,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_plan_items_project_owner_fk
    foreign key (project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id) on delete cascade,
  constraint v2_plan_items_owned_key unique (id, project_id, owner_user_id),
  constraint v2_plan_items_label_check
    check (pg_catalog.btrim(label) <> '' and pg_catalog.octet_length(label) <= 256),
  constraint v2_plan_items_intended_outcome_check
    check (pg_catalog.btrim(intended_outcome) <> '' and pg_catalog.octet_length(intended_outcome) <= 4096),
  constraint v2_plan_items_scope_band_check
    check (scope_band in ('first_version', 'later')),
  constraint v2_plan_items_status_check
    check (status in ('proposed', 'ready', 'deferred', 'done', 'removed')),
  constraint v2_plan_items_order_key_check
    check (
      (status = 'removed' and order_key < 0)
      or (status <> 'removed' and order_key > 0)
    ),
  constraint v2_plan_items_completion_check
    check (
      (status = 'done' and completed_at is not null)
      or (status <> 'done' and completed_at is null and terminal_current_change_id is null)
    ),
  constraint v2_plan_items_version_check check (version > 0)
);

alter table public.v2_plan_items
  add constraint v2_plan_items_order_key
  unique (project_id, scope_band, order_key)
  deferrable initially immediate;
create index v2_plan_items_owner_project_order_idx
  on public.v2_plan_items (owner_user_id, project_id, scope_band, order_key)
  where status <> 'removed';

create table public.v2_current_changes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  plan_item_id uuid,
  change_kind varchar(16) not null,
  lifecycle_state varchar(24) not null,
  resume_step varchar(40),
  goal_snapshot text not null,
  done_condition_snapshot text,
  boundary_snapshots text[] not null default '{}'::text[],
  prompt_draft text,
  prompt_draft_version bigint not null default 1,
  coding_agent_key varchar(64),
  effort_category varchar(16),
  latest_prompt_version_id uuid,
  teaching_mode varchar(16) not null,
  teaching_target varchar(64),
  teaching_reason_key varchar(128) not null,
  teaching_policy_version varchar(64) not null,
  risk varchar(16) not null,
  risk_reason_key varchar(128),
  risk_policy_version varchar(64) not null,
  check_requirement varchar(16) not null default 'required',
  check_waiver_reason_key varchar(128),
  help_context_key varchar(64),
  support_level_disclosed varchar(16) not null default 'none',
  student_return_outcome varchar(16),
  accepted_outcome_summary text,
  unresolved_uncertainty_summary text,
  create_command_id uuid not null,
  handoff_command_id uuid,
  completion_command_id uuid,
  cancellation_command_id uuid,
  completed_at timestamptz,
  cancelled_at timestamptz,
  cancellation_reason_key varchar(128),
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_current_changes_project_owner_fk
    foreign key (project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id) on delete cascade,
  constraint v2_current_changes_plan_item_fk
    foreign key (plan_item_id, project_id, owner_user_id)
    references public.v2_plan_items (id, project_id, owner_user_id)
    on delete set null (plan_item_id),
  constraint v2_current_changes_owned_key unique (id, project_id, owner_user_id),
  constraint v2_current_changes_kind_check check (change_kind in ('build', 'recovery')),
  constraint v2_current_changes_lifecycle_check
    check (lifecycle_state in (
      'preparing', 'awaiting_agent', 'reviewing', 'recovering', 'completed', 'cancelled'
    )),
  constraint v2_current_changes_resume_matrix_check
    check (
      (lifecycle_state = 'preparing' and resume_step in (
        'confirm_change', 'choose_agent', 'intervention', 'prompt', 'effort'
      ))
      or (lifecycle_state = 'awaiting_agent' and resume_step = 'return_outcome')
      or (lifecycle_state = 'reviewing' and resume_step in (
        'return_outcome', 'check', 'inspect', 'understand'
      ))
      or (lifecycle_state = 'recovering' and resume_step in (
        'recovery_symptom', 'recovery_investigate', 'recovery_correct', 'recovery_recheck'
      ))
      or (lifecycle_state in ('completed', 'cancelled') and resume_step is null)
    ),
  constraint v2_current_changes_goal_check
    check (pg_catalog.btrim(goal_snapshot) <> '' and pg_catalog.octet_length(goal_snapshot) <= 4096),
  constraint v2_current_changes_done_condition_check
    check (
      done_condition_snapshot is null
      or (
        pg_catalog.btrim(done_condition_snapshot) <> ''
        and pg_catalog.octet_length(done_condition_snapshot) <= 8192
      )
    ),
  constraint v2_current_changes_boundaries_check
    check (public.v2_valid_text_array(boundary_snapshots, 32, 8192, 256, true)),
  constraint v2_current_changes_prompt_draft_check
    check (
      prompt_draft is null
      or (pg_catalog.btrim(prompt_draft) <> '' and pg_catalog.octet_length(prompt_draft) <= 65536)
    ),
  constraint v2_current_changes_versions_check
    check (prompt_draft_version > 0 and version > 0),
  constraint v2_current_changes_effort_check
    check (effort_category is null or effort_category in ('quick', 'standard', 'deep')),
  constraint v2_current_changes_teaching_check
    check (
      teaching_mode in ('skip', 'ask', 'remind', 'teach')
      and ((teaching_mode = 'skip' and teaching_target is null)
        or (teaching_mode <> 'skip' and teaching_target in (
          'first_version_scoping', 'define_done', 'protect_working_behavior',
          'effort_selection', 'inspect_changes', 'testing', 'debugging',
          'causal_explanation', 'functions', 'state', 'events', 'api', 'database',
          'authentication', 'client_server', 'persistence', 'async_work',
          'validation', 'error_handling', 'data_ownership', 'rendering', 'routing',
          'dependencies', 'version_control'
        )))
      and pg_catalog.btrim(teaching_reason_key) <> ''
      and pg_catalog.octet_length(teaching_reason_key) <= 256
      and pg_catalog.btrim(teaching_policy_version) <> ''
    ),
  constraint v2_current_changes_risk_check
    check (
      risk in ('normal', 'slowdown')
      and ((risk = 'normal' and risk_reason_key is null)
        or (risk = 'slowdown' and risk_reason_key is not null
          and pg_catalog.btrim(risk_reason_key) <> ''
          and pg_catalog.octet_length(risk_reason_key) <= 256))
      and pg_catalog.btrim(risk_policy_version) <> ''
    ),
  constraint v2_current_changes_check_requirement_check
    check (
      (check_requirement = 'required' and check_waiver_reason_key is null)
      or (check_requirement = 'waived' and risk = 'normal'
        and check_waiver_reason_key is not null
        and pg_catalog.btrim(check_waiver_reason_key) <> ''
        and pg_catalog.octet_length(check_waiver_reason_key) <= 256)
    ),
  constraint v2_current_changes_help_check
    check (
      support_level_disclosed in ('none', 'nudge', 'clue', 'teach')
      and (support_level_disclosed = 'none' or help_context_key is not null)
    ),
  constraint v2_current_changes_return_outcome_check
    check (student_return_outcome is null or student_return_outcome in ('worked', 'broken', 'unsure')),
  constraint v2_current_changes_outcome_bounds_check
    check (
      (accepted_outcome_summary is null or (
        pg_catalog.btrim(accepted_outcome_summary) <> ''
        and pg_catalog.octet_length(accepted_outcome_summary) <= 16384
      ))
      and (unresolved_uncertainty_summary is null or (
        pg_catalog.btrim(unresolved_uncertainty_summary) <> ''
        and pg_catalog.octet_length(unresolved_uncertainty_summary) <= 16384
      ))
    ),
  constraint v2_current_changes_terminal_state_check
    check (
      (
        lifecycle_state = 'completed'
        and completed_at is not null
        and completion_command_id is not null
        and cancelled_at is null
        and cancellation_command_id is null
        and cancellation_reason_key is null
      )
      or (
        lifecycle_state = 'cancelled'
        and cancelled_at is not null
        and cancellation_command_id is not null
        and cancellation_reason_key is not null
        and pg_catalog.btrim(cancellation_reason_key) <> ''
        and pg_catalog.octet_length(cancellation_reason_key) <= 256
        and completed_at is null
        and completion_command_id is null
      )
      or (
        lifecycle_state not in ('completed', 'cancelled')
        and completed_at is null
        and completion_command_id is null
        and cancelled_at is null
        and cancellation_command_id is null
        and cancellation_reason_key is null
      )
    )
);

create unique index v2_current_changes_one_nonterminal_per_project_key
  on public.v2_current_changes (project_id)
  where lifecycle_state in ('preparing', 'awaiting_agent', 'reviewing', 'recovering');
create unique index v2_current_changes_create_command_key
  on public.v2_current_changes (owner_user_id, create_command_id);
create unique index v2_current_changes_handoff_command_key
  on public.v2_current_changes (owner_user_id, handoff_command_id)
  where handoff_command_id is not null;
create unique index v2_current_changes_completion_command_key
  on public.v2_current_changes (owner_user_id, completion_command_id)
  where completion_command_id is not null;
create unique index v2_current_changes_cancellation_command_key
  on public.v2_current_changes (owner_user_id, cancellation_command_id)
  where cancellation_command_id is not null;
create index v2_current_changes_owner_project_history_idx
  on public.v2_current_changes (owner_user_id, project_id, created_at desc);
create index v2_current_changes_terminal_history_idx
  on public.v2_current_changes (
    owner_user_id, project_id, (coalesce(completed_at, cancelled_at)) desc
  )
  where lifecycle_state in ('completed', 'cancelled');
create index v2_current_changes_plan_item_idx
  on public.v2_current_changes (plan_item_id) where plan_item_id is not null;

create table public.v2_generation_attempts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  target_current_change_id uuid,
  target_recovery_case_id uuid,
  purpose varchar(40) not null,
  target_aggregate_version bigint not null,
  policy_version varchar(64),
  config_version varchar(64) not null,
  status varchar(16) not null,
  provider_key varchar(64) not null,
  model_key varchar(128) not null,
  input_sha256 char(64) not null,
  safe_error_category varchar(64),
  retryable boolean,
  result_record_type varchar(32),
  result_record_id uuid,
  attempt_command_id uuid not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_generation_attempts_project_owner_fk
    foreign key (project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id) on delete cascade,
  constraint v2_generation_attempts_current_change_fk
    foreign key (target_current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id)
    on delete set null (target_current_change_id),
  constraint v2_generation_attempts_owned_key unique (id, project_id, owner_user_id),
  constraint v2_generation_attempts_purpose_check
    check (purpose in (
      'setup_summary', 'first_version_proposal', 'plan_proposal', 'intervention_copy',
      'prompt_draft', 'recovery_summary', 'diagnostic_prompt', 'correction_prompt',
      'concept_explanation', 'project_answer'
    )),
  constraint v2_generation_attempts_target_check
    check (not (target_current_change_id is not null and target_recovery_case_id is not null)),
  constraint v2_generation_attempts_version_check
    check (target_aggregate_version > 0 and version > 0),
  constraint v2_generation_attempts_status_check
    check (status in ('pending', 'succeeded', 'failed', 'superseded')),
  constraint v2_generation_attempts_key_bounds_check
    check (
      pg_catalog.btrim(provider_key) <> ''
      and pg_catalog.octet_length(provider_key) <= 256
      and pg_catalog.btrim(model_key) <> ''
      and pg_catalog.octet_length(model_key) <= 256
      and (safe_error_category is null or (
        pg_catalog.btrim(safe_error_category) <> ''
        and pg_catalog.octet_length(safe_error_category) <= 256
      ))
    ),
  constraint v2_generation_attempts_hash_check
    check (input_sha256 ~ '^[0-9a-f]{64}$'),
  constraint v2_generation_attempts_result_pair_check
    check ((result_record_type is null) = (result_record_id is null)),
  constraint v2_generation_attempts_state_fields_check
    check (
      (status = 'pending' and completed_at is null and safe_error_category is null
        and retryable is null and result_record_id is null)
      or (status = 'succeeded' and completed_at is not null and safe_error_category is null
        and retryable is null and result_record_id is not null)
      or (status = 'failed' and completed_at is not null and safe_error_category is not null
        and pg_catalog.btrim(safe_error_category) <> '' and retryable is not null
        and result_record_id is null)
      or (status = 'superseded' and completed_at is not null and safe_error_category is null
        and retryable is null and result_record_id is null)
    )
);

create unique index v2_generation_attempts_command_key
  on public.v2_generation_attempts (owner_user_id, attempt_command_id);
create index v2_generation_attempts_owner_project_status_idx
  on public.v2_generation_attempts (owner_user_id, project_id, status, created_at);
create index v2_generation_attempts_current_change_idx
  on public.v2_generation_attempts (target_current_change_id)
  where target_current_change_id is not null;

create table public.v2_prompt_versions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  current_change_id uuid not null,
  ordinal integer not null,
  purpose varchar(16) not null,
  content text not null,
  content_sha256 char(64) not null,
  input_current_change_version bigint not null,
  generation_attempt_id uuid,
  coding_agent_key varchar(64) not null,
  effort_category varchar(16),
  provider_mapping_key varchar(128),
  provider_mapping_version varchar(64),
  acceptance_command_id uuid not null,
  accepted_at timestamptz not null default now(),
  handoff_command_id uuid,
  handed_off_at timestamptz,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_prompt_versions_current_change_fk
    foreign key (current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id) on delete cascade,
  constraint v2_prompt_versions_generation_attempt_fk
    foreign key (generation_attempt_id, project_id, owner_user_id)
    references public.v2_generation_attempts (id, project_id, owner_user_id)
    on delete set null (generation_attempt_id),
  constraint v2_prompt_versions_owned_key
    unique (id, current_change_id, project_id, owner_user_id),
  constraint v2_prompt_versions_ordinal_check check (ordinal > 0),
  constraint v2_prompt_versions_purpose_check
    check (purpose in ('feature', 'diagnostic', 'correction')),
  constraint v2_prompt_versions_content_check
    check (pg_catalog.btrim(content) <> '' and pg_catalog.octet_length(content) <= 65536),
  constraint v2_prompt_versions_hash_check
    check (content_sha256 ~ '^[0-9a-f]{64}$'),
  constraint v2_prompt_versions_input_version_check
    check (input_current_change_version > 0 and version > 0),
  constraint v2_prompt_versions_effort_check
    check (effort_category is null or effort_category in ('quick', 'standard', 'deep')),
  constraint v2_prompt_versions_mapping_pair_check
    check (
      (provider_mapping_key is null) = (provider_mapping_version is null)
      and (provider_mapping_key is null or (
        pg_catalog.btrim(provider_mapping_key) <> ''
        and pg_catalog.octet_length(provider_mapping_key) <= 256
      ))
    ),
  constraint v2_prompt_versions_handoff_pair_check
    check ((handoff_command_id is null) = (handed_off_at is null))
);

create unique index v2_prompt_versions_ordinal_key
  on public.v2_prompt_versions (current_change_id, ordinal);
create unique index v2_prompt_versions_acceptance_command_key
  on public.v2_prompt_versions (owner_user_id, acceptance_command_id);
create unique index v2_prompt_versions_handoff_command_key
  on public.v2_prompt_versions (owner_user_id, handoff_command_id)
  where handoff_command_id is not null;
create index v2_prompt_versions_history_idx
  on public.v2_prompt_versions (current_change_id, accepted_at);
create index v2_prompt_versions_generation_attempt_idx
  on public.v2_prompt_versions (generation_attempt_id)
  where generation_attempt_id is not null;

alter table public.v2_current_changes
  add constraint v2_current_changes_latest_prompt_fk
  foreign key (latest_prompt_version_id, id, project_id, owner_user_id)
  references public.v2_prompt_versions (id, current_change_id, project_id, owner_user_id)
  on delete set null (latest_prompt_version_id);

create index v2_current_changes_latest_prompt_idx
  on public.v2_current_changes (latest_prompt_version_id)
  where latest_prompt_version_id is not null;

create table public.v2_checks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  current_change_id uuid not null,
  check_plan text not null,
  plan_source varchar(16) not null,
  status varchar(16) not null,
  result varchar(24),
  student_observation text,
  performed_at timestamptz,
  not_run_at timestamptz,
  source_build_turn_id uuid,
  supersedes_check_id uuid,
  create_command_id uuid not null,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_checks_current_change_fk
    foreign key (current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id) on delete cascade,
  constraint v2_checks_owned_key unique (id, current_change_id, project_id, owner_user_id),
  constraint v2_checks_plan_check
    check (pg_catalog.btrim(check_plan) <> '' and pg_catalog.octet_length(check_plan) <= 8192),
  constraint v2_checks_plan_source_check check (plan_source in ('codize', 'student')),
  constraint v2_checks_status_check check (status in ('proposed', 'performed', 'not_run')),
  constraint v2_checks_result_check
    check (result is null or result in ('worked', 'partly_worked', 'did_not_work', 'unsure')),
  constraint v2_checks_observation_check
    check (
      student_observation is null
      or (
        pg_catalog.btrim(student_observation) <> ''
        and pg_catalog.octet_length(student_observation) <= 16384
      )
    ),
  constraint v2_checks_state_fields_check
    check (
      (status = 'proposed' and result is null and student_observation is null
        and performed_at is null and not_run_at is null)
      or (status = 'performed' and result is not null and performed_at is not null
        and not_run_at is null)
      or (status = 'not_run' and result is null and student_observation is null
        and performed_at is null and not_run_at is not null)
    ),
  constraint v2_checks_not_self_superseding_check
    check (supersedes_check_id is null or supersedes_check_id <> id),
  constraint v2_checks_version_check check (version > 0),
  constraint v2_checks_supersedes_fk
    foreign key (supersedes_check_id, current_change_id, project_id, owner_user_id)
    references public.v2_checks (id, current_change_id, project_id, owner_user_id)
    on delete set null (supersedes_check_id)
    deferrable initially deferred
);

create unique index v2_checks_create_command_key
  on public.v2_checks (owner_user_id, create_command_id);
create index v2_checks_history_idx
  on public.v2_checks (current_change_id, created_at);
create unique index v2_checks_supersedes_key
  on public.v2_checks (supersedes_check_id)
  where supersedes_check_id is not null;

create table public.v2_project_facts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  fact_type varchar(64) not null,
  subject_key varchar(128) not null,
  value_kind varchar(16) not null,
  value_text text,
  value_boolean boolean,
  value_number numeric(30,10),
  value_text_list text[],
  source_kind varchar(32) not null,
  source_record_type varchar(32) not null,
  source_record_id uuid not null,
  source_operation_id uuid,
  status varchar(16) not null,
  observed_at timestamptz not null,
  fresh_until timestamptz,
  supersedes_fact_id uuid,
  student_confirmation varchar(16) not null default 'unreviewed',
  student_confirmed_at timestamptz,
  confirmation_build_turn_id uuid,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_project_facts_project_owner_fk
    foreign key (project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id) on delete cascade,
  constraint v2_project_facts_owned_subject_key
    unique (id, project_id, owner_user_id, fact_type, subject_key),
  constraint v2_project_facts_fact_type_check
    check (fact_type in (
      'project_goal', 'first_version_scope', 'saved_for_later',
      'known_working_behavior', 'constraint', 'boundary', 'tech_stack',
      'tool', 'unresolved_behavior'
    )),
  constraint v2_project_facts_subject_key_check
    check (pg_catalog.btrim(subject_key) <> '' and pg_catalog.octet_length(subject_key) <= 256),
  constraint v2_project_facts_value_kind_check
    check (value_kind in ('text', 'boolean', 'number', 'text_list')),
  constraint v2_project_facts_typed_value_check
    check (
      (value_kind = 'text' and value_text is not null and value_boolean is null
        and value_number is null and value_text_list is null
        and pg_catalog.btrim(value_text) <> '' and pg_catalog.octet_length(value_text) <= 16384)
      or (value_kind = 'boolean' and value_text is null and value_boolean is not null
        and value_number is null and value_text_list is null)
      or (value_kind = 'number' and value_text is null and value_boolean is null
        and value_number is not null and value_text_list is null
        and value_number <> 'NaN'::numeric
        and value_number <> 'Infinity'::numeric
        and value_number <> '-Infinity'::numeric)
      or (value_kind = 'text_list' and value_text is null and value_boolean is null
        and value_number is null and value_text_list is not null
        and public.v2_valid_text_array(value_text_list, 32, 8192, 256, false))
    ),
  constraint v2_project_facts_source_kind_check
    check (source_kind in (
      'student_stated', 'student_observed', 'agent_claimed',
      'repository_observed', 'system_observed', 'codize_inferred'
    )),
  constraint v2_project_facts_source_record_type_check
    check (source_record_type in (
      'build_turn', 'current_change', 'prompt_version', 'check', 'recovery_case'
    )),
  constraint v2_project_facts_status_check
    check (status in ('active', 'unresolved', 'contradicted', 'stale', 'superseded')),
  constraint v2_project_facts_freshness_check
    check (fresh_until is null or fresh_until >= observed_at),
  constraint v2_project_facts_not_self_superseding_check
    check (supersedes_fact_id is null or supersedes_fact_id <> id),
  constraint v2_project_facts_confirmation_check
    check (
      (student_confirmation = 'unreviewed' and student_confirmed_at is null
        and confirmation_build_turn_id is null)
      or (student_confirmation in ('confirmed', 'rejected')
        and student_confirmed_at is not null and confirmation_build_turn_id is not null)
    ),
  constraint v2_project_facts_version_check check (version > 0),
  constraint v2_project_facts_supersedes_fk
    foreign key (
      supersedes_fact_id, project_id, owner_user_id, fact_type, subject_key
    ) references public.v2_project_facts (
      id, project_id, owner_user_id, fact_type, subject_key
    ) on delete set null (supersedes_fact_id)
    deferrable initially deferred
);

create index v2_project_facts_active_subject_idx
  on public.v2_project_facts (
    owner_user_id, project_id, fact_type, subject_key, status
  );
create index v2_project_facts_freshness_idx
  on public.v2_project_facts (project_id, fresh_until)
  where fresh_until is not null;
create index v2_project_facts_source_idx
  on public.v2_project_facts (project_id, source_record_type, source_record_id);
create unique index v2_project_facts_source_operation_key
  on public.v2_project_facts (
    project_id, source_operation_id, fact_type, subject_key
  ) where source_operation_id is not null;
create unique index v2_project_facts_supersedes_key
  on public.v2_project_facts (supersedes_fact_id)
  where supersedes_fact_id is not null;

create table public.v2_build_turns (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  current_change_id uuid,
  recovery_case_id uuid,
  sequence_no bigint generated always as identity,
  turn_kind varchar(32) not null,
  speaker varchar(16) not null,
  content text,
  content_sha256 char(64),
  structured_payload jsonb,
  related_record_type varchar(32),
  related_record_id uuid,
  help_context_key varchar(64),
  support_level varchar(16),
  policy_version varchar(64),
  config_version varchar(64),
  retention_class varchar(24) not null,
  expires_at timestamptz,
  redacted_at timestamptz,
  created_at timestamptz not null default now(),

  constraint v2_build_turns_project_owner_fk
    foreign key (project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id) on delete cascade,
  constraint v2_build_turns_current_change_fk
    foreign key (current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id)
    on delete set null (current_change_id),
  constraint v2_build_turns_owned_key unique (id, project_id, owner_user_id),
  constraint v2_build_turns_turn_kind_check
    check (turn_kind in (
      'mentor_question', 'student_answer', 'student_decision', 'student_override',
      'help_nudge', 'help_clue', 'help_teach', 'generated_explanation',
      'return_report', 'recovery_observation', 'safe_failure', 'system_note'
    )),
  constraint v2_build_turns_speaker_check check (speaker in ('student', 'codize', 'system')),
  constraint v2_build_turns_content_check
    check (
      content is null
      or (pg_catalog.btrim(content) <> '' and pg_catalog.octet_length(content) <= 32768)
    ),
  constraint v2_build_turns_hash_check
    check (content_sha256 is null or content_sha256 ~ '^[0-9a-f]{64}$'),
  constraint v2_build_turns_payload_check
    check (
      structured_payload is null
      or (
        pg_catalog.jsonb_typeof(structured_payload) = 'object'
        and structured_payload <> '{}'::jsonb
        and pg_catalog.octet_length(structured_payload::text) <= 16384
      )
    ),
  constraint v2_build_turns_meaningful_content_check
    check (
      (redacted_at is null and (content is not null or structured_payload is not null))
      or (redacted_at is not null and content is null and structured_payload is null)
    ),
  constraint v2_build_turns_related_pair_check
    check ((related_record_type is null) = (related_record_id is null)),
  constraint v2_build_turns_support_check
    check (
      support_level is null
      or (support_level in ('none', 'nudge', 'clue', 'teach') and help_context_key is not null)
    ),
  constraint v2_build_turns_retention_check
    check (retention_class in ('structured', 'raw_short', 'sensitive_short')),
  constraint v2_build_turns_expiry_check
    check (expires_at is null or expires_at >= created_at)
);

create index v2_build_turns_resume_idx
  on public.v2_build_turns (owner_user_id, project_id, sequence_no desc);
create index v2_build_turns_current_change_idx
  on public.v2_build_turns (current_change_id, sequence_no)
  where current_change_id is not null;

create table public.v2_recovery_cases (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  owner_user_id uuid not null,
  current_change_id uuid not null,
  status varchar(24) not null,
  intended_behavior text not null,
  observed_symptom text not null,
  last_known_working_statement text,
  last_known_working_certainty varchar(16) not null,
  candidate_current_change_id uuid,
  candidate_change_summary text,
  student_hypothesis text,
  proposed_first_check text,
  investigation_finding text,
  cause_summary text,
  correction_summary text,
  resolution_summary text,
  open_command_id uuid not null,
  opened_at timestamptz not null default now(),
  resolved_at timestamptz,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_recovery_cases_current_change_fk
    foreign key (current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id) on delete cascade,
  constraint v2_recovery_cases_candidate_change_fk
    foreign key (candidate_current_change_id, project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id)
    on delete set null (candidate_current_change_id),
  constraint v2_recovery_cases_owned_key unique (id, project_id, owner_user_id),
  constraint v2_recovery_cases_same_change_key
    unique (id, current_change_id, project_id, owner_user_id),
  constraint v2_recovery_cases_status_check
    check (status in (
      'open', 'investigating', 'correcting', 'rechecking', 'resolved', 'abandoned'
    )),
  constraint v2_recovery_cases_intended_behavior_check
    check (pg_catalog.btrim(intended_behavior) <> '' and pg_catalog.octet_length(intended_behavior) <= 16384),
  constraint v2_recovery_cases_observed_symptom_check
    check (pg_catalog.btrim(observed_symptom) <> '' and pg_catalog.octet_length(observed_symptom) <= 16384),
  constraint v2_recovery_cases_last_known_check
    check (
      last_known_working_certainty in ('yes', 'no', 'unsure')
      and (last_known_working_statement is null or (
        pg_catalog.btrim(last_known_working_statement) <> ''
        and pg_catalog.octet_length(last_known_working_statement) <= 16384
      ))
    ),
  constraint v2_recovery_cases_candidate_summary_check
    check (
      candidate_change_summary is null
      or (
        pg_catalog.btrim(candidate_change_summary) <> ''
        and pg_catalog.octet_length(candidate_change_summary) <= 8192
      )
    ),
  constraint v2_recovery_cases_detail_bounds_check
    check (
      (student_hypothesis is null or (
        pg_catalog.btrim(student_hypothesis) <> '' and pg_catalog.octet_length(student_hypothesis) <= 16384
      ))
      and (proposed_first_check is null or (
        pg_catalog.btrim(proposed_first_check) <> '' and pg_catalog.octet_length(proposed_first_check) <= 8192
      ))
      and (investigation_finding is null or (
        pg_catalog.btrim(investigation_finding) <> '' and pg_catalog.octet_length(investigation_finding) <= 16384
      ))
      and (cause_summary is null or (
        pg_catalog.btrim(cause_summary) <> '' and pg_catalog.octet_length(cause_summary) <= 16384
      ))
      and (correction_summary is null or (
        pg_catalog.btrim(correction_summary) <> '' and pg_catalog.octet_length(correction_summary) <= 16384
      ))
      and (resolution_summary is null or (
        pg_catalog.btrim(resolution_summary) <> '' and pg_catalog.octet_length(resolution_summary) <= 16384
      ))
    ),
  constraint v2_recovery_cases_terminal_check
    check (
      (status = 'resolved' and resolved_at is not null and resolution_summary is not null)
      or (status = 'abandoned' and resolved_at is not null)
      or (status not in ('resolved', 'abandoned') and resolved_at is null)
    ),
  constraint v2_recovery_cases_version_check check (version > 0)
);

create unique index v2_recovery_cases_one_open_per_change_key
  on public.v2_recovery_cases (current_change_id)
  where status in ('open', 'investigating', 'correcting', 'rechecking');
create unique index v2_recovery_cases_open_command_key
  on public.v2_recovery_cases (owner_user_id, open_command_id);
create index v2_recovery_cases_history_idx
  on public.v2_recovery_cases (current_change_id, opened_at desc);
create index v2_recovery_cases_candidate_change_idx
  on public.v2_recovery_cases (candidate_current_change_id)
  where candidate_current_change_id is not null;

alter table public.v2_build_turns
  add constraint v2_build_turns_recovery_case_fk
  foreign key (recovery_case_id, project_id, owner_user_id)
  references public.v2_recovery_cases (id, project_id, owner_user_id)
  on delete set null (recovery_case_id);

alter table public.v2_generation_attempts
  add constraint v2_generation_attempts_recovery_case_fk
  foreign key (target_recovery_case_id, project_id, owner_user_id)
  references public.v2_recovery_cases (id, project_id, owner_user_id)
  on delete set null (target_recovery_case_id);

create index v2_build_turns_recovery_case_idx
  on public.v2_build_turns (recovery_case_id)
  where recovery_case_id is not null;
create index v2_generation_attempts_recovery_case_idx
  on public.v2_generation_attempts (target_recovery_case_id)
  where target_recovery_case_id is not null;

alter table public.v2_checks
  add constraint v2_checks_source_build_turn_fk
  foreign key (source_build_turn_id, project_id, owner_user_id)
  references public.v2_build_turns (id, project_id, owner_user_id)
  on delete set null (source_build_turn_id);

create index v2_checks_source_build_turn_idx
  on public.v2_checks (source_build_turn_id)
  where source_build_turn_id is not null;

alter table public.v2_project_facts
  add constraint v2_project_facts_confirmation_turn_fk
  foreign key (confirmation_build_turn_id, project_id, owner_user_id)
  references public.v2_build_turns (id, project_id, owner_user_id)
  on delete set null (confirmation_build_turn_id);

create index v2_project_facts_confirmation_turn_idx
  on public.v2_project_facts (confirmation_build_turn_id)
  where confirmation_build_turn_id is not null;

alter table public.v2_plan_items
  add constraint v2_plan_items_terminal_change_fk
  foreign key (terminal_current_change_id, project_id, owner_user_id)
  references public.v2_current_changes (id, project_id, owner_user_id)
  on delete set null (terminal_current_change_id);

create index v2_plan_items_terminal_change_idx
  on public.v2_plan_items (terminal_current_change_id)
  where terminal_current_change_id is not null;

create table public.v2_learner_evidence (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null,
  source_project_id uuid,
  source_current_change_id uuid,
  competency_key varchar(64) not null,
  observed_behavior text not null,
  elicitation varchar(16) not null,
  support_level varchar(16) not null,
  context_key varchar(64) not null,
  source_record_type varchar(32) not null,
  source_record_id uuid,
  source_operation_id uuid,
  observed_at timestamptz not null,
  status varchar(16) not null,
  status_reason_key varchar(128),
  evidence_policy_version varchar(64) not null,
  source_minimized_at timestamptz,
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_learner_evidence_owner_user_fk
    foreign key (owner_user_id) references auth.users (id) on delete restrict,
  constraint v2_learner_evidence_source_project_fk
    foreign key (source_project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id)
    on delete set null (source_project_id),
  constraint v2_learner_evidence_source_change_fk
    foreign key (source_current_change_id, source_project_id, owner_user_id)
    references public.v2_current_changes (id, project_id, owner_user_id)
    on delete set null (source_current_change_id),
  constraint v2_learner_evidence_competency_check
    check (competency_key in (
      'first_version_scoping', 'define_done', 'protect_working_behavior',
      'effort_selection', 'inspect_changes', 'testing', 'debugging',
      'causal_explanation', 'functions', 'state', 'events', 'api', 'database',
      'authentication', 'client_server', 'persistence', 'async_work',
      'validation', 'error_handling', 'data_ownership', 'rendering', 'routing',
      'dependencies', 'version_control'
    )),
  constraint v2_learner_evidence_behavior_check
    check (pg_catalog.btrim(observed_behavior) <> '' and pg_catalog.octet_length(observed_behavior) <= 4096),
  constraint v2_learner_evidence_elicitation_check
    check (elicitation in ('spontaneous', 'asked', 'after_hint', 'taught')),
  constraint v2_learner_evidence_support_check
    check (support_level in ('none', 'nudge', 'clue', 'teach')),
  constraint v2_learner_evidence_context_check
    check (
      context_key in (
        'normal_novel', 'normal_familiar', 'slowdown_novel', 'slowdown_familiar',
        'build', 'recovery', 'transfer'
      )
    ),
  constraint v2_learner_evidence_source_type_check
    check (source_record_type in (
      'build_turn', 'check', 'recovery_case', 'current_change', 'minimized'
    )),
  constraint v2_learner_evidence_status_check
    check (status in ('active', 'retracted', 'invalidated')),
  constraint v2_learner_evidence_status_reason_check
    check (
      (status = 'active' and status_reason_key is null)
      or (status in ('retracted', 'invalidated') and status_reason_key is not null
        and pg_catalog.btrim(status_reason_key) <> ''
        and pg_catalog.octet_length(status_reason_key) <= 256)
    ),
  constraint v2_learner_evidence_source_state_check
    check (
      (
        source_minimized_at is null
        and source_record_type <> 'minimized'
        and source_record_id is not null
        and source_project_id is not null
      )
      or (
        source_minimized_at is not null
        and source_record_type = 'minimized'
        and source_record_id is null
        and source_operation_id is null
        and source_project_id is null
        and source_current_change_id is null
      )
    ),
  constraint v2_learner_evidence_version_check check (version > 0)
);

create unique index v2_learner_evidence_source_operation_key
  on public.v2_learner_evidence (
    owner_user_id, source_operation_id, competency_key, context_key
  ) where source_operation_id is not null;
create index v2_learner_evidence_learning_idx
  on public.v2_learner_evidence (
    owner_user_id, competency_key, status, observed_at desc
  );
create index v2_learner_evidence_source_project_idx
  on public.v2_learner_evidence (source_project_id)
  where source_project_id is not null;
create index v2_learner_evidence_source_change_idx
  on public.v2_learner_evidence (source_current_change_id)
  where source_current_change_id is not null;
create index v2_learner_evidence_source_record_idx
  on public.v2_learner_evidence (owner_user_id, source_record_type, source_record_id)
  where source_record_id is not null;

create table public.v2_user_preferences (
  owner_user_id uuid primary key,
  active_v2_project_id uuid,
  default_coding_agent_key varchar(64),
  selected_character_key varchar(64) not null default 'codybara',
  dialogue_sound_enabled boolean not null default true,
  motion_preference varchar(16) not null default 'system',
  version bigint not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint v2_user_preferences_owner_user_fk
    foreign key (owner_user_id) references auth.users (id) on delete restrict,
  constraint v2_user_preferences_active_project_fk
    foreign key (active_v2_project_id, owner_user_id)
    references public.v2_projects (id, owner_user_id)
    on delete set null (active_v2_project_id),
  constraint v2_user_preferences_character_check
    check (selected_character_key = 'codybara'),
  constraint v2_user_preferences_motion_check
    check (motion_preference in ('system', 'full', 'reduced')),
  constraint v2_user_preferences_version_check check (version > 0)
);

create index v2_user_preferences_active_project_idx
  on public.v2_user_preferences (active_v2_project_id)
  where active_v2_project_id is not null;

-- ---------------------------------------------------------------------------
-- Mutation, immutability, and transaction-order guards.
-- ---------------------------------------------------------------------------
create function public.v2_touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at := pg_catalog.now();
  return new;
end;
$$;

create function public.v2_change_completion_is_eligible(p_current_change_id uuid)
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select exists (
    select 1
    from public.v2_current_changes as cc
    where cc.id = p_current_change_id
      and cc.lifecycle_state in ('reviewing', 'recovering')
      and cc.latest_prompt_version_id is not null
      and cc.handoff_command_id is not null
      and exists (
        select 1
        from public.v2_prompt_versions as pv
        where pv.id = cc.latest_prompt_version_id
          and pv.current_change_id = cc.id
          and pv.project_id = cc.project_id
          and pv.owner_user_id = cc.owner_user_id
          and pv.handed_off_at is not null
          and pv.handoff_command_id = cc.handoff_command_id
      )
      and (
        cc.student_return_outcome in ('worked', 'unsure')
        or (
          cc.lifecycle_state = 'recovering'
          and cc.student_return_outcome = 'broken'
        )
      )
      and not exists (
        select 1
        from public.v2_checks as failed
        where failed.current_change_id = cc.id
          and failed.project_id = cc.project_id
          and failed.owner_user_id = cc.owner_user_id
          and failed.status = 'performed'
          and failed.result in ('did_not_work', 'unsure')
          and not exists (
            select 1 from public.v2_checks as successor
            where successor.supersedes_check_id = failed.id
              and successor.status = 'performed'
          )
      )
      and (
        cc.check_requirement = 'waived'
        or exists (
          select 1
          from public.v2_checks as passed
          where passed.current_change_id = cc.id
            and passed.project_id = cc.project_id
            and passed.owner_user_id = cc.owner_user_id
            and passed.status = 'performed'
            and passed.result in ('worked', 'partly_worked')
            and not exists (
              select 1 from public.v2_checks as successor
              where successor.supersedes_check_id = passed.id
                and successor.status = 'performed'
            )
        )
      )
      and (
        not exists (
          select 1 from public.v2_recovery_cases as open_rc
          where open_rc.current_change_id = cc.id
            and open_rc.status in ('open', 'investigating', 'correcting', 'rechecking')
        )
        or (
          cc.lifecycle_state = 'recovering'
          and exists (
            select 1
            from public.v2_recovery_cases as rc
            where rc.current_change_id = cc.id
              and rc.project_id = cc.project_id
              and rc.owner_user_id = cc.owner_user_id
              and rc.status = 'rechecking'
              and exists (
                select 1
                from public.v2_checks as recheck
                where recheck.current_change_id = cc.id
                  and recheck.project_id = cc.project_id
                  and recheck.owner_user_id = cc.owner_user_id
                  and recheck.status = 'performed'
                  and recheck.result in ('worked', 'partly_worked')
                  and recheck.performed_at >= rc.updated_at
                  and not exists (
                    select 1 from public.v2_checks as successor
                    where successor.supersedes_check_id = recheck.id
                      and successor.status = 'performed'
                  )
              )
          )
        )
      )
  );
$$;

create function public.v2_guard_projects()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' then
    if not (
      old.lifecycle_state = 'temporary_recovery'
      or (
        old.lifecycle_state = 'deletion_pending'
        and old.purge_after is not null
        and old.purge_after <= pg_catalog.now()
      )
    ) or exists (
      select 1 from public.v2_learner_evidence as le
      where le.source_project_id = old.id and le.owner_user_id = old.owner_user_id
    ) or exists (
      select 1 from public.v2_user_preferences as up
      where up.active_v2_project_id = old.id and up.owner_user_id = old.owner_user_id
    ) then
      raise exception using errcode = '23514', message = 'v2 project is not in a fully minimized purgeable state';
    end if;
    return old;
  end if;

  if tg_op = 'INSERT' then
    if new.version <> 1 or new.plan_version <> 1 then
      raise exception using errcode = '23514', message = 'v2 project versions must start at 1';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.id is distinct from old.id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.workflow_version is distinct from old.workflow_version
     or new.create_command_id is distinct from old.create_command_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 project identity changed';
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 project version must increment by exactly one';
  end if;
  if new.plan_version not in (old.plan_version, old.plan_version + 1) then
    raise exception using errcode = '40001', message = 'v2 plan version must stay current or increment by exactly one';
  end if;
  if new.plan_version = old.plan_version + 1 then
    if new.last_plan_command_id is null
       or new.last_plan_command_id is not distinct from old.last_plan_command_id then
      raise exception using errcode = '23514', message = 'plan mutation requires a new command id';
    end if;
  elsif new.last_plan_command_id is distinct from old.last_plan_command_id then
    raise exception using errcode = '23514', message = 'plan command id changed without a plan version change';
  end if;
  if old.first_version_completed_at is not null
     and new.first_version_completed_at is distinct from old.first_version_completed_at then
    raise exception using errcode = '23514', message = 'first version completion time is immutable';
  end if;
  if old.lifecycle_state = 'deletion_pending' and new.lifecycle_state <> 'deletion_pending' then
    raise exception using errcode = '23514', message = 'deletion-pending project cannot be reopened in place';
  end if;
  return new;
end;
$$;

create function public.v2_guard_plan_items()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 plan item version must start at 1';
    end if;
    if new.status in ('done', 'removed') then
      raise exception using errcode = '23514', message = 'v2 plan item cannot start terminal';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 plan item version must increment by exactly one';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 plan item identity changed';
  end if;
  if old.status in ('done', 'removed') and (
    new.label is distinct from old.label
    or new.intended_outcome is distinct from old.intended_outcome
    or new.scope_band is distinct from old.scope_band
    or new.status is distinct from old.status
    or new.order_key is distinct from old.order_key
    or new.completed_at is distinct from old.completed_at
  ) then
    raise exception using errcode = '23514', message = 'terminal v2 plan item is immutable';
  end if;
  if old.status <> 'done' and new.status = 'done'
     and (
       new.terminal_current_change_id is null
       or not exists (
         select 1 from public.v2_current_changes as cc
         where cc.id = new.terminal_current_change_id
           and cc.project_id = new.project_id
           and cc.owner_user_id = new.owner_user_id
           and cc.lifecycle_state = 'completed'
           and cc.completed_at = new.completed_at
       )
     ) then
    raise exception using errcode = '23514', message = 'plan completion requires a matching completed current change';
  end if;
  return new;
end;
$$;

create function public.v2_guard_current_changes()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_support_old integer;
  v_support_new integer;
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 or new.prompt_draft_version <> 1 then
      raise exception using errcode = '23514', message = 'v2 current change versions must start at 1';
    end if;
    if new.lifecycle_state <> 'preparing' then
      raise exception using errcode = '23514', message = 'v2 current change must start in preparing';
    end if;
    if (new.teaching_policy_version = 'unresolved-v0'
        or new.risk_policy_version = 'unresolved-v0')
       and not (
         new.lifecycle_state = 'preparing'
         and new.resume_step = 'confirm_change'
         and new.done_condition_snapshot is null
         and pg_catalog.cardinality(new.boundary_snapshots) = 0
         and new.prompt_draft is null
         and new.coding_agent_key is null
         and new.effort_category is null
         and new.latest_prompt_version_id is null
         and new.handoff_command_id is null
         and new.completion_command_id is null
         and new.student_return_outcome is null
         and new.accepted_outcome_summary is null
         and new.unresolved_uncertainty_summary is null
       ) then
      raise exception using errcode = '23514',
        message = 'unresolved V2 policy permits only initial preparation';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 current change version must increment by exactly one';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.change_kind is distinct from old.change_kind
     or new.goal_snapshot is distinct from old.goal_snapshot
     or new.create_command_id is distinct from old.create_command_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 current change identity or goal changed';
  end if;
  if old.lifecycle_state in ('completed', 'cancelled') then
    raise exception using errcode = '23514', message = 'terminal v2 current change cannot be updated';
  end if;
  if (new.teaching_policy_version = 'unresolved-v0'
      or new.risk_policy_version = 'unresolved-v0')
     and new.lifecycle_state <> 'cancelled'
     and not (
       new.lifecycle_state = 'preparing'
       and new.resume_step = 'confirm_change'
       and new.done_condition_snapshot is null
       and pg_catalog.cardinality(new.boundary_snapshots) = 0
       and new.prompt_draft is null
       and new.coding_agent_key is null
       and new.effort_category is null
       and new.latest_prompt_version_id is null
       and new.handoff_command_id is null
       and new.completion_command_id is null
       and new.student_return_outcome is null
       and new.accepted_outcome_summary is null
       and new.unresolved_uncertainty_summary is null
     ) then
    raise exception using errcode = '23514',
      message = 'unresolved V2 policy permits only initial preparation or cancellation';
  end if;
  if new.lifecycle_state is distinct from old.lifecycle_state and not (
    (old.lifecycle_state = 'preparing' and new.lifecycle_state in ('awaiting_agent', 'cancelled'))
    or (old.lifecycle_state = 'awaiting_agent' and new.lifecycle_state in ('reviewing', 'recovering', 'cancelled'))
    or (old.lifecycle_state = 'reviewing' and new.lifecycle_state in ('recovering', 'completed', 'cancelled'))
    or (old.lifecycle_state = 'recovering' and new.lifecycle_state in ('awaiting_agent', 'reviewing', 'completed', 'cancelled'))
  ) then
    raise exception using errcode = '23514', message = 'illegal v2 current change lifecycle transition';
  end if;
  if old.handoff_command_id is not null and (
    new.done_condition_snapshot is distinct from old.done_condition_snapshot
    or new.boundary_snapshots is distinct from old.boundary_snapshots
  ) then
    raise exception using errcode = '23514', message = 'handed-off current change snapshots are immutable';
  end if;
  if new.prompt_draft is distinct from old.prompt_draft then
    if new.prompt_draft_version <> old.prompt_draft_version + 1 then
      raise exception using errcode = '40001', message = 'prompt draft version must increment with the draft';
    end if;
  elsif new.prompt_draft_version <> old.prompt_draft_version then
    raise exception using errcode = '40001', message = 'prompt draft version changed without a draft change';
  end if;

  v_support_old := case old.support_level_disclosed
    when 'none' then 0 when 'nudge' then 1 when 'clue' then 2 else 3 end;
  v_support_new := case new.support_level_disclosed
    when 'none' then 0 when 'nudge' then 1 when 'clue' then 2 else 3 end;
  if new.help_context_key is not distinct from old.help_context_key
     and v_support_new < v_support_old then
    raise exception using errcode = '23514', message = 'support disclosure cannot move backward in one help context';
  end if;

  if new.lifecycle_state = 'awaiting_agent'
     and (old.lifecycle_state <> 'awaiting_agent'
       or new.handoff_command_id is distinct from old.handoff_command_id) then
    if new.latest_prompt_version_id is null or new.handoff_command_id is null or not exists (
      select 1
      from public.v2_prompt_versions as pv
      where pv.id = new.latest_prompt_version_id
        and pv.current_change_id = new.id
        and pv.project_id = new.project_id
        and pv.owner_user_id = new.owner_user_id
        and pv.handed_off_at is not null
        and pv.handoff_command_id = new.handoff_command_id
    ) then
      raise exception using errcode = '23514', message = 'awaiting_agent requires the matching handed-off prompt version';
    end if;
  end if;

  if new.lifecycle_state = 'completed' and (
    not public.v2_change_completion_is_eligible(new.id)
    or (old.student_return_outcome = 'unsure'
      and new.unresolved_uncertainty_summary is null)
  ) then
    raise exception using errcode = '23514', message = 'v2 completion is not supported by durable check/recovery state';
  end if;

  if (pg_catalog.to_jsonb(new) - array['version', 'updated_at'])
       = (pg_catalog.to_jsonb(old) - array['version', 'updated_at'])
     and not exists (
       select 1 from public.v2_recovery_cases as rc
       where rc.current_change_id = new.id
         and rc.project_id = new.project_id
         and rc.owner_user_id = new.owner_user_id
         and rc.status in ('open', 'investigating', 'correcting', 'rechecking')
     ) then
    raise exception using errcode = '23514', message = 'version-only current change update requires an open recovery case';
  end if;
  return new;
end;
$$;

create function public.v2_guard_prompt_versions()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_handoff boolean;
  v_origin_clear boolean;
begin
  if exists (
    select 1 from public.v2_current_changes as cc
    where cc.id = new.current_change_id
      and cc.project_id = new.project_id
      and cc.owner_user_id = new.owner_user_id
      and (cc.teaching_policy_version = 'unresolved-v0'
        or cc.risk_policy_version = 'unresolved-v0')
  ) then
    raise exception using errcode = '23514',
      message = 'prompt acceptance and handoff require resolved V2 policy';
  end if;

  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 prompt version must start at 1';
    end if;
    if new.handoff_command_id is not null or new.handed_off_at is not null then
      raise exception using errcode = '23514', message = 'v2 prompt version must be handed off through its controlled transition';
    end if;
    if new.content_sha256 <> pg_catalog.encode(
      pg_catalog.sha256(pg_catalog.convert_to(new.content, 'UTF8')), 'hex'
    ) then
      raise exception using errcode = '23514', message = 'v2 prompt content hash does not match content';
    end if;
    new.accepted_at := pg_catalog.now();
    new.created_at := new.accepted_at;
    new.updated_at := new.accepted_at;
    if new.generation_attempt_id is not null and not exists (
      select 1 from public.v2_generation_attempts as ga
      where ga.id = new.generation_attempt_id
        and ga.project_id = new.project_id
        and ga.owner_user_id = new.owner_user_id
        and ga.target_current_change_id = new.current_change_id
        and ga.status = 'succeeded'
        and ga.target_aggregate_version = new.input_current_change_version
    ) then
      raise exception using errcode = '23514', message = 'prompt generation origin is stale or invalid';
    end if;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 prompt version must increment by exactly one';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.current_change_id is distinct from old.current_change_id
     or new.ordinal is distinct from old.ordinal
     or new.purpose is distinct from old.purpose
     or new.content is distinct from old.content
     or new.content_sha256 is distinct from old.content_sha256
     or new.input_current_change_version is distinct from old.input_current_change_version
     or new.coding_agent_key is distinct from old.coding_agent_key
     or new.effort_category is distinct from old.effort_category
     or new.provider_mapping_key is distinct from old.provider_mapping_key
     or new.provider_mapping_version is distinct from old.provider_mapping_version
     or new.acceptance_command_id is distinct from old.acceptance_command_id
     or new.accepted_at is distinct from old.accepted_at
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 prompt snapshot changed';
  end if;

  v_handoff := old.handoff_command_id is null
    and new.handoff_command_id is not null
    and new.handed_off_at is not null
    and new.generation_attempt_id is not distinct from old.generation_attempt_id;
  v_origin_clear := old.generation_attempt_id is not null
    and new.generation_attempt_id is null
    and new.handoff_command_id is not distinct from old.handoff_command_id
    and new.handed_off_at is not distinct from old.handed_off_at;

  if not (v_handoff or v_origin_clear) then
    raise exception using errcode = '23514', message = 'v2 prompt permits only handoff or operational-origin clearing';
  end if;
  return new;
end;
$$;

create function public.v2_guard_checks()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_pointer_clear boolean;
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 check version must start at 1';
    end if;
    if new.status = 'performed' then
      new.performed_at := pg_catalog.now();
      new.not_run_at := null;
    elsif new.status = 'not_run' then
      new.not_run_at := pg_catalog.now();
      new.performed_at := null;
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 check version must increment by exactly one';
  end if;
  v_pointer_clear := (
      new.source_build_turn_id is distinct from old.source_build_turn_id
      or new.supersedes_check_id is distinct from old.supersedes_check_id
    )
    and (new.source_build_turn_id is not distinct from old.source_build_turn_id
      or (old.source_build_turn_id is not null and new.source_build_turn_id is null))
    and (new.supersedes_check_id is not distinct from old.supersedes_check_id
      or (old.supersedes_check_id is not null and new.supersedes_check_id is null))
    and (pg_catalog.to_jsonb(new) - array[
      'version', 'updated_at', 'source_build_turn_id', 'supersedes_check_id'
    ]) = (pg_catalog.to_jsonb(old) - array[
      'version', 'updated_at', 'source_build_turn_id', 'supersedes_check_id'
    ]);
  if v_pointer_clear then
    return new;
  end if;
  if old.status <> 'proposed' or new.status not in ('performed', 'not_run') then
    raise exception using errcode = '23514', message = 'illegal v2 check transition';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.current_change_id is distinct from old.current_change_id
     or new.check_plan is distinct from old.check_plan
     or new.plan_source is distinct from old.plan_source
     or new.source_build_turn_id is distinct from old.source_build_turn_id
     or new.supersedes_check_id is distinct from old.supersedes_check_id
     or new.create_command_id is distinct from old.create_command_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 check identity or plan changed';
  end if;
  if new.status = 'performed' then
    new.performed_at := pg_catalog.now();
    new.not_run_at := null;
  else
    new.not_run_at := pg_catalog.now();
    new.performed_at := null;
    new.result := null;
    new.student_observation := null;
  end if;
  return new;
end;
$$;

-- A system observation may promote only a claim whose complete typed value is
-- present in an immutable or already-locked durable source field. The mapping
-- is intentionally small: source existence alone never proves caller-supplied
-- project truth, and unsupported combinations fail closed.
create function public.v2_system_fact_source_matches(
  p_project_id uuid,
  p_owner_user_id uuid,
  p_fact_type text,
  p_subject_key text,
  p_value_kind text,
  p_value_text text,
  p_value_boolean boolean,
  p_value_number numeric,
  p_value_text_list text[],
  p_source_record_type text,
  p_source_record_id uuid
)
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select case p_source_record_type
    when 'current_change' then exists (
      select 1
      from public.v2_current_changes as cc
      where cc.id = p_source_record_id
        and cc.project_id = p_project_id
        and cc.owner_user_id = p_owner_user_id
        and p_fact_type = 'boundary'
        and p_subject_key = 'current_change_boundaries'
        and p_value_kind = 'text_list'
        and p_value_text is null
        and p_value_boolean is null
        and p_value_number is null
        and pg_catalog.cardinality(cc.boundary_snapshots) > 0
        and p_value_text_list is not distinct from cc.boundary_snapshots
    )
    when 'prompt_version' then exists (
      select 1
      from public.v2_prompt_versions as pv
      where pv.id = p_source_record_id
        and pv.project_id = p_project_id
        and pv.owner_user_id = p_owner_user_id
        and p_fact_type = 'tool'
        and p_subject_key = 'selected_coding_agent'
        and p_value_kind = 'text'
        and p_value_text is not distinct from pv.coding_agent_key
        and p_value_boolean is null
        and p_value_number is null
        and p_value_text_list is null
    )
    when 'recovery_case' then exists (
      select 1
      from public.v2_recovery_cases as rc
      where rc.id = p_source_record_id
        and rc.project_id = p_project_id
        and rc.owner_user_id = p_owner_user_id
        and p_fact_type = 'unresolved_behavior'
        and p_subject_key = 'recovery_observed_symptom'
        and p_value_kind = 'text'
        and p_value_text is not distinct from rc.observed_symptom
        and p_value_boolean is null
        and p_value_number is null
        and p_value_text_list is null
    )
    -- A performed Check constrains Fact strength, but the current Check schema
    -- has no stable semantic Fact subject/value field. It therefore cannot
    -- support a system_observed Fact without inventing truth. Build Turns and
    -- future Repository Observations are likewise unsupported for this source
    -- kind in the current eleven-table schema.
    else false
  end;
$$;

create function public.v2_validate_fact_source()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_check_result text;
begin
  if not (
    (new.source_kind = 'student_stated' and new.source_record_type = 'build_turn')
    or (new.source_kind = 'student_observed' and new.source_record_type in ('build_turn', 'check'))
    or (new.source_kind = 'agent_claimed' and new.source_record_type = 'build_turn')
    or (new.source_kind = 'system_observed' and new.source_record_type in (
      'current_change', 'prompt_version', 'check', 'recovery_case'
    ))
    or (new.source_kind = 'codize_inferred' and new.source_record_type in (
      'build_turn', 'current_change', 'prompt_version', 'check', 'recovery_case'
    ))
  ) then
    raise exception using errcode = '23514', message = 'illegal project fact source-kind/source-record combination';
  end if;

  if new.source_kind = 'system_observed' and not public.v2_system_fact_source_matches(
    new.project_id, new.owner_user_id, new.fact_type, new.subject_key,
    new.value_kind, new.value_text, new.value_boolean, new.value_number,
    new.value_text_list, new.source_record_type, new.source_record_id
  ) then
    raise exception using errcode = '23514', message = 'system-observed project fact is not established by its durable source';
  end if;

  if new.source_record_type = 'build_turn' then
    if not exists (
      select 1 from public.v2_build_turns as bt
      where bt.id = new.source_record_id
        and bt.project_id = new.project_id
        and bt.owner_user_id = new.owner_user_id
        and (
          (new.source_kind = 'student_stated' and bt.speaker = 'student'
            and bt.turn_kind in ('student_answer', 'student_decision', 'student_override'))
          or (new.source_kind = 'student_observed' and bt.speaker = 'student')
          or (new.source_kind = 'agent_claimed' and bt.turn_kind = 'return_report')
          or new.source_kind = 'codize_inferred'
        )
    ) then
      raise exception using errcode = '23503', message = 'invalid build-turn project fact source';
    end if;
  elsif new.source_record_type = 'current_change' then
    if not exists (
      select 1 from public.v2_current_changes as cc
      where cc.id = new.source_record_id and cc.project_id = new.project_id
        and cc.owner_user_id = new.owner_user_id
    ) then
      raise exception using errcode = '23503', message = 'invalid current-change project fact source';
    end if;
  elsif new.source_record_type = 'prompt_version' then
    if not exists (
      select 1 from public.v2_prompt_versions as pv
      where pv.id = new.source_record_id and pv.project_id = new.project_id
        and pv.owner_user_id = new.owner_user_id
    ) then
      raise exception using errcode = '23503', message = 'invalid prompt-version project fact source';
    end if;
  elsif new.source_record_type = 'check' then
    select vc.result into v_check_result
    from public.v2_checks as vc
    where vc.id = new.source_record_id and vc.project_id = new.project_id
      and vc.owner_user_id = new.owner_user_id and vc.status = 'performed';
    if not found then
      raise exception using errcode = '23503', message = 'project fact check source must be performed';
    end if;
    if not (
      (v_check_result = 'worked' and (
        (new.fact_type = 'known_working_behavior'
          and new.status in ('active', 'contradicted', 'stale', 'superseded'))
        or (new.fact_type = 'unresolved_behavior'
          and new.status in ('contradicted', 'stale', 'superseded'))
      ))
      or (v_check_result = 'partly_worked'
        and new.fact_type in ('known_working_behavior', 'unresolved_behavior')
        and new.status in ('unresolved', 'contradicted', 'stale', 'superseded'))
      or (v_check_result = 'did_not_work' and (
        (new.fact_type = 'known_working_behavior'
          and new.status in ('contradicted', 'superseded'))
        or (new.fact_type = 'unresolved_behavior'
          and new.status in ('active', 'unresolved', 'contradicted', 'stale', 'superseded'))
      ))
      or (v_check_result = 'unsure'
        and new.fact_type in ('known_working_behavior', 'unresolved_behavior')
        and new.status in ('unresolved', 'stale', 'superseded'))
    ) then
      raise exception using errcode = '23514', message = 'project fact type/status overstates its Check result';
    end if;
  elsif new.source_record_type = 'recovery_case' then
    if not exists (
      select 1 from public.v2_recovery_cases as rc
      where rc.id = new.source_record_id and rc.project_id = new.project_id
        and rc.owner_user_id = new.owner_user_id
    ) then
      raise exception using errcode = '23503', message = 'invalid recovery project fact source';
    end if;
  end if;
  return new;
end;
$$;

create function public.v2_guard_project_facts()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_pointer_clear boolean;
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 project fact version must start at 1';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 project fact version must increment by exactly one';
  end if;
  v_pointer_clear := (
      new.supersedes_fact_id is distinct from old.supersedes_fact_id
      or new.confirmation_build_turn_id is distinct from old.confirmation_build_turn_id
    )
    and (new.supersedes_fact_id is not distinct from old.supersedes_fact_id
      or (old.supersedes_fact_id is not null and new.supersedes_fact_id is null))
    and (new.confirmation_build_turn_id is not distinct from old.confirmation_build_turn_id
      or (old.confirmation_build_turn_id is not null and new.confirmation_build_turn_id is null))
    and (pg_catalog.to_jsonb(new) - array[
      'version', 'updated_at', 'supersedes_fact_id', 'confirmation_build_turn_id'
    ]) = (pg_catalog.to_jsonb(old) - array[
      'version', 'updated_at', 'supersedes_fact_id', 'confirmation_build_turn_id'
    ]);
  if v_pointer_clear then
    return new;
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.fact_type is distinct from old.fact_type
     or new.subject_key is distinct from old.subject_key
     or new.value_kind is distinct from old.value_kind
     or new.value_text is distinct from old.value_text
     or new.value_boolean is distinct from old.value_boolean
     or new.value_number is distinct from old.value_number
     or new.value_text_list is distinct from old.value_text_list
     or new.source_kind is distinct from old.source_kind
     or new.source_record_type is distinct from old.source_record_type
     or new.source_record_id is distinct from old.source_record_id
     or new.source_operation_id is distinct from old.source_operation_id
     or new.observed_at is distinct from old.observed_at
     or new.supersedes_fact_id is distinct from old.supersedes_fact_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable v2 project fact value or provenance changed';
  end if;
  if old.status = 'superseded' and new.status <> 'superseded' then
    raise exception using errcode = '23514', message = 'superseded project fact cannot be reopened';
  end if;
  if old.student_confirmation <> 'unreviewed'
     and (
       new.student_confirmation is distinct from old.student_confirmation
       or new.student_confirmed_at is distinct from old.student_confirmed_at
       or new.confirmation_build_turn_id is distinct from old.confirmation_build_turn_id
     ) then
    raise exception using errcode = '23514', message = 'project fact confirmation is immutable';
  end if;
  if old.student_confirmation = 'unreviewed'
     and new.student_confirmation in ('confirmed', 'rejected') then
    if not exists (
      select 1 from public.v2_build_turns as bt
      where bt.id = new.confirmation_build_turn_id
        and bt.project_id = new.project_id
        and bt.owner_user_id = new.owner_user_id
        and bt.speaker = 'student'
    ) then
      raise exception using errcode = '23503', message = 'fact confirmation requires a same-project student turn';
    end if;
    new.student_confirmed_at := pg_catalog.now();
  end if;
  return new;
end;
$$;

create function public.v2_assert_fact_supersession()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_affected_ids uuid[];
begin
  v_affected_ids := case when tg_op = 'INSERT'
    then array[new.id, new.supersedes_fact_id]
    else array[new.id, new.supersedes_fact_id, old.supersedes_fact_id]
  end;
  if exists (
    select 1
    from public.v2_project_facts as fact
    where fact.id = any (v_affected_ids)
      and (
        (fact.status = 'superseded' and (
          select pg_catalog.count(*)
          from public.v2_project_facts as successor
          where successor.supersedes_fact_id = fact.id
        ) <> 1)
        or (fact.status <> 'superseded' and exists (
          select 1
          from public.v2_project_facts as successor
          where successor.supersedes_fact_id = fact.id
        ))
      )
  ) then
    raise exception using errcode = '23514', message = 'project fact supersession must be reciprocal';
  end if;
  return null;
end;
$$;

create function public.v2_guard_build_turns()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.content is not null then
      new.content_sha256 := pg_catalog.encode(
        pg_catalog.sha256(pg_catalog.convert_to(new.content, 'UTF8')), 'hex'
      );
    else
      new.content_sha256 := null;
    end if;
    new.created_at := pg_catalog.now();
    return new;
  end if;
  if pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if old.redacted_at is not null then
    raise exception using errcode = '23514', message = 'redacted build turn cannot be restored or changed';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.current_change_id is distinct from old.current_change_id
     or new.recovery_case_id is distinct from old.recovery_case_id
     or new.sequence_no is distinct from old.sequence_no
     or new.turn_kind is distinct from old.turn_kind
     or new.speaker is distinct from old.speaker
     or new.related_record_type is distinct from old.related_record_type
     or new.related_record_id is distinct from old.related_record_id
     or new.help_context_key is distinct from old.help_context_key
     or new.support_level is distinct from old.support_level
     or new.policy_version is distinct from old.policy_version
     or new.config_version is distinct from old.config_version
     or new.retention_class is distinct from old.retention_class
     or new.expires_at is distinct from old.expires_at
     or new.created_at is distinct from old.created_at
     or new.content_sha256 is distinct from old.content_sha256
     or new.content is not null
     or new.structured_payload is not null
     or new.redacted_at is null then
    raise exception using errcode = '23514', message = 'build turns are append-only except one-way redaction';
  end if;
  new.redacted_at := pg_catalog.now();
  return new;
end;
$$;

create function public.v2_guard_generation_attempts()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_target_clear boolean;
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 generation attempt version must start at 1';
    end if;
    if (
      new.purpose in ('setup_summary', 'first_version_proposal', 'plan_proposal', 'project_answer')
      and (new.target_current_change_id is not null or new.target_recovery_case_id is not null)
    ) or (
      new.purpose in ('intervention_copy', 'prompt_draft', 'concept_explanation')
      and new.target_current_change_id is null
    ) or (
      new.purpose in ('recovery_summary', 'diagnostic_prompt', 'correction_prompt')
      and new.target_recovery_case_id is null
    ) then
      raise exception using errcode = '23514', message = 'generation purpose has an invalid target';
    end if;
    new.started_at := pg_catalog.now();
    new.created_at := new.started_at;
    new.updated_at := new.started_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 generation attempt version must increment by exactly one';
  end if;
  v_target_clear := (
      new.target_current_change_id is distinct from old.target_current_change_id
      or new.target_recovery_case_id is distinct from old.target_recovery_case_id
    )
    and (new.target_current_change_id is not distinct from old.target_current_change_id
      or (old.target_current_change_id is not null and new.target_current_change_id is null))
    and (new.target_recovery_case_id is not distinct from old.target_recovery_case_id
      or (old.target_recovery_case_id is not null and new.target_recovery_case_id is null))
    and (pg_catalog.to_jsonb(new) - array[
      'version', 'updated_at', 'target_current_change_id', 'target_recovery_case_id'
    ]) = (pg_catalog.to_jsonb(old) - array[
      'version', 'updated_at', 'target_current_change_id', 'target_recovery_case_id'
    ]);
  if v_target_clear then
    return new;
  end if;
  if old.status <> 'pending' or new.status not in ('succeeded', 'failed', 'superseded') then
    raise exception using errcode = '23514', message = 'illegal generation-attempt transition';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.target_current_change_id is distinct from old.target_current_change_id
     or new.target_recovery_case_id is distinct from old.target_recovery_case_id
     or new.purpose is distinct from old.purpose
     or new.target_aggregate_version is distinct from old.target_aggregate_version
     or new.policy_version is distinct from old.policy_version
     or new.config_version is distinct from old.config_version
     or new.provider_key is distinct from old.provider_key
     or new.model_key is distinct from old.model_key
     or new.input_sha256 is distinct from old.input_sha256
     or new.attempt_command_id is distinct from old.attempt_command_id
     or new.started_at is distinct from old.started_at
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable generation-attempt input changed';
  end if;
  new.completed_at := pg_catalog.now();
  return new;
end;
$$;

create function public.v2_guard_recovery_cases()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 recovery case version must start at 1';
    end if;
    if new.status not in ('open', 'investigating') then
      raise exception using errcode = '23514', message = 'v2 recovery case must start open or investigating';
    end if;
    if not exists (
      select 1 from public.v2_current_changes as cc
      where cc.id = new.current_change_id and cc.project_id = new.project_id
        and cc.owner_user_id = new.owner_user_id and cc.lifecycle_state = 'recovering'
    ) then
      raise exception using errcode = '23514', message = 'recovery case requires a recovering current change';
    end if;
    new.opened_at := pg_catalog.now();
    new.created_at := new.opened_at;
    new.updated_at := new.opened_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 recovery case version must increment by exactly one';
  end if;
  if new.id is distinct from old.id
     or new.project_id is distinct from old.project_id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.current_change_id is distinct from old.current_change_id
     or new.intended_behavior is distinct from old.intended_behavior
     or new.observed_symptom is distinct from old.observed_symptom
     or new.open_command_id is distinct from old.open_command_id
     or new.opened_at is distinct from old.opened_at
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable recovery identity or symptom changed';
  end if;
  if old.status in ('resolved', 'abandoned') then
    raise exception using errcode = '23514', message = 'terminal recovery case cannot be reopened';
  end if;
  if new.status is distinct from old.status and not (
    (old.status = 'open' and new.status in ('investigating', 'correcting', 'abandoned'))
    or (old.status = 'investigating' and new.status in ('correcting', 'rechecking', 'abandoned'))
    or (old.status = 'correcting' and new.status in ('investigating', 'rechecking', 'abandoned'))
    or (old.status = 'rechecking' and new.status in ('investigating', 'correcting', 'resolved', 'abandoned'))
  ) then
    raise exception using errcode = '23514', message = 'illegal recovery-case transition';
  end if;
  if new.status = 'resolved' and (
    old.status <> 'rechecking'
    or not exists (
      select 1 from public.v2_current_changes as cc
      where cc.id = new.current_change_id
        and cc.project_id = new.project_id
        and cc.owner_user_id = new.owner_user_id
        and cc.lifecycle_state = 'completed'
    )
    or not exists (
      select 1 from public.v2_checks as recheck
      where recheck.current_change_id = new.current_change_id
        and recheck.project_id = new.project_id
        and recheck.owner_user_id = new.owner_user_id
        and recheck.status = 'performed'
        and recheck.result in ('worked', 'partly_worked')
        and recheck.performed_at >= old.updated_at
        and not exists (
          select 1 from public.v2_checks as successor
          where successor.supersedes_check_id = recheck.id
            and successor.status = 'performed'
        )
    )
  ) then
    raise exception using errcode = '23514', message = 'recovery resolution requires completed change and successful post-recovery recheck';
  end if;
  if new.status in ('resolved', 'abandoned') then
    new.resolved_at := pg_catalog.now();
  else
    new.resolved_at := null;
  end if;
  return new;
end;
$$;

create function public.v2_validate_learner_source()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if new.source_record_type = 'minimized' then
    if new.source_minimized_at is null
       or new.source_project_id is not null
       or new.source_current_change_id is not null
       or new.source_record_id is not null
       or new.source_operation_id is not null then
      raise exception using errcode = '23514', message = 'invalid minimized learner evidence source';
    end if;
    return new;
  end if;

  if new.source_project_id is null or new.source_record_id is null then
    raise exception using errcode = '23514', message = 'unminimized learner evidence requires a project source';
  end if;
  if new.source_record_type = 'build_turn' then
    if not exists (
      select 1 from public.v2_build_turns as bt
      where bt.id = new.source_record_id
        and bt.project_id = new.source_project_id
        and bt.owner_user_id = new.owner_user_id
        and bt.speaker = 'student'
        and (new.source_current_change_id is null
          or bt.current_change_id = new.source_current_change_id)
    ) then
      raise exception using errcode = '23503', message = 'invalid learner-evidence build-turn source';
    end if;
  elsif new.source_record_type = 'check' then
    if new.source_current_change_id is null or not exists (
      select 1 from public.v2_checks as vc
      where vc.id = new.source_record_id
        and vc.project_id = new.source_project_id
        and vc.owner_user_id = new.owner_user_id
        and vc.current_change_id = new.source_current_change_id
        and vc.status = 'performed'
    ) then
      raise exception using errcode = '23503', message = 'learner-evidence check source must be performed';
    end if;
  elsif new.source_record_type = 'recovery_case' then
    if new.source_current_change_id is null or not exists (
      select 1 from public.v2_recovery_cases as rc
      where rc.id = new.source_record_id
        and rc.project_id = new.source_project_id
        and rc.owner_user_id = new.owner_user_id
        and rc.current_change_id = new.source_current_change_id
        and rc.status = 'resolved'
    ) then
      raise exception using errcode = '23503', message = 'invalid learner-evidence recovery source';
    end if;
  elsif new.source_record_type = 'current_change' then
    if new.source_current_change_id is null
       or new.source_record_id <> new.source_current_change_id
       or not exists (
         select 1 from public.v2_current_changes as cc
         where cc.id = new.source_record_id
           and cc.project_id = new.source_project_id
           and cc.owner_user_id = new.owner_user_id
           and cc.lifecycle_state = 'completed'
       ) then
      raise exception using errcode = '23503', message = 'invalid learner-evidence current-change source';
    end if;
  end if;
  return new;
end;
$$;

create function public.v2_guard_learner_evidence()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_minimizing boolean;
begin
  if tg_op = 'DELETE' then
    if old.source_project_id is null or not exists (
      select 1 from public.v2_projects as p
      where p.id = old.source_project_id
        and p.owner_user_id = old.owner_user_id
        and (
          p.lifecycle_state = 'temporary_recovery'
          or (p.lifecycle_state = 'deletion_pending'
            and p.purge_after is not null and p.purge_after <= pg_catalog.now())
        )
    ) then
      raise exception using errcode = '23514', message = 'learner evidence deletion requires an eligible source-project purge';
    end if;
    return old;
  end if;

  if tg_op = 'INSERT' then
    if new.version <> 1 or new.source_minimized_at is not null then
      raise exception using errcode = '23514', message = 'learner evidence must start unminimized at version 1';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;

  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'learner evidence version must increment by exactly one';
  end if;
  if new.id is distinct from old.id
     or new.owner_user_id is distinct from old.owner_user_id
     or new.competency_key is distinct from old.competency_key
     or new.elicitation is distinct from old.elicitation
     or new.support_level is distinct from old.support_level
     or new.context_key is distinct from old.context_key
     or new.observed_at is distinct from old.observed_at
     or new.evidence_policy_version is distinct from old.evidence_policy_version
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable learner-evidence identity changed';
  end if;

  v_minimizing := old.source_minimized_at is null
    and new.source_minimized_at is not null
    and new.source_project_id is null
    and new.source_current_change_id is null
    and new.source_record_type = 'minimized'
    and new.source_record_id is null
    and new.source_operation_id is null;

  if v_minimizing and (
    old.source_project_id is null or not exists (
      select 1 from public.v2_projects as p
      where p.id = old.source_project_id
        and p.owner_user_id = old.owner_user_id
        and (
          p.lifecycle_state = 'temporary_recovery'
          or (p.lifecycle_state = 'deletion_pending'
            and p.purge_after is not null and p.purge_after <= pg_catalog.now())
        )
    )
  ) then
    raise exception using errcode = '23514', message = 'learner evidence minimization requires an eligible source-project purge';
  end if;

  if old.source_minimized_at is not null and (
    new.source_project_id is distinct from old.source_project_id
    or new.source_current_change_id is distinct from old.source_current_change_id
    or new.source_record_type is distinct from old.source_record_type
    or new.source_record_id is distinct from old.source_record_id
    or new.source_operation_id is distinct from old.source_operation_id
    or new.observed_behavior is distinct from old.observed_behavior
    or new.source_minimized_at is distinct from old.source_minimized_at
  ) then
    raise exception using errcode = '23514', message = 'minimized learner source cannot be restored or rewritten';
  end if;

  if not v_minimizing and (
    new.source_project_id is distinct from old.source_project_id
    or new.source_current_change_id is distinct from old.source_current_change_id
    or new.source_record_type is distinct from old.source_record_type
    or new.source_record_id is distinct from old.source_record_id
    or new.source_operation_id is distinct from old.source_operation_id
    or new.observed_behavior is distinct from old.observed_behavior
    or new.source_minimized_at is distinct from old.source_minimized_at
  ) then
    raise exception using errcode = '23514', message = 'ordinary learner evidence cannot be rewritten';
  end if;

  if old.status <> new.status then
    if old.status <> 'active' or new.status not in ('retracted', 'invalidated') then
      raise exception using errcode = '23514', message = 'illegal learner-evidence status transition';
    end if;
  elsif new.status_reason_key is distinct from old.status_reason_key then
    raise exception using errcode = '23514', message = 'learner-evidence status reason changed without status';
  end if;
  return new;
end;
$$;

create function public.v2_guard_user_preferences()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.version <> 1 then
      raise exception using errcode = '23514', message = 'v2 user-preference version must start at 1';
    end if;
    new.created_at := pg_catalog.now();
    new.updated_at := new.created_at;
    return new;
  end if;
  if new.version = old.version and pg_catalog.pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.version <> old.version + 1 then
    raise exception using errcode = '40001', message = 'v2 user-preference version must increment by exactly one';
  end if;
  if new.owner_user_id is distinct from old.owner_user_id
     or new.created_at is distinct from old.created_at then
    raise exception using errcode = '23514', message = 'immutable preference owner changed';
  end if;
  return new;
end;
$$;

create function public.v2_assert_deleted_after_fk_cleanup()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_survives boolean := false;
begin
  case tg_table_name
    when 'v2_plan_items' then
      select exists (
        select 1 from public.v2_plan_items where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_current_changes' then
      select exists (
        select 1 from public.v2_current_changes where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_prompt_versions' then
      select exists (
        select 1 from public.v2_prompt_versions where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_checks' then
      select exists (
        select 1 from public.v2_checks where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_project_facts' then
      select exists (
        select 1 from public.v2_project_facts where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_build_turns' then
      select exists (
        select 1 from public.v2_build_turns where id = new.id
      ) into v_survives;
    when 'v2_generation_attempts' then
      select exists (
        select 1 from public.v2_generation_attempts where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_recovery_cases' then
      select exists (
        select 1 from public.v2_recovery_cases where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_learner_evidence' then
      select exists (
        select 1 from public.v2_learner_evidence where id = new.id and version = old.version
      ) into v_survives;
    when 'v2_user_preferences' then
      select exists (
        select 1 from public.v2_user_preferences
        where owner_user_id = new.owner_user_id and version = old.version
      ) into v_survives;
  end case;

  if v_survives then
    raise exception using errcode = '40001',
      message = 'surviving V2 row requires a controlled versioned detach before referenced-row deletion';
  end if;
  return null;
end;
$$;

-- Guard triggers run before the timestamp trigger because names are ordered.
create trigger v2_10_projects_guard
  before insert or update or delete on public.v2_projects
  for each row execute function public.v2_guard_projects();
create trigger v2_10_plan_items_guard
  before insert or update on public.v2_plan_items
  for each row execute function public.v2_guard_plan_items();
create trigger v2_10_current_changes_guard
  before insert or update on public.v2_current_changes
  for each row execute function public.v2_guard_current_changes();
create trigger v2_10_prompt_versions_guard
  before insert or update on public.v2_prompt_versions
  for each row execute function public.v2_guard_prompt_versions();
create trigger v2_10_checks_guard
  before insert or update on public.v2_checks
  for each row execute function public.v2_guard_checks();
create trigger v2_05_project_facts_source
  before insert or update of status on public.v2_project_facts
  for each row execute function public.v2_validate_fact_source();
create trigger v2_10_project_facts_guard
  before insert or update on public.v2_project_facts
  for each row execute function public.v2_guard_project_facts();
create constraint trigger v2_80_project_facts_reciprocal
  after insert or update of status, supersedes_fact_id on public.v2_project_facts
  deferrable initially deferred
  for each row execute function public.v2_assert_fact_supersession();
create trigger v2_10_build_turns_guard
  before insert or update on public.v2_build_turns
  for each row execute function public.v2_guard_build_turns();
create trigger v2_10_generation_attempts_guard
  before insert or update on public.v2_generation_attempts
  for each row execute function public.v2_guard_generation_attempts();
create trigger v2_10_recovery_cases_guard
  before insert or update on public.v2_recovery_cases
  for each row execute function public.v2_guard_recovery_cases();
create trigger v2_05_learner_evidence_source
  before insert or update of source_project_id, source_current_change_id,
    source_record_type, source_record_id, source_operation_id, source_minimized_at
  on public.v2_learner_evidence
  for each row execute function public.v2_validate_learner_source();
create trigger v2_10_learner_evidence_guard
  before insert or update or delete on public.v2_learner_evidence
  for each row execute function public.v2_guard_learner_evidence();
create trigger v2_10_user_preferences_guard
  before insert or update on public.v2_user_preferences
  for each row execute function public.v2_guard_user_preferences();

create trigger v2_90_projects_touch before update on public.v2_projects
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_plan_items_touch before update on public.v2_plan_items
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_current_changes_touch before update on public.v2_current_changes
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_prompt_versions_touch before update on public.v2_prompt_versions
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_checks_touch before update on public.v2_checks
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_project_facts_touch before update on public.v2_project_facts
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_generation_attempts_touch before update on public.v2_generation_attempts
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_recovery_cases_touch before update on public.v2_recovery_cases
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_learner_evidence_touch before update on public.v2_learner_evidence
  for each row execute function public.v2_touch_updated_at();
create trigger v2_90_user_preferences_touch before update on public.v2_user_preferences
  for each row execute function public.v2_touch_updated_at();

create constraint trigger v2_99_plan_items_fk_cleanup
  after update on public.v2_plan_items deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_current_changes_fk_cleanup
  after update on public.v2_current_changes deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_prompt_versions_fk_cleanup
  after update on public.v2_prompt_versions deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_checks_fk_cleanup
  after update on public.v2_checks deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_project_facts_fk_cleanup
  after update on public.v2_project_facts deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_build_turns_fk_cleanup
  after update on public.v2_build_turns deferrable initially deferred
  for each row when (
    old.current_change_id is distinct from new.current_change_id
    or old.recovery_case_id is distinct from new.recovery_case_id
  ) execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_generation_attempts_fk_cleanup
  after update on public.v2_generation_attempts deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_recovery_cases_fk_cleanup
  after update on public.v2_recovery_cases deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_learner_evidence_fk_cleanup
  after update on public.v2_learner_evidence deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();
create constraint trigger v2_99_user_preferences_fk_cleanup
  after update on public.v2_user_preferences deferrable initially deferred
  for each row when (old.version = new.version)
  execute function public.v2_assert_deleted_after_fk_cleanup();

-- ---------------------------------------------------------------------------
-- Backend-only transaction primitives.
-- ---------------------------------------------------------------------------
create function public.mutate_v2_plan(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_expected_plan_version bigint,
  p_command_id uuid,
  p_operations jsonb,
  p_expected_current_change_version bigint default null,
  p_linked_item_action text default null,
  p_cancellation_command_id uuid default null,
  p_cancellation_reason_key text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_item public.v2_plan_items%rowtype;
  v_active_change public.v2_current_changes%rowtype;
  v_op jsonb;
  v_action text;
  v_item_id uuid;
  v_expected_version bigint;
  v_removed_order bigint;
  v_removes_active_item boolean := false;
begin
  if p_owner_user_id is null or p_project_id is null or p_command_id is null
     or p_expected_project_version is null or p_expected_plan_version is null
     or p_operations is null
     or pg_catalog.jsonb_typeof(p_operations) <> 'array'
     or pg_catalog.jsonb_array_length(p_operations) not between 1 and 128
     or pg_catalog.octet_length(p_operations::text) > 262144 then
    raise exception using errcode = '22023', message = 'invalid V2 Plan command';
  end if;

  for v_op in select value from pg_catalog.jsonb_array_elements(p_operations) loop
    v_action := v_op ->> 'action';
    if pg_catalog.jsonb_typeof(v_op) <> 'object' or not (v_op ? 'action') then
      raise exception using errcode = '22023', message = 'invalid V2 Plan operation shape';
    end if;
    if v_action = 'add' then
      if v_op - array[
        'action', 'plan_item_id', 'label', 'intended_outcome',
        'scope_band', 'status', 'order_key'
      ] <> '{}'::jsonb or not (v_op ?& array[
        'plan_item_id', 'label', 'intended_outcome', 'scope_band', 'status', 'order_key'
      ]) then
        raise exception using errcode = '22023', message = 'invalid Plan add operation';
      end if;
    elsif v_action = 'edit' then
      if v_op - array[
        'action', 'plan_item_id', 'expected_version', 'label',
        'intended_outcome', 'status'
      ] <> '{}'::jsonb or not (v_op ?& array[
        'plan_item_id', 'expected_version', 'label', 'intended_outcome', 'status'
      ]) then
        raise exception using errcode = '22023', message = 'invalid Plan edit operation';
      end if;
    elsif v_action = 'reorder' then
      if v_op - array['action', 'plan_item_id', 'expected_version', 'order_key'] <> '{}'::jsonb
         or not (v_op ?& array['plan_item_id', 'expected_version', 'order_key']) then
        raise exception using errcode = '22023', message = 'invalid Plan reorder operation';
      end if;
    elsif v_action = 'move' then
      if v_op - array[
        'action', 'plan_item_id', 'expected_version', 'scope_band', 'order_key'
      ] <> '{}'::jsonb or not (v_op ?& array[
        'plan_item_id', 'expected_version', 'scope_band', 'order_key'
      ]) then
        raise exception using errcode = '22023', message = 'invalid Plan move operation';
      end if;
    elsif v_action = 'remove' then
      if v_op - array['action', 'plan_item_id', 'expected_version'] <> '{}'::jsonb
         or not (v_op ?& array['plan_item_id', 'expected_version']) then
        raise exception using errcode = '22023', message = 'invalid Plan remove operation';
      end if;
    else
      raise exception using errcode = '22023', message = 'unknown V2 Plan operation';
    end if;
    perform (v_op ->> 'plan_item_id')::uuid;
    if v_action <> 'add' then
      perform (v_op ->> 'expected_version')::bigint;
    end if;
  end loop;

  if exists (
    select 1
    from (
      select value ->> 'plan_item_id' as id, pg_catalog.count(*) as n
      from pg_catalog.jsonb_array_elements(p_operations)
      group by value ->> 'plan_item_id'
    ) as duplicate
    where duplicate.n <> 1
  ) then
    raise exception using errcode = '22023', message = 'a Plan Item may appear only once per command';
  end if;

  select * into v_project
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  if v_project.last_plan_command_id = p_command_id then
    return pg_catalog.jsonb_build_object(
      'project_id', v_project.id,
      'project_version', v_project.version,
      'plan_version', v_project.plan_version,
      'replayed', true,
      'items', coalesce((
        select pg_catalog.jsonb_agg(pg_catalog.to_jsonb(pi) order by pi.scope_band, pi.order_key, pi.id)
        from public.v2_plan_items as pi
        where pi.project_id = v_project.id and pi.owner_user_id = p_owner_user_id
          and pi.status <> 'removed'
      ), '[]'::jsonb)
    );
  end if;
  if v_project.version <> p_expected_project_version
     or v_project.plan_version <> p_expected_plan_version then
    raise exception using errcode = '40001', message = 'stale v2 project or Plan version';
  end if;
  if v_project.lifecycle_state = 'deletion_pending' then
    raise exception using errcode = '23514', message = 'deletion-pending Project Plan cannot change';
  end if;

  select * into v_active_change
  from public.v2_current_changes as cc
  where cc.project_id = p_project_id and cc.owner_user_id = p_owner_user_id
    and cc.lifecycle_state in ('preparing', 'awaiting_agent', 'reviewing', 'recovering')
    and exists (
      select 1 from pg_catalog.jsonb_array_elements(p_operations) as operation(value)
      where operation.value ->> 'action' <> 'add'
        and (operation.value ->> 'plan_item_id')::uuid = cc.plan_item_id
    )
  for update;

  if found then
    select exists (
      select 1 from pg_catalog.jsonb_array_elements(p_operations) as operation(value)
      where operation.value ->> 'action' = 'remove'
        and (operation.value ->> 'plan_item_id')::uuid = v_active_change.plan_item_id
    ) into v_removes_active_item;

    if v_removes_active_item then
      if p_linked_item_action is null
         or p_linked_item_action not in ('detach', 'cancel')
         or p_expected_current_change_version is null
         or v_active_change.version <> p_expected_current_change_version then
        raise exception using errcode = '40001', message = 'linked active Plan Item requires DETACH or CANCEL with the current version';
      end if;
      if p_linked_item_action = 'detach' then
        if p_cancellation_command_id is not null or p_cancellation_reason_key is not null then
          raise exception using errcode = '22023', message = 'DETACH cannot include cancellation fields';
        end if;
        update public.v2_current_changes as cc
        set plan_item_id = null, version = cc.version + 1
        where cc.id = v_active_change.id;
      else
        if p_cancellation_command_id is null or p_cancellation_reason_key is null
           or pg_catalog.btrim(p_cancellation_reason_key) = ''
           or pg_catalog.octet_length(p_cancellation_reason_key) > 256 then
          raise exception using errcode = '22023', message = 'CANCEL requires bounded cancellation identity and reason';
        end if;
        update public.v2_current_changes as cc
        set lifecycle_state = 'cancelled', resume_step = null,
            cancellation_command_id = p_cancellation_command_id,
            cancellation_reason_key = p_cancellation_reason_key,
            cancelled_at = pg_catalog.now(), version = cc.version + 1
        where cc.id = v_active_change.id;
      end if;
    elsif p_linked_item_action is not null
       or p_expected_current_change_version is not null
       or p_cancellation_command_id is not null
       or p_cancellation_reason_key is not null then
      raise exception using errcode = '22023', message = 'linked-item action is valid only for active linked removal';
    end if;
  elsif p_linked_item_action is not null
     or p_expected_current_change_version is not null
     or p_cancellation_command_id is not null
     or p_cancellation_reason_key is not null then
    raise exception using errcode = '22023', message = 'linked-item action supplied without a linked active removal';
  end if;

  perform pi.id
  from public.v2_plan_items as pi
  where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id
    and pi.id in (
      select (operation.value ->> 'plan_item_id')::uuid
      from pg_catalog.jsonb_array_elements(p_operations) as operation(value)
      where operation.value ->> 'action' <> 'add'
    )
  order by pi.id
  for update;

  if (
    select pg_catalog.count(*)
    from public.v2_plan_items as pi
    where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id
      and pi.id in (
        select (operation.value ->> 'plan_item_id')::uuid
        from pg_catalog.jsonb_array_elements(p_operations) as operation(value)
        where operation.value ->> 'action' <> 'add'
      )
  ) <> (
    select pg_catalog.count(*) from pg_catalog.jsonb_array_elements(p_operations) as operation(value)
    where operation.value ->> 'action' <> 'add'
  ) then
    raise exception using errcode = 'P0002', message = 'V2 Plan Item not found';
  end if;

  set constraints public.v2_plan_items_order_key deferred;
  for v_op in select value from pg_catalog.jsonb_array_elements(p_operations) loop
    v_action := v_op ->> 'action';
    v_item_id := (v_op ->> 'plan_item_id')::uuid;
    if v_action = 'add' then
      if v_op ->> 'status' not in ('proposed', 'ready', 'deferred') then
        raise exception using errcode = '23514', message = 'new Plan Item has an illegal status';
      end if;
      insert into public.v2_plan_items (
        id, project_id, owner_user_id, label, intended_outcome,
        scope_band, status, order_key
      ) values (
        v_item_id, p_project_id, p_owner_user_id, v_op ->> 'label',
        v_op ->> 'intended_outcome', v_op ->> 'scope_band',
        v_op ->> 'status', (v_op ->> 'order_key')::bigint
      );
      continue;
    end if;

    v_expected_version := (v_op ->> 'expected_version')::bigint;
    select * into strict v_item from public.v2_plan_items as pi
    where pi.id = v_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id;
    if v_item.version <> v_expected_version then
      raise exception using errcode = '40001', message = 'stale V2 Plan Item version';
    end if;

    if v_action = 'edit' then
      if v_op ->> 'status' not in ('proposed', 'ready', 'deferred') then
        raise exception using errcode = '23514', message = 'Plan Item edit has an illegal status';
      end if;
      update public.v2_plan_items as pi
      set label = v_op ->> 'label', intended_outcome = v_op ->> 'intended_outcome',
          status = v_op ->> 'status', version = pi.version + 1
      where pi.id = v_item.id;
    elsif v_action = 'reorder' then
      update public.v2_plan_items as pi
      set order_key = (v_op ->> 'order_key')::bigint, version = pi.version + 1
      where pi.id = v_item.id;
    elsif v_action = 'move' then
      update public.v2_plan_items as pi
      set scope_band = v_op ->> 'scope_band',
          order_key = (v_op ->> 'order_key')::bigint,
          version = pi.version + 1
      where pi.id = v_item.id;
    else
      select coalesce(pg_catalog.min(pi.order_key), 0) - 1 into v_removed_order
      from public.v2_plan_items as pi
      where pi.project_id = p_project_id and pi.scope_band = v_item.scope_band
        and pi.status = 'removed';
      update public.v2_plan_items as pi
      set status = 'removed', completed_at = null, terminal_current_change_id = null,
          order_key = v_removed_order, version = pi.version + 1
      where pi.id = v_item.id;
    end if;
  end loop;
  set constraints public.v2_plan_items_order_key immediate;

  update public.v2_projects as p
  set plan_version = p.plan_version + 1,
      last_plan_command_id = p_command_id,
      version = p.version + 1
  where p.id = v_project.id
  returning * into v_project;

  return pg_catalog.jsonb_build_object(
    'project_id', v_project.id,
    'project_version', v_project.version,
    'plan_version', v_project.plan_version,
    'replayed', false,
    'items', coalesce((
      select pg_catalog.jsonb_agg(pg_catalog.to_jsonb(pi) order by pi.scope_band, pi.order_key, pi.id)
      from public.v2_plan_items as pi
      where pi.project_id = v_project.id and pi.owner_user_id = p_owner_user_id
        and pi.status <> 'removed'
    ), '[]'::jsonb)
  );
end;
$$;

create function public.accept_v2_prompt_version(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint,
  p_acceptance_command_id uuid,
  p_purpose text,
  p_recovery_case_id uuid,
  p_content text,
  p_content_sha256 text,
  p_generation_attempt_id uuid,
  p_coding_agent_key text,
  p_effort_category text,
  p_provider_mapping_key text,
  p_provider_mapping_version text
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  prompt_version_id uuid,
  prompt_version bigint,
  prompt_ordinal integer,
  replayed boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_prompt public.v2_prompt_versions%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_ordinal integer;
begin
  perform 1
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  if v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514',
      message = 'prompt acceptance requires resolved V2 policy';
  end if;

  if p_recovery_case_id is not null then
    select * into v_recovery
    from public.v2_recovery_cases as rc
    where rc.id = p_recovery_case_id and rc.current_change_id = v_change.id
      and rc.project_id = p_project_id and rc.owner_user_id = p_owner_user_id
    for update;
    if not found then
      raise exception using errcode = 'P0002', message = 'v2 recovery case not found';
    end if;
  end if;

  select * into v_prompt
  from public.v2_prompt_versions as pv
  where pv.owner_user_id = p_owner_user_id
    and pv.acceptance_command_id = p_acceptance_command_id
  for update;
  if found then
    if v_prompt.current_change_id <> v_change.id
       or v_prompt.purpose <> p_purpose
       or not (
         (v_prompt.purpose = 'feature' and p_recovery_case_id is null)
         or (v_prompt.purpose = 'diagnostic' and p_recovery_case_id is not null
           and v_recovery.status = 'investigating')
         or (v_prompt.purpose = 'correction' and p_recovery_case_id is not null
           and v_recovery.status = 'correcting')
       ) then
      raise exception using errcode = '23505', message = 'prompt acceptance command id already used';
    end if;
    return query select v_change.id, v_change.version, v_prompt.id,
      v_prompt.version, v_prompt.ordinal, true;
    return;
  end if;

  if v_change.version <> p_expected_current_change_version
     or v_change.prompt_draft_version <> p_expected_prompt_draft_version then
    raise exception using errcode = '40001', message = 'stale or ineligible prompt acceptance';
  end if;
  if not (
    (v_change.lifecycle_state = 'preparing'
      and v_change.resume_step in ('prompt', 'effort')
      and p_purpose = 'feature'
      and p_recovery_case_id is null)
    or (v_change.lifecycle_state = 'recovering'
      and p_recovery_case_id is not null
      and (
        (p_purpose = 'diagnostic'
          and v_change.resume_step = 'recovery_investigate'
          and v_recovery.status = 'investigating')
        or (p_purpose = 'correction'
          and v_change.resume_step = 'recovery_correct'
          and v_recovery.status = 'correcting')
      ))
  ) then
    raise exception using errcode = '23514', message = 'prompt purpose does not match the current Build or Recovery step';
  end if;
  if v_change.prompt_draft is distinct from p_content then
    raise exception using errcode = '23514', message = 'accepted prompt must match the current prompt draft';
  end if;
  if p_content_sha256 <> pg_catalog.encode(
    pg_catalog.sha256(pg_catalog.convert_to(p_content, 'UTF8')), 'hex'
  ) then
    raise exception using errcode = '23514', message = 'prompt content hash mismatch';
  end if;

  select coalesce(pg_catalog.max(pv.ordinal), 0) + 1 into v_ordinal
  from public.v2_prompt_versions as pv
  where pv.current_change_id = v_change.id;

  insert into public.v2_prompt_versions (
    project_id, owner_user_id, current_change_id, ordinal, purpose, content,
    content_sha256, input_current_change_version, generation_attempt_id,
    coding_agent_key, effort_category, provider_mapping_key,
    provider_mapping_version, acceptance_command_id
  ) values (
    p_project_id, p_owner_user_id, v_change.id, v_ordinal, p_purpose, p_content,
    p_content_sha256, v_change.version, p_generation_attempt_id,
    p_coding_agent_key, p_effort_category, p_provider_mapping_key,
    p_provider_mapping_version, p_acceptance_command_id
  ) returning * into v_prompt;

  update public.v2_current_changes as cc
  set latest_prompt_version_id = v_prompt.id,
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  return query select v_change.id, v_change.version, v_prompt.id,
    v_prompt.version, v_prompt.ordinal, false;
end;
$$;

create function public.handoff_v2_prompt_version(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_prompt_version_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_version bigint,
  p_handoff_command_id uuid
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  lifecycle_state text,
  prompt_version_id uuid,
  prompt_version bigint,
  handed_off_at timestamptz,
  replayed boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_prompt public.v2_prompt_versions%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
begin
  perform 1
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  if v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514',
      message = 'prompt handoff requires resolved V2 policy';
  end if;

  if p_recovery_case_id is not null then
    select * into v_recovery
    from public.v2_recovery_cases as rc
    where rc.id = p_recovery_case_id and rc.current_change_id = v_change.id
      and rc.project_id = p_project_id and rc.owner_user_id = p_owner_user_id
    for update;
    if not found then
      raise exception using errcode = 'P0002', message = 'v2 recovery case not found';
    end if;
  end if;

  select * into v_prompt
  from public.v2_prompt_versions as pv
  where pv.id = p_prompt_version_id and pv.current_change_id = v_change.id
    and pv.project_id = p_project_id and pv.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 prompt version not found';
  end if;

  if v_change.handoff_command_id = p_handoff_command_id
     and v_prompt.handoff_command_id = p_handoff_command_id
     and v_change.latest_prompt_version_id = v_prompt.id
     and v_change.lifecycle_state = 'awaiting_agent'
     and (
       (v_prompt.purpose = 'feature' and p_recovery_case_id is null)
       or (v_prompt.purpose = 'diagnostic' and p_recovery_case_id is not null
         and v_recovery.status = 'investigating')
       or (v_prompt.purpose = 'correction' and p_recovery_case_id is not null
         and v_recovery.status = 'correcting')
     ) then
    return query select v_change.id, v_change.version, v_change.lifecycle_state::text,
      v_prompt.id, v_prompt.version, v_prompt.handed_off_at, true;
    return;
  end if;

  if v_change.version <> p_expected_current_change_version
     or v_prompt.version <> p_expected_prompt_version
     or v_change.latest_prompt_version_id <> v_prompt.id
     or v_prompt.handoff_command_id is not null then
    raise exception using errcode = '40001', message = 'stale or ineligible prompt handoff';
  end if;
  if not (
    (v_change.lifecycle_state = 'preparing'
      and v_prompt.purpose = 'feature'
      and p_recovery_case_id is null)
    or (v_change.lifecycle_state = 'recovering'
      and p_recovery_case_id is not null
      and (
        (v_prompt.purpose = 'diagnostic'
          and v_change.resume_step = 'recovery_investigate'
          and v_recovery.status = 'investigating')
        or (v_prompt.purpose = 'correction'
          and v_change.resume_step = 'recovery_correct'
          and v_recovery.status = 'correcting')
      ))
  ) then
    raise exception using errcode = '23514', message = 'handed-off prompt does not match the current Build or Recovery step';
  end if;

  update public.v2_prompt_versions as pv
  set handoff_command_id = p_handoff_command_id,
      handed_off_at = pg_catalog.now(),
      version = pv.version + 1
  where pv.id = v_prompt.id
  returning * into v_prompt;

  update public.v2_current_changes as cc
  set handoff_command_id = p_handoff_command_id,
      lifecycle_state = 'awaiting_agent',
      resume_step = 'return_outcome',
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  return query select v_change.id, v_change.version, v_change.lifecycle_state::text,
    v_prompt.id, v_prompt.version, v_prompt.handed_off_at, false;
end;
$$;

create function public.resume_v2_recovery_handoff(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_prompt_version_id uuid,
  p_expected_current_change_version bigint,
  p_expected_recovery_version bigint,
  p_expected_prompt_version bigint
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  resume_step text,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_prompt public.v2_prompt_versions%rowtype;
begin
  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  select * into v_recovery
  from public.v2_recovery_cases as rc
  where rc.id = p_recovery_case_id and rc.current_change_id = v_change.id
    and rc.project_id = p_project_id and rc.owner_user_id = p_owner_user_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'v2 recovery case not found';
  end if;

  select * into v_prompt
  from public.v2_prompt_versions as pv
  where pv.id = p_prompt_version_id and pv.current_change_id = v_change.id
    and pv.project_id = p_project_id and pv.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 prompt version not found';
  end if;

  if v_change.version <> p_expected_current_change_version
     or v_recovery.version <> p_expected_recovery_version
     or v_prompt.version <> p_expected_prompt_version
     or v_change.lifecycle_state <> 'awaiting_agent'
     or v_change.latest_prompt_version_id <> v_prompt.id
     or v_change.handoff_command_id is null
     or v_prompt.handoff_command_id <> v_change.handoff_command_id
     or v_prompt.handed_off_at is null then
    raise exception using errcode = '40001', message = 'stale or invalid Recovery handoff return';
  end if;
  if not (
    (v_prompt.purpose = 'diagnostic' and v_recovery.status = 'investigating')
    or (v_prompt.purpose = 'correction' and v_recovery.status = 'correcting')
  ) then
    raise exception using errcode = '23514', message = 'Recovery handoff purpose does not match the Recovery Case';
  end if;

  update public.v2_current_changes as cc
  set lifecycle_state = 'recovering',
      resume_step = case v_prompt.purpose
        when 'diagnostic' then 'recovery_investigate'
        else 'recovery_recheck'
      end,
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  if v_prompt.purpose = 'correction' then
    update public.v2_recovery_cases as rc
    set status = 'rechecking', version = rc.version + 1
    where rc.id = v_recovery.id
    returning * into v_recovery;
  end if;

  return query select v_change.id, v_change.version, v_change.resume_step::text,
    v_recovery.id, v_recovery.version, v_recovery.status::text;
end;
$$;

create function public.open_v2_recovery_case(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_open_command_id uuid,
  p_intended_behavior text,
  p_observed_symptom text,
  p_last_known_working_statement text,
  p_last_known_working_certainty text,
  p_candidate_current_change_id uuid,
  p_candidate_change_summary text
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text,
  replayed boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
begin
  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
    and p.lifecycle_state not in ('archived', 'deletion_pending')
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  select * into v_recovery
  from public.v2_recovery_cases as rc
  where rc.owner_user_id = p_owner_user_id
    and rc.open_command_id = p_open_command_id
  for update;
  if found then
    if v_recovery.current_change_id <> v_change.id
       or v_recovery.id <> p_recovery_case_id then
      raise exception using errcode = '23505', message = 'recovery open command id was already used';
    end if;
    return query select v_change.id, v_change.version, v_recovery.id,
      v_recovery.version, v_recovery.status::text, true;
    return;
  end if;

  select * into v_recovery
  from public.v2_recovery_cases as rc
  where rc.current_change_id = v_change.id
    and rc.project_id = p_project_id
    and rc.owner_user_id = p_owner_user_id
    and rc.status in ('open', 'investigating', 'correcting', 'rechecking')
  for update;
  if found then
    raise exception using errcode = '23505', message = 'v2 current change already has an open recovery case';
  end if;

  if v_change.version <> p_expected_current_change_version
     or v_change.lifecycle_state not in ('awaiting_agent', 'reviewing', 'recovering') then
    raise exception using errcode = '40001', message = 'stale or ineligible recovery opening';
  end if;

  update public.v2_current_changes as cc
  set lifecycle_state = 'recovering',
      resume_step = 'recovery_symptom',
      student_return_outcome = case
        when cc.lifecycle_state = 'awaiting_agent'
          and cc.student_return_outcome is null then 'broken'
        else cc.student_return_outcome end,
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  insert into public.v2_recovery_cases (
    id, project_id, owner_user_id, current_change_id, status,
    intended_behavior, observed_symptom, last_known_working_statement,
    last_known_working_certainty, candidate_current_change_id,
    candidate_change_summary, open_command_id
  ) values (
    p_recovery_case_id, p_project_id, p_owner_user_id, v_change.id, 'open',
    p_intended_behavior, p_observed_symptom, p_last_known_working_statement,
    p_last_known_working_certainty, p_candidate_current_change_id,
    p_candidate_change_summary, p_open_command_id
  ) returning * into v_recovery;

  return query select v_change.id, v_change.version, v_recovery.id,
    v_recovery.version, v_recovery.status::text, false;
end;
$$;

create function public.transition_v2_recovery_case(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_expected_recovery_version bigint,
  p_new_status text,
  p_patch jsonb default '{}'::jsonb
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_change public.v2_current_changes%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
begin
  if p_new_status = 'resolved' then
    raise exception using errcode = '23514', message = 'recovery is resolved only by atomic completion after recheck';
  end if;
  if p_patch is null
     or pg_catalog.jsonb_typeof(p_patch) <> 'object'
     or p_patch - array[
       'last_known_working_statement', 'last_known_working_certainty',
       'candidate_current_change_id', 'candidate_change_summary',
       'student_hypothesis', 'proposed_first_check', 'investigation_finding',
       'cause_summary', 'correction_summary', 'resolution_summary'
     ] <> '{}'::jsonb then
    raise exception using errcode = '22023', message = 'invalid recovery patch shape';
  end if;

  perform 1 from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  select * into v_recovery
  from public.v2_recovery_cases as rc
  where rc.id = p_recovery_case_id and rc.current_change_id = v_change.id
    and rc.project_id = p_project_id and rc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 recovery case not found';
  end if;

  if v_change.version <> p_expected_current_change_version
     or v_recovery.version <> p_expected_recovery_version
     or v_change.lifecycle_state <> 'recovering' then
    raise exception using errcode = '40001', message = 'stale or ineligible recovery mutation';
  end if;

  update public.v2_current_changes as cc
  set lifecycle_state = case when p_new_status in ('resolved', 'abandoned')
        then 'reviewing' else 'recovering' end,
      resume_step = case p_new_status
        when 'open' then 'recovery_symptom'
        when 'investigating' then 'recovery_investigate'
        when 'correcting' then 'recovery_correct'
        when 'rechecking' then 'recovery_recheck'
        when 'resolved' then 'check'
        else 'understand'
      end,
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  update public.v2_recovery_cases as rc
  set status = p_new_status,
      last_known_working_statement = case when p_patch ? 'last_known_working_statement'
        then p_patch ->> 'last_known_working_statement' else rc.last_known_working_statement end,
      last_known_working_certainty = case when p_patch ? 'last_known_working_certainty'
        then p_patch ->> 'last_known_working_certainty' else rc.last_known_working_certainty end,
      candidate_current_change_id = case when p_patch ? 'candidate_current_change_id'
        then (p_patch ->> 'candidate_current_change_id')::uuid else rc.candidate_current_change_id end,
      candidate_change_summary = case when p_patch ? 'candidate_change_summary'
        then p_patch ->> 'candidate_change_summary' else rc.candidate_change_summary end,
      student_hypothesis = case when p_patch ? 'student_hypothesis'
        then p_patch ->> 'student_hypothesis' else rc.student_hypothesis end,
      proposed_first_check = case when p_patch ? 'proposed_first_check'
        then p_patch ->> 'proposed_first_check' else rc.proposed_first_check end,
      investigation_finding = case when p_patch ? 'investigation_finding'
        then p_patch ->> 'investigation_finding' else rc.investigation_finding end,
      cause_summary = case when p_patch ? 'cause_summary'
        then p_patch ->> 'cause_summary' else rc.cause_summary end,
      correction_summary = case when p_patch ? 'correction_summary'
        then p_patch ->> 'correction_summary' else rc.correction_summary end,
      resolution_summary = case when p_patch ? 'resolution_summary'
        then p_patch ->> 'resolution_summary' else rc.resolution_summary end,
      version = rc.version + 1
  where rc.id = v_recovery.id
  returning * into v_recovery;

  return query select v_change.id, v_change.version, v_recovery.id,
    v_recovery.version, v_recovery.status::text;
end;
$$;

create function public.complete_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_plan_version bigint,
  p_expected_plan_item_version bigint,
  p_completion_command_id uuid,
  p_complete_linked_plan_item boolean,
  p_accepted_outcome_summary text,
  p_unresolved_uncertainty_summary text,
  p_fact_inputs jsonb default '[]'::jsonb,
  p_learner_evidence_inputs jsonb default '[]'::jsonb
)
returns table (
  project_id uuid,
  project_version bigint,
  plan_version bigint,
  current_change_id uuid,
  current_change_version bigint,
  current_change_state text,
  current_change_completed_at timestamptz,
  plan_item_id uuid,
  plan_item_version bigint,
  plan_item_status text,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_case_status text,
  replayed boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_change public.v2_current_changes%rowtype;
  v_plan_item public.v2_plan_items%rowtype;
  v_recovery public.v2_recovery_cases%rowtype;
  v_item jsonb;
  v_value_kind text;
  v_source_kind text;
  v_source_type text;
  v_source_id uuid;
  v_observed_at timestamptz;
  v_fresh_until timestamptz;
  v_value_text text;
  v_value_boolean boolean;
  v_value_number numeric(30,10);
  v_value_text_list text[];
  v_fact_status text;
  v_check_result text;
  v_first_version_complete boolean := false;
begin
  if p_owner_user_id is null or p_project_id is null or p_current_change_id is null
     or p_expected_current_change_version is null or p_completion_command_id is null
     or p_complete_linked_plan_item is null then
    raise exception using errcode = '22023', message = 'missing required completion input';
  end if;
  if p_accepted_outcome_summary is null
     or pg_catalog.btrim(p_accepted_outcome_summary) = ''
     or pg_catalog.octet_length(p_accepted_outcome_summary) > 16384
     or (p_unresolved_uncertainty_summary is not null and (
       pg_catalog.btrim(p_unresolved_uncertainty_summary) = ''
       or pg_catalog.octet_length(p_unresolved_uncertainty_summary) > 16384
     )) then
    raise exception using errcode = '22023', message = 'invalid completion summary';
  end if;
  if p_fact_inputs is null or p_learner_evidence_inputs is null
     or pg_catalog.jsonb_typeof(p_fact_inputs) <> 'array'
     or pg_catalog.jsonb_array_length(p_fact_inputs) > 32
     or pg_catalog.jsonb_typeof(p_learner_evidence_inputs) <> 'array'
     or pg_catalog.jsonb_array_length(p_learner_evidence_inputs) > 32
     or pg_catalog.octet_length(p_fact_inputs::text) > 131072
     or pg_catalog.octet_length(p_learner_evidence_inputs::text) > 131072 then
    raise exception using errcode = '22023', message = 'completion fact/evidence arrays are invalid or too large';
  end if;

  -- Lock order is architectural: Project -> Current Change -> Plan Item -> Recovery Case.
  select * into v_project
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  select * into v_change
  from public.v2_current_changes as cc
  where cc.id = p_current_change_id and cc.project_id = p_project_id
    and cc.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 current change not found';
  end if;

  if v_change.plan_item_id is not null then
    select * into v_plan_item
    from public.v2_plan_items as pi
    where pi.id = v_change.plan_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id
    for update;
    if not found then
      raise exception using errcode = '23503', message = 'linked v2 plan item not found';
    end if;
  end if;

  select * into v_recovery
  from public.v2_recovery_cases as rc
  where rc.current_change_id = v_change.id and rc.project_id = p_project_id
    and rc.owner_user_id = p_owner_user_id
  order by
    case when rc.status in ('open', 'investigating', 'correcting', 'rechecking') then 0 else 1 end,
    rc.opened_at desc,
    rc.id
  limit 1
  for update;

  -- This recheck is intentionally after every applicable aggregate lock.
  if v_change.teaching_policy_version = 'unresolved-v0'
     or v_change.risk_policy_version = 'unresolved-v0' then
    raise exception using errcode = '23514',
      message = 'completion requires resolved V2 policy';
  end if;

  if v_change.lifecycle_state = 'completed'
     and v_change.completion_command_id = p_completion_command_id then
    return query select
      v_project.id, v_project.version, v_project.plan_version,
      v_change.id, v_change.version, v_change.lifecycle_state::text, v_change.completed_at,
      v_plan_item.id, v_plan_item.version, v_plan_item.status::text,
      v_recovery.id, v_recovery.version, v_recovery.status::text, true;
    return;
  end if;
  if v_change.lifecycle_state in ('completed', 'cancelled')
     or v_change.completion_command_id is not null then
    raise exception using errcode = '40001', message = 'v2 current change is already terminal';
  end if;
  if exists (
    select 1 from public.v2_current_changes as other
    where other.owner_user_id = p_owner_user_id
      and other.completion_command_id = p_completion_command_id
      and other.id <> v_change.id
  ) then
    raise exception using errcode = '23505', message = 'completion command id was already used';
  end if;

  if v_project.lifecycle_state not in ('active', 'temporary_recovery')
     or (v_project.lifecycle_state = 'temporary_recovery'
       and v_change.change_kind <> 'recovery')
     or v_change.lifecycle_state not in ('reviewing', 'recovering')
     or v_change.version <> p_expected_current_change_version then
    raise exception using errcode = '40001', message = 'stale or ineligible v2 completion';
  end if;
  if v_change.plan_item_id is null then
    if p_expected_plan_version is not null or p_expected_plan_item_version is not null
       or p_complete_linked_plan_item then
      raise exception using errcode = '22023', message = 'unlinked completion cannot supply plan tokens or complete an item';
    end if;
  elsif p_expected_plan_version is null or p_expected_plan_item_version is null
     or v_project.plan_version <> p_expected_plan_version
     or v_plan_item.version <> p_expected_plan_item_version then
    raise exception using errcode = '40001', message = 'stale linked plan state';
  end if;
  if p_complete_linked_plan_item and v_plan_item.status not in ('proposed', 'ready', 'deferred') then
    raise exception using errcode = '23514', message = 'linked plan item cannot be completed from its current state';
  end if;
  if v_change.latest_prompt_version_id is null
     or v_change.handoff_command_id is null
     or not exists (
       select 1 from public.v2_prompt_versions as pv
       where pv.id = v_change.latest_prompt_version_id
         and pv.current_change_id = v_change.id
         and pv.project_id = v_project.id
         and pv.owner_user_id = p_owner_user_id
         and pv.handed_off_at is not null
         and pv.handoff_command_id = v_change.handoff_command_id
     ) then
    raise exception using errcode = '23514', message = 'completion requires the matching handed-off prompt';
  end if;
  if v_change.student_return_outcome not in ('worked', 'unsure')
     and not (
       v_change.lifecycle_state = 'recovering'
       and v_change.student_return_outcome = 'broken'
     ) then
    raise exception using errcode = '23514', message = 'completion requires an honest return outcome or a successful Recovery recheck';
  end if;
  if v_change.student_return_outcome = 'unsure'
     and p_unresolved_uncertainty_summary is null then
    raise exception using errcode = '23514', message = 'unsure completion requires bounded unresolved uncertainty';
  end if;

  if not public.v2_change_completion_is_eligible(v_change.id) then
    raise exception using errcode = '23514', message = 'completion is not supported by the latest durable Check and Recovery state';
  end if;

  -- Validate exact FactInput and LearnerEvidenceInput shapes and stable sources
  -- before making any write. Trigger validators perform the same owner/source checks.
  for v_item in select value from pg_catalog.jsonb_array_elements(p_fact_inputs) loop
    if pg_catalog.jsonb_typeof(v_item) <> 'object'
       or v_item - array[
         'fact_type', 'subject_key', 'value_kind', 'value', 'source_kind',
         'source_record_type', 'source_record_id', 'observed_at', 'fresh_until'
       ] <> '{}'::jsonb
       or not (v_item ?& array[
         'fact_type', 'subject_key', 'value_kind', 'value', 'source_kind',
         'source_record_type', 'source_record_id', 'observed_at'
       ]) then
      raise exception using errcode = '22023', message = 'invalid FactInput shape';
    end if;
    v_value_kind := v_item ->> 'value_kind';
    v_source_kind := v_item ->> 'source_kind';
    v_source_type := v_item ->> 'source_record_type';
    v_source_id := (v_item ->> 'source_record_id')::uuid;
    if not (
      (v_source_type = 'build_turn' and exists (
        select 1 from public.v2_build_turns as bt where bt.id = v_source_id
          and bt.project_id = v_project.id and bt.owner_user_id = p_owner_user_id
          and bt.current_change_id = v_change.id
      ))
      or (v_source_type = 'current_change' and v_source_id = v_change.id)
      or (v_source_type = 'prompt_version' and exists (
        select 1 from public.v2_prompt_versions as pv where pv.id = v_source_id
          and pv.current_change_id = v_change.id and pv.project_id = v_project.id
          and pv.owner_user_id = p_owner_user_id
      ))
      or (v_source_type = 'check' and exists (
        select 1 from public.v2_checks as vc where vc.id = v_source_id
          and vc.current_change_id = v_change.id and vc.project_id = v_project.id
          and vc.owner_user_id = p_owner_user_id and vc.status = 'performed'
      ))
      or (v_source_type = 'recovery_case' and exists (
        select 1 from public.v2_recovery_cases as rc where rc.id = v_source_id
          and rc.current_change_id = v_change.id and rc.project_id = v_project.id
          and rc.owner_user_id = p_owner_user_id
      ))
    ) then
      raise exception using errcode = '23503', message = 'FactInput source is not durable state for this change';
    end if;

    -- Parse the proposed typed value before any completion write so the full
    -- source-to-claim relationship is validated atomically and fail-closed.
    v_value_text := null;
    v_value_boolean := null;
    v_value_number := null;
    v_value_text_list := null;
    if v_value_kind = 'text' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'string' then
      v_value_text := v_item ->> 'value';
    elsif v_value_kind = 'boolean' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'boolean' then
      v_value_boolean := (v_item ->> 'value')::boolean;
    elsif v_value_kind = 'number' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'number' then
      v_value_number := (v_item ->> 'value')::numeric(30,10);
    elsif v_value_kind = 'text_list'
          and pg_catalog.jsonb_typeof(v_item -> 'value') = 'array'
          and not exists (
            select 1 from pg_catalog.jsonb_array_elements(v_item -> 'value') as x(value)
            where pg_catalog.jsonb_typeof(x.value) <> 'string'
          ) then
      select pg_catalog.array_agg(x.value order by x.ordinality)
      into v_value_text_list
      from pg_catalog.jsonb_array_elements_text(v_item -> 'value')
        with ordinality as x(value, ordinality);
    else
      raise exception using errcode = '22023', message = 'FactInput typed value does not match value_kind';
    end if;

    if v_source_kind = 'system_observed' and not public.v2_system_fact_source_matches(
      v_project.id, p_owner_user_id, v_item ->> 'fact_type',
      v_item ->> 'subject_key', v_value_kind, v_value_text, v_value_boolean,
      v_value_number, v_value_text_list, v_source_type, v_source_id
    ) then
      raise exception using errcode = '23514', message = 'system-observed FactInput is not established by its durable source';
    end if;
  end loop;

  for v_item in select value from pg_catalog.jsonb_array_elements(p_learner_evidence_inputs) loop
    if pg_catalog.jsonb_typeof(v_item) <> 'object'
       or v_item - array[
         'competency_key', 'observed_behavior', 'elicitation', 'support_level',
         'context_key', 'source_record_type', 'source_record_id', 'observed_at',
         'evidence_policy_version'
       ] <> '{}'::jsonb
       or not (v_item ?& array[
         'competency_key', 'observed_behavior', 'elicitation', 'support_level',
         'context_key', 'source_record_type', 'source_record_id', 'observed_at',
         'evidence_policy_version'
       ]) then
      raise exception using errcode = '22023', message = 'invalid LearnerEvidenceInput shape';
    end if;
    v_source_type := v_item ->> 'source_record_type';
    v_source_id := (v_item ->> 'source_record_id')::uuid;
    if not (
      (v_source_type = 'build_turn' and exists (
        select 1 from public.v2_build_turns as bt where bt.id = v_source_id
          and bt.project_id = v_project.id and bt.owner_user_id = p_owner_user_id
          and bt.current_change_id = v_change.id and bt.speaker = 'student'
      ))
      or (v_source_type = 'current_change' and v_source_id = v_change.id)
      or (v_source_type = 'check' and exists (
        select 1 from public.v2_checks as vc where vc.id = v_source_id
          and vc.current_change_id = v_change.id and vc.project_id = v_project.id
          and vc.owner_user_id = p_owner_user_id and vc.status = 'performed'
      ))
      or (v_source_type = 'recovery_case' and v_recovery.id = v_source_id
          and v_recovery.status = 'rechecking')
    ) then
      raise exception using errcode = '23503', message = 'LearnerEvidenceInput source is not qualifying state for this change';
    end if;
  end loop;

  update public.v2_current_changes as cc
  set lifecycle_state = 'completed',
      resume_step = null,
      accepted_outcome_summary = p_accepted_outcome_summary,
      unresolved_uncertainty_summary = p_unresolved_uncertainty_summary,
      completion_command_id = p_completion_command_id,
      completed_at = pg_catalog.now(),
      version = cc.version + 1
  where cc.id = v_change.id
  returning * into v_change;

  if p_complete_linked_plan_item then
    update public.v2_plan_items as pi
    set status = 'done',
        completed_at = v_change.completed_at,
        terminal_current_change_id = v_change.id,
        version = pi.version + 1
    where pi.id = v_plan_item.id
    returning * into v_plan_item;

    select exists (
      select 1 from public.v2_plan_items as pi
      where pi.project_id = v_project.id and pi.scope_band = 'first_version'
    ) and not exists (
      select 1 from public.v2_plan_items as pi
      where pi.project_id = v_project.id and pi.scope_band = 'first_version'
        and pi.status not in ('done', 'removed')
    ) into v_first_version_complete;

    update public.v2_projects as p
    set plan_version = p.plan_version + 1,
        last_plan_command_id = p_completion_command_id,
        first_version_completed_at = case
          when p.first_version_completed_at is null and v_first_version_complete
          then v_change.completed_at else p.first_version_completed_at end,
        version = p.version + 1
    where p.id = v_project.id
    returning * into v_project;
  end if;

  for v_item in select value from pg_catalog.jsonb_array_elements(p_fact_inputs) loop
    v_value_kind := v_item ->> 'value_kind';
    v_source_kind := v_item ->> 'source_kind';
    v_source_type := v_item ->> 'source_record_type';
    v_source_id := (v_item ->> 'source_record_id')::uuid;
    v_observed_at := (v_item ->> 'observed_at')::timestamptz;
    v_fresh_until := case when v_item ? 'fresh_until'
      then (v_item ->> 'fresh_until')::timestamptz else null end;
    v_value_text := null;
    v_value_boolean := null;
    v_value_number := null;
    v_value_text_list := null;
    v_fact_status := case when v_source_kind in ('agent_claimed', 'codize_inferred')
      then 'unresolved' else 'active' end;

    if v_source_type = 'check' then
      select vc.result into strict v_check_result
      from public.v2_checks as vc
      where vc.id = v_source_id and vc.current_change_id = v_change.id
        and vc.project_id = v_project.id and vc.owner_user_id = p_owner_user_id
        and vc.status = 'performed';
      v_fact_status := case v_check_result
        when 'worked' then 'active'
        when 'partly_worked' then 'unresolved'
        when 'unsure' then 'unresolved'
        when 'did_not_work' then case
          when v_item ->> 'fact_type' = 'known_working_behavior' then 'contradicted'
          else 'active'
        end
      end;
    end if;

    if v_value_kind = 'text' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'string' then
      v_value_text := v_item ->> 'value';
    elsif v_value_kind = 'boolean' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'boolean' then
      v_value_boolean := (v_item ->> 'value')::boolean;
    elsif v_value_kind = 'number' and pg_catalog.jsonb_typeof(v_item -> 'value') = 'number' then
      v_value_number := (v_item ->> 'value')::numeric(30,10);
    elsif v_value_kind = 'text_list'
          and pg_catalog.jsonb_typeof(v_item -> 'value') = 'array'
          and not exists (
            select 1 from pg_catalog.jsonb_array_elements(v_item -> 'value') as x(value)
            where pg_catalog.jsonb_typeof(x.value) <> 'string'
          ) then
      select pg_catalog.array_agg(x.value order by x.ordinality)
      into v_value_text_list
      from pg_catalog.jsonb_array_elements_text(v_item -> 'value')
        with ordinality as x(value, ordinality);
    else
      raise exception using errcode = '22023', message = 'FactInput typed value does not match value_kind';
    end if;

    insert into public.v2_project_facts (
      project_id, owner_user_id, fact_type, subject_key,
      value_kind, value_text, value_boolean, value_number, value_text_list,
      source_kind, source_record_type, source_record_id, source_operation_id,
      status, observed_at, fresh_until
    ) values (
      v_project.id, p_owner_user_id, v_item ->> 'fact_type', v_item ->> 'subject_key',
      v_value_kind, v_value_text, v_value_boolean, v_value_number, v_value_text_list,
      v_source_kind, v_source_type, v_source_id, p_completion_command_id,
      v_fact_status,
      v_observed_at, v_fresh_until
    );
  end loop;

  if v_recovery.id is not null and v_recovery.status = 'rechecking' then
    update public.v2_recovery_cases as rc
    set status = 'resolved',
        resolution_summary = p_accepted_outcome_summary,
        version = rc.version + 1
    where rc.id = v_recovery.id
    returning * into v_recovery;
  end if;

  for v_item in select value from pg_catalog.jsonb_array_elements(p_learner_evidence_inputs) loop
    insert into public.v2_learner_evidence (
      owner_user_id, source_project_id, source_current_change_id,
      competency_key, observed_behavior, elicitation, support_level, context_key,
      source_record_type, source_record_id, source_operation_id, observed_at,
      status, evidence_policy_version
    ) values (
      p_owner_user_id, v_project.id, v_change.id,
      v_item ->> 'competency_key', v_item ->> 'observed_behavior',
      v_item ->> 'elicitation', v_item ->> 'support_level', v_item ->> 'context_key',
      v_item ->> 'source_record_type', (v_item ->> 'source_record_id')::uuid,
      p_completion_command_id, (v_item ->> 'observed_at')::timestamptz,
      'active', v_item ->> 'evidence_policy_version'
    );
  end loop;

  return query select
    v_project.id, v_project.version, v_project.plan_version,
    v_change.id, v_change.version, v_change.lifecycle_state::text, v_change.completed_at,
    v_plan_item.id, v_plan_item.version, v_plan_item.status::text,
    v_recovery.id, v_recovery.version, v_recovery.status::text, false;
end;
$$;

create function public.purge_v2_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_purge_kind text,
  p_evidence_actions jsonb default '[]'::jsonb
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_evidence public.v2_learner_evidence%rowtype;
  v_action jsonb;
  v_exception_count integer;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null
     or p_purge_kind is null or p_evidence_actions is null
     or p_purge_kind not in ('standard', 'temporary_recovery')
     or pg_catalog.jsonb_typeof(p_evidence_actions) <> 'array'
     or pg_catalog.jsonb_array_length(p_evidence_actions) > 64
     or pg_catalog.octet_length(p_evidence_actions::text) > 65536 then
    raise exception using errcode = '22023', message = 'invalid v2 project purge input';
  end if;

  select * into v_project
  from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    -- Absence and cross-owner mismatch intentionally have the same safe retry result.
    return true;
  end if;
  if v_project.version <> p_expected_project_version then
    raise exception using errcode = '40001', message = 'stale v2 project purge';
  end if;
  if (p_purge_kind = 'standard' and (
        v_project.lifecycle_state <> 'deletion_pending'
        or v_project.purge_after is null
        or v_project.purge_after > pg_catalog.now()
      ))
     or (p_purge_kind = 'temporary_recovery'
       and v_project.lifecycle_state <> 'temporary_recovery') then
    raise exception using errcode = '23514', message = 'v2 project is not eligible for this purge kind';
  end if;

  if exists (
    select 1
    from pg_catalog.jsonb_array_elements(p_evidence_actions) as a(value)
    where pg_catalog.jsonb_typeof(a.value) <> 'object'
      or a.value - array['evidence_id', 'expected_version', 'action'] <> '{}'::jsonb
      or not (a.value ?& array['evidence_id', 'expected_version', 'action'])
      or a.value ->> 'action' <> 'minimize'
  ) then
    raise exception using errcode = '22023', message = 'invalid purge evidence action shape';
  end if;
  select pg_catalog.count(distinct (a.value ->> 'evidence_id'))
  into v_exception_count
  from pg_catalog.jsonb_array_elements(p_evidence_actions) as a(value);
  if v_exception_count <> pg_catalog.jsonb_array_length(p_evidence_actions) then
    raise exception using errcode = '22023', message = 'duplicate purge evidence action';
  end if;

  -- Lock every affected row in stable order. The default action is set-based
  -- deletion; callers name only the bounded exceptions that remain truthful
  -- after complete source/content minimization.
  perform le.id from public.v2_learner_evidence as le
    where le.source_project_id = v_project.id and le.owner_user_id = p_owner_user_id
    order by le.id
    for update;

  for v_action in select value from pg_catalog.jsonb_array_elements(p_evidence_actions) loop
    select * into v_evidence
    from public.v2_learner_evidence as le
    where le.id = (v_action ->> 'evidence_id')::uuid
      and le.source_project_id = v_project.id
      and le.owner_user_id = p_owner_user_id;
    if not found or v_evidence.version <> (v_action ->> 'expected_version')::bigint then
      raise exception using errcode = '40001', message = 'stale or invalid purge minimization exception';
    end if;
    update public.v2_learner_evidence as le
    set source_project_id = null,
        source_current_change_id = null,
        source_record_type = 'minimized',
        source_record_id = null,
        source_operation_id = null,
        observed_behavior = 'Observed this competency in a prior project without retained project details.',
        source_minimized_at = pg_catalog.now(),
        version = le.version + 1
    where le.id = v_evidence.id;
  end loop;

  delete from public.v2_learner_evidence as le
  where le.source_project_id = v_project.id and le.owner_user_id = p_owner_user_id;

  -- Preference locking follows Evidence locking and precedes physical deletion.
  perform 1 from public.v2_user_preferences as up
  where up.owner_user_id = p_owner_user_id
  for update;
  update public.v2_user_preferences as up
  set active_v2_project_id = null,
      version = up.version + 1
  where up.owner_user_id = p_owner_user_id
    and up.active_v2_project_id = v_project.id;

  delete from public.v2_projects as p
  where p.id = v_project.id and p.owner_user_id = p_owner_user_id;
  if not found then
    raise exception using errcode = '40001', message = 'v2 project changed during purge';
  end if;
  return true;
end;
$$;

-- ---------------------------------------------------------------------------
-- Backend-only exposure: browser roles have no V2 table or RPC access.
-- RLS remains enabled with an intentionally empty/default-deny policy set.
-- ---------------------------------------------------------------------------
do $v2_execution_role$
begin
  if not exists (
    select 1 from pg_catalog.pg_roles where rolname = 'codize_v2_executor'
  ) then
    create role codize_v2_executor
      nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
  end if;
end
$v2_execution_role$;

-- PostgreSQL requires SET membership in a target role before a non-superuser
-- can transfer object ownership to it or alter its default privileges. Keep
-- that membership transaction-local to this migration's privilege setup.
grant codize_v2_executor to current_user with set true;

create schema if not exists codize_v2_internal;
revoke all on schema codize_v2_internal from public, anon, authenticated, service_role;

alter function public.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text)
  set schema codize_v2_internal;
alter function public.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text)
  set schema codize_v2_internal;
alter function public.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid)
  set schema codize_v2_internal;
alter function public.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint)
  set schema codize_v2_internal;
alter function public.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text)
  set schema codize_v2_internal;
alter function public.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb)
  set schema codize_v2_internal;
alter function public.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb)
  set schema codize_v2_internal;
alter function public.purge_v2_project(uuid, uuid, bigint, text, jsonb)
  set schema codize_v2_internal;

create function public.mutate_v2_plan(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_expected_plan_version bigint,
  p_command_id uuid,
  p_operations jsonb,
  p_expected_current_change_version bigint default null,
  p_linked_item_action text default null,
  p_cancellation_command_id uuid default null,
  p_cancellation_reason_key text default null
)
returns jsonb
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.mutate_v2_plan(
    p_owner_user_id, p_project_id, p_expected_project_version,
    p_expected_plan_version, p_command_id, p_operations,
    p_expected_current_change_version, p_linked_item_action,
    p_cancellation_command_id, p_cancellation_reason_key
  );
$wrapper$;

create function public.accept_v2_prompt_version(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint,
  p_acceptance_command_id uuid,
  p_purpose text,
  p_recovery_case_id uuid,
  p_content text,
  p_content_sha256 text,
  p_generation_attempt_id uuid,
  p_coding_agent_key text,
  p_effort_category text,
  p_provider_mapping_key text,
  p_provider_mapping_version text
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  prompt_version_id uuid,
  prompt_version bigint,
  prompt_ordinal integer,
  replayed boolean
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.accept_v2_prompt_version(
    p_owner_user_id, p_project_id, p_current_change_id,
    p_expected_current_change_version, p_expected_prompt_draft_version,
    p_acceptance_command_id, p_purpose, p_recovery_case_id, p_content,
    p_content_sha256, p_generation_attempt_id, p_coding_agent_key,
    p_effort_category, p_provider_mapping_key, p_provider_mapping_version
  );
$wrapper$;

create function public.handoff_v2_prompt_version(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_prompt_version_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_version bigint,
  p_handoff_command_id uuid
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  lifecycle_state text,
  prompt_version_id uuid,
  prompt_version bigint,
  handed_off_at timestamptz,
  replayed boolean
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.handoff_v2_prompt_version(
    p_owner_user_id, p_project_id, p_current_change_id, p_prompt_version_id,
    p_recovery_case_id, p_expected_current_change_version,
    p_expected_prompt_version, p_handoff_command_id
  );
$wrapper$;

create function public.resume_v2_recovery_handoff(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_prompt_version_id uuid,
  p_expected_current_change_version bigint,
  p_expected_recovery_version bigint,
  p_expected_prompt_version bigint
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  resume_step text,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.resume_v2_recovery_handoff(
    p_owner_user_id, p_project_id, p_current_change_id, p_recovery_case_id,
    p_prompt_version_id, p_expected_current_change_version,
    p_expected_recovery_version, p_expected_prompt_version
  );
$wrapper$;

create function public.open_v2_recovery_case(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_open_command_id uuid,
  p_intended_behavior text,
  p_observed_symptom text,
  p_last_known_working_statement text,
  p_last_known_working_certainty text,
  p_candidate_current_change_id uuid,
  p_candidate_change_summary text
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text,
  replayed boolean
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.open_v2_recovery_case(
    p_owner_user_id, p_project_id, p_current_change_id, p_recovery_case_id,
    p_expected_current_change_version, p_open_command_id, p_intended_behavior,
    p_observed_symptom, p_last_known_working_statement,
    p_last_known_working_certainty, p_candidate_current_change_id,
    p_candidate_change_summary
  );
$wrapper$;

create function public.transition_v2_recovery_case(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_expected_recovery_version bigint,
  p_new_status text,
  p_patch jsonb default '{}'::jsonb
)
returns table (
  current_change_id uuid,
  current_change_version bigint,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_status text
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.transition_v2_recovery_case(
    p_owner_user_id, p_project_id, p_current_change_id, p_recovery_case_id,
    p_expected_current_change_version, p_expected_recovery_version,
    p_new_status, p_patch
  );
$wrapper$;

create function public.complete_v2_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_plan_version bigint,
  p_expected_plan_item_version bigint,
  p_completion_command_id uuid,
  p_complete_linked_plan_item boolean,
  p_accepted_outcome_summary text,
  p_unresolved_uncertainty_summary text,
  p_fact_inputs jsonb default '[]'::jsonb,
  p_learner_evidence_inputs jsonb default '[]'::jsonb
)
returns table (
  project_id uuid,
  project_version bigint,
  plan_version bigint,
  current_change_id uuid,
  current_change_version bigint,
  current_change_state text,
  current_change_completed_at timestamptz,
  plan_item_id uuid,
  plan_item_version bigint,
  plan_item_status text,
  recovery_case_id uuid,
  recovery_case_version bigint,
  recovery_case_status text,
  replayed boolean
)
language sql
security invoker
set search_path = ''
as $wrapper$
  select * from codize_v2_internal.complete_v2_current_change(
    p_owner_user_id, p_project_id, p_current_change_id,
    p_expected_current_change_version, p_expected_plan_version,
    p_expected_plan_item_version, p_completion_command_id,
    p_complete_linked_plan_item, p_accepted_outcome_summary,
    p_unresolved_uncertainty_summary, p_fact_inputs,
    p_learner_evidence_inputs
  );
$wrapper$;

create function public.purge_v2_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_purge_kind text,
  p_evidence_actions jsonb default '[]'::jsonb
)
returns boolean
language sql
security invoker
set search_path = ''
as $wrapper$
  select codize_v2_internal.purge_v2_project(
    p_owner_user_id, p_project_id, p_expected_project_version,
    p_purge_kind, p_evidence_actions
  );
$wrapper$;

alter table public.v2_projects enable row level security;
alter table public.v2_plan_items enable row level security;
alter table public.v2_current_changes enable row level security;
alter table public.v2_prompt_versions enable row level security;
alter table public.v2_checks enable row level security;
alter table public.v2_project_facts enable row level security;
alter table public.v2_build_turns enable row level security;
alter table public.v2_generation_attempts enable row level security;
alter table public.v2_recovery_cases enable row level security;
alter table public.v2_learner_evidence enable row level security;
alter table public.v2_user_preferences enable row level security;

revoke all privileges on table
  public.v2_projects,
  public.v2_plan_items,
  public.v2_current_changes,
  public.v2_prompt_versions,
  public.v2_checks,
  public.v2_project_facts,
  public.v2_build_turns,
  public.v2_generation_attempts,
  public.v2_recovery_cases,
  public.v2_learner_evidence,
  public.v2_user_preferences
from public, anon, authenticated, service_role;

grant select on table
  public.v2_projects,
  public.v2_plan_items,
  public.v2_current_changes,
  public.v2_prompt_versions,
  public.v2_checks,
  public.v2_project_facts,
  public.v2_build_turns,
  public.v2_recovery_cases,
  public.v2_generation_attempts,
  public.v2_learner_evidence,
  public.v2_user_preferences
to service_role;

grant select, insert, update, delete on table
  public.v2_projects,
  public.v2_plan_items,
  public.v2_current_changes,
  public.v2_prompt_versions,
  public.v2_checks,
  public.v2_project_facts,
  public.v2_build_turns,
  public.v2_generation_attempts,
  public.v2_recovery_cases,
  public.v2_learner_evidence,
  public.v2_user_preferences
to codize_v2_executor;

revoke all privileges on sequence public.v2_build_turns_sequence_no_seq
  from public, anon, authenticated, service_role, codize_v2_executor;
grant usage, select on sequence public.v2_build_turns_sequence_no_seq to codize_v2_executor;

alter default privileges in schema public
  revoke all privileges on tables from public, anon, authenticated, service_role;
alter default privileges in schema public
  revoke all privileges on sequences from public, anon, authenticated, service_role;
-- Hosted Supabase projects add schema-scoped EXECUTE defaults for the Data API
-- roles. Remove those separately because per-schema defaults are additive.
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated, service_role;
-- PostgreSQL also grants EXECUTE to PUBLIC in its ordinary global defaults. A
-- schema-scoped revoke cannot subtract that global privilege.
alter default privileges for role postgres
  revoke execute on functions from public;
alter default privileges for role codize_v2_executor
  revoke execute on functions from public, anon, authenticated, service_role;

revoke execute on function
  public.v2_valid_text_array(text[], integer, integer, integer, boolean),
  public.v2_system_fact_source_matches(uuid, uuid, text, text, text, text, boolean, numeric, text[], text, uuid),
  public.v2_change_completion_is_eligible(uuid),
  public.v2_touch_updated_at(),
  public.v2_guard_projects(),
  public.v2_guard_plan_items(),
  public.v2_guard_current_changes(),
  public.v2_guard_prompt_versions(),
  public.v2_guard_checks(),
  public.v2_validate_fact_source(),
  public.v2_guard_project_facts(),
  public.v2_assert_fact_supersession(),
  public.v2_guard_build_turns(),
  public.v2_guard_generation_attempts(),
  public.v2_guard_recovery_cases(),
  public.v2_validate_learner_source(),
  public.v2_guard_learner_evidence(),
  public.v2_guard_user_preferences(),
  public.v2_assert_deleted_after_fk_cleanup(),
  public.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text),
  public.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text),
  public.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid),
  public.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint),
  public.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text),
  public.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb),
  public.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb),
  public.purge_v2_project(uuid, uuid, bigint, text, jsonb)
from public, anon, authenticated, service_role;

grant usage, create on schema public to codize_v2_executor;
grant usage, create on schema codize_v2_internal to codize_v2_executor;
grant usage on schema codize_v2_internal to service_role;

revoke execute on function
  codize_v2_internal.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text),
  codize_v2_internal.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text),
  codize_v2_internal.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid),
  codize_v2_internal.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint),
  codize_v2_internal.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text),
  codize_v2_internal.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb),
  codize_v2_internal.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb),
  codize_v2_internal.purge_v2_project(uuid, uuid, bigint, text, jsonb)
from public, anon, authenticated, service_role;

alter function codize_v2_internal.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text)
  security definer;
alter function codize_v2_internal.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text)
  security definer;
alter function codize_v2_internal.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid)
  security definer;
alter function codize_v2_internal.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint)
  security definer;
alter function codize_v2_internal.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text)
  security definer;
alter function codize_v2_internal.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb)
  security definer;
alter function codize_v2_internal.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb)
  security definer;
alter function codize_v2_internal.purge_v2_project(uuid, uuid, bigint, text, jsonb)
  security definer;

alter function codize_v2_internal.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text)
  owner to codize_v2_executor;
alter function codize_v2_internal.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text)
  owner to codize_v2_executor;
alter function codize_v2_internal.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid)
  owner to codize_v2_executor;
alter function codize_v2_internal.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint)
  owner to codize_v2_executor;
alter function codize_v2_internal.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text)
  owner to codize_v2_executor;
alter function codize_v2_internal.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb)
  owner to codize_v2_executor;
alter function codize_v2_internal.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb)
  owner to codize_v2_executor;
alter function codize_v2_internal.purge_v2_project(uuid, uuid, bigint, text, jsonb)
  owner to codize_v2_executor;

revoke create on schema public from codize_v2_executor;
revoke create on schema codize_v2_internal from codize_v2_executor;
grant execute on function
  public.v2_valid_text_array(text[], integer, integer, integer, boolean),
  public.v2_system_fact_source_matches(uuid, uuid, text, text, text, text, boolean, numeric, text[], text, uuid),
  public.v2_change_completion_is_eligible(uuid)
to codize_v2_executor;

grant execute on function
  codize_v2_internal.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text),
  codize_v2_internal.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text),
  codize_v2_internal.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid),
  codize_v2_internal.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint),
  codize_v2_internal.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text),
  codize_v2_internal.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb),
  codize_v2_internal.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb),
  codize_v2_internal.purge_v2_project(uuid, uuid, bigint, text, jsonb)
to service_role;

grant execute on function
  public.mutate_v2_plan(uuid, uuid, bigint, bigint, uuid, jsonb, bigint, text, uuid, text),
  public.accept_v2_prompt_version(uuid, uuid, uuid, bigint, bigint, uuid, text, uuid, text, text, uuid, text, text, text, text),
  public.handoff_v2_prompt_version(uuid, uuid, uuid, uuid, uuid, bigint, bigint, uuid),
  public.resume_v2_recovery_handoff(uuid, uuid, uuid, uuid, uuid, bigint, bigint, bigint),
  public.open_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, uuid, text, text, text, text, uuid, text),
  public.transition_v2_recovery_case(uuid, uuid, uuid, uuid, bigint, bigint, text, jsonb),
  public.complete_v2_current_change(uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb),
  public.purge_v2_project(uuid, uuid, bigint, text, jsonb)
to service_role;

-- Drop migration-time ownership authority only after every executor-owned
-- function privilege has been configured.
revoke codize_v2_executor from current_user;

comment on table public.v2_projects is
  'Codize V2 project root. Separate from and does not reinterpret public.projects.';
comment on function public.complete_v2_current_change(
  uuid, uuid, uuid, bigint, bigint, bigint, uuid, boolean, text, text, jsonb, jsonb
) is 'Backend-only atomic V2 Current Change completion transaction.';
comment on function public.purge_v2_project(uuid, uuid, bigint, text, jsonb) is
  'Backend-only privacy-minimizing V2 Project purge transaction.';
