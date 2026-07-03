-- M9 Interrogation Gate: gate_sessions needs passed_at alongside failed_at
-- (instructions: set passed_at when passed, failed_at when failed; failed_at
-- keeps driving the 30-minute cooldown).
alter table public.gate_sessions add column passed_at timestamptz;

-- gate_sessions grants are column-level (score stays revoked from clients);
-- new columns are not granted automatically, so grant read on passed_at to
-- keep the owner-read-only contract: students can see their result timestamps
-- but never the score.
grant select (passed_at) on public.gate_sessions to authenticated;
