# Bounded Assignment Practice

**Status:** Accepted
**Decision type:** Educational interaction, Prompt artifact, and compatibility
**Applies to:** New current-phase AI-assignment Prompts in Prompt Builder

## Context

Students can select a concrete phase assignment, but the existing Prompt
Builder can still begin with a broad Task field. M18C.1 tests one narrow
learning claim before Codize builds a larger learning system: whether a
student can make one real AI request more bounded and checkable without Codize
writing the answer.

## Decision

The single objective is `bounded_assignment_v1`, displayed as:

> Keep one AI request bounded and checkable

A new Prompt bound to a current AI-owned assignment requires three
student-authored decisions:

1. what will exist when the task is done;
2. what related work is excluded;
3. what observable result will be inspected after the AI responds.

Prompt Builder shows one short principle, one optional habit-tracker contrast,
and a deterministic checklist. The checklist verifies only current AI
assignment binding and valid non-empty responses. It never scores semantic
quality, correctness, mastery, or likely project success.

## Prompt integration

M18C.1 uses an explicit apply action. It:

- writes the finish and inspection conditions into the editable Task field;
- writes excluded work into the editable `Don't touch` guardrail;
- leaves Context and every other Prompt field unchanged;
- warns before replacing non-empty Task or guardrail text;
- is idempotent and never merges assignments;
- does not save, call a provider, complete a build task, or create downstream
  artifacts.

The generated Prompt separately names the server-authoritative selected
assignment. The student may edit Task and Guardrails after applying; Codize
preserves those edits and shows only a non-blocking deterministic mismatch
notice.

## Persistence and authority

Final submitted scope is stored inside the existing phase Prompt artifact in
`projects.workflow_artifacts`; no migration or new store exists. The browser
sends only the three responses. The server derives the objective ID/version
and selected assignment task ID, validates the current owned active project,
current phase, current selected AI task, field bounds, unsafe controls,
secret markers, and unknown fields, then performs the existing optimistic
Prompt write.

Incomplete scope stays local in a user, active-project placeholder, phase,
assignment, Prompt-surface, and objective-version scoped draft. Existing
Prompt drafts remain in their original assignment-scoped key. The existing
assignment-switch warning detects either draft and preserves both without
merging.

## Compatibility

- Existing unassigned Prompts remain legacy and readable.
- A currently saved assignment-bound Prompt without scope remains editable and
  savable without retroactive blocking.
- A scoped Prompt cannot later strip its scope record.
- Switching assignments archives prior saved Prompts through the existing
  bounded server history.
- Assignment selection, task completion, Continue priority, phase advancement,
  Change Map, Review, Verification, Evidence, Defense, and Report remain
  unchanged.

## Non-goals

No provider evaluation, semantic scoring, competency profile, mastery,
learning analytics, scaffold fading, transfer engine, recovery curriculum,
Defense change, separate lesson route, navigation authority, migration, or
automatic task completion is introduced.

## Review seam

M18C.2 may independently audit whether this interaction improves the student's
bounded-assignment decision, whether the explicit apply flow avoids duplicate
entry, and whether the support is appropriately small. It must not assume
semantic learning evidence from the M18C.1 completeness checklist.
