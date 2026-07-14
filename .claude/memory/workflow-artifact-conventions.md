# Workflow artifact conventions (Milestone 13B)

The store is a COLUMN, not a table: `projects.workflow_artifacts` jsonb,
default `{}`, migration `20260703130000` — the exact `task_progress`
precedent (see [[phase-workspace-conventions]]). Shape, backend-owned:
`{"<phase_number>": {"prompt_builder": {…}, "review_board": {…},
"evidence": {…}, "verification": {…}}}`. M13B originally inherited broad
table grants for `authenticated`; owner RLS isolated rows but still let an
owner directly replace the owner's JSONB through PostgREST. M16S.1 corrects
that integrity gap with forward migration `20260714064425`: authenticated
clients retain table `SELECT` plus owner RLS and have no project mutation
privileges; the trusted FastAPI credential and owner-filtered repository retain
writes. See [[workflow-artifact-write-boundary]].

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
`GET /workflow/{phase}` always returns all section keys (null when unset).
Sections are `prompt_builder`, `review_board`, `evidence`, `verification`
(M13B; the v3 loop's plan inputs live inside prompt_builder.inputs; a
reflection section was deliberately not added — smallest useful MVP) plus
`implementation_import` (M15A — see
[[implementation-import-conventions]]; registering a new section is ONE
`SECTION_MODELS` entry, the routes/service/ownership are generic; its M15B
frontend page is [[implementation-import-ui-conventions]] — frontend counts
now say "N/5 captured"). Unknown
section names 404 WITHOUT echoing the submitted name (reflected-input
caution); unknown keys in stored data are dropped on read (corruption
defense, like task_progress).

Validation is fail-closed at the boundary (`schemas/workflow.py`):
`extra="forbid"` everywhere, per-string caps (300/2000/8000), list caps,
URL kinds must be http(s) ≤ 2048, commit_hash must be 7–40 hex, verification
check ids are a fixed 8-item enum (unique per save), plus a per-section
serialized-body belt checked before model validation (30 KB default;
100 KB for implementation_import via `_SECTION_CHAR_LIMITS` — per-field caps
stay authoritative, the belt only rejects grossly oversized bodies). Every free-text field
rejects secret-looking content (`sb_secret_`, `sk-or-`, `AIza`, `-----BEGIN `)
— a deliberate short marker list protecting students from persisting a real
key into their own evidence; don't grow it into a scanner.

Eligibility reuses `phase_service.load_active_project` and the M13B-public
`phase_service.require_phase(project, n)` (the seam-publicizing pattern from
M11/M12). CORS note: M13B added "PUT" to main.py's allow_methods — the first
PUT route in the API; removing it breaks browser calls in M13C.

