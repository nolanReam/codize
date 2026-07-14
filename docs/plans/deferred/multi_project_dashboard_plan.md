> [!WARNING]
> ## Status: Deferred architecture plan
>
> This document records the repository architecture as audited during M13E.1.
>
> Re-audit all repository, ownership, project-resolution, API, RLS, and
> frontend assumptions before implementation.
>
> This document is not current implementation authority.
>
> Current code, tests, migrations, Git history, and accepted architecture
> decisions override stale details in this plan.

# Multi-Project & Dashboard Plan (audited M13E.1, 2026-07-05)

Status: **multiple projects are DEFERRED.** The M13E.1 dashboard improvement
ships single-project honestly (clear current project, "Continue project", a
disabled "+ New project" affordance labelled as planned). Nothing pretends to
be multi-project.

## Audit: what the system assumes today

Answered against the code as of M13E.1 (routes in `backend/app/routers/`,
services in `backend/app/services/`).

### Does the backend support multiple projects per user?

**Storage: yes. API: no.** The `projects` table has no uniqueness constraint
on `user_id` — a user *could* have many rows. But the entire API surface
resolves "the project" as **the newest row**:
`ProjectRepository.get_project(user_id)` is
`GET /projects?user_id=eq.X&order=created_at.desc&limit=1`
(`project_repository.py`). There is no `list_projects`, no project-id
parameter on any route, and no way to address an older row.

### Does it support multiple active projects?

No. Every service loads "the" project via that same seam:

- **Intake** (`intake_service`) — starts a project implicitly on Q1's answer;
  a second project would need `create_project` to be reachable again, and it
  isn't once a project exists (answers go to the newest row forever).
- **Roadmap / phases / workflow artifacts** (`roadmap_service`,
  `phase_service.load_active_project`, `workflow_service`) — all operate on
  the newest row only.
- **Gate** (`gate_service`) — `gate_sessions` rows carry a `project_id`, so
  the *data* is project-scoped, but session lookup starts from the singular
  current project.
- **Unlocks** (`unlock_service`) — keyed by `project_id` (unique
  `(project_id, unlock_key)`), so data is fine; the query path assumes the
  one current project.
- **Evaluation** (`evaluation_service`) — computed from the one current
  project.
- **Reconnection** (`reconnection_service`) — `profiles.last_login_at` is
  **per user, not per project**. With several projects "away 72h+" would need
  a per-project notion of activity that doesn't exist.

### Do routes assume "current project" instead of a project id?

Yes, universally. `/intake/*`, `/roadmap/*`, `/phases/*`, `/workflow/*`,
`/gate/*`, `/unlocks`, `/evaluation`, `/reconnection` — none take a project
id. The frontend (`lib/api.ts`) mirrors this exactly.

### What would break if a second project were created today?

The moment a second `projects` row exists, it becomes "the project"
(newest-first) and the first project **silently disappears** from every
surface: its roadmap, task progress, workflow artifacts, gate history, and
unlocks all still exist in the DB but are unreachable. Evaluation and
reconnection would describe the new project. Nothing errors — which is worse
than erroring. This is why M13E.1 must not add a working "+ New project"
button.

## Safest implementation plan (a future milestone, ~M14-sized)

Backend first, in one milestone; frontend in the same or the next:

1. **Repository seam**: add `list_projects(user_id)` and
   `get_project_by_id(user_id, project_id)` (ownership-filtered like every
   existing query). Keep `get_project` for back-compat during migration.
2. **Project selection, not route explosion**: keep all existing routes
   unchanged and add a single "active project" pointer — either a
   `profiles.active_project_id` column (one tiny migration, RLS already
   covers profiles) or an explicit `/projects/{id}/activate` route writing
   it. Every service swaps `get_project(user_id)` for "the active project".
   This avoids rewriting 8 routers to take `{project_id}` and avoids breaking
   the frontend API client.
3. **New routes**: `GET /projects` (id, purpose, archetype, status,
   current_phase — client-safe fields only) and `POST /projects` (creates an
   empty row and activates it, so intake Q1 targets it; intake's implicit
   create remains for first-time users).
4. **Reconnection**: keep `last_login_at` per user (spec's 72h trigger is
   about the *user* being away); the summary simply describes the active
   project. No change needed beyond wording.
5. **Invariants to re-verify**: RLS on projects already ownership-scoped
   (unchanged); gate cooldown is derived per project's sessions (fine);
   unlock recompute is per project (fine); evaluation is per project (fine).
6. **Frontend**: cockpit lists projects with the active one first, "+ New
   project" becomes real, switching projects calls activate then reloads.
7. **Tests**: repository fakes grow `list/activate`; every service test adds
   a two-project isolation case (project B's data never leaks into project
   A's views).

Explicitly out of scope even then: per-project deletion/archival, sharing,
templates from past projects.

## Why deferred now

M13E.1 is a usability pass. The change above touches every service's project
resolution and needs its own test round; bolting a partial version on would
create exactly the fragile half-system instructions.md forbids.
