# Verification → Evidence handoff conventions (Milestone 16B.3A)

**Permanent distinction:** a Codize-suggested check, a student-performed check,
a student-recorded result, a student-selected Evidence target, student-provided
Evidence, and a student explanation that Evidence is unavailable are separate
states. Pass is not proof. Fail can have useful Evidence. Skipped/N/A/unrecorded
are not performed. Unavailable is not Evidence and never means verified.

**Eligibility and preview:** authenticated pure
`GET /workflow/{phase}/evidence/from-verification` loads the owned active project
and real roadmap phase, then the server-saved typed Verification and the single
`verification_service.evidence_handoff_targets(...)` seam. Missing and manual
Verification are controlled 200 states. Current linked previews preserve every
target in source order with pass/fail/skipped/not_applicable/unrecorded result,
notes, effective check, performed flag, and server eligibility. Only current
pass/fail are eligible. Stale previews preserve context but make every target
ineligible. The response omits Review/Change Map ids, raw bindings,
fingerprints, timestamps, raw import, and provider data. GET never writes,
creates Evidence, or calls a provider.

**Explicit initialization:** `POST` on the same route requires 1–20 unique
well-formed Verification target ids. Unknown, skipped, N/A, and null targets get
422; missing/manual/stale Verification and existing Evidence get 409. Request
order is normalized to stored Verification order. The server creates only
empty `not_addressed` targets—no entries, explanation, unavailable reason,
evidenced flag, completion, URL, screenshot, log, proof, or result-to-Evidence
copy. `replace_existing=true` is the only deliberate destructive rebuild;
there is no auto-replace, merge, deletion, reattachment, or history.

**Persistence and manual compatibility:** linked Evidence reuses
`projects.workflow_artifacts[phase]["evidence"]`; no migration/table/store.
Legacy `EvidenceArtifact(entries, summary)` and its full-replace PUT/read shape
remain intact. A linked `StoredEvidenceArtifact` adds internal initialization,
Verification binding, and selected targets. Existing manual work is never
converted or overwritten without explicit replacement. Linked writes and all
other workflow writes still touch only the one JSONB column and preserve phase
siblings.

**Server-owned provenance:** each stored target has deterministic `ev-...` id,
source Verification/Review/Change Map ids, category, effective-check snapshot,
pass/fail snapshot, result-notes snapshot, and artifact binding. The client view
gets only the Evidence target id, source Verification target id, safe source
context, and student fields. Review/Change Map ids and fingerprints stay
internal. Normal PUT schemas reject client attempts to send provenance,
snapshots, binding, initialization, stale, completion, or full target objects.

**Student-owned state:** linked Evidence PUT `target_updates` may change only
Evidence target id + `evidence_status`, `entries`, `explanation`, and
`unavailable_reason`. `evidence_recorded` needs at least one existing
`EvidenceEntry`; `evidence_unavailable` needs a bounded reason and must have no
entries/explanation; `not_addressed` has no student content. Duplicate target
updates and duplicate entries fail. The aggregate phase target entry cap remains
20; entries keep the existing nine kinds, 8k content cap, http(s) URL/7–40 hex
rules, and 30 KB request belt. New Evidence text rejects empty normalized
content and unsafe controls while retaining tab/newline/CR for logs. The shared
four-marker secret seatbelt is reused; detected values are rejected without
echo/logging. Unicode limits are code points, never bytes; nothing truncates.

**Completion:** computed `evidence_record_complete` means at least one selected
target exists and every selected target is either recorded with an entry or
unavailable with a reason. It means “Evidence record addressed,” never
implementation correct/proved/verified. Unselected Verification targets are
not evidenced and are irrelevant to linked Evidence completion.

**Binding and stale behavior:** the server binds to Verification
`initialized_at`, a hash of its Review binding, and a deterministic hash of the
selected target ids/linkage/category/effective check/result/result notes. A
selected context change, source identity change, missing/corrupt/stale
Verification, or Verification rebuild makes Evidence stale. Unselected target
updates and neighboring workflow-section changes do not. Stale student Evidence
and unavailable reasons remain readable and unchanged; normal linked edits are
409. Only explicit POST replacement rebinds, and it intentionally resets the
single current linked record without merge/history.

**Ownership and downstream boundary:** routes take identity only from verified
JWT, repository reads/writes remain user-filtered, roadmap phase validation is
server-side, and M16S.1 prevents direct browser JSONB writes. No content is
logged. M16B.3A changes no gate, evaluator, Defense, Report, navigation, or
frontend product code. Existing Defense/Report normalizers continue reading
only legacy top-level entries/summary; nested linked Evidence is deliberately
absent until M16C.

**Exact M16B.3B frontend seam:** preview with the GET; trust server eligibility;
let the student deliberately choose eligible ids; POST selection only after an
explicit action; apply the returned artifact; save changed student fields only
through generic Evidence PUT. Preserve manual mode and every result label.
Explicit rebuild may send `replace_existing=true` only after warning that old
linked/manual Evidence is replaced. Never auto-create/prefill, read local
Verification drafts, derive proof, or echo server provenance.

**Exact M16C backend seam:** from an already-owned project call
`evidence_service.get_stored_evidence(project, phase_number)` and use
`evidence_service.evidence_is_stale(...)`. Build a new bounded safe downstream
view containing only student-recorded target entries/explanations and explicit
unavailable reasons, with their honest source-result context. Exclude internal
bindings/Review/Change Map ids, do not treat result snapshots as Evidence, and
do not silently include stale linked work as current. Wire that purpose-built
view into Defense Context and the Report contract only in M16C.
