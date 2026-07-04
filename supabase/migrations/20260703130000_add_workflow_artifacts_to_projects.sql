-- Milestone 13B (workflow artifact store): student-authored v3 Build Loop
-- artifacts (Prompt Builder, Review Board, Evidence Panel, Verification Lab),
-- phase-scoped. Lives OUTSIDE the roadmap jsonb so storing artifacts can never
-- mutate the fixed roadmap structure. Shape (backend-owned):
--   {"<phase_number>": {"prompt_builder": {...}, "review_board": {...},
--                       "evidence": {...}, "verification": {...}}}
-- Same ownership model as every other projects column (task_progress
-- precedent): RLS owner policies already cover the row, projects grants are
-- table-level for authenticated, and the backend's service-role queries
-- filter by user_id.
alter table public.projects
  add column workflow_artifacts jsonb not null default '{}'::jsonb;
