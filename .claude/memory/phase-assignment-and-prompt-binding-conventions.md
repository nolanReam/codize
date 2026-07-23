# Phase Assignment and Prompt Binding Conventions

M18B.2 adds one concrete unit of current-phase work without restoring Phase Workspace or creating a second lifecycle.

## Authority and storage

- `GET /phases/current/assignment` returns the authoritative explicit selection or a deterministic recommendation.
- `PUT /phases/current/assignment` accepts only a stable phase-local roadmap `task_id`; task text, ownership, completion, phase, and rationale remain server-owned.
- Explicit selection is stored in the existing `projects.task_progress` JSONB under `_phase_assignments["<phase>"]`. It stores the task id, whether a completed task was deliberately selected for revisit, and a server-derived roadmap fingerprint. No migration is involved.
- Selection and task completion use bounded optimistic compare-and-swap writes. They preserve one another and every neighboring task-progress key; a conflict that does not settle fails safely with 409.
- A roadmap fingerprint mismatch, missing/malformed task, or phase change invalidates the selection. The client receives an explicit invalidation flag and a fresh current-phase recommendation; no position or text matching is used.

## Recommendation and ownership

- Recommendation order is the earliest incomplete AI-appropriate task, then the earliest incomplete student-owned task, then phase-complete/no-valid-task.
- Ownership labels are exactly `Use AI` and `You decide`.
- Student-owned tasks never receive a Prompt Builder action. Selection never marks a task complete.
- Completing the selected task recommends the next incomplete task while preserving the old Prompt/draft binding. A completed task becomes selected again only through the explicit revisit control.

## Project Home and Continue

- Project Home is still the sole orientation dashboard. The assignment surface appears above the secondary phase checklist and chooser.
- The chooser exposes current-phase tasks only, keeps completed revisits secondary, and performs no write when merely opened.
- Continue remains the shared lifecycle authority. Assignment affects Continue only when Prompt Builder is genuinely the next missing step; stale workflow repair and Defense lifecycle states retain their established priority.

## Prompt binding and preservation

- New Prompt saves may include `assignment_task_id`. The backend accepts it only when it matches the explicitly selected current-phase `Use AI` task.
- Prompt association is optional for legacy compatibility. Absence of metadata is shown as legacy/unassigned, never fabricated or called stale.
- When a Prompt is saved for a different assignment, the prior Prompt moves to the server-owned `prompt_history` sibling in the same phase map. The history is bounded and validated; clients cannot submit it through the generic Prompt payload.
- Bound Prompt saves use optimistic workflow-artifact replacement so concurrent sibling writes survive.
- Prompt Builder shows the real assignment before generic starters. `Use this assignment` selects it but does not prefill the Task field. M18C.1's explicit scope application writes the student's finish and inspection conditions into Task and the student's exclusion into Don't touch; Context and all other fields remain untouched.
- Local Prompt drafts use `prompt_builder:<phase>:assignment:<task_id>`, still nested under the authenticated user draft key. The old `prompt_builder:<phase>` draft remains readable as an explicit legacy draft seam.
- Local scope drafts use a separate assignment- and objective-version-scoped surface. They participate in the same existing switch warning; no second confirmation is introduced.
- Switching assignments never merges drafts. Project Home warns when the current assignment has unsaved or saved Prompt work; cancel performs no write, and confirmation preserves the old work under its original binding.

## Product boundaries

- Assignment is not completion, workflow progress, phase advancement, an AI answer, or a provider call.
- Roadmap, task completion, workflow artifacts, Change Map, Defense, and Report semantics remain separate.
- Expected provider calls added by this milestone: zero.
