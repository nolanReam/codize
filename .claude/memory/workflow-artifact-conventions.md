# Workflow artifact conventions (Milestone 13B)

The store is a COLUMN, not a table: `projects.workflow_artifacts` jsonb,
default `{}`, migration `20260703130000` — the exact `task_progress`
precedent (see [[phase-workspace-conventions]]). Shape, backend-owned:
`{"<phase_number>": {"prompt_builder": {…}, "review_board": {…},
"evidence": {…}, "verification": {…}}}`. Projects grants are table-level for
`authenticated` and the owner RLS policies cover the row, so the migration
needed no grant/policy work — verified live in M13B (owner reads the column
through PostgREST with a real JWT; cross-user reads return zero rows).

STORAGE ONLY is the load-bearing constraint: `workflow_service` takes only
the ProjectRepository (cannot reach gates/unlocks/profiles by construction),
a write patches exactly the `workflow_artifacts` key, and there is no LLM
import anywhere in the module (tested by source inspection + route-level
provider-explosion test). The Interrogation Gate does NOT read these
artifacts — making the gate evidence-aware is a future spec-guardian-reviewed
change with its own adversarial-testing round, not a quiet extension (see
[[gate-conventions]], [[product-vision-v3]]). Since M14A the read seam
`workflow_service.stored_sections(project, phase_number)` (public wrapper,
read-only) feeds the defense context builder — which normalizes/redacts/
bounds artifact content for FUTURE M14B use without touching the gate (see
[[defense-context-conventions]]). The Project Defense Report has
no backend endpoint: M13C assembles it client-side from `GET /workflow/{phase}`
plus the existing evaluation/phases/unlocks/gate routes.

API semantics: `PUT /workflow/{phase}/{section}` is an idempotent
FULL-SECTION REPLACE (no merge); the server stamps `saved_at` on each write;
`GET /workflow/{phase}` always returns all four section keys (null when
unset). Sections are exactly the four instruction-pinned names —
`prompt_builder`, `review_board`, `evidence`, `verification` (the v3 loop's
plan inputs live inside prompt_builder.inputs; a reflection section was
deliberately not added — smallest useful MVP). Unknown section names 404
WITHOUT echoing the submitted name (reflected-input caution); unknown keys in
stored data are dropped on read (corruption defense, like task_progress).

Validation is fail-closed at the boundary (`schemas/workflow.py`):
`extra="forbid"` everywhere, per-string caps (300/2000/8000), list caps,
URL kinds must be http(s) ≤ 2048, commit_hash must be 7–40 hex, verification
check ids are a fixed 8-item enum (unique per save), plus a 30 KB
total-section cap checked before model validation. Every free-text field
rejects secret-looking content (`sb_secret_`, `sk-or-`, `AIza`, `-----BEGIN `)
— a deliberate short marker list protecting students from persisting a real
key into their own evidence; don't grow it into a scanner.

Eligibility reuses `phase_service.load_active_project` and the M13B-public
`phase_service.require_phase(project, n)` (the seam-publicizing pattern from
M11/M12). CORS note: M13B added "PUT" to main.py's allow_methods — the first
PUT route in the API; removing it breaks browser calls in M13C.
