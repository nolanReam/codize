# Codize M13D.3 — Landing Page Spatial + Scroll Experience Pass

Improve the landing page after M13D.2 visual review.

This is a focused frontend design-polish milestone.

Do not start M14.

Do not change backend behavior.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations.

Do not add analytics.

Do not add product features.

Do not redesign protected app screens.

Do not replace the M13D.2 landing page from scratch unless a section is clearly broken.

## Current State

M13D.2 improved the landing page with:

- premium dark devtool aesthetic
- animated patch-loop terminal hero
- 80% Trap git-log transcript
- CI-style Build Loop rail
- Project Defense section
- closing CTA
- next/font loading
- reduced-motion support

Commit:

- M13D.2 landing redesign: `edbfabc`

The visual review found that the page is better, but still not premium enough.

Main issues:

1. Sections feel too squished.
2. Too much text appears close together.
3. The page still feels like stacked content blocks, not an interactive scroll experience.
4. The Build Loop timeline should be more cinematic and scroll-driven.
5. The typography should feel more editorial and premium.
6. The page needs more spatial depth and distinctive UI components.
7. The terminal idea is good, but the whole page still needs stronger scene-by-scene storytelling.
8. The landing page should feel more like a premium interactive website, not a dense one-page product explainer.

## Goal

Turn the landing page into an interactive, full-screen, premium devtool landing experience.

The page should feel like a sequence of scenes:

1. The 80% Trap
2. The patch loop
3. The Codize Build Loop
4. Project Defense
5. Defense Report
6. Final CTA

Each major section should have breathing room and feel intentional.

The user should not feel overwhelmed by dense text blocks.

The page should feel like something designed around Codize’s specific product idea, not a generic SaaS template.

## Design Direction

The page should feel:

- premium
- spacious
- interactive
- editorial
- cinematic but usable
- developer-focused
- unique to Codize
- not generic SaaS
- not a template
- not childish
- not purple-gradient AI slop

Think:

- high-end devtool landing page
- editorial typography
- full-screen scroll scenes
- interactive workflow visualization
- glassy cockpit panels
- terminal/dev environment aesthetic
- Codize as the intervention in the AI patch loop

## Critical Layout Change

Make each major landing section feel closer to a full-screen scene.

Use:

- `min-height: 100svh` where appropriate
- strong vertical spacing
- fewer competing text blocks per viewport
- one dominant visual per section
- sticky/scroll-driven sections where useful
- responsive fallbacks for mobile

Do not simply add more text or more cards.

Reduce density.

Let each idea breathe.

The page should not feel like five compact sections stacked together.

## Section Requirements

### 1. Hero Scene

Keep the animated terminal/patch-loop idea, but make the hero feel more cinematic and less cramped.

Improve:

- spacing
- scale
- visual hierarchy
- terminal depth
- overlay drama
- glass/cockpit feel
- mobile composition

The hero should still clearly say:

> AI built your first 80%. Now you’re stuck fixing the rest.

The terminal should remain the signature visual.

The CTA should stay obvious.

Do not add real AI calls.

Do not add real code execution.

The hero should fit the viewport better and feel like an opening scene, not a compressed header.

### 2. Patch Loop Scene

The 80% Trap transcript currently works, but it should become a full scene, not a compact block.

Make it feel like the user is descending into the patch loop.

Possible approach:

- sticky terminal/git-log panel
- scroll reveal one line at a time
- each line gets more urgent
- final Codize intervention line interrupts the loop
- optional side label showing “control loss increasing”
- more atmosphere and depth

Do not make it silly.

It should feel familiar and slightly painful to anyone who has used AI coding tools.

The goal is not just to list the trap. The goal is to make the user feel the trap.

### 3. Build Loop Scroll Scene

Replace or substantially upgrade the current static Build Loop rail into a scroll-driven or interactive workflow section.

The Build Loop is:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

As the user scrolls, one stage should expand or become active at a time.

Possible implementation:

- sticky section with stages on the side and an active detail card
- expanding cards adapted to Codize stages
- scroll progress controls active stage
- hover/focus/click can also activate a stage
- mobile fallback becomes stacked cards

Review / Verify / Explain should be visually emphasized as Codize’s core value.

Generate should be labeled as “your AI tool.”

The interaction should feel like a premium workflow instrument panel.

Do not render the Build Loop as a plain horizontal timeline only.

The Build Loop should be one of the most memorable parts of the landing page.

## Expanding Cards Reference Component Guidance

The user provided a 21stdev expanding-cards component idea.

Use this as interaction inspiration, not as literal visual/copy source.

The desired interaction:

