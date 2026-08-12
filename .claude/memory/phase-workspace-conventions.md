# Phase workspace conventions (Milestone 8)

> [!WARNING]
> **Current/legacy V1 product or lifecycle record.** Use this file only to understand or maintain the implemented V1 subsystem. It is not V2 product or architecture authority.

Persistence decision: task completion lives in `projects.task_progress` jsonb
(migration `20260703015217_add_task_progress_to_projects.sql`), shape
`{"<phase_number>": ["ai-1", "human-2", ...]}` — completed ids only. It is a
COLUMN, not a new table, and deliberately OUTSIDE the `roadmap` jsonb so
ticking tasks can never mutate the fixed roadmap structure (the M7 validator
still passes on the stored roadmap after any number of task updates —
tested). `phase_service.set_task_completion` PATCHes only `task_progress`.

Task ids are `ai-<n>` / `human-<n>`, 1-based indexes into the phase's
`ai_appropriate_tasks` / `human_required_tasks`. Stable because the roadmap is
immutable after generation. Unknown ids in stored progress are dropped on
read (corruption defense), and a service write rewrites that phase's list
clean.

`projects.current_phase` is the student's position and is advanced ONLY by a
passed Interrogation Gate (implemented in M9 — `gate_service.evaluate_gate`
is the single writer) — never by task completion; the gate, not the
checklist, completes a phase. `GET /phases/current` reads it. Since M9,
`phase_service.load_active_project` is public and shared with the gate
service as the one eligibility check.

Eligibility for every workspace call: intake complete + archetype + roadmap +
status 'active' (all four checked; not-ready → 409, unknown phase/task → 404).
Since M11, `current_phase_view(project)` is public — the reconnection service
builds its summary from it after loading the project once itself. Since M12,
`incomplete_tasks(phase_view)` is also public here (moved from reconnection's
private helper) — shared by the reconnection and evaluation services (see
[[evaluation-conventions]]). Since M13B, `require_phase(project, n)` is public
too — the workflow artifact store scopes artifacts to real roadmap phases
with it (see [[workflow-artifact-conventions]]).

No LLM call in the workspace: the stored roadmap already carries the
personalized phase content, so `phase_explanation.md` prose generation is
deliberately NOT wired up (deferred until a milestone needs streamed prose).
When it is wired up, temperature is 0.7 per `prompts/README.md` and it must go
through `llm_service`.
