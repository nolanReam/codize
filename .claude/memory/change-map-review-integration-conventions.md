# Change Map → Review integration conventions (Milestone 16A.1)

**Purpose:** prevention-first, recovery-capable. A reviewed Change Map reduces
the Review Board's blank-page work, but never replaces student judgment.
Change Map asks whether a description accurately represents what appears to
have changed. Review separately asks what the student thinks about that
implementation and what should happen next. Change Map confirmation is never
implementation approval; every linked Review target starts `pending`.

**Persistence and compatibility:** linked Review reuses
`projects.workflow_artifacts[phase]["review_board"]`, the existing section and
JSONB column. No migration/table/parallel store. `ReviewBoardArtifact` remains
the byte-compatible M13B manual write schema. `StoredReviewBoardArtifact`
adds optional source timestamps + targets, so old artifacts and current
frontend payloads still validate/load/save. Legacy/manual reads retain their
old shape; linked reads are additive. The generic Review PUT remains.

**Explicit initialization:** authenticated
`POST /workflow/{phase}/review/from-change-map` accepts no body or only
`{"replace_existing": bool}`. `review_service.create_from_change_map` loads
the owner-scoped active project once, validates the roadmap phase, then uses
`workflow_service.get_change_map` and the typed
`change_map_service.confirmed_items` / `unresolved_items` helpers. It requires
a present, confirmed, non-import-stale map with no pending items. It never
loads raw Implementation Import, calls a provider, executes code, or reaches
Evidence/Verification/gates/reports.

**Category filtering and ordering:** only implementation-relevant categories
become targets, in fixed priority order, then original Change Map order:
`behavior_change`, `implementation_decision`, `out_of_scope_change`,
`security_sensitive_area`, `unresolved_risk`, `unverified_behavior`.
`changed_file` is context, not automatically a decision; a
`question_to_understand` remains a Change Map prompt. Rejected and pending
items never enter. Student-added items preserve `origin=student_added`.
Uncertain/needs-inspection items are not discarded: they enter cautiously as
`source_resolution=unresolved` with their exact source decision.

**Stable source snapshot and ids:** each target stores the minimum reviewed
statement (`change_text`, ≤600 and secret-guarded), Change Map item id,
category/origin/student-decision snapshot, and source resolution. It never
copies raw import, references/excerpts, prompts, hidden reasoning, or complete
Change Map JSON. `review_target_id = "rv-" +
sha256("codize-review-target-v1\n" + change_map_item_id)[:12]`: deterministic,
no timestamp, server-generated only.

**Human-owned Review decisions:** exact values are `pending`, `keep`,
`revise`, `remove`, `needs_verification`, `uncertain`. None means correct,
safe, approved, or verified. `revise` requires student rationale or a proposed
revision. `review_decision`, `student_rationale`, and `student_revision` are
student-owned. All source linkage/provenance/snapshots/ids/timestamps and
computed stale state are server-owned.

**Safe updates:** existing `PUT /workflow/{phase}/review_board` accepts the
unchanged manual payload plus additive `target_updates` of only target id +
the three student-owned fields. Linked updates locate server-issued ids and
copy every source field from stored targets; forged source binding, targets,
timestamps, ids, categories, origins, source decisions/text/resolution,
initialized flag, or stale flag gets 422. Manual fields keep full-section
replacement semantics. Omitting target updates preserves linked decisions.

**Overwrite rule:** any existing Review value — empty, manual/legacy, linked,
or completed — blocks initialization with 409. Only deliberate
`replace_existing=true` replaces it, resets every linked decision to pending,
and clears old manual Review fields. One active Review only; no merge,
version history, or silent overwrite. Sibling workflow sections and the
Change Map remain unchanged.

**Version binding and staleness:** linked Review stores the source Change Map
`generated_at` + `confirmed_at`. `review_service.review_is_stale` derives the
flag on every read; stale when the current map is missing/corrupt/draft,
import-stale, regenerated, reconfirmed, or has different binding timestamps.
Stale is never stored/client-supplied. A stale Review remains readable and its
snapshots remain the statements reviewed then; no silent rewrite/merge.
Explicit reinitialization rebinds to the current confirmed map.