- a set of Codize workflow stages
- one stage expands at a time
- inactive stages compress
- active stage shows richer detail
- desktop can use horizontal expanding cards
- mobile should stack vertically or use a simpler active-card layout
- hover/focus/click can activate a stage
- scroll position may also activate stages if practical
- the active stage should feel like a live system panel, not an image card

Adapt the interaction to Codize’s Build Loop:

1. Plan
2. Prompt
3. Generate
4. Review
5. Verify
6. Explain
7. Commit/Reflect

Do not use the architectural wonders demo.

Do not use Unsplash images.

Do not use tourist/place content.

Do not use external image URLs.

Do not create generic image cards.

Instead, each card should look like a Codize workflow/system panel using:

- code snippets
- terminal fragments
- report fragments
- status dots
- glass/cockpit panels
- subtle gradients
- phase labels
- defense workflow language
- small mono labels
- “Codize” badges only where Codize adds value

Review, Verify, and Explain should feel like Codize’s strongest value-add.

Generate should be labeled as “your AI tool,” not Codize.

If implementing the expanding-card pattern requires `lucide-react` and it is already installed, icons may be used.

If `lucide-react` is not installed, prefer CSS/status-dot visuals unless icons are clearly worth the dependency.

Do not add random dependencies just to match the reference component.

Do not copy the demo content.

Do not make this look like a shadcn demo page.

Make it feel native to Codize.

### Expanding Cards Behavior Reference

The expanding-card pattern may use this behavior:

- maintain an `activeIndex`
- on desktop, active card expands to around `5fr` while inactive cards compress to around `1fr`
- on mobile, stack cards or use vertical expansion instead of forcing a cramped horizontal rail
- `onMouseEnter`, `onFocus`, and `onClick` can activate cards
- keyboard users must be able to focus and activate cards
- active card shows title, description, mini visual, and value badge
- inactive card shows compressed stage number/title
- animation should use CSS transitions unless Framer Motion is already present and clearly useful
- reduced-motion should show a static usable version

A Codize-native item shape could look like:

```ts
type WorkflowStage = {
  id: string
  number: string
  title: string
  shortLabel: string
  description: string
  role: "builder" | "ai-tool" | "codize"
  artifact: string
  sample: string[]
}
```

Possible stage content:

- Plan: “Decide architecture before AI writes files.”
- Prompt: “Ask with scope, constraints, and no-touch zones.”
- Generate: “Your AI tool creates the first pass.”
- Review: “Read the diff. Accept, reject, or edit deliberately.”
- Verify: “Prove behavior with evidence, not vibes.”
- Explain: “Defend what changed in a live gate.”
- Commit/Reflect: “Ship with a report behind it.”

Do not include the raw architecture/wonders demo in the product.

### 4. Project Defense Scene

Make the Project Defense section feel more like an event.

It should communicate:

- every phase ends with defense
- the user must explain what they built
- the gate is live and implementation-specific
- the report records evidence

Possible visual:

- two large glass/cockpit panels
- left: live defense gate
- right: defense report preview
- subtle status indicators
- “Ready to defend” state
- small mono labels like `gate/current`, `turn_01`, `defense_status`

Avoid dense paragraphs.

This scene should feel like the product has stakes.

### 5. Report / Proof Scene

Add or improve a section that previews the Project Defense Report as a tangible artifact.

It should feel like the payoff:

- planned
- prompted
- reviewed
- verified
- defended
- exportable

Show a stylized Markdown/report preview.

Do not claim the report proves correctness.

Use honest language:

- “Submitted evidence”
- “Self-reported verification”
- “Defense status”
- “Ready to review”

The report preview should feel useful and real, not like a fake dashboard screenshot.

### 6. Closing CTA Scene

Make the final CTA feel like a full closing scene.

Use the line:

> Your workflow is incomplete. Codize helps you fix it.

Make it dramatic and spacious.

Include CTA to login/signup.

The closing scene should feel like the end of the story, not just a footer.

## Typography Direction

The current fonts are better, but the page needs more editorial contrast.

For large headings, move toward a refined Garamond-like editorial display feel.

Preferred if legally available in the project:

- Garamond Premier Pro Subhead or similar licensed font

If not legally available, use a safe open-source approximation such as:

- Cormorant Garamond
- Fraunces

For body/UI text, keep it clean and readable.

Preferred if legally available:

- TeoriaMF Bold or similar licensed font

If not legally available, use the closest existing or open-source alternative already available in the app.

Do not add unlicensed font files.

Do not commit proprietary font files.

Do not download fonts from random free-font websites.

Use `next/font` where possible.

The typography should feel premium, not default SaaS.

Important:

