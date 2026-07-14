---
name: codize-ui-ux
description: Build, substantially modify, or audit user-facing Codize interfaces while preserving Codize's engineering-cockpit identity, shared workflow, product truth, accessibility, responsive behavior, and pilot-tested cognitive-load conventions. Use for new pages, major frontend workflow changes, dashboards, multi-step forms, workflow navigation, complex loading/error/empty/stale/completion states, responsive or accessibility work, UI refreshes, visual-hierarchy or cognitive-load reduction, and explicit Codize UI/UX polish or audit requests. Do not use for backend-only, database, API-only, migration, pure schema/type, isolated unit-test, documentation-only, tiny copy, small nonvisual bug-fix, or interface-free security work.
---

# Codize UI/UX

Use one of two explicit modes:

- **BUILD** — create or substantially modify a user-facing interface.
- **AUDIT** — review a substantial frontend milestone or an existing interface.

State the mode in the UI intent plan or audit heading. If the request includes both, audit the current journey first, then build the scoped fixes.

## Apply the authority order

Resolve every choice in this order:

1. Accessibility and usability
2. Actual Codize pilot feedback
3. Clear task completion
4. Current Codize product and frontend conventions
5. Established UX principles
6. Visual polish and aesthetic preference

Treat Codize as prevention-first and recovery-capable. Help the student see where they are, what happened, what they must decide, what remains uncertain, and what action comes next.

Before acting, inspect the surrounding journey, current components, styles, navigation, adjacent pages, and relevant product conventions. Read the active product brief and accepted decisions through [references/source-index.md](references/source-index.md). Do not invent a new aesthetic, component library, workflow, or backend behavior.

## Test every recommendation

For each material design choice, answer:

1. What user problem does it solve?
2. Is that problem present in the current interface?
3. Does it conflict with accessibility, product truth, current conventions, or pilot evidence?
4. Is it functional, visual, or subjective?
5. What is the smallest change that solves it?

Reject advice that cannot pass this test. Never apply transcript guidance mechanically.

## MODE 1 — BUILD

1. Inspect the full user journey and adjacent states, not only the requested component.
2. Identify the user goal, current workflow state, primary action, secondary actions, essential information, optional information, likely confusion, and recovery path. Preserve state-aware guided navigation: show the journey, emphasize the current step, and do not expose future modules as equal destinations.
3. Read the relevant references below and inspect reusable Codize components/tokens before creating a pattern.
4. Write a concise **UI intent plan** covering goal, state, hierarchy, primary action, information disclosure, reused patterns, responsive behavior, and verification.
5. Design every applicable state: prerequisite, empty, loading, success, saved, error, retry, disabled, incomplete, complete, stale, and recovery.
6. Keep one obvious primary action for each state. Use progressive disclosure only for secondary help, advanced controls, source detail, and destructive secondary actions.
7. Preserve provenance, uncertainty, student agency, and honest self-reported labels. Never imply AI output, evidence, a Change Map, or a Review decision is verified when it is not.
8. Prefer current components, tokens, spacing, copy tone, navigation, and state patterns. Avoid nested-card overload, excessive borders or badges, resting glow, giant gutters, repeated instructions, and equal emphasis everywhere.
9. Implement semantic HTML, keyboard-operable controls, visible focus, meaningful status announcements, and reduced-motion behavior.
10. Check approximately 390px, tablet, 1080p, and 1920px. Test long labels, paths, code, errors, and user content.
11. Inspect the rendered interface in a browser when browser tools are available. Refine hierarchy, density, wrapping, feedback, and focus states from the rendered result.
12. Run relevant frontend tests, typecheck, lint, and build. Keep implementation scoped; do not redesign unrelated pages.

## MODE 2 — AUDIT

Audit the complete task flow, not a screenshot in isolation. Use [references/ui-audit-rubric.md](references/ui-audit-rubric.md).

Review user-goal and next-action clarity, information and visual hierarchy, cognitive load, progressive disclosure, consistency, content density, system status, loading/save/error recovery, empty and stale states, trust, provenance, uncertainty, user control, accessibility, keyboard interaction, responsive behavior, and consistency with Codize.

Separate findings into:

1. Confirmed usability or accessibility defects
2. Likely improvements
3. Subjective aesthetic preferences

Fix or recommend confirmed defects first. Include evidence, user impact, location/state, smallest suitable change, and verification. Do not redesign merely because a different style is fashionable.

## Route to references

- Start with [references/codize-product-ui.md](references/codize-product-ui.md) for any protected-app work.
- Read [references/workflow-and-cognitive-load.md](references/workflow-and-cognitive-load.md) for navigation, dashboards, multi-step flows, text density, or next-action clarity.
- Read [references/forms-feedback-and-states.md](references/forms-feedback-and-states.md) for forms, async operations, drafts, save/error/retry, empty, complete, or stale states.
- Read [references/visual-hierarchy.md](references/visual-hierarchy.md) for hierarchy, density, grouping, typography, color, polish, and motion.
- Read [references/responsive-accessibility.md](references/responsive-accessibility.md) for any user-facing implementation or audit.
- Read [references/landing-page-design.md](references/landing-page-design.md) only for public landing/marketing surfaces.
- Read [references/source-index.md](references/source-index.md) when checking provenance, authority, or transcript attribution.

## Non-negotiable boundaries

- Preserve the established Codize visual system; do not create generic SaaS, school-LMS, quiz, or fake-IDE UI.
- Optimize for comprehension and task completion, not screenshots.
- Use motion only when it clarifies state, relationship, or continuity.
- Keep uncertainty visible and AI-generated or student-reported material honestly labeled.
- Do not remove accessibility semantics or introduce a component library without explicit approval.
- Do not change backend behavior merely to simplify UI implementation.
- Do not expand milestone scope or start unrelated work.