**Read and progress:** the existing `GET /workflow/{phase}` remains the only
GET. `sections.review_board` exposes linked targets/binding/decisions and
computed `initialized_from_change_map=true` + `stale`. Helpers
`pending_review_targets`, `reviewed_target_count`, and `review_complete` are
Review-specific only — never build-task, N/5 workflow, Change Map, gate, or
Project Defense progress. An empty linked target set is not called complete.

**Ownership and isolation:** user id comes only from the verified JWT;
project id/user id are never accepted from clients. ProjectRepository queries
remain owner-filtered, phase numbers are checked against the owned roadmap,
and writes touch only that phase's `workflow_artifacts` map. Another user or
phase cannot read/update/initialize the Review.

**No downstream integration in M16A.1:** linked target fields are ignored by
the unchanged M14 Review normalizer; no target text enters Defense Context,
Project Defense, evaluator, gate PASS/FAIL/cooldown, Evidence, Verification,
or Defense Report. No frontend file/type/API client/page changes.

**Exact M16A.2 frontend seam:** call
`POST /workflow/{phase}/review/from-change-map` (normal no body; replacement
only after explicit UI confirmation), consume `GET /workflow/{phase}` →
`sections.review_board` (`review_targets`, bindings, initialized, stale), and
save decisions through existing `PUT /workflow/{phase}/review_board` using
`target_updates: [{review_target_id, review_decision, student_rationale,
student_revision}]` plus the existing manual fields when retained. Never echo
server-owned target/source fields in the PUT.

**Exact M16B backend seam:** load a typed `StoredReviewBoardArtifact`, then
call `review_service.needs_verification_targets(review) ->
list[NeedsVerificationReviewTarget]`. Each result contains review target id,
Change Map item id, reviewed effective-text snapshot, student rationale, and
category. M16A.1 creates no Verification checks.

**M16A.2 frontend consumer (built 2026-07-13):** `/app/phase/review` consumes
the exact additive read shape without converting manual artifacts. No artifact
shows Change Map prerequisites and an explicit Start Review action; current
linked artifacts show grouped server snapshots plus student decisions; stale
linked artifacts remain readable and disabled until an explicitly confirmed
replacement. `lib/review.ts` canonicalizes the PUT from active student fields,
so hidden revision/rationale never causes dirty state or reaches the server.
Draft compatibility uses the source binding plus ordered target ids—never source
text—and sits inside the existing authenticated-user draft namespace. Progress
is target decisions only and never changes workflow N/5. Completion navigation
opens `/app/phase/verify` but creates no suggestions, checks, Evidence, Defense,
or report data. See [[linked-review-ui-conventions]].

**Exact M16B frontend seam after M16A.2:** the saved, current linked artifact is
available from the existing workflow GET as `sections.review_board`; the future
Verification surface may request a server-owned suggestion handoff only after
explicit student action, keyed by the saved Review target references. It must
not derive tests from Change Map text in the browser, read raw imports, or treat
`needs_verification` as a completed check. `/app/phase/verify` currently receives
navigation only and has no Review-prefill code.

**M16B.1 backend consumer (built 2026-07-13):**
`verification_service.create_from_review` loads this typed saved Review,
requires it complete/current/non-stale, and calls ONLY
`review_service.needs_verification_targets(review)`. Each returned target gets
one deterministic category template and server `vt-...` id; pending/keep/
revise/remove/uncertain never enter. The linked Verification binding includes
this Review's saved timestamp, source Change Map timestamps, and an ordered
identity/decision fingerprint, so later Review changes make Verification stale
without rewriting either artifact. Review source text/rationale is copied only
for needs-testing targets; raw import, Change Map references, full Review JSON,
and non-needs target snapshots are absent. A suggestion is proposed work, never
a performed result, proof, Evidence, or automatic pass. Exact conventions:
[[review-verification-integration-conventions]].
