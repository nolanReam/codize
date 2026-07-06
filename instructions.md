# Codize M13D.5 — Landing Page Precision Fix Pass

Fix the issues found in the M13D.4 visual review.

This is a focused frontend design/UX polish milestone.

Do not start M14.

Do not change backend behavior.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations.

Do not add analytics.

Do not add product features.

Do not redesign protected app screens except the login page visual/layout fixes explicitly listed below.

Do not replace the landing page from scratch.

## Current State

M13D.4 was completed at commit:

- `833e48b76890cce9c58f1f94ef54b00e96631659`

M13D.4 completed:

- Garamond removed
- centered landing scenes
- scroll-driven Build Loop
- shorter Build Loop cards
- premium hero TiltCard
- CSS-simulated glass
- sign-in-card reference used as inspiration only
- no liquid-glass-js
- no React Three Fiber
- no backend changes

The page is closer, but the user found several concrete issues that need fixing.

## User Feedback To Address

Fix these exact issues:

1. Bigger headline text still feels like a different font from body text.
2. The hero headline should be larger.
3. Header and footer appear to stop after a certain width; the user wants them to extend across the full screen.
4. The whole screen should feel used, not boxed into a narrow layout.
5. The terminal text inside the hero should be left-aligned like a real terminal.
6. The terminal window itself should remain centered.
7. The scroll-expanding Build Loop works but feels clunky.
8. When a new Build Loop box opens, the other boxes briefly increase in height and then shrink back down; fix that janky height behavior.
9. A Build Loop box should stay open longer while scrolling so users have time to read it.
10. The Gate section is confusing because it shows two boxes without enough clear flow.
11. The Gate section should simulate the user answering gate questions through a scroll animation.
12. The “80% Trap” concept needs more proof/context for skeptical users.
13. When clicking sign in from far down the landing page, the login page opens scrolled down.
14. The login page should not be scrollable and should be completely centered on screen.

## Goal

Make the landing page feel smoother, clearer, more premium, and less confusing.

This is not a new concept pass.

This is a precision fix pass.

Prioritize:

- typography consistency
- full-width header/footer
- better hero scale
- real terminal alignment
- smoother scroll timing
- clearer Gate story
- evidence-backed credibility
- centered non-scroll login page

## Typography Fix

The user does not like the big headline font because it still feels different from the body text.

Make large text and body text feel like the same type system.

Do not use Garamond, Cormorant, Fraunces, or any fancy editorial serif.

Use the closest safe TeoriaMF-like direction already available in the app.

If the project currently uses Space Grotesk / DM Sans / IBM Plex Mono, choose the best cohesive combination, but make the big titles feel closer to the body/UI type.

Important:

- title text should not feel like a different font family from body text
- headings can still be larger/bolder, but not stylistically separate
- preserve mono only for terminal/code/system labels
- do not add unlicensed font files
- do not download proprietary font files
- do not use random free font websites

## Hero Fixes

Improve the hero scene.

Requirements:

- make the hero headline larger
- keep it centered
- keep the terminal window centered
- make terminal text inside the terminal left-aligned
- terminal should feel like a real terminal/dev panel
- maintain the premium glass/tilt behavior
- maintain reduced-motion safety
- do not make the terminal text centered
- do not make the hero cramped on mobile

The hero should clearly communicate:

> AI built your first 80%. Now you’re stuck fixing the rest.

## Header / Footer Width Fix

The header and footer currently appear to stop after a certain width.

Fix them so the header and footer visually extend across the whole screen.

Requirements:

- full-bleed visual background/border/glass treatment
- content may still have a readable max-width inside, but the bar/background should span the viewport
- no awkward boxed/stopped appearance
- footer should feel like it belongs to the full page width
- no horizontal overflow

Do not make the header huge.

Do not make the footer cluttered.

## Build Loop Scroll Smoothness Fix

The Build Loop currently works, but feels clunky.

Fix the scroll-driven expanding boxes.

Requirements:

- scroll remains the primary activation mechanism
- active stage changes smoothly as the user scrolls
- when a box opens, the whole row/section should not jump taller and then shrink
- lock or stabilize the card container height so expansion does not create layout jank
- make cards shorter if needed
- match content to card height
- active card should remain active for a longer scroll range
- add hysteresis/dead-zone/leeway so micro-scrolling does not immediately snap to the next card
- users should have enough time to read the active card while continuing to scroll
- hover/focus/click may remain secondary, but should not fight scroll state
- keyboard and mobile must remain usable
- reduced-motion must remain usable

Possible implementation ideas:

- divide the scroll track into wider stage bands
- use a sticky panel with fixed-height card container
- compute active stage with progress thresholds that have more spacing
- keep active card open until scroll passes the next clear threshold
- avoid measuring dynamic card height during animation
- avoid content entering/exiting in a way that changes parent height

The Build Loop should feel like a smooth scroll story, not a jittery accordion.

## Gate Section Fix

The Gate section is confusing.

Make it tell a simple user flow through scroll animation.

The goal is that a visitor instantly understands:

1. User answers a gate question.
2. Codize asks a deeper follow-up.
3. User explains implementation.
4. Codize returns a defense status.
5. The report records the result.

Possible visual:

