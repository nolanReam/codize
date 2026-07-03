-- Milestone 8 (phase workspace): per-phase task completion state.
-- Progress lives OUTSIDE the roadmap jsonb so the fixed roadmap structure is
-- never mutated by marking tasks complete. Shape (backend-owned):
--   {"<phase_number>": ["ai-1", "human-2", ...]}  — completed task ids only.
-- Same ownership model as every other projects column: RLS owner policies
-- already cover the row; the backend's service-role queries filter by user_id.
alter table public.projects
  add column task_progress jsonb not null default '{}'::jsonb;
