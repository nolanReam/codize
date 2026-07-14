# Codize Product UI

## Product truth

Codize is a prevention-first, recovery-capable, guided AI coding workflow trainer. It uses one shared workflow for beginners, builders, and students recovering from the 80% Trap. It is not a generic roadmap, checklist, dashboard, quiz, IDE, LMS, or AI coding assistant.

The interface must help a student:

- direct AI deliberately;
- bring back what changed;
- review decisions and scope;
- verify behavior with honest evidence;
- explain the implementation;
- preserve uncertainty and next actions;
- produce a Project Defense Report without unsupported claims.

Source: `[A1]`

## Preserve the guided workflow

- **Principle:** Show the full journey for orientation, emphasize the current actionable step, protect prerequisites, and keep completed work available through the project record.
- **Why:** Codize knows the expected next action; asking students to choose among equal internal modules creates avoidable navigation work.
- **Use:** Project Home, shell navigation, progress, handoffs, stale states, and direct-route prerequisite handling.
- **Do not use:** Do not hide the journey, prevent safe review of completed work, or treat navigation visibility as the only lifecycle control.
- **Anti-pattern:** Prompt, Import, Change Map, Review, Verification, Evidence, Defense, and Report all appear as equal unrestricted destinations.
- **Codize:** Keep Project Home available, make one state-aware Continue action dominant, show future steps as unavailable with reasons, preserve readable stale records, and require deliberate rebuilds after upstream changes.
- **Source:** `[A1, A7]`

## Preserve the current identity

- **Principle:** Extend the existing sharp, serious, high-contrast engineering cockpit.
- **Why:** Familiarity and product coherence reduce learning cost.
- **Use:** All protected-app work; adapt landing treatment without severing the identity.
- **Do not use:** Do not introduce a new aesthetic, component library, fake IDE, childish gamification, or generic SaaS dashboard styling.
- **Anti-pattern:** Trend-driven redesign, decorative glass everywhere, or a new palette/type system for one milestone.
- **Codize:** Reuse `--bg #0d0d12`, dark surfaces, violet `--accent #a78bfa`, DM Sans, Space Grotesk, IBM Plex Mono, current radii, restrained borders, status colors, and accent-left-rail primary card.
- **Source:** `[A1, A2, A6]`

## Reuse before inventing

Inspect these seams before building a pattern:

- app shell and navigation: `frontend/app/app/layout.tsx`
- core tokens/layout/state styles: `frontend/app/globals.css`
- workflow navigation: `frontend/components/WorkflowSteps.tsx`
- collapsed guidance: `GuideCard.tsx`, `LoopOverview.tsx`
- async/prerequisite/save: `Async.tsx`, `NotReady.tsx`, `SaveBar.tsx`
- workflow loading/saving: `frontend/lib/useWorkflowSection.ts`
- typed contracts and pure UI logic: `frontend/lib/types.ts` plus feature-specific libraries
- accessible linked decisions: `LinkedReviewTarget.tsx`

Prefer extending a pure helper and its tests over duplicating page logic. Do not force reuse when the existing component's semantics or state contract is wrong.

## Preserve workflow semantics

- **Principle:** UI labels and progress must match real backend/client contracts.
- **Why:** False progress damages trust and teaches the wrong workflow.
- **Use:** Cockpit, workflow navigation, handoffs, reports, and state pills.
- **Do not use:** Do not invent fields, endpoints, automatic transitions, scores, or verification claims.
- **Anti-pattern:** Treating saved artifacts as completed build tasks or showing hidden gate/evaluator data.
- **Codize:** Product data flows Frontend → FastAPI; Supabase is auth-only. Generate occurs externally. Saved workflow sections, Change Map, linked Review targets, Verification suggestions/results, evidence, gate state, and roadmap phase progress remain distinct. Only the gate advances phases. Hidden scores, thresholds, evaluator reasoning, prompts, and secrets never enter UI.
- **Source:** `[A1–A6]`

## Keep honesty visible

- **Principle:** Distinguish AI draft, student claim, student decision, observed result, and verified fact.
- **Why:** Codize trains reasoning; certainty theater defeats the product.
- **Use:** Evidence, Verification, Change Map, Review, Defense context, outcomes, and report copy.
- **Do not use:** Do not call confirmation approval, a claim proof, or `needs_verification` a completed test.
- **Anti-pattern:** Green success treatment for ambiguous or self-reported state.
- **Codize:** Use “appears to have changed,” “confirmed in Change Map,” “corrected by you,” “self-reported,” “needs testing,” “uncertain,” “skipped,” and “n/a” precisely. Keep provenance snapshots server-owned and uneditable where designed.
- **Source:** `[A1, A3–A6]`

## Use the established tone

Write direct, useful, warm, non-shaming copy.

Prefer:

- Stop debugging blindly.
- Review and try again.
- One small piece is enough.
- Keep what you know; mark what still needs inspection.
- Be ready to defend what you shipped.

Avoid “cheating,” “fake engineer,” “prove you are not a prompter,” “AI is bad,” exam-like language, and internal evaluator strictness. Project Defense is coaching around the student's project, not a textbook quiz.

Source: `[A1; P2; A2]`

## Scope discipline

- Keep product changes inside the requested surface and milestone.
- Do not redesign adjacent pages solely for visual consistency; note follow-up opportunities separately.
- Do not change backend behavior to avoid a frontend state.
- Do not create multi-project UI until its data contract exists.
- Do not add automated verification, repo access, provider calls, or downstream artifact use without the required milestone/spec approval.
