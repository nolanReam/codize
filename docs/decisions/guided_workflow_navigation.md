# Guided Workflow Navigation

**Status:** Accepted product decision
**Decision type:** Product architecture and UX
**Applies to:** Project Home, sidebar/navigation, workflow routing, progress, completed work, stale downstream artifacts
**Implementation timing:** After the shared M16 core is stable, unless a smaller prerequisite change is required earlier

---

## Context

Codize's product promise is a deliberate sequence:

```text
Goal
→ Plan
→ Prompt
→ Use an external AI tool
→ Bring Back What Changed
→ Change Map
→ Review
→ Verification
→ Evidence
→ Project Defense
→ Learning Progress + Defense Report
```

A navigation system that presents Prompt Builder, Review, Verification, Evidence, Defense, and Report as equal destinations asks the student to understand Codize's internal module structure before they can use the product.

That creates avoidable questions:

- Where am I supposed to go next?
- Should I do Verification before Review?
- Why is Evidence available when I have not tested anything?
- Did I skip a required step?
- Which page matters right now?

The product already knows the expected next action. The interface should communicate it.

---

## Decision

Codize will use **state-aware guided navigation**.

The full journey may remain visible for orientation, but future workflow stages will not appear as equal, unrestricted destinations.

The interface will emphasize:

1. Project Home;
2. one current primary action;
3. the student's progress through the journey;
4. access to completed work through a Project Record;
5. clear handling of stale or blocked downstream work.

Core principle:

> Show the journey. Emphasize the current step. Protect the sequence. Preserve access to the student's completed record.

---

## Navigation Model

### Always available

- Project Home
- Help/support
- Account/settings

### Dominant workflow action

A dynamic **Continue** destination based on project state.

Examples:

```text
Continue
Plan Your Project
```

```text
Continue
Bring Back What Changed
```

```text
Continue
Review Your Change Map
```

```text
Continue
Test What You Changed
```

The student should not need to choose among every internal module.

### Journey overview

Show the complete sequence with state:

- completed;
- current;
- ready;
- future;
- needs attention;
- stale.

Future stages are visible for orientation but unavailable until prerequisites are met.

### Project Record

Completed work remains accessible through a history/record surface.

Potential entries:

- Goal
- Plan
- Final Prompt
- Implementation Import
- Confirmed Change Map
- Review Decisions
- Verification Results
- Evidence
- Project Defense
- Defense Report

Viewing completed work should not change workflow state.

---

## State Rules

| State | Meaning | Navigation behavior |
|---|---|---|
| Completed | Required work was saved | Viewable through Project Record |
| Current | This is the expected action now | Dominant primary action |
| Ready | Prerequisites are satisfied | May become the next action |
| Future | Prerequisites are incomplete | Visible but not directly available |
| Needs attention | Earlier work requires action | Route to the earliest required correction |
| Stale | Upstream source changed | Old record remains readable; rebuild required |
| Optional | Relevant only in some contexts | Hidden or progressively disclosed until useful |

Do not use progress styling that implies correctness, mastery, or verification.

---

## Upstream Editing

Students must retain agency to revisit earlier work.

However, editing upstream artifacts can invalidate downstream context.

Rules:

- viewing completed work is safe;
- editing is deliberate;
- show a warning before an upstream edit that may stale downstream work;
- identify the downstream records affected;
- never silently rewrite downstream records;
- preserve old downstream work as readable historical context;
- require an explicit rebuild from current source material;
- never silently merge old decisions into new generated targets.

Example:

> Editing this confirmed Change Map may make your Review and Verification records outdated.

Actions:

```text
Cancel
Edit Change Map
```

---

## Route Access Versus Navigation Visibility

Navigation gating is a UX rule, not the only security or integrity control.

Backend lifecycle validation must continue to enforce prerequisites.

A hidden link does not protect an endpoint.

Direct route access should:

- redirect to the correct current step; or
- show a clear prerequisite state; or
- display the stale record with rebuild guidance;

according to the current product contract.

Do not rely only on sidebar visibility.

---

## Project Home

Project Home is the orientation center.

It should prioritize:

1. project identity and goal;
2. current step;
3. current status or progress;
4. one primary Continue action;
5. full journey orientation;
6. concise issues requiring attention.

Conceptual layout:

```text
PROJECT

Study Planner

Goal
Help students organize homework and deadlines.


CURRENT STEP

Review What Changed

4 of 7 implementation items reviewed.

[ Continue Review ]


YOUR BUILD JOURNEY

✓ Goal
✓ Plan
✓ Prompt
✓ Bring Back What Changed
✓ Change Map
● Review
○ Verification
○ Evidence
○ Project Defense
○ Learning Progress + Report
```

Do not make the dashboard a grid of equal feature cards.

---

## Sidebar

Preferred high-level structure:

```text
CODIZE

Project Home

Continue
Current Step Name
Current progress/status

Project Record
collapsed or secondary

Help

Account
```

Avoid exposing every workflow module as a permanent equal-priority tab.

Student-facing labels should describe the task, not internal implementation names.

---

## Accessibility

- Current, completed, locked, and stale states must not rely on color alone.
- Locked stages must explain the prerequisite.
- The current step must be programmatically identifiable.
- Keyboard navigation must work.
- Focus must move predictably after a route or state change.
- Status changes should be announced where appropriate.
- Disabled future steps should not become inaccessible mystery items; explain why they are unavailable.
- Mobile navigation must preserve the current-step emphasis.

---

## Non-Goals

This decision does not require:

- deleting workflow routes;
- preventing completed-work viewing;
- creating a fully linear wizard with no backward access;
- hiding the overall journey;
- merging all workflow pages into one page;
- auto-advancing without student confirmation;
- weakening backend lifecycle validation;
- silently changing stale downstream work.

---

## Acceptance Criteria

The decision is implemented successfully when:

1. a new user can identify the current step without understanding internal module names;
2. each state has one obvious primary next action;
3. future stages do not appear as equally available tools;
4. completed work remains easy to inspect;
5. upstream edits warn about downstream staleness;
6. stale work remains readable but is not treated as current;
7. downstream records are never silently regenerated or merged;
8. direct route access still respects backend lifecycle rules;
9. the journey remains visible enough to provide orientation;
10. user testing shows fewer “where do I go next?” hesitations.

---

## Relationship to the Product Brief

This decision implements the operating brief's rule that Codize is one guided workflow, not a collection of independent tools.

When this record conflicts with an older dashboard or module-navigation plan, this accepted decision wins unless explicitly superseded by a newer decision record.
