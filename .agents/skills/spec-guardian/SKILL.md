# Codize Spec Guardian

## Purpose

Prevent product drift and accidental reuse of V1 mechanics as V2 requirements.

Use before product logic, workflow, architecture, runtime prompts, learning behavior, characters, or major UX changes.

## Required authority

Read in order:

1. `docs/context/context_authority.md`
2. `docs/context/v2/codize_v2_product_thesis.md`
3. `docs/context/v2/codize_v2_exact_ux_specification.md`
4. `docs/context/v2/codize_v2_character_system_blueprint.md` when relevant

Approved Figma controls visual composition only. Code, tests, migrations, Git history, and verified deployment evidence control current implementation truth.

Do not read `conversations.json` unless the user explicitly authorizes historical research.

## First classification

Before acting, state which kind of work this is:

- **V2 product/design work** — canonical V2 documents govern.
- **Current V1 maintenance** — preserve existing contracts while labeling them implementation-only.
- **V2 architecture planning** — do not implement; identify unresolved decisions and produce an accepted decision/architecture artifact only when requested.

## V2 product guardrails

- Product Thesis is highest authority.
- One project, one current change, one useful habit at a time.
- Chat is the Build interface; constrained system logic owns workflow and teaching decisions.
- Students keep using an external coding agent; Codize guides and supervises rather than silently coding.
- Student agency, truthful uncertainty, project grounding, just-in-time teaching, progressive help, and per-competency fading are required.
- Do not force a full workflow for every change.
- Do not create global mastery scores, compliance rewards, routine Project Defense, or hidden advancement gates.
- Character differences and unlocks are cosmetic, evidence-backed, and never pedagogical power.

## V1 rules that are not V2 invariants

Exactly five intake questions, exactly three archetypes, seven phases, `current_phase`, the visible eight-stage journey, mandatory Defense, PASS/FAIL gates, cooldowns, gate-controlled advancement, functional gate-score unlocks, and phase-scoped assignment rules describe the implemented V1 system only.

When maintaining V1, preserve them unless the task explicitly changes that system. When designing V2, do not carry them forward without an accepted V2 decision.

## Unresolved architecture

No V2 Technical Architecture / State Model or Learning / Teaching Policy is accepted. Do not invent schemas, routes, state machines, persistence, compatibility, GitHub trust boundaries, learner thresholds, retention, or character entitlement storage.

## Durable constraints

Never weaken authentication, authorization, RLS/ownership, server-only secrets, validation, provenance, uncertainty, write boundaries, staleness, prompt-injection defenses, accessibility, or verified reporting.

## Review questions

1. Which canonical source authorizes the behavior?
2. Is a V1 implementation fact being mistaken for V2 direction?
3. Is an unresolved architecture choice being smuggled into code or UX?
4. Does the change preserve student agency, truth, and appropriate independence?
5. Is the smallest safe scope being used?