- use editorial display type for big section headlines
- keep body text highly readable
- avoid making the whole UI look like a literary magazine
- retain the developer/terminal identity with mono accents

## Liquid Glass Guidance

The user is interested in liquid glass.

Do not add `liquid-glass-js` by default.

Before using it, inspect the repo, package size/risk, SSR compatibility, performance risk, and whether it works safely with Next.js.

Preferred approach for this milestone:

- create a lightweight Codize glass treatment using CSS:
  - translucent panels
  - backdrop blur
  - border highlights
  - radial highlights
  - subtle refraction-like gradients
  - pointer/hover glow if cheap

Only add `liquid-glass-js` if:

1. It integrates cleanly with Next.js client components.
2. It does not break build.
3. It does not create scroll lag.
4. It respects reduced motion.
5. It is used only in one contained non-critical accent.
6. It is easy to remove.
7. CSS alone clearly cannot achieve the intended effect.

Do not use it in the navbar.

Do not use it across large sticky scroll sections.

Do not make it a hard dependency for basic page readability.

Do not use it as a dependency if CSS can achieve the desired effect.

If liquid glass is not used, explicitly report that it was CSS-simulated and why.

## React Three Fiber Guidance

Do not add `react-three-fiber`.

Do not add `three`.

Do not add WebGL/3D in this pass.

Reason:

- the current problem is layout, hierarchy, interaction, and art direction
- 3D adds complexity without solving the core issue
- this is pre-pilot polish, not a 3D showcase

If a 3D-like feeling is desired, use CSS perspective, gradients, transforms, and layered panels instead.

## 21stdev / Expanding Cards Guidance

Use the expanding-cards idea as inspiration only.

Do not copy the architecture/wonders demo.

Do not use external image URLs.

Adapt the interaction into Codize’s workflow if useful.

Possible Codize stages:

1. Plan
2. Prompt
3. Generate
4. Review
5. Verify
6. Explain
7. Commit/Reflect

Each card should feel like a system/workflow state, not a tourist image card.

No stock images.

Use gradients, code snippets, report fragments, status lines, or abstract panels instead.

The outcome should not feel like a copied component.

It should feel like Codize invented this workflow visualization for its own product.

## Accessibility / Performance Requirements

Must support:

- mobile layout
- keyboard navigation
- visible focus states
- good contrast
- no raw HTML rendering
- no horizontal overflow
- no scroll-jacking that traps the user
- reduced-motion support

Animations should enhance the story, not block usability.

Use `prefers-reduced-motion`.

If scroll-driven sections are implemented, make sure they degrade cleanly.

Do not make the page unusable on lower-powered student laptops.

Avoid heavy runtime animation if CSS and simple scroll state are enough.

## Copy Requirements

Keep copy concise.

Reduce text density.

Use fewer words per viewport.

Use Codize-specific lines like:

- “AI built your first 80%. Now you’re stuck fixing the rest.”
- “Stop debugging blindly.”
- “Review AI like a teammate, not a magic box.”
- “Be ready to defend what you shipped.”
- “Plan. Prompt. Review. Verify. Explain.”
- “Codize helps students stay the engineer.”
- “Your workflow is incomplete. Codize helps you fix it.”

Avoid:

- generic SaaS copy
- fake enterprise claims
- fake customers
- fake logos
- fake testimonials
- overclaiming learning outcomes
- “revolutionary”
- “unlock your potential”

## Scope Boundary

This milestone should only affect:

- public landing page
- landing-specific components
- global styles if needed
- font setup if needed
- tiny shared style polish only if safe

Do not modify:

- backend
- auth flow
- intake flow
- gate logic
- report logic
- workflow artifact logic
- database
- protected app screens, except tiny shared style regression fixes

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
2. hero fits desktop viewport
3. sections feel spacious
4. CTA routes to `/login`
5. Build Loop scroll/interaction works
6. mobile layout has no horizontal overflow
7. keyboard focus is visible
8. reduced-motion mode is safe
9. no obvious console errors

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `.claude/memory/frontend-conventions.md`
- `CLAUDE.md`

Only update docs if new landing-page conventions, fonts, or dependencies should be remembered.

Do not rewrite product vision docs.

## End Requirements

At the end, output:

- visual diagnosis addressed
- design direction implemented
- files changed
- dependencies added/removed
- font choices
- whether liquid glass was used or CSS-simulated
- whether React Three Fiber was used
- how the expanding-card reference was adapted
- landing sections changed
- accessibility/performance notes
- commands run
- test/build results
- visual smoke result
- secret scan result
- known issues
- git commit hash
- next step: local visual review, then first pilot tester

Commit completed landing-page spatial/scroll redesign.

Stop after commit.