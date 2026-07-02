-- Milestone 2: remove the legacy (non-Codize) schema that previously occupied
-- this project. All tables were empty (0 rows) and the wipe was approved by the
-- project owner on 2026-07-02. Codize schema is created in the next migration.

-- Legacy trigger on auth.users (would break signups once public.users is gone)
drop trigger if exists on_auth_user_created on auth.users;

-- Legacy event trigger (auto-enabled RLS on new tables; replaced by explicit
-- per-table statements in the Codize schema migration)
drop event trigger if exists ensure_rls;

-- Legacy tables (dependency order handled by cascade)
drop table if exists
  public.session_summaries,
  public.student_concept_mastery,
  public.concept_mastery_snapshots,
  public.lane_attempts,
  public.intervention_flags,
  public.reflections,
  public.review_attachments,
  public.reviews,
  public.predictions,
  public.case_progress,
  public.session_participants,
  public.sessions,
  public.prediction_gates,
  public.case_concept_weights,
  public.case_lanes,
  public.cases,
  public.memberships,
  public.organizations,
  public.student_profiles,
  public.users
cascade;

-- Legacy functions
drop function if exists public.handle_new_auth_user() cascade;
drop function if exists public.is_instructor() cascade;
drop function if exists public.is_volunteer_or_instructor() cascade;
drop function if exists public.update_updated_at_column() cascade;
drop function if exists public.rls_auto_enable() cascade;

-- Legacy enum types
drop type if exists
  public.user_role,
  public.difficulty_lane,
  public.case_status,
  public.session_status,
  public.case_progress_state,
  public.review_type,
  public.flag_reason,
  public.lane_type
cascade;
