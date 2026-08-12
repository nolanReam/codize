# Codize UI/UX

## Purpose

Guide Codize interface work through the canonical V2 product and UX authority while preserving current V1 behavior during maintenance.

## Sources

Read `docs/context/context_authority.md`, then the V2 Product Thesis and Exact UX Specification. Read the Character System Blueprint for character/customization work. Approved Figma controls visual composition, styling, layout, responsive behavior, component appearance, and motion intent only.

The current dark engineering-cockpit UI is V1 implementation evidence, not a mandatory V2 aesthetic. Do not derive a new V2 visual system from old CSS when approved Figma is available.

## V2 rules

- The interface is beginner-first, conversational, character-guided, and project-specific.
- Show one primary cognitive task and one obvious primary action at a time.
- Keep Project / Build / Learning / History primary; Character / Settings secondary; Something broke contextual.
- Use progressive disclosure for secondary detail and help.
- Preserve student agency, uncertainty, provenance, accessible help, and recovery.
- Guidance fades when the student demonstrates the habit.
- Do not expose phases, gates, archetypes, provenance ontology, or a mandatory full workflow merely because V1 implements them.
- Character animation, sound, and expression are optional/supportive and must respect reduced motion and sound settings.
- Maintain keyboard access, semantic controls, visible focus, readable contrast, responsive layouts, and screen-reader status.

## Current V1 maintenance

When a task explicitly changes the current V1 interface, preserve its API and lifecycle contracts unless authorized otherwise. Label V1-specific choices as implementation maintenance; do not present them as future V2 direction.
