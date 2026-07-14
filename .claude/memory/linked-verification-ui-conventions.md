# Linked Verification UI conventions (Milestone 16B.2)

**Permanent semantic boundary:** Review records “I need to test this.” Codize
then suggests a grounded check. The student performs a check outside Codize and
records a result. Evidence is supporting material. None of those states may be
collapsed: a suggestion is not performed, passed, proof, or independent Codize
verification; a student-recorded result is not automatically proof.

**One route, two modes:** use `/app/phase/verify`. A strict runtime guard for
the additive M16B.1 shape (`initialized_from_review=true`, Review binding,
server stale flag, linked targets) selects linked UI. Any existing manual
artifact keeps the original fixed checklist, explanation, result-specific
notes, `verification:<phase>` draft, generic PUT, errors, and save behavior.
Manual work is never silently converted. Starting over from Review is secondary
and requires a replacement warning.

**Explicit initialization and prerequisites:** nothing initializes on mount.
No Review → Complete Review first; pending Review → Finish every item; stale
Review → Update Review first; current complete saved linked Review → Create
Verification checks from Review. The Start button alone calls
`POST /workflow/{phase}/verification/from-review` with no body. A concurrent
409 refetches and displays the existing artifact. First initialization uses a
stable announced preparation state. No provider, prompt, LLM, browser-derived
suggestion, or client suggestion logic exists.

**Target rendering:** group only populated categories in backend order:
behavior changes, implementation decisions, possible out-of-scope changes,
areas to review carefully, unresolved risks, behavior still needing testing.
Preserve order inside each group. Each row separates From your Review, optional
saved rationale, immutable Suggested check, editable Check you will perform,
Your result, and conditional What happened notes. Source/rationale/suggestion
are plain React text with whitespace/wrapping; never HTML, Markdown, inferred
links, raw imports, extra Change Map excerpts, internal ids, bindings,
timestamps, prompts, or provider data.

**Student check and results:** `student_check` is optional; blank means the
server suggestion remains the effective check. “Use suggested check” copies the
displayed server suggestion into the editable field. Text caps use Python-style
Unicode code-point counts at 2,000 with visible counters and blockers—never
`maxLength` clipping. Native fieldset/radio choices are null/Not recorded yet,
pass/Passed, fail/Failed, skipped/Skipped, and
not_applicable/Not applicable. Pass means this check observed expected behavior,
not total correctness. Fail is useful recorded information. Skipped means not
performed. N/A means the check does not fit. Neither skipped nor N/A is pass.
Result notes remain optional under the backend contract; changing a result
clears the old result-specific note so contradictory hidden text cannot survive.

**Safe save and dirty state:** use the existing generic
`PUT /workflow/{phase}/verification`. The linked payload contains changed
`target_updates` only: server-issued `verification_target_id` plus normalized
`student_check`, exact result/null, and active normalized `result_notes`. Never
echo Review/Change Map ids, category, source snapshots/rationale, suggestion,
binding, initialization time, stale, or metadata. Dirty state compares this
canonical payload against the server artifact. Hidden notes normalize to null;
unchanged/reverted/server-saved forms are clean. A 422 or network error keeps
the mounted form and local draft; success remains on-page, announces
“Verification saved,” reconciles from the response, and clears the draft.

Keep the save acknowledgement through the matching returned server revision;
clear it only after a later revision, rebuild/reload, or student edit.

**Draft scope:** reuse `useDraft` and its authenticated-user key prefix, 400ms
debounce, storage-failure tolerance, and four-marker secret guard. Surface is
`linked_verification:active-project:<phase>:<fingerprint>`; the current
one-project account contract supplies project scope until a safe project id is
client-visible. The fingerprint hashes initialization identity, Review binding,
and ordered Verification target ids—never source text. Stored draft data is
only fingerprint + target ids + student check/result/notes. Exact ids and
fingerprint must match. Stale or rebuilt/rebound work rejects and clears the
incompatible draft. Manual drafts remain separate.

**Progress, completion, and zero targets:** primary progress is `N of M checks
recorded`, where every explicit result is recorded. A separate accessible
summary keeps Recorded, Passed, Failed, Skipped, Not applicable, and Unperformed
counts. Never show a correctness percentage or score. Recorded completion
requires at least one generated target, an explicit outcome for every target,
valid active fields, and a clean server-saved form. It may include failures,
skips, and N/A; copy says “Verification results recorded,” never implementation
verified. A valid zero-target artifact shows no Review items marked Needs
testing, never 0/0 passed or completion, and offers Review decisions plus
Continue to Evidence.

**Stale and replacement:** server stale is read-only. Keep old checks/results
visible but disable edits and save. Primary stale action is Rebuild Verification
from current Review. The inline confirmation states that targets, edited
checks, results, and notes will be replaced; only its final action sends
`replace_existing=true`. A current rebuild lives under More options. Failed
replacement keeps old work and unsaved form mounted. Success applies the server
artifact, invalidates the old draft, and never merges results or builds history.

**Guided navigation and progress:** Build Loop Verification distinguishes
unavailable, ready to start, in progress, results recorded, stale, and no checks
requested. Phase next action stays Review for missing/incomplete/stale Review,
then Start Verification, Continue Verification, Rebuild Verification, or
Continue to Evidence. Existing manual Verification keeps its evidence-first
behavior. Continue to Evidence is navigation only: no Evidence creation,
prefill, attachment, or completion. Verification still contributes one section
to workflow N/5 regardless of targets/progress/stale; build tasks, Change Map,
Review, Evidence, Defense, and phase advancement remain separate.

**Accessibility and responsive:** one page h1; category h3s; native
fieldset/legend/radios; visible label focus; field errors wired through
`aria-describedby`; text plus color for stale/result meaning; loading, save,
result, and recorded-completion live regions; keyboard-native disclosures and
inline replacement warning. Long source/check/note text wraps. The standard
rail collapses at 1150px; linked surface padding, result summary, radio grid,
field actions, and primary buttons stack at 640px; 390px has no page overflow.
The existing reduced-motion rule applies.

**Exact M16B.3B frontend seam after M16B.3A:** on the existing
`/app/phase/evidence` surface, explicitly call
`GET /workflow/{phase}/evidence/from-verification`. Render its server-derived
missing/manual/current/stale state and all result outcomes; allow selection only
where `eligibility=eligible`. After an explicit student action, POST
`{selected_verification_target_ids, replace_existing?}` to the same route.
Consume the returned curated linked Evidence artifact through the existing
workflow state and save only changed
`target_updates: [{evidence_target_id, evidence_status, entries, explanation,
unavailable_reason}]` via the generic Evidence PUT. Do not derive eligibility,
send Review/Change Map ids or bindings, auto-run on navigation, read
Verification drafts, copy result notes into Evidence, or treat unavailable as
Evidence. Existing manual mode remains unchanged.

**Exact M16C backend seam:** load typed linked Evidence with
`evidence_service.get_stored_evidence(project, phase_number)`, require
`initialized_from_verification` and server-derived non-stale state, then add a
purpose-built safe normalizer for student-recorded target entries and explicit
unavailable reasons. Do not feed internal bindings/ids or promote result
snapshots into Evidence. M16B.3A intentionally leaves Defense Context and the
client-assembled Report without linked Evidence: Defense treats linked Evidence
as missing, while Report remains on legacy top-level `entries + summary`.
