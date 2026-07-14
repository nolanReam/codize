# Review → Verification integration conventions (Milestone 16B.1)

**Purpose and permanent semantic boundary:** prevention-first,
recovery-capable. A saved Review decision `needs_verification` means "I need to
test this." Linked Verification turns it into a proposed check. It never means
the check ran, passed, proved correctness, created Evidence, or verified the
source claim. M16B.1 initializes every result as null/unperformed and never
creates pass/fail/skipped/not_applicable/verified/approved automatically.

**Persistence and legacy compatibility:** linked Verification reuses
`projects.workflow_artifacts[phase]["verification"]`, the existing section and
JSONB column. No migration/table/parallel store. `VerificationArtifact` remains
the M13B manual write schema (`checks` from the fixed eight ids, completed
result enum, optional explanation). `StoredVerificationArtifact` adds optional
`initialized_at`, `source_review_binding`, and `verification_targets`; old
artifacts and the current frontend payload still validate/load/save/display.
Legacy/manual reads retain their exact old shape; linked reads are additive.

**Explicit initialization only:** authenticated
`POST /workflow/{phase}/verification/from-review` accepts no body or only
`{"replace_existing": bool}`. Nothing runs when Review saves/completes, a phase
loads, or the student navigates to Verification. The service loads the owned
active project, validates the roadmap phase, then requires a present, linked,
saved, complete, current, non-stale Review. Manual Review gets a safe 409; it is
never parsed as linked. Source content comes ONLY from the typed
`review_service.needs_verification_targets(review)` seam—never raw Review JSON,
Implementation Import, or Change Map excerpts.

**Exact filtering/order:** only saved `needs_verification` decisions enter.
pending/keep/revise/remove/uncertain are excluded; pending also prevents Review
completion. The helper's existing deterministic Review order is preserved.
Zero needs-testing targets intentionally succeeds with a linked artifact whose
target list and legacy checks list are empty. It is not called complete and no
fake check is created.

**Category-aware no-LLM suggestions:** one explicit registry covers exactly
behavior_change, implementation_decision, out_of_scope_change,
security_sensitive_area, unresolved_risk, unverified_behavior. Templates embed
the bounded effective Review text and ask the beginner to perform/inspect the
relevant behavior and record observations. Security wording asks cautiously
for intended/authorized plus appropriate restricted behavior without claiming
a vulnerability or giving exploit steps. No Gemini/OpenRouter/stub provider,
prompt, model output, code execution, browser automation, or invented project
identifier/outcome exists.

**Target identity/source snapshot:** each target stores deterministic
`verification_target_id = "vt-" +
sha256("codize-verification-target-v1\n" + review_target_id)[:12]`, Review
target id, Change Map item id, six-category value, bounded reviewed effective
text, optional saved student rationale, deterministic suggestion, plus nullable
student check/result/notes. Duplicate Verification/Review/Change Map ids fail
closed. Raw import, Change Map references, provider data, full Review JSON, and
non-needs target text are never copied.

**Source binding/staleness:** the server stores source Change Map generated_at
and confirmed_at, Review saved_at, and a SHA-256 fingerprint of ordered Review
target ids/Change Map ids/categories/decisions. Raw text is not the primary
version key. `verification_is_stale` derives state on every read; linked work is
stale when Review is missing/corrupt/manual/stale/incomplete/rebuilt/re-saved,
its binding or relevant decision/target membership/identity changes, or the
needs-testing target order differs. Stale work remains readable and unchanged;
the client cannot clear stale. Deliberate replacement rebinds to current Review.

**Overwrite rule:** any existing Verification value—manual, linked, completed,
empty, or corrupt—blocks initialization with 409. Only explicit
`replace_existing=true` replaces the one active artifact; this deliberately
clears old manual checks and linked student results and creates no merge,
history, or multiple active versions. Sibling workflow sections remain intact.

**Student-owned update protection:** existing
`PUT /workflow/{phase}/verification` accepts the unchanged manual payload. For
a linked artifact, additive `target_updates` may contain only server-issued
Verification target id plus nullable `student_check`, exact existing result
value, and `result_notes`. All source ids/category/text/rationale/suggestion,
binding/timestamps/initialized/stale fields are absent from write schemas and
copied server-side. Unknown/duplicate ids and forged fields get 422. Manual
artifacts reject target updates. The current 30 KB request belt remains; future
UI should send changed target updates, not echo the full server object.

**Result honesty/helpers:** null means no result recorded. Existing result
meanings are unchanged: pass=student performed and observed expected behavior
(not total proof); fail=performed and observed a mismatch; skipped=not
performed; not_applicable=does not apply. `pending_targets` returns null-result
targets; `completed_targets` returns performed pass/fail only;
`failed_targets` returns fail; `unresolved_targets` returns everything not pass.
Skipped/N/A never count as pass.

**Ownership/isolation/privacy:** identity comes only from verified JWT; no user,
project, or workspace id is accepted. ProjectRepository remains owner-filtered,
phase validation uses the owned roadmap, writes touch only that phase's
workflow_artifacts column, and another user cannot read/update/initialize or
infer owner state. No source/rationale/suggestion/result note/raw payload is
logged. Linked fields are ignored by the unchanged Defense Context normalizer;
no Evidence, Project Defense, Report, evaluator, gate, cooldown, or roadmap
integration exists.

**Exact M16B.2 frontend seam:** after the student explicitly asks to create
suggestions, call `POST /workflow/{phase}/verification/from-review` (normal no
body; explicit destructive replacement only after confirmation). Consume
`GET /workflow/{phase}` → `sections.verification` for linked/manual mode,
targets, suggestions, source Review context, student fields, binding, and
server stale. Save only changed
`target_updates: [{verification_target_id, student_check, result,
result_notes}]` through the existing generic Verification PUT. Never derive
checks in the browser, echo server fields, or equate suggestion with result.

**Implemented M16B.3A Evidence seam:** the typed helper remains the only
Verification → Evidence derivation. `evidence_service.handoff_preview` calls it
and exposes a curated view of every outcome; only current saved pass/fail
results are eligible. Explicit `create_from_verification` selects helper target
ids and stores empty linked Evidence records with internal Review/Change Map
linkage and snapshots—never student Evidence. Skipped/N/A/null remain visible
but ineligible. See [[verification-evidence-handoff-conventions]].

**M16B.2 frontend consumer (2026-07-14):** the existing
`/app/phase/verify` route now implements the seam above without changing this
backend contract. Initialization remains click-only; linked/manual modes remain
separate; source snapshots, rationale, and suggestions render as escaped plain
text; and only canonical changed student fields are sent in `target_updates`.
Null stays unrecorded. Explicit pass/fail/skipped/not_applicable outcomes all
count toward recorded workflow completion, while the summary and copy preserve
their distinct meanings. Linked local drafts carry only a safe fingerprint,
target id, student check, result, and notes. Stale work is readable but not
editable and replacement is deliberate. Zero targets remain neutral. Evidence
navigation creates and prefills nothing; the typed M16B.3 backend handoff above
is still unused.

**M16C.1 downstream use:** linked Review and Verification now enter Defense
and Report only through `workflow_context_service`. Review decisions/rationale/
revision and exact Verification result states remain separate; internal ids,
bindings, and fingerprints never cross. Stale linked records are labeled stale
rather than rewritten. Verification pass remains a student-recorded result,
never Evidence or proof.
