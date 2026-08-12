# Codize context authority

**Status:** Active V2 authority router/index
**Purpose:** Identify the source that governs each kind of decision without turning this index into a competing product specification.

This file routes to authority. It does not override, summarize away, or reinterpret the Codize V2 Product Thesis.

## First rule

For persistent product decisions, the [Codize V2 Product Thesis](v2/codize_v2_product_thesis.md) is the highest authority.

A current user instruction controls the scope, permissions, deliverables, and stop conditions of the active task. It does not silently redefine Codize V2. A durable product change must be reconciled with the canonical V2 documents and recorded deliberately.

## Authority hierarchy

Use this order when sources conflict:

1. **[Codize V2 Product Thesis](v2/codize_v2_product_thesis.md)** — why Codize exists, who it serves, product boundaries, principles, positioning, and the highest-level V2 direction.
2. **[Codize V2 Exact UX Specification](v2/codize_v2_exact_ux_specification.md)** — interaction behavior, state transitions, information architecture, copy intent, teaching behavior, and forbidden UX patterns. It is subordinate to the Product Thesis.
3. **[Codize V2 Character System Blueprint](v2/codize_v2_character_system_blueprint.md)** — character visuals, animation semantics, customization, accessories, and cosmetic unlock rules only. It does not redefine teaching or product behavior.
4. **[Approved Codize V2 Figma](https://www.figma.com/design/QBGSdTLG7iQ2xEFzU7v0Li/Codize-V2-Product-Design)** — visual composition, styling, sizing, component appearance, responsive layout, and motion intent only. Figma cannot silently change product behavior.
5. **Future V2 Technical Architecture / State Model** — not written or accepted yet. It will govern V2 implementation architecture after an explicit decision. Do not infer it from V1 tables, routes, JSONB, or lifecycle state.
6. **Future V2 Learning / Teaching Policy** — not written or accepted yet. The Product Thesis and Exact UX Specification provide current product constraints, but evidence schemas, fading thresholds, retention, and detailed inference policy remain unresolved.
7. **Accepted V2 decision records** — narrow, explicit decisions in `docs/decisions/` that identify their V2 status and do not conflict with higher authority.
8. **Current implementation truth** — code, tests, migrations, Git history, and verified deployment evidence. These control what exists today, not what V2 should become.
9. **Durable V1 technical references** — authentication, JWT/JWKS, RLS and ownership, write boundaries, validation, secret handling, provenance, uncertainty, prompt-injection defenses, deployment boundaries, and adversarial-test lessons. These are reusable engineering evidence, not V2 product architecture.
10. **Historical V1 product documents** — old intake, archetype, roadmap, phase, gate, Defense, workflow-navigation, pilot, release, milestone, and product-vision documents. They explain the current/legacy system or its history and never override V2.

## Conflict routing

| Question | Source to use first |
|---|---|
| What is Codize V2 and why does it exist? | V2 Product Thesis |
| What should a student see or be able to do? | Product Thesis, then Exact UX Specification |
| How do characters, accessories, animation, and cosmetic unlocks behave? | Character System Blueprint, within the Thesis and Exact UX |
| What should the interface look like? | Approved Figma, within the three canonical documents |
| How should V2 data, APIs, state, transactions, compatibility, or storage work? | Future accepted V2 Technical Architecture; until it exists, the question is unresolved |
| How should learner evidence, fading, help, retention, or teaching inference work? | Future accepted V2 Learning / Teaching Policy; until it exists, do not invent the contract |
| What is implemented now? | Current code, tests, migrations, Git history, and verified deployment evidence |
| How does the current V1 subsystem work? | Current implementation plus the labeled backend/frontend/schema/memory references |
| Which trust/security lessons survive? | Current implementation evidence plus labeled durable V1 technical references |
| What did an old milestone intend? | Historical V1 product documents and archive, never as V2 authority |

## V1 mechanics: implementation truth, not V2 requirements

The current repository implements several V1 mechanics. They remain real compatibility and maintenance constraints until deliberately migrated, but they are not mandatory future V2 architecture:

- five sequential intake questions;
- exactly three archetypes;
- a fixed seven-phase roadmap;
- `current_phase` as lifecycle state;
- the visible Prompt → Import → Change Map → Review → Verification → Evidence → Defense → Report journey;
- mandatory Project Defense;
- binary PASS/FAIL gates and cooldowns;
- gate-controlled advancement;
- hidden-score functional unlock thresholds;
- phase-scoped assignment and workflow-artifact rules.

Do not delete, repurpose, or weaken these implemented contracts casually. Do not preserve them as V2 requirements merely because they exist.

## Durable technical rules that survive the authority reset

This reset does not weaken:

- server-side authentication and authorization;
- owner-scoped access and RLS;
- backend-only secrets and external-service boundaries;
- input/output validation and fail-closed handling;
- provenance and honest uncertainty;
- untrusted-content isolation and prompt-injection defenses;
- safe writes, idempotency, staleness, and concurrency protections;
- accessibility, responsive behavior, and truthful system status;
- evidence-backed verification and explicit reporting of what was not verified.

Their future V2 implementation shape remains subject to the future Technical Architecture and Learning / Teaching Policy.

## Agent reading order

Before product, workflow, architecture, or major UX work:

1. read this router;
2. read the Product Thesis completely;
3. read the relevant canonical specification(s);
4. inspect current code/tests/migrations for implementation truth;
5. read only the relevant labeled technical references or V2 decisions;
6. identify unresolved architecture explicitly instead of filling gaps with V1 assumptions.

Do not read `conversations.json` unless the user explicitly requests historical research and authorizes it.

## Change control

When accepting a durable V2 decision:

1. identify the higher authority it implements;
2. state what remains unresolved;
3. state what V1 behavior is compatibility-only;
4. record security, provenance, accessibility, and migration consequences;
5. update this router only if the authority path itself changes.

Never edit historical documents to make them appear current.
