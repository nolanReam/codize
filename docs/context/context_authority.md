# Codize Context Authority

**Status:** Active
**Purpose:** Define which source wins when Codize documents disagree and prevent stale plans from steering implementation.

---

## Core Rule

Different sources answer different questions.

Do not use a roadmap to decide what is already implemented.

Do not use Git history alone to redefine product purpose.

Do not let a temporary milestone prompt silently become permanent product direction.

---

## Authority Hierarchy

### 1. Current user instruction and `instructions.md`

Controls:

- the active task;
- milestone scope;
- allowed and forbidden changes;
- required tests;
- stop conditions;
- temporary process instructions.

Limits:

- `instructions.md` does not permanently redefine Codize's product direction by itself;
- a permanent product change must update the active product brief or create an accepted decision record;
- an implementation prompt cannot override safety, ownership, provenance, or trust rules without an explicit approved architecture/product decision.

### 2. Repository reality

Controls what is actually implemented.

Inspect:

1. current code;
2. tests;
3. migrations;
4. Git history;
5. deployed-environment evidence when deployment state matters.

Repository reality outranks stale milestone labels, old checklists, old dates, and old “next step” statements.

Never duplicate a milestone because a strategy document still calls it “next.”

### 3. `docs/context/codize_product_operating_brief_v2.md`

Controls stable:

- product thesis;
- audience;
- positioning;
- workflow;
- adaptive-support model;
- product scope;
- trust and claims model;
- UX direction;
- guided-navigation principles;
- validation philosophy;
- long-term sequencing.

This is the primary product-direction source.

### 4. `docs/context/codize_master_spec_v2.1.md`

Controls only the still-applicable architecture and safety invariants explicitly preserved by current code and later decisions, including:

- the five intake questions unless explicitly migrated;
- archetype/template constraints where still implemented;
- server-side secrets;
- RLS and ownership requirements;
- API-layer authentication;
- gate turn structure and safety mechanics where still implemented;
- hidden evaluator scores and thresholds;
- fail-closed evaluation;
- cooldown and retry behavior;
- security architecture principles.

Limits:

- its original target-audience language is superseded by the active operating brief;
- its older product positioning is superseded by the active operating brief;
- its older workflow and UX assumptions are superseded by the active operating brief and accepted decision records;
- unimplemented ideas in the old spec are not automatically current requirements;
- current repository behavior must be inspected before changing existing architecture.

### 5. Accepted decision records in `docs/decisions/`

Control narrow, durable decisions that need more detail than the operating brief.

Examples:

- guided workflow navigation;
- artifact trust boundaries;
- database write boundaries;
- provider selection;
- deployment architecture.

A decision record should include status, context, decision, consequences, and supersession rules.

### 6. `CLAUDE.md`, `.claude/memory/`, and repo-scoped skills

Control durable implementation conventions and operational lessons.

Use them for:

- how an implemented subsystem works;
- verified seams;
- testing conventions;
- security lessons;
- frontend conventions;
- reusable agent workflows.

They do not redefine product purpose unless the active product brief or an accepted decision record is updated.

### 7. Strategy and planning documents

Examples:

- the full one-stop PDF;
- deferred feature plans;
- pilot plans;
- competition plans;
- milestone implementation plans.

These inform strategy and history.

They are not authoritative for current implementation state.

Time-sensitive dates, model availability, milestone labels, and “next step” statements may become stale.

### 8. Archive

Examples:

- old product visions;
- completed milestone plans;
- old learning roadmaps;
- chat exports;
- superseded model guides.

Archive material is non-authoritative and should not be loaded unless historical context is explicitly needed.

---

## Conflict Resolution by Question

| Question | Source to trust first |
|---|---|
| What should this active task do? | `instructions.md` |
| Is this already implemented? | Code, tests, migrations, Git history |
| What is Codize and who is it for? | `codize_product_operating_brief_v2.md` |
| What is the canonical shared workflow? | `codize_product_operating_brief_v2.md` |
| What trust language is allowed? | Operating brief, then accepted trust decisions |
| What security/auth/gate invariant must remain? | Current code/tests plus applicable master-spec invariant |
| How does a subsystem currently work? | Code/tests, then `.claude/memory/` |
| Why was a narrow product/architecture choice made? | `docs/decisions/` |
| What feature should come after the current release? | Current user direction plus strategy docs, reconciled with repo state |
| What happened in an old milestone? | Git history, archived plan, memory |
| What are the current competition rules? | Current official source, not a cached context document |

---

## Anti-Drift Rules for Agents

Before a major implementation task:

1. run `git status`;
2. inspect recent Git history;
3. read the active milestone instructions;
4. read only the relevant context documents;
5. inspect existing code and tests before designing a replacement;
6. reconcile milestone labels with repository reality;
7. preserve unrelated work;
8. do not revive superseded product assumptions;
9. do not create duplicate architectures;
10. update durable context only when a permanent lesson or decision is confirmed.

Do not:

- read the full chat archive by default;
- load large legacy roadmaps for routine tasks;
- treat old dates as current;
- treat old model-specific prompting advice as product direction;
- make product changes only in `instructions.md`;
- create a new context file for every milestone.

---

## When Product Direction Changes

A real product-direction change should include:

1. the reason;
2. evidence or user decision;
3. what is superseded;
4. what remains unchanged;
5. impact on workflow, UX, trust, scope, and roadmap;
6. an update to the active operating brief or a new accepted decision record;
7. an update to this authority file when precedence changes.

Do not silently edit history to make old documents appear current.

Archive superseded documents and preserve a clear status banner.
