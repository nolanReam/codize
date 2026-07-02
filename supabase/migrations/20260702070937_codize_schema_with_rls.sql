-- Codize Milestone 2: core schema with RLS.
-- Every table gets RLS enabled and its policies in this same migration, so no
-- table is ever live without RLS (spec Security Constraint 2).
-- Architecture note: the frontend talks only to the FastAPI backend, which uses
-- the service role (bypasses RLS). These policies are defense-in-depth against
-- direct use of the public anon key.

-- ---------------------------------------------------------------------------
-- Helper: keep updated_at current
-- ---------------------------------------------------------------------------
create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- profiles — one row per auth user, auto-created on signup.
-- last_login_at drives the Yeager reconnection modal (login delta > 72h).
-- ---------------------------------------------------------------------------
create table public.profiles (
  user_id       uuid primary key references auth.users (id) on delete cascade,
  display_name  text,
  last_login_at timestamptz not null default now(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles_select_own" on public.profiles
  for select to authenticated using (auth.uid() = user_id);
create policy "profiles_insert_own" on public.profiles
  for insert to authenticated with check (auth.uid() = user_id);
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Auto-create a profile when a user signs up.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (user_id) values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- projects — one row per student project. Stores the five mandatory intake
-- answers (purpose, scope, stack, self-assessment, timeline), the archetype
-- classification, the personalized roadmap JSON, phase progress, and the gate
-- history summary used to calibrate future gates.
-- ---------------------------------------------------------------------------
create table public.projects (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references auth.users (id) on delete cascade,
  -- The five mandatory intake answers, in question order. intake_purpose is
  -- the verbatim answer to Q1 and is re-shown by the reconnection modal.
  intake_purpose         text,
  intake_scope           text,
  intake_stack           text,
  intake_self_assessment text,
  intake_timeline        text,
  intake_completed_at    timestamptz,
  archetype_id           smallint check (archetype_id in (1, 2, 3)),
  stack_warning          text,
  roadmap                jsonb,
  current_phase          smallint not null default 1 check (current_phase between 1 and 7),
  gate_history_summary   text,
  status                 text not null default 'intake' check (status in ('intake', 'active', 'completed')),
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create index projects_user_id_idx on public.projects (user_id);

alter table public.projects enable row level security;

create policy "projects_select_own" on public.projects
  for select to authenticated using (auth.uid() = user_id);
create policy "projects_insert_own" on public.projects
  for insert to authenticated with check (auth.uid() = user_id);
create policy "projects_update_own" on public.projects
  for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "projects_delete_own" on public.projects
  for delete to authenticated using (auth.uid() = user_id);

create trigger projects_set_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- gate_sessions — one row per Interrogation Gate attempt (shape pinned by the
-- roadmap). turns holds the transcript as a JSONB array. failed_at drives the
-- 30-minute cooldown (gate start checks now() - failed_at > interval '30 minutes').
-- OWNER READ-ONLY BY DESIGN: verdicts, scores, and transcripts are written only
-- by the backend (service role); students must not write their own results, so
-- there are deliberately no insert/update/delete policies.
-- The score column is revoked from client roles below: functional unlock
-- thresholds must not be observable by the student (spec: variable reward).
-- ---------------------------------------------------------------------------
create table public.gate_sessions (
  id               uuid primary key default gen_random_uuid(),
  project_id       uuid not null references public.projects (id) on delete cascade,
  phase_id         smallint not null check (phase_id between 1 and 7),
  user_id          uuid not null references auth.users (id) on delete cascade,
  anchor_statement text,
  turns            jsonb not null default '[]'::jsonb,
  score            smallint check (score between 0 and 10),
  passed           boolean,
  reason           text,
  failed_at        timestamptz,
  created_at       timestamptz not null default now()
);

create index gate_sessions_project_phase_idx on public.gate_sessions (project_id, phase_id);
create index gate_sessions_user_id_idx on public.gate_sessions (user_id);

alter table public.gate_sessions enable row level security;

create policy "gate_sessions_select_own" on public.gate_sessions
  for select to authenticated using (auth.uid() = user_id);

-- Column-level lockdown: clients may read their own gate rows but never the
-- score. Backend (service role) retains full access.
revoke all on public.gate_sessions from anon, authenticated;
grant select (id, project_id, phase_id, user_id, anchor_statement, turns,
              passed, reason, failed_at, created_at)
  on public.gate_sessions to authenticated;

-- ---------------------------------------------------------------------------
-- unlocks — functional unlocks granted by the backend when hidden performance
-- thresholds are met (e.g. score >= 7 across two consecutive gates).
-- OWNER READ-ONLY BY DESIGN: only the backend grants unlocks; students can see
-- what they unlocked but never trigger or forge one, so no write policies.
-- ---------------------------------------------------------------------------
create table public.unlocks (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  project_id   uuid not null references public.projects (id) on delete cascade,
  phase_number smallint not null check (phase_number between 1 and 7),
  unlock_key   text not null,
  granted_at   timestamptz not null default now(),
  unique (project_id, unlock_key)
);

create index unlocks_user_id_idx on public.unlocks (user_id);

alter table public.unlocks enable row level security;

create policy "unlocks_select_own" on public.unlocks
  for select to authenticated using (auth.uid() = user_id);

revoke insert, update, delete on public.unlocks from anon, authenticated;

-- anon (unauthenticated) gets nothing on any Codize table.
revoke all on public.profiles, public.projects, public.unlocks from anon;
