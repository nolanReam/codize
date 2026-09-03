-- PostgREST resolves JSON RPC payloads against function argument names. The
-- public wrappers added for setup and Phases 4-6 originally declared only
-- argument types, so otherwise-correct named backend payloads could not match.
--
-- PostgreSQL permits adding names to previously unnamed input parameters with
-- CREATE OR REPLACE FUNCTION. This preserves each function identity, owner,
-- dependencies, and existing ACL while avoiding a drop/recreate availability
-- gap. The restricted ACL and hardened wrapper properties are still reasserted
-- explicitly below.

create or replace function public.save_v2_setup_draft(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid,
  p_project_context text,
  p_initial_change_label text,
  p_done_condition text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.save_v2_setup_draft($1,$2,$3,$4,$5,$6,$7)
$$;

create or replace function public.establish_v2_manual_project(
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
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.establish_v2_manual_project($1,$2,$3,$4,$5,$6,$7,$8)
$$;

create or replace function public.confirm_v2_manual_current_change(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.confirm_v2_manual_current_change($1,$2,$3,$4,$5)
$$;

create or replace function public.record_v2_manual_return(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_outcome text,
  p_check_id uuid
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_manual_return($1,$2,$3,$4,$5,$6,$7)
$$;

create or replace function public.record_v2_manual_check(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_check_id uuid,
  p_expected_current_change_version bigint,
  p_expected_check_version bigint,
  p_command_id uuid,
  p_result text,
  p_observation text,
  p_performed_by_student boolean,
  p_next_check_id uuid
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_manual_check(
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11
  )
$$;

create or replace function public.update_v2_dialogue_sound(
  p_owner_user_id uuid,
  p_expected_version bigint,
  p_dialogue_sound_enabled boolean
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.update_v2_dialogue_sound($1,$2,$3)
$$;

create or replace function public.disclose_v2_teaching_help(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_context text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.disclose_v2_teaching_help($1,$2,$3,$4,$5,$6)
$$;

create or replace function public.record_v2_teaching_response(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_context text,
  p_response text,
  p_elicitation text,
  p_support_level text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_teaching_response(
    $1,$2,$3,$4,$5,$6,$7,$8,$9
  )
$$;

create or replace function public.record_v2_effort_attempt(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_selected text,
  p_recommended text,
  p_appropriate boolean
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_effort_attempt($1,$2,$3,$4,$5,$6,$7,$8)
$$;

create or replace function public.create_v2_student_check_plan(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_check_id uuid,
  p_check_plan text,
  p_elicitation text,
  p_support_level text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.create_v2_student_check_plan(
    $1,$2,$3,$4,$5,$6,$7,$8,$9
  )
$$;

create or replace function public.update_v2_prompt_draft_with_risk(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_expected_current_change_version bigint,
  p_expected_prompt_draft_version bigint,
  p_prompt_draft text,
  p_done_condition_snapshot text,
  p_boundary_snapshots text[],
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_risk_input_fingerprint text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.update_v2_prompt_draft_with_risk(
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12
  )
$$;

create or replace function public.record_v2_recovery_symptom(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_observed_symptom text,
  p_last_known_working_statement text,
  p_last_known_working_certainty text,
  p_investigation_prompt text,
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_risk_input_fingerprint text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_recovery_symptom(
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14
  )
$$;

create or replace function public.record_v2_recovery_investigation_return(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_finding text,
  p_correction_summary text,
  p_correction_prompt text,
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_risk_input_fingerprint text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_recovery_investigation_return(
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13
  )
$$;

create or replace function public.record_v2_recovery_correction_return(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_expected_current_change_version bigint,
  p_command_id uuid,
  p_check_id uuid,
  p_check_plan text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_recovery_correction_return(
    $1,$2,$3,$4,$5,$6,$7,$8
  )
$$;

create or replace function public.record_v2_recovery_check(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_current_change_id uuid,
  p_recovery_case_id uuid,
  p_check_id uuid,
  p_expected_current_change_version bigint,
  p_expected_check_version bigint,
  p_command_id uuid,
  p_result text,
  p_observation text,
  p_performed_by_student boolean,
  p_next_check_id uuid,
  p_investigation_prompt text,
  p_risk text,
  p_risk_reason_key text,
  p_risk_policy_version text,
  p_risk_input_fingerprint text
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select codize_v2_internal.record_v2_recovery_check(
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17
  )
$$;

revoke all on function
  public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text),
  public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  public.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  public.update_v2_dialogue_sound(uuid,bigint,boolean),
  public.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  public.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  public.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  public.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  public.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text),
  public.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text),
  public.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text),
  public.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text),
  public.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text)
from public, anon, authenticated;

grant execute on function
  public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text),
  public.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text),
  public.confirm_v2_manual_current_change(uuid,uuid,uuid,bigint,uuid),
  public.record_v2_manual_return(uuid,uuid,uuid,bigint,uuid,text,uuid),
  public.record_v2_manual_check(uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid),
  public.update_v2_dialogue_sound(uuid,bigint,boolean),
  public.disclose_v2_teaching_help(uuid,uuid,uuid,bigint,uuid,text),
  public.record_v2_teaching_response(uuid,uuid,uuid,bigint,uuid,text,text,text,text),
  public.record_v2_effort_attempt(uuid,uuid,uuid,bigint,uuid,text,text,boolean),
  public.create_v2_student_check_plan(uuid,uuid,uuid,bigint,uuid,uuid,text,text,text),
  public.update_v2_prompt_draft_with_risk(uuid,uuid,uuid,bigint,bigint,text,text,text[],text,text,text,text),
  public.record_v2_recovery_symptom(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text,text),
  public.record_v2_recovery_investigation_return(uuid,uuid,uuid,uuid,bigint,uuid,text,text,text,text,text,text,text),
  public.record_v2_recovery_correction_return(uuid,uuid,uuid,uuid,bigint,uuid,uuid,text),
  public.record_v2_recovery_check(uuid,uuid,uuid,uuid,uuid,bigint,bigint,uuid,text,text,boolean,uuid,text,text,text,text,text)
to service_role;

notify pgrst, 'reload schema';
