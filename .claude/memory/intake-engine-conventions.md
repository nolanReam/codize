# Intake engine conventions (Milestone 6)

The five intake questions in `backend/app/services/intake_service.py` are
**spec-verbatim** — including Q4's odd phrasing "On a scale of honest to
honest: …", which is literally what the master spec says (with its three fixed
options). Do not "fix" the wording. Q1 is the Yeager purpose question and must
never become "What do you want to build?".

Classification seam: the future temperature-0 LLM classification call replaces
exactly `_derive_classification_signals` (the keyword fallback that produces
the two tiebreaker booleans). `template_service.resolve_archetype` is the
spec-fixed mapping and never changes. The spec's classification prompt is
inline in the spec ("How Archetype Matching Works") — it is NOT one of the six
prebuild prompt files.

Storage seam: intake logic depends on the `ProjectRepository` protocol
(`services/project_repository.py`). The Supabase implementation talks to
PostgREST with the service-role key, so **ownership lives in every query**
(`user_id=eq.{sub}` filters — the PATCH filters on id AND user_id). Tests
override the FastAPI dependency `get_project_repository` with
`tests/fakes.py::InMemoryProjectRepository`. **Live PostgREST reads/writes are
unverified** (built without env vars in the M6 session) — exercise them in the
first session with `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` set.

Status transition decision: completing intake sets `intake_completed_at` +
`archetype_id` but leaves `projects.status = 'intake'`; the roadmap milestone
(M7) flips it to 'active' when the roadmap is generated.

**M13E.1 update (2026-07-05):** `submit_answer` now allows revising an
already-answered question until `intake_completed_at` is set (student
back/edit). First-time answers remain strictly sequential (an unanswered
question is only accepted when it is the expected next one — gaps are still
impossible), completion still requires all five, and after completion nothing
is editable. Classification runs on the final stored answers at completion,
so pre-completion edits are always consistent. The frontend pairs this with
an explicit "Finish intake" review step (no auto-complete after Q5).
