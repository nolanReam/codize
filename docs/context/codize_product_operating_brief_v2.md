# Codize Product Operating Brief v2.1

> [!WARNING]
> **Status: Historical V1 product-direction record — not V2 authority.**
>
> This document describes the prevention-first / Project Defense direction that shaped the current V1 implementation. Its required shared workflow, Change Map destinations, Verification/Evidence stages, mandatory Defense, reports, and related navigation do not govern Codize V2.
>
> For V2, start with `docs/context/context_authority.md` and the canonical documents in `docs/context/v2/`. Preserve this file for product history only.

**Former status:** Active product-direction source
**Purpose:** Stable, machine-readable summary of Codize's prevention-first, recovery-capable product direction
**Supersedes for product direction:** `docs/archive/product/codize_product_vision_v3.md`
**Derived from:** `docs/strategy/Codize_One_Stop_Plan_Prevention_First_Recovery_Capable.pdf`
**Not an implementation tracker:** Current repository state, tests, migrations, and Git history determine what is actually built.

---

## 1. North-Star Thesis

> Codize teaches student builders how to use AI without giving up understanding or control.

Beginners learn the workflow before the patch loop begins. Builders who are already stuck use the same system to regain control.

Codize is **prevention-first and recovery-capable**.

The product should help a student reach this outcome:

> I know what changed. I reviewed the decisions. I tested the behavior. I recorded the evidence. I can defend what I built.

---

## 2. Product Category and Positioning

Codize is:

> A guided, project-based AI coding workflow trainer.

AI coding tools help users generate code. Codize teaches users how to remain the engineer while using those tools.

Codize sits above tools such as Codex, Claude Code, Cursor, Copilot, Replit, ChatGPT, and Gemini. It does not need to replace them.

Codize is not:

- a browser IDE;
- a generic AI coding assistant;
- a generic chatbot;
- a full programming-syntax curriculum;
- a school LMS;
- a quiz platform;
- a social network;
- a marketplace;
- a public ranking system.

### Canonical brand language

- **Named problem:** The 80% Trap
- **Identity promise:** Stay the engineer.
- **Recovery message:** Stop Debugging Blindly.
- **Beginner bridge:** Build with AI without falling into the 80% Trap.
- **Workflow explanation:** Plan. Prompt. Review. Verify. Explain. Defend.
- **Challenge hook:** Can you defend what AI built?

The 80% Trap is both:

1. a failure state Codize helps prevent; and
2. a failure state Codize helps repair.

Do not frame users as lazy, fake, or dishonest. Describe Codize as the missing workflow, not as punishment or extra homework.

---

## 3. Primary Users

### Primary audience

Beginner and early-intermediate student builders who want to build with AI but need structure before they lose understanding or control.

They may:

- know little about project architecture;
- know basic coding concepts but not how to organize a complete application;
- have used AI coding tools without a reliable review or testing workflow;
- want to build a meaningful project but do not know where to start;
- want guidance that appears when relevant rather than a full course before building.

### Secondary audience

Intermediate or experienced student builders who already have an AI-assisted project and need to recover from:

- unread diffs;
- repeated patches;
- regressions;
- unclear architecture;
- lost context;
- uncertainty about what changed;
- inability to explain or safely extend the project.

### Institutional audience

Teachers, coaches, school programs, and AI-literacy initiatives that want a repeatable workflow for planning, prompting, reviewing, testing, and explaining AI-assisted work.

### Scope boundary

Codize teaches the workflow of AI-assisted project building. It is not currently a complete programming course.

Teach concepts just in time when they become relevant. Do not front-load long lessons or expand into a generic curriculum without evidence that the product needs it.

---

## 4. One Shared Workflow

All supported entry paths converge on one architecture:

```text
ENTRY
→ Goal
→ Plan
→ Prompt
→ Use an external AI coding tool
→ Bring Back What Changed
→ AI-generated Change Map draft
→ Student edits and confirms
→ Review decisions
→ Suggested verification checks
→ Student performs checks and records results
→ Student records evidence
→ Artifact-Aware Project Defense
→ Learning Progress + Defense Report
```

