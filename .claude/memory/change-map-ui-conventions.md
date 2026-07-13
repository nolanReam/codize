# Change Map UI conventions (Milestone 15C.2)

**Purpose and framing:** prevention-first, recovery-capable. The page teaches
the default habit: use AI → bring back what changed → review Codize's draft →
correct it → preserve uncertainty honestly → confirm that the map was
reviewed. Recovery uses the same page through one collapsed "Already in a
patch loop?" rail note; it never assumes the student failed or lost control.
User-facing route/name: `/app/phase/change-map`, **Review Your Change Map**.

**Page architecture:** one dominant `.card.primary` workspace plus quiet
category sections and a collapsed `GuideCard` rail. Only populated categories
render, in the fixed backend order. Items are rows separated by rules—not
nested cards. Top copy is two short thoughts: Codize drafted what appears to
have changed; this is a draft, not proof. The eight labels are Changed files,
Behavior changes, Implementation decisions, Possible out-of-scope changes,
Areas to review carefully, Unresolved risks, Behavior still needing testing,
and Questions you should understand.

**Generate and failure states:** no import → Bring Back action; saved import +
no map → explicit **Create Change Map**; generation never runs on mount. Normal
generation omits the body. Loading is one calm live-region state with no fake
percent/countdown. A 502 gets fixed student-safe copy, preserves the saved
import/current map, and offers **Try again** + **Review imported material**;
provider names, model errors, prompts, validation internals, raw output, and
unsupported identifiers never render. There is no automatic retry.

**Provenance and uncertainty:** AI items say **Codize draft**; student items say
**Added by you**. Student decisions are Looks right (`confirmed`), I need to
correct it (`edited`), Not accurate or not relevant (`rejected`), I'm not sure
(`uncertain`), and I need to inspect this (`needs_inspection`). Pending is
untouched, not selectable. AI uncertainty is a separate quiet label: Clearly
supported by the imported material, The imported material is unclear, or Needs
a closer look. `supported` is never "verified"; no numeric confidence exists.
Corrections preserve the original draft and keep line breaks. Rejected items
remain visible with an explicit exclusion note. Uncertain/needs-inspection
items remain visible and can coexist with an overall confirmed map.

**Source safety:** "Why did Codize suggest this?" is a collapsed native
disclosure. Human labels are Imported material, Changed-file list, and Your
summary. File path and bounded excerpt render through React as plain text only;
the excerpt is a `<pre>` with wrapping/bounded scrolling. Never render imported
Markdown/HTML, raw import content beyond returned references, internal source
ids, prompts, or hidden reasoning. The fixed note says a source supported the
draft but does not prove it correct.

**Review state and updates:** `frontend/lib/changeMap.ts` holds mappings,
grouping, progress, effective display, validation, dirty/readiness/stale/page
states, draft compatibility, safe payload shaping, and phase routing. The
frontend PUT sends only existing AI `item_id` + `student_decision` /
`student_text` / `student_note`, and the full student-added replacement set of
category/text/note/allowed decision. It never sends origin, AI draft,
uncertainty, references, timestamps, status, import binding, redaction flags,
or student-added ids. Edited text and student-added text cap at 600; notes cap
at 1,000; no silent truncation. **Save review** is explicit; failure preserves
state; success reconciles from the server. Adding a missing item creates an
editable student-owned row (default confirmed, with uncertain/needs-inspection
allowed), visibly authored by the student.

**Local drafts:** reuse `useDraft`; do not add persistence machinery. Surface
key: `change_map_review:<phase>:<generated_at>`, nested under the existing
authenticated-user key. Codize currently has exactly one project per user, so
that authenticated user is also the project scope; phase + generation bind the
draft to the exact map. Stored value contains only item decisions/text/notes
and student-added editing state—never raw import, excerpts, prompts,
provenance, timestamps, auth, or provider data. The existing four-marker guard
refuses secret-like drafts. Restore requires the exact AI item set. Stale maps
clear their compatible draft; successful save/confirmation clears it; explicit
replacement clears the old key; a new `generated_at` cannot load an old draft.
Storage failure remains non-fatal.

**Confirmation:** progress says `N of M items reviewed`, never correct/scored.
Every AI item must leave pending, but confirmed/edited/rejected/uncertain/
needs-inspection all count as reviewed. Confirmation requires no local dirty
state, no pending AI item, a non-stale draft, and backend approval. Copy states:
confirming records review decisions and remaining uncertainty; it does not
prove implementation correctness. Confirmation performs no LLM call. The
confirmed state preserves unresolved items/references/student-added items and
offers Continue to Review. **Edit reviewed map** is explicit; merely entering
edit mode changes nothing. Only a subsequent Save returns it to draft and
requires reconfirmation.

**Staleness and regeneration:** stale maps stay visible with all decisions but
cannot confirm or edit. Banner: implementation material changed; regenerate to
review the latest material. The primary stale action and secondary current-map
More options both open the same inline warning: regeneration replaces the map
and current review decisions while the saved import remains unchanged. Only
the deliberate final action sends `replace_existing=true`; no auto-
regeneration or version history. `source_redacted` explains credential-like
values were removed only from the analysis view; the saved import is unchanged.
`source_truncated` explains not every character was analyzed; no internal
budgets appear.

**Build Loop / progress / handoff:** shell + `WorkflowSteps` place Change Map
after Bring Back and before Review, with not-created/draft-needs-review/
reviewed/stale status. It has no workflow section key, so cockpit and phase
remain **N/5 captured** and build tasks remain separate. Phase next action is:
Prompt (if absent) → Bring Back (if import absent) → Create Change Map → Review
or Regenerate Change Map → Review implementation decisions (only after map
confirmation) → the existing Evidence/Verification/Gate sequence. Successful
Implementation Import save offers Create Change Map plus Back to Build Loop;
it never auto-generates.

**Accessibility and responsive rules:** semantic page/category headings;
fieldset + legend + real radio inputs for decisions; native disclosures;
plain-text excerpts; field-level edited/added errors; visible focus rings;
generation/save/confirmation live regions; progress carries numeric ARIA
values and text; rejected/uncertain states have explicit words, never
color/strike alone. At ≤640px decisions become full-width rows and action
buttons stack; long paths wrap and excerpts scroll within bounds. The existing
workspace collapses its rail ≤1150px and shell becomes a top bar ≤840px. The
global reduced-motion rule covers the progress transition.

**Deliberately not M16:** Review Board is unmodified/unprefilled; Evidence,
Verification, Defense Context, Project Defense, evaluator, and Defense Report
do not consume the Change Map. No code execution, GitHub/repo/file upload,
analytics, multi-project, prompt tuning, provider changes, or backend changes.

**Exact M16A seams:** frontend—`useWorkflowSection("review_board").changeMap`
at `frontend/app/app/phase/review/page.tsx` now exposes the strict top-level
`StoredChangeMap`; M16A may use it only when `status === "confirmed"` and
`stale === false`, and must present suggestions as student decisions without
silently overwriting/saving the current Review form. Backend—load the owned
active project once, then `workflow_service.get_change_map(project,
phase_number) -> StoredChangeMap | None`, followed by
`change_map_service.confirmed_items(map)` for reviewed facts and
`change_map_service.unresolved_items(map)` for cautious unresolved context.
Rejected/pending items stay excluded and raw Implementation Import never enters
the M16 context.