M15C.1: the Change Map lives in the SAME column as a SIBLING key
(`workflow_artifacts[phase]["change_map"]`) but is NOT a section — not in
SECTION_MODELS (generic PUT 404s on it), filtered out of `_stored_sections`
(so it can never reach the defense context), returned TOP-LEVEL by
`GET /workflow/{phase}` (never inside `sections`, protecting the "N/5
captured" counts). Its dedicated routes register BEFORE the generic section
PUT in routers/workflow.py — moving them below breaks
`PUT /workflow/{n}/change-map`. See [[change-map-conventions]].

M15C.2 frontend rule: `WorkflowPhaseState.change_map` mirrors that top-level
key and `useWorkflowSection` carries it from the SAME existing GET alongside
the requested section. `WorkflowSteps` displays Change Map after Bring Back
with its own not-created/draft/reviewed/stale status, but it has `section=null`
and can never contribute to `Object.values(sections)`—phase and cockpit remain
exactly N/5 captured. The Change Map page uses only its three dedicated routes;
it never calls the generic section PUT and never sends server-owned provenance.
See [[change-map-ui-conventions]].

M16A.1 keeps Review in the SAME existing section key and JSONB column — no
table, migration, parallel persistence system, or duplicate GET. A linked
Review is a backward-compatible `review_board` artifact with additive
`source_change_map_generated_at`, `source_change_map_confirmed_at`, and
bounded `review_targets`. `GET /workflow/{phase}` runs only this section
through `review_service.review_board_view` so linked artifacts gain computed
`initialized_from_change_map=true` + `stale`; legacy/manual artifacts retain
their exact M13B read shape. `POST /workflow/{phase}/review/from-change-map`
is the explicit deterministic initializer. The existing generic Review PUT
still accepts its old payload, plus `target_updates`; review_service patches
only student decision/rationale/revision and copies every source field from
storage. The PUT remains full-replace for legacy manual fields. Review writes
still merge one phase key and touch only `workflow_artifacts`; sibling
sections + Change Map survive. No linked target/source text enters the
Defense Context output — the existing Review normalizer continues to select
only its legacy student-authored fields from `stored_sections`. See
[[change-map-review-integration-conventions]].

M16A.2 is a frontend consumer only. The shared `GET /workflow/{phase}` and
generic Review PUT remain the sole read/save system; the explicit initializer's
artifact response is applied back into `useWorkflowSection`, not a second store.
Frontend linked saves send only changed `target_updates`; manual saves keep the
M13B shape. The presence of any `review_board` value still contributes exactly
one captured artifact to `Object.values(sections)`, regardless of target count,
progress, completion, or stale state. Change Map remains top-level and excluded,
so cockpit/phase progress stays N/5. See [[linked-review-ui-conventions]].

M16B.1 keeps Verification in the SAME existing `verification` section and
JSONB column—no table, migration, parallel store, duplicate GET, or frontend
change. `VerificationArtifact` remains the byte-compatible M13B manual write
shape (`checks + explanation`). `StoredVerificationArtifact` adds an optional
Review binding, initialization time, and linked targets; manual reads retain
their exact old shape. Explicit
`POST /workflow/{phase}/verification/from-review` is the only initializer and
accepts replacement intent only. `GET /workflow/{phase}` computes linked
`initialized_from_review=true` + `stale`. The generic Verification PUT still
accepts the old frontend payload and adds student-only `target_updates`; the
service copies ids/source snapshots/category/suggestion/binding/timestamps and
stale authority from storage. A linked artifact still contributes exactly one
captured section to N/5 regardless of target count or stale state. Linked
source/suggestion fields are ignored by the existing Defense Context
normalizer and do not reach Project Defense. See
[[review-verification-integration-conventions]].

M16B.2 is a frontend consumer only. It adds no persistence route or store:
normal initialization uses the M16B.1 POST, reads the resulting linked/manual
mode through the shared workflow GET, and saves changed student fields through
the existing generic Verification PUT. `useWorkflowSection` now exposes the
already-fetched `sections` object so Verification can inspect its Review
prerequisite without a duplicate client or request system; applying/saving an
artifact keeps that local sections snapshot synchronized. Linked PUT bodies
contain only `target_updates` with Verification target id + student check,
result, and notes. Manual payloads remain the M13B full-section shape. Any
Verification artifact still contributes exactly one of five captured sections,
independent of target count, recorded progress, or stale state. Continue to
Evidence is navigation only and creates no downstream record. See
[[linked-verification-ui-conventions]].

M16B.3A keeps Evidence in that SAME existing section/key/JSONB column—no
migration, table, parallel store, or automatic handoff. Manual `entries +
summary` reads/PUTs remain exact. Linked Evidence is created only by explicit
`POST /workflow/{phase}/evidence/from-verification` selection after a pure
preview GET; only current saved linked pass/fail results qualify. The generic
Evidence PUT gains student-only target updates while source Verification/
Review/Change Map linkage, snapshots, ids, binding, initialization, completion,
and stale state stay server-owned. `GET /workflow/{phase}` uses the curated
`evidence_service.evidence_view`; raw `stored_sections` still feeds the existing
Defense normalizer, which intentionally reads only legacy top-level entries and
summary, so nested linked Evidence does not enter Defense/Report before M16C.
See [[verification-evidence-handoff-conventions]].