There are not separate beginner, builder, and recovery products.

The same workflow adapts its:

- terminology;
- explanation depth;
- examples;
- project scope;
- prompt guidance;
- review guidance;
- verification depth;
- Defense question depth.

Adaptation changes support, not standards. It must never make passing automatic or remove the student's responsibility to review, test, and explain.

---

## 5. Entry Paths

### Guided Build

For students starting a first or new AI-assisted project.

Codize should help them:

1. choose a meaningful, manageable goal;
2. identify who the project helps;
3. reduce the project to a realistic first version;
4. understand the architecture in plain language;
5. build a scoped prompt with context, constraints, no-touch zones, and expected checks;
6. use an external AI tool;
7. import what changed;
8. review and correct the Change Map;
9. make Review decisions;
10. perform suggested checks;
11. record results and evidence;
12. defend the implementation;
13. leave with visible learning progress and a Defense Report.

### Builder

For students with basic project experience.

Use the same workflow with less explanation and more control. Preserve structure without over-explaining every technical term.

### Recovery

For students already inside the 80% Trap.

Codize should help them:

1. stop blind patching;
2. import available project material;
3. reconstruct what appears to have changed;
4. preserve uncertainty where the source is incomplete;
5. identify consequential changes and unresolved risks;
6. decide what to keep, revise, remove, test, or inspect;
7. perform checks and record evidence;
8. use Project Defense to rebuild a usable mental model;
9. record what is known, tested, and unresolved.

---

## 6. The Change Map Is the Shared Source

After Implementation Import, the confirmed Change Map becomes the shared source for downstream workflow steps.

Its purpose is to reduce repeated work without replacing human judgment.

### Capture once, reuse downstream

| Captured information | Reused in | New student work still required |
|---|---|---|
| Changed files | Review, Verification context, Defense, Report | Decide whether the changes matter and inspect them |
| Behavior changes | Review, Verification suggestions, Report | Perform tests and record outcomes |
| Implementation decisions | Review, Defense, Report | Evaluate tradeoffs and defend the decision |
| Unresolved risks | Verification, Defense, next actions | Inspect, test, or preserve uncertainty |
| Verification targets | Verification workflow and Report | Perform the checks; Codize never auto-completes them |

Later steps should ask for judgment, action, evidence, or explanation—not duplicate transcription.

---

## 7. Permanent Trust and Claims Model

Never merge student input, AI inference, student confirmation, student testing, and evidence into one ambiguous truth state.

Preserve the distinctions among:

```text
student-provided
→ AI-inferred
→ student-edited / confirmed / rejected / uncertain / needs inspection
→ student Review decision
→ Codize-suggested verification check
→ student-performed test
→ student-recorded result
→ student-provided evidence
```

### Provenance rules

- Preserve raw source attribution.
- Label AI-generated Change Map content as a draft.
- Record the student's action on every item.
- Keep Review decisions separate from Change Map confirmation.
- Keep suggested checks separate from performed checks.
- Keep results separate from evidence.
- Keep uncertainty visible downstream.
- Preserve source references where they explain why an inference exists.
- A source reference supports traceability; it does not prove correctness.

### Human-judgment rules

AI may help organize, summarize, suggest, or ask questions.

AI must not:

- approve its own generated implementation;
- silently decide Review outcomes;
- silently confirm inferred changes;
- automatically complete Verification;
- automatically mark checks as passed;
- convert skipped or not-applicable checks into success;
- present student-recorded testing as independent Codize verification;
- erase rejected or unresolved context from the historical record;
- replace the student's explanation in Project Defense.

### Honest language

Prefer:

- “appears to have changed”;
- “Codize draft”;
- “suggested check”;
- “student-recorded result”;
- “student-provided evidence”;
- “reviewed and confirmed”;
- “still uncertain”;
- “needs inspection.”

Avoid:

- “Codize verified the implementation”;
- “AI approved”;
- “guaranteed correct”;
- “safe” without a grounded basis;
- “proof” when the system only has self-reported information;
- “verified change” for an AI-inferred summary.

