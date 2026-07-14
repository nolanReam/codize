# Codize Context Directory

**Purpose:** Keep a small, high-signal set of documents that agents can read to understand Codize without loading old plans, chat history, or stale milestone details.

The context directory is for durable product direction and authority—not every useful project document.

---

## Active Files

### `context_authority.md`

Read first when sources may disagree.

Defines:

- what controls the active task;
- what controls implementation state;
- what controls product direction;
- what remains authoritative from the legacy master spec;
- how decisions, memory, strategy, and archives fit together.

### `codize_product_operating_brief_v2.md`

Primary product-direction source.

Defines:

- north-star thesis;
- prevention-first, recovery-capable positioning;
- primary and secondary audiences;
- one shared workflow;
- adaptive support;
- Change Map reuse;
- trust and claims rules;
- guided workflow navigation;
- UX principles;
- validation and scope rules;
- institutional and competition direction.

This file intentionally avoids live commit hashes, test counts, and milestone status.

### `codize_master_spec_v2.1.md`

Legacy foundation with still-active architecture and safety invariants.

The filename remains stable for references, and the document carries a status banner explaining that:

- audience and product positioning are superseded;
- current workflow/UX direction comes from the operating brief;
- only still-applicable intake, archetype, security, auth/RLS, and gate invariants remain authoritative;
- repository reality must be inspected before changing implemented behavior.

---

## Files That Do Not Belong Here

Keep these outside `docs/context/`.

### Completed milestone plans

Store in:

```text
docs/archive/plans/completed/
```

Examples:

- `m13_ai_workflow_workspace_plan.md`

Reason:

- useful historical implementation rationale;
- stale as active context;
- current implementation is already captured by code, tests, Git, and memory.

### Deferred feature plans

Store in:

```text
docs/plans/deferred/
```

Examples:

- `multi_project_dashboard_plan.md`

Add a banner:

> Re-audit against the current repository before implementation. This plan records the architecture at the date shown and is not current implementation authority.

### Old product visions

Store in:

```text
docs/archive/product/
```

Examples:

- `codize_product_vision_v3.md`

Reason:

- historically important;
- superseded by the prevention-first, recovery-capable operating brief;
- conflicts with the broader beginner audience and newer Import → Change Map → Review → Verification architecture.

### Old learning/build roadmaps

Store in:

```text
docs/archive/learning-roadmaps/
```

Examples:

- `codize_roadmap_v2.html`

Reason:

- roadmap for building/learning Codize itself;
- not current product direction;
- too large and visually oriented for routine agent context.

### Model-specific prompting guides

Store in:

```text
docs/archive/tooling/
```

Examples:

- `fable_5_prompting.md`

Reason:

- model-specific and time-sensitive;
- not product context;
- reusable model-agnostic lessons should live in `CLAUDE.md`, `AGENTS.md`, or a focused memory/skill.

### Chat exports

Prefer removing from the Git repository and retaining a private local backup.

Example:

- `conversations.json`

Reason:

- very large;
- non-authoritative;
- may contain personal or sensitive history;
- expensive and distracting for agents;
- product decisions should be distilled into the operating brief, decision records, or memory.

When retention in the repository is unavoidable, place it under:

```text
docs/archive/private/
```

and prevent default agent loading.

---

## The Full One-Stop PDF

Store the human-readable PDF outside the active context directory:

```text
docs/strategy/Codize_One_Stop_Plan_Prevention_First_Recovery_Capable.pdf
```

The PDF remains valuable for:

- detailed growth strategy;
- beta plans;
- institutionalization;
- metrics;
- competition preparation;
- historical July–October sequencing;
- human review.

The active Markdown operating brief is the agent-facing synthesis.

Repository state outranks stale milestone labels and dates in the PDF.

---

## Decision Records

Use:

```text
docs/decisions/
```

for narrow durable decisions.

Current recommended record:

```text
docs/decisions/guided_workflow_navigation.md
```

Decision records should not duplicate the full operating brief. They should explain a specific accepted choice in enough detail to guide later implementation.

---

## Final Recommended Structure

```text
docs/
├── context/
│   ├── README.md
│   ├── context_authority.md
│   ├── codize_product_operating_brief_v2.md
│   └── codize_master_spec_v2.1.md
│
├── decisions/
│   └── guided_workflow_navigation.md
│
├── strategy/
│   └── Codize_One_Stop_Plan_Prevention_First_Recovery_Capable.pdf
│
├── plans/
│   └── deferred/
│       └── multi_project_dashboard_plan.md
│
└── archive/
    ├── plans/
    │   └── completed/
    │       └── m13_ai_workflow_workspace_plan.md
    ├── product/
    │   └── codize_product_vision_v3.md
    ├── learning-roadmaps/
    │   └── codize_roadmap_v2.html
    └── tooling/
        └── fable_5_prompting.md
```

Keep `conversations.json` outside Git when possible.

---

## Rules for Adding a New Context File

Add a file to `docs/context/` only when it is:

- durable for months;
- needed across many future milestones;
- authoritative for product direction or source precedence;
- concise enough to load routinely;
- not already represented by code, tests, decisions, or memory.

Do not add:

- per-milestone prompts;
- completion reports;
- full transcripts;
- model guides;
- temporary schedules;
- large research dumps;
- duplicate summaries;
- speculative feature plans.

Prefer updating an existing active context document over creating another overlapping source.
