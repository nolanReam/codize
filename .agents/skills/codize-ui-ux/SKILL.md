---
name: codize-ui-ux
description: Build, substantially modify, or audit Codize interfaces using the canonical V2 Product Thesis, Exact UX Specification, Character Blueprint, approved Figma visual composition, accessibility, product truth, responsive behavior, and progressive disclosure. Use for user-facing product work; do not use for documentation-only, backend-only, schema-only, or nonvisual tasks.
---

# Codize UI/UX

Use **BUILD** for implementation and **AUDIT** for review. If both apply, audit the journey first.

## Authority

Read [references/source-index.md](references/source-index.md) and [references/codize-product-ui.md](references/codize-product-ui.md). Product Thesis is highest authority; Exact UX controls behavior; Character Blueprint controls its subsystem; approved Figma controls visual composition only.

Classify the work before acting:

- **V2 design/build:** canonical V2 sources govern.
- **V1 maintenance:** current components and contracts are implementation truth, not future design authority.

## BUILD

1. Inspect the full journey, adjacent states, current contracts, and approved Figma context.
2. Identify the student's goal, one primary cognitive task, one primary action, optional information, likely confusion, help path, and recovery path.
3. Reuse appropriate implementation primitives without inheriting obsolete V1 workflow semantics.
4. Plan empty, loading, saved, error, retry, incomplete, complete, uncertainty, stale, recovery, and reduced-motion states as applicable.
5. Preserve student agency and distinguish student statements, agent claims, repository observations, system inferences, performed checks, and evidence.
6. Keep the conversational Build experience orchestrated; the model may supply wording but cannot invent workflow or UI primitives.
7. Use semantic HTML, keyboard interaction, visible focus, screen-reader status, readable contrast, and responsive progressive disclosure.
8. Inspect roughly 390px, tablet, 1080p, and wide desktop with real/long content.
9. Verify rendered behavior and run relevant type, lint, test, and build checks.

## AUDIT

Audit the complete task flow. Separate confirmed defects, likely improvements, and subjective preferences. For each finding give evidence, impact, location/state, smallest safe fix, authority source, and verification.

Prioritize comprehension, next-action clarity, truth/uncertainty, recovery, accessibility, and student control before aesthetic preference.

## V2 boundaries

- One project, one current change, one useful habit at a time.
- Project / Build / Learning / History are primary; Character / Settings secondary; Something broke contextual.
- Character guidance is supportive, not required to understand state.
- Do not show phases, archetypes, gates, scores, a mandatory Defense, or the full V1 workflow merely because current code contains them.
- Do not require every change to traverse the same ceremony.
- Do not create a generic chatbot, school LMS, fake IDE, or dashboard-first experience.
- Do not change backend behavior to avoid handling a UI state.
- Do not invent unresolved V2 architecture.

## References

- [codize-product-ui.md](references/codize-product-ui.md) — V2 product/UX rules and V1 boundary
- [workflow-and-cognitive-load.md](references/workflow-and-cognitive-load.md) — current change, progressive disclosure, recovery
- [forms-feedback-and-states.md](references/forms-feedback-and-states.md) — forms and async state
- [visual-hierarchy.md](references/visual-hierarchy.md) — hierarchy and polish
- [responsive-accessibility.md](references/responsive-accessibility.md) — required for user-facing work
- [landing-page-design.md](references/landing-page-design.md) — V2 public landing
- [ui-audit-rubric.md](references/ui-audit-rubric.md) — audit checklist