- one centered gate simulation panel
- scroll reveals turn 1, turn 2, turn 3, evaluation
- chat/terminal hybrid
- user answer cards slide in
- gate question cards appear one at a time
- final state: `DEFENSE STATUS: READY / NEEDS REVIEW`
- small report preview updates beside or below it

Avoid the current “two boxes with unclear meaning” feel.

Do not expose hidden scores.

Do not show evaluator reasoning.

Do not imply the landing page is running a real gate.

This is a simulated visual explanation only.

Use labels like:

- `turn_01`
- `follow_up`
- `explain_implementation`
- `defense_status`
- `recorded_in_report`

Make the section centered and easy to understand.

## 80% Trap Proof / Credibility Fix

The “80% Trap” is a product metaphor, not a literal statistic.

Do not present “80%” as a verified numerical research claim.

Add a concise credibility layer explaining the real problem:

- AI coding tools can generate code quickly.
- Generated code may still be insecure, incorrect, or hard to maintain.
- Users can become overconfident in AI-assisted code.
- The missing step is review, verification, and explanation.

Add either:

- a short proof paragraph
- a small “Why this matters” section
- a small footnote-style citation row
- or a compact evidence card

Keep it concise.

Do not overwhelm the landing page.

Do not add a huge academic block.

Use these evidence sources or equivalent reputable sources already known to the repo/docs if available:

1. “Do Users Write More Insecure Code with AI Assistants?” by Perry et al. / Stanford-affiliated security study.
2. “Security Weaknesses of Copilot-Generated Code in GitHub Projects: An Empirical Study.”
3. Optional: recent developer survey or platform report about AI code review/verification bottlenecks, but only if sourced clearly.

User-facing copy can say something like:

> “The 80% Trap is Codize’s name for a real pattern: AI can accelerate code generation, but research has found that AI-assisted code can still introduce security issues and overconfidence. Codize focuses on the missing workflow after generation: review, verify, explain.”

If adding citations, use compact parenthetical or footnote-style links.

Do not overclaim.

Do not say Codize has proven learning outcomes yet.

## Login Page Scroll Fix

When the user clicks Sign In from far down the landing page, the login page opens scrolled down.

Fix this.

Requirements:

- `/login` should reset to the top on navigation
- login page should be completely centered on screen
- login page should not be vertically scrollable under normal desktop conditions
- use `min-height: 100svh` or equivalent
- ensure body/page scroll state does not carry over visually
- preserve existing Supabase auth behavior
- do not add fake Google sign-in
- do not add fake forgot-password flows
- do not replace auth logic with demo state

It is acceptable to apply the same premium glass/card style to the real login page if it preserves all auth behavior.

## Sign-In Reference Boundary

The provided sign-in card reference is a visual/interaction reference only.

Use inspiration from:

- centered full-screen login composition
- glass card
- subtle glow
- edge light
- premium input focus behavior
- tilt/glass behavior if safe

Do not copy:

- fake Google sign-in
- fake forgot-password
- “StyleMe” copy
- demo loading state that replaces real auth
- unrelated icons or logo
- unsupported auth methods

## Scope Boundary

This milestone may modify:

- public landing page
- landing-specific components
- landing/global CSS
- font setup
- login page layout/styling
- tiny shared visual utilities if needed

Do not modify:

- backend
- auth logic
- intake flow
- gate logic
- report logic
- workflow artifact logic
- database
- protected app functionality

## Accessibility / Performance Requirements

Must support:

- mobile layout
- keyboard navigation
- visible focus states
- good contrast
- no raw HTML rendering
- no horizontal overflow
- no scroll-jacking
- reduced-motion support
- no unusable hover-only interactions
- smooth scroll-driven Build Loop without layout jank

Animations should enhance the story, not block usage.

## Testing / Verification

Run:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

If backend files change accidentally, stop and explain.

Run a local visual smoke:

1. landing page loads
2. hero headline is larger
3. big text and body text use cohesive font direction
4. header spans full viewport visually
5. footer spans full viewport visually
6. terminal window is centered
7. terminal text is left-aligned
8. Build Loop active stage changes smoothly on scroll
9. Build Loop boxes do not height-jump when active card changes
10. active Build Loop card stays open long enough while scrolling
11. Gate section explains answer flow clearly
12. 80% Trap proof/context appears without overclaiming
13. CTA routes to `/login`
14. `/login` opens centered and not scrolled down
15. login page is not scrollable under normal desktop viewport
16. mobile layout has no horizontal overflow
17. keyboard focus is visible
18. reduced-motion mode is safe
19. no obvious console errors

If login page styling changed, verify existing auth behavior is preserved at least visually and structurally.

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `.claude/memory/frontend-conventions.md`
- `CLAUDE.md`

Only update docs if new landing-page conventions, font decisions, scroll behavior, citation/proof copy, or login-page behavior should be remembered.

Do not rewrite product vision docs.

## End Requirements

At the end, output:

- user feedback addressed
- design fixes implemented
- files changed
- dependencies added/removed
- font changes
- login page changes
- how Build Loop smoothness was fixed
- how Gate section flow was clarified
- how 80% Trap proof/context was added
- whether citations were added and where
- accessibility/performance notes
- commands run
- test/build results
- visual smoke result
- secret scan result
- known issues
- git commit hash
- next step: local visual review, then first pilot tester

Commit completed landing page precision fix pass.

Stop after commit.