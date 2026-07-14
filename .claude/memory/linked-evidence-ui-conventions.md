# Linked Evidence UI conventions

M16B.3B is a frontend-only consumer of the reviewed M16B.3A contract. The
existing `/app/phase/evidence` route and shared workflow store remain the one
surface and persistence path. No backend, schema, provider, prompt, Defense,
Report, gate, evaluator, or broad navigation behavior changes here.

**Modes and initialization.** Strict `initialized_from_verification=true`
artifacts use linked mode. Legacy `entries + summary` artifacts keep the
original manual UI and draft key. A malformed artifact that claims linked mode
fails closed as an invalid linked state instead of falling back to manual.
When no linked artifact is mounted, use the pure preview GET for the
server-derived missing/manual/current/stale state. Never POST on mount, derive
eligibility, read local Verification drafts, or infer from result labels.
Eligible pass/fail targets are selectable only because the server marks them
eligible. Start with zero checked targets. Skipped, not-applicable, unrecorded,
and other ineligible targets stay visible in a secondary native disclosure.
The explicit initializer POST contains only selected Verification target ids.

**Source versus student work.** Each target renders its category, saved check,
result, and optional result notes as read-only plain text in one quiet source
region above the editable Evidence fields. A result or note is context, never
an Evidence entry and never proof. Student status is exactly not addressed,
add supporting Evidence, or Evidence unavailable. Recorded status requires at
least one of the existing nine entry kinds and may include an explanation.
Unavailable requires a reason and canonically excludes entries/explanation. Not addressed
canonically excludes all student content. React text rendering and safe-link
checks preserve hostile text as text; only valid http(s) URLs become links.

**Validation and writes.** Mirror the reviewed backend boundaries without
silently clipping: 20 selected targets, 20 aggregate entries, 8,000 code points
per entry content, 2,000 per explanation/reason, existing URL and 7–40 hex
rules, unsafe-control rejection, duplicate-entry rejection, and the 30,000
Python-style JSON code-point request belt. Counters count Unicode code points.
Build canonical active-field-only target updates, compare them with the saved
artifact, and send changed targets only. Never echo eligibility, snapshots,
source ids beyond the Evidence target reference, binding, initialization,
stale, completion, or whole target objects. A 422/network failure keeps the
mounted form and draft. Success reconciles from the response, acknowledges the
save, and clears the draft.

**Drafts.** Reuse `useDraft` with surface
`linked_evidence:active-project:<phase>:<fingerprint>`; authenticated user scope
comes from the hook and `active-project` reflects the current one-project
contract. The safe fingerprint hashes initialization/binding identity and
ordered Evidence target ids, never source text. Stored draft data contains the
fingerprint, target ids, and student-owned status/entries/explanation/reason
only. Exact identity must match. Stale, rebuilt, or rebound artifacts reject
and clear incompatible drafts. The shared debounce, storage-failure tolerance,
secret-marker guard, successful-save clearing, and manual-draft separation
remain intact.

**Progress and completion.** Primary progress is `N of M targets addressed`,
computed from server-saved target states rather than unsaved local choices.
An accessible summary distinguishes recorded, unavailable, and not addressed;
there is no pass rate, correctness score, evidenced percentage, or proof
claim. Completion appears only when the returned server artifact says
`evidence_record_complete=true` and the form is clean. Copy says the Evidence
record is complete, never that the implementation is verified/correct. The
next action is a neutral Project Home link; linked Evidence does not enter
Defense or Report in M16B.3B.

**Stale and replacement.** Stale linked Evidence stays fully readable but all
student controls and Save are disabled. Rebuild first fetches the current
preview and starts with zero selected targets while old Evidence remains
mounted. The inline warning states that prior linked/manual Evidence is
replaced; only its final explicit action sends `replace_existing=true`. Failed
replacement preserves old work and unsaved state. Success applies a fresh
not-addressed artifact whose new fingerprint makes the old draft incompatible,
and never merges or creates history. Current manual/linked replacement lives
under secondary options.

**Navigation and accessibility.** Workflow Evidence status distinguishes
unavailable, ready, in progress, complete, and stale from the server contract;
section presence still contributes exactly one of N/5 and never ticks build
tasks. Phase next actions use Start/Continue/Rebuild Evidence or Evidence
record complete without jumping to Defense. Keep one h1, semantic
fieldset/legend/radio/checkbox controls, visible focus, associated errors,
text-plus-color status, live loading/save/completion announcements, native
disclosures, and long-text wrapping. The rail collapses at the existing
breakpoint; selection rows, radio grids, entry controls, and actions stack at
640px; 390px must have no horizontal overflow; reduced-motion rules remain.

**Exact M16C seams.** Backend: from the already-owned project call
`evidence_service.get_stored_evidence(project, phase_number)`, require
`initialized_from_verification`, and determine currency with
`evidence_service.evidence_is_stale(...)`. Add a bounded purpose-built safe
downstream normalizer containing student-recorded entries/explanations and
explicit unavailable reasons with honest source-result context. Exclude
bindings, Review/Change Map ids, and result snapshots as Evidence; do not
silently present stale linked work as current. Wire that curated view into
Defense Context and a Report contract only in M16C. Frontend: consume only that
new curated backend shape for Defense readiness/context and Report rendering;
do not parse raw nested Evidence/provenance, keep unavailable distinct from
Evidence, and mark or exclude stale linked work according to the backend
contract.