---

## 8. Review, Verification, Evidence, and Defense

### Review

Change Map asks:

> Is this an accurate description of what appears to have changed?

Review asks:

> Now that I know what changed, what do I decide should happen next?

A student may decide to:

- keep;
- revise;
- remove;
- test;
- remain uncertain.

A Review decision is not proof of correctness.

### Verification

Codize may suggest checks from reviewed implementation items.

The student must perform the check and record the result.

Honest result states may include:

- pass;
- fail;
- skipped;
- not applicable;
- unperformed/pending.

No result is automatic.

### Evidence

Evidence remains attributable to the student or its actual source.

Evidence may include:

- terminal output;
- test output;
- screenshots;
- links;
- commit identifiers;
- API responses;
- observations;
- notes about what was checked.

Evidence should support a recorded test or explanation. It must not be silently upgraded into a stronger claim than it supports.

### Artifact-Aware Project Defense

Defense questions should be:

- grounded in the student's actual project record;
- implementation-specific;
- traceable to confirmed, reviewed, tested, or evidenced information;
- cautious when based on unresolved material;
- adaptive in depth without becoming automatic passing.

Project Defense should reveal understanding gaps and help the student explain decisions, system behavior, tradeoffs, and failure modes.

### Learning Progress + Defense Report

The Report is the durable payoff.

It should preserve:

- project purpose;
- goal and scope;
- plan;
- final prompt;
- imported implementation context;
- confirmed Change Map;
- Review decisions;
- student-performed checks;
- student-recorded results;
- Evidence;
- Defense record;
- unresolved risks;
- next actions;
- learning progress.

The Report must preserve provenance and uncertainty. It must not turn self-reported work into unsupported claims.

---

## 9. Guided Workflow Navigation

Codize is a guided workflow, not a collection of independent tools.

The interface should always make clear:

1. where the student is;
2. what is complete;
3. what requires attention;
4. what the student should do next;
5. why later steps are not yet available.

### Navigation principles

- Project Home is always available.
- The current actionable step is the dominant navigation action.
- The full journey may remain visible for orientation.
- Future steps must not appear as equal, unrestricted destinations.
- Completed steps remain available through a Project Record or equivalent history view.
- Viewing completed work should not disturb downstream state.
- Editing an upstream artifact requires an explicit warning when downstream work may become stale.
- Downstream records are never silently rewritten after an upstream change.
- Stale work remains readable but must be deliberately rebuilt from current source material.
- Every page should have one clear primary next action.
- Student-facing navigation should use workflow language, not internal storage or module names.

Core principle:

> Show the journey. Emphasize the current step. Protect the sequence. Preserve access to the student's completed record.

This is a product rule, not only a visual-design preference.

---

## 10. Experience and Interface Principles

Every major interface should answer:

- What is this step for?
- What do I need to do now?
- What information is essential?
- What is optional?
- What happens after I finish?
- What remains uncertain?
- What was saved?
- What needs attention?

Use:

- one dominant primary action per state;
- progressive disclosure;
- calm loading states;
- visible save state;
- safe retry behavior;
- honest stale-state messaging;
- responsive layouts;
- semantic controls;
- keyboard access;
- visible focus;
- accessible status announcements;
- plain language before technical terminology for beginners.

Avoid:

- walls of instructions;
- nested-card overload;
- exposing every optional field at once;
- making every surface glow;
- badges without meaning;
- fake progress;
- scores that imply correctness;
- internal enum names;
- internal IDs;
- module navigation that lets users skip required workflow context.

Visual polish should support comprehension, not hide an unclear workflow.

---

## 11. Build Priorities

Repository state determines what is already complete.

The durable sequencing rule is:

1. Finish the shared workflow core before expanding the beginner front door.
2. Preserve data integrity, provenance, ownership, and end-to-end coherence.
3. Build adaptive entry and Guided Build on top of the shared core.
4. Add learning-progress and Report improvements.
5. Add a guided starter or judge/teacher demo path.
6. Run reliability, accessibility, security, deployment, and competition hardening.
7. Add broader features only after user and pilot evidence supports them.

