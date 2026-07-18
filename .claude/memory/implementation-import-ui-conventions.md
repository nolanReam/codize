# Implementation import UI conventions (Milestone 15B)

**User-facing name:** the page title is **"Bring Back What AI Changed"**
(`lib/implementationImport.ts::PAGE_TITLE`); the Build Loop strip step is
"Bring Back" and the sidebar link is "Bring Back What Changed". The internal
name `implementation_import` is schema/service vocabulary only — a unit test
asserts no label or description ever shows it (or any underscore) to a
student.

**Framing is prevention-first, recovery-capable:** the intro teaches the
habit ("After you use AI, bring back whatever you have so you can keep track
of what changed before moving on") with the reassurance "You do not need
every item — add the material you have" — never "your project is broken".
Recovery lives in ONE collapsed rail GuideCard ("Already stuck?"). Do not
build separate beginner/recovery pathways; do not modify the landing page
for this.

**Route + integration:** `app/app/phase/import/page.tsx`, matching the other
workflow pages. ZERO new client machinery: `useWorkflowSection
("implementation_import")` + the generic `saveWorkflowSection` (the section
was added to `WorkflowSectionName`, `WorkflowSections`, and api.ts's
`SectionPayloadMap` — that's the whole API integration). All pure logic
(source-kind options, form ↔ payload shaping, save-blocking rules, page copy
constants) lives in `lib/implementationImport.ts`, unit-tested — vitest here
is node-only, so testable copy/logic goes in the lib, not the page.

**Source-kind mapping** (SOURCE_OPTIONS, exactly six): AI response →
ai_response, Git diff → git_diff, Selected code → code_snippet, Changed
files → changed_files, My own summary → manual_summary, Something else →
other. The picker is a semantic `fieldset.kind-picker` + legend with
label-wrapped radios styled as chips (`label.chip` in globals.css — the
input is visually hidden but keyboard-operable; `label.chip:has(input:
focus-visible)` echoes the focus ring; arrow keys move the selection).
Selecting a kind NEVER clears entered content — hidden-field data persists
in state and is still sent.

**Field layout / progressive disclosure:** the primary card shows the picker,
the selected kind's one-line description, and the kind's emphasized main
field (content textarea for ai_response/git_diff/code_snippet/other;
changed-files for changed_files; summary for manual_summary). Everything
else — including a generic content field in the non-content modes so no data
is ever invisible — lives behind a collapsed `details.help` "Add more detail
(optional)". The git-diff explanation is a collapsed disclosure shown only
in git_diff mode (GIT_DIFF_EXPLANATION — a few sentences with a way out,
never a Git lesson).

**Formatting honesty:** the content textarea is `textarea.code` (mono),
`spellCheck={false}`, has NO maxLength (a browser maxLength would silently
clip large pastes) — instead an unobtrusive `N / 40,000` counter and
`saveBlocker()` disabling Save with a message naming the over-limit field.
Content/summary are sent VERBATIM when non-blank (backend normalizes edges);
`parseChangedFiles` only splits lines/trims/drops empties — deduplication
stays the backend's job (and the round-trip shows it).

**Meaningful-content rule:** Save is disabled (SaveBar's M15B `disabled`
prop) until content OR changed files OR summary carries something
(`hasMeaningfulMaterial`), with the reason as a visible hint line; the
backend stays the authoritative validator. Optional fields (tool name)
never block.

**Drafts + secrets:** standard M13E.2 layer, surface
`implementation_import:<phase>`; the whole `ImportForm` is the draft shape.
`containsSecretMarker(JSON.stringify(form))` drives a visible warning when
the draft layer refuses credential-like content ("isn't being kept on this
device"); the backend's 422 message is shown as-is and never echoes the
value (live-verified). The static safety line ("Remove API keys…") is one
hint above the save bar — compact, never the visual focus. No new scanner
was built.

**Save states:** first save = "Save implementation material", existing =
"Save changes" plus a plain-language "replacing this phase's previous save"
draft-hint suffix (full-section replace, no version history/append/merge).
Success = `.notice ok` (role="status") "Implementation material saved" with
the M15C.2 next action **"Create Change Map →"** plus the preserved secondary
"Back to Build Loop" link. It navigates only—no generation or other LLM call
happens on save. A failed save preserves form values and the local draft.

**Build Loop position:** the canonical student Journey is defined once in
`frontend/lib/workflowJourney.ts`: Prompt Builder → Bring Back What Changed →
Change Map → Review → Verification → Evidence → Project Defense → Defense
Report. Using an external AI tool happens between Prompt Builder and Bring Back
What Changed, but is not a Codize route or a ninth stage. Phase next-step logic
places Change Map between the saved import and Review; the
"Workflow: N/**5** captured" counts on the phase page and cockpit were the
easy-to-miss change (the backend returns five keys, so the old /4 display
would have shown 5/4). Artifact saves still never tick a build task. The
Prompt Builder shows a one-line handoff ("Use your prompt in your AI coding
tool. Then bring back what changed →") only after its artifact is saved.

**Not in M15B (and why):** no LLM/Change Map/analysis (M15C, spec-guardian
gated), no import content in the report or Defense Context (report stays
untouched; the M14 pack excludes raw imports by backend construction —
live-checked that /gate/context-summary is 8 sources before and after
imports), no file upload/GitHub fetch, no per-question source attribution.
**M15C UI seam (built):** `/app/phase/change-map` reads the same stored section
and top-level `change_map` through `GET /workflow/{phase}`. The import page
changed only its post-save handoff; its storage payload, draft, and replacement
semantics are unchanged. See [[change-map-ui-conventions]].

See [[implementation-import-conventions]] (backend contract),
[[workflow-artifact-conventions]], [[frontend-conventions]],
[[pilot-ux-lessons]] (the density rules this page was built under).