Milestone names and numbering may change. Do not duplicate work because a strategy document uses an old label.

---

## 12. Validation and Metrics

Do not rely only on signups or page views.

Measure:

### Acquisition

- relevant users invited;
- visits;
- signups;
- session attendance.

### Activation

- reached a useful prompt or insight;
- imported implementation material;
- confirmed a Change Map;
- reached the current guided step.

### Workflow

- completed Review;
- completed Verification;
- recorded Evidence;
- started and completed Defense;
- generated or viewed the Report;
- returned for another phase.

### Learning and usefulness

- user could explain at least one concept better;
- Codize revealed something the user could not explain;
- user corrected an AI inference;
- user identified unverified behavior;
- user changed how they review AI-assisted code;
- user felt more able to extend or defend the project;
- user would use Codize again.

### Product friction

Observe:

- where the user hesitates;
- which words are unclear;
- which step feels like homework;
- what the user tries to skip;
- whether the next action is obvious;
- whether the Change Map is useful enough to correct;
- whether verification suggestions are actionable;
- whether Defense asks something genuinely revealing;
- whether the user can continue without Nolan guiding every click.

### Institutional repeatability

Measure:

- facilitator satisfaction;
- willingness to repeat;
- completion;
- common misconceptions;
- whether another facilitator can run the protocol;
- whether results can be compared across pilots.

---

## 13. Decision Rules and Scope Control

Before adding a major feature, ask:

1. Does it help a student plan, prompt, understand changes, review, test, record evidence, explain, or maintain ownership?
2. Does it improve recruitment, activation, completion, learning, repeatability, or a current validation goal?
3. Can it be built without weakening integrity, provenance, security, ownership, or reliability?
4. Do user or pilot observations support it?
5. Can its effect be measured?

After beta, prioritize:

> Frequency × Severity × Mission Alignment

Then apply feasibility and risk as constraints.

When schedule pressure appears:

- preserve core coherence before feature breadth;
- drop polish before ownership, security, or provenance tests;
- document known limitations honestly;
- move a target date rather than normalizing repeated all-nighters;
- prefer a stable, coherent, demoable product over many unfinished features.

---

## 14. Not Before Validation

Do not prioritize these before the shared core and pilot evidence are stable:

- public individual leaderboards;
- public LLM gate-score rankings;
- social feed;
- marketplace or payments;
- large teacher dashboard;
- teams/collaboration suite;
- full GitHub integration;
- IDE extension;
- mobile app;
- complex gamification;
- full programming-syntax curriculum;
- broad multi-project support unless the active workflow requires it.

Challenge or recognition features may be considered after validation, but should reward thoughtful process rather than raw model scores, completion speed, or activity volume.

---

## 15. Institutional and Competition Direction

Codize should become more than a founder-operated app.

The institutional goal is a repeatable protocol with:

- a clear student workflow;
- facilitator guidance;
- privacy and data explanations;
- measurable outcomes;
- documented iteration;
- evidence that another adult or organization can run it.

For competition and public demonstration:

- show the beginner opportunity;
- show the differentiated Change Map → Review → Test → Defense loop;
- show honest provenance and student ownership;
- show meaningful technical decisions;
- document AI tools and Nolan's individual contribution;
- prefer a stable, accessible, reliable demonstration over feature breadth;
- maintain technical-decision and AI-usage documentation.

Competition rules and deadlines are time-sensitive. Verify them from current official sources rather than treating this brief as a permanent rules document.

---

## 16. Source-of-Truth Rule

Before acting, an implementation agent must:

1. inspect the repository;
2. inspect Git status and recent history;
3. inspect current tests and migrations;
4. reconcile this brief with completed work;
5. avoid duplicating a finished milestone.

For implementation status:

```text
repository code
→ tests
→ migrations
→ Git history
→ current implementation memory
```

outweigh stale milestone labels in strategy documents.

For stable product direction, this operating brief remains authoritative until an explicit product decision updates it.

Changes to product direction should update this document or create an accepted decision record. They should not exist only in a temporary milestone prompt.
