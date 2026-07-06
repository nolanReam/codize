# Codize M13D.4 — Landing Page Scroll Experience Fix Pass

Fix the issues found in the M13D.3 visual review.

This is a focused frontend design-fix milestone.

Do not start M14.

Do not change backend behavior.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations.

Do not add analytics.

Do not add product features.

Do not redesign protected app screens, except the public/login visual surface if explicitly needed for consistency.

Do not replace the landing page from scratch unless a section is clearly broken.

## Current State

M13D.3 was completed at commit:

- `777cd52810df2761b3b57e035941e0f01e3ec138`

M13D.3 added:

- full-screen-ish landing scenes
- patch-loop scroll scene
- Build Loop expanding cards
- glass/cockpit panels
- Cormorant Garamond editorial headlines
- CSS-simulated liquid glass
- no React Three Fiber
- no liquid-glass-js dependency

The visual review found that it is better, but still misses the intended feel.

## Visual Problems To Fix

User feedback:

1. The fancy Garamond-like font is not desired anymore.
2. The title text should use the same general font direction as the regular body text, closer to “TeoriaMF” style.
3. The Build Loop expansion cards are too tall for how little content they contain.
4. The Build Loop cards currently expand on mouse hover/focus/click, but the user wanted them to expand one by one as the user scrolls.
5. The whole website should feel more scroll-oriented.
6. Each major part of the landing page should be centered instead of left-aligned.
7. The terminal box in the hero should behave more like the provided premium sign-in card reference:
   - subtle 3D tilt
   - glow border
   - traveling light beam / edge shimmer
   - glassy depth
   - motion that feels premium, not noisy
8. The page should feel more unique and premium, but not cluttered or overwhelming.

## Goal

Make the landing page feel like a centered, scroll-driven, premium Codize experience.

The page should feel less like a left-aligned devtool document and more like a cinematic guided scroll:

- centered scenes
- one idea per viewport
- scroll controls the story
- Build Loop expands with scroll
- hero terminal feels like a premium interactive glass object
- typography feels cohesive and not overly fancy
- less visual density
- no generic SaaS/template feel

## Typography Fix

Remove the fancy Garamond/editorial display look from landing headings.

Do not use Cormorant Garamond / Garamond-style display headings for the landing page.

The user wants the title text to feel closer to the body/UI font direction, similar to “TeoriaMF.”

If TeoriaMF is legally available in the project, use it.

If TeoriaMF is not legally available, do not download or commit unlicensed font files.

Use the closest existing safe font already in the app, or a safe open-source equivalent if already configured through `next/font`.

The result should be:

- cohesive
- premium
- clean
- not overly serif/editorial
- not default browser/SaaS
- strong enough for large headings

Keep mono accents for code comments, terminal labels, and system states.

## Layout Fix

Make major landing sections centered.

For each major scene:

- center the section content horizontally
- center the main heading/text block
- avoid dense left-aligned paragraphs unless inside terminal/code/report UI
- keep text blocks narrower
- reduce competing text in the same viewport
- maintain strong vertical breathing room

The page should not feel like a documentation page.

It should feel like a centered product story.

## Scroll Experience Fix

Make the whole landing page feel more scroll-oriented.

Do not scroll-jack.

Do not trap the user.

But use scroll position to reveal and activate key scenes.

Use simple, reliable techniques:

- sticky sections
- scroll progress
- IntersectionObserver
- CSS sticky
- rAF-throttled passive scroll listener if needed

Respect `prefers-reduced-motion`.

Reduced motion should show static usable states.

## Hero Terminal Fix

Keep the patch-loop terminal concept, but upgrade the terminal card behavior using the provided sign-in card reference as inspiration.

The user likes how the sign-in box acts.

Use the sign-in card reference for behavior/aesthetic inspiration only.

Do not copy it literally.

Do not replace Codize branding with unrelated login/demo copy.

Do not add fake Google sign-in or fake auth UI to the landing hero.

Apply the premium card interaction to the hero terminal:

- subtle 3D tilt based on pointer movement on desktop
- return-to-neutral on mouse leave
- glassy black/purple panel
- edge glow
- traveling light beam or border shimmer
- soft radial background glow
- card depth/shadow
- no excessive movement
- reduced-motion safe
- mobile should disable or simplify tilt

The terminal should feel like a premium interactive object.

It should not feel like a plain box.

## Sign-In Reference Component Guidance

The user provided a 21stdev sign-in card reference component.

Use it as inspiration for visual behavior only.

Specifically, borrow/adapt ideas like:

- card perspective
- mouse-position tilt
- subtle animated card glow
- traveling edge light
- translucent glass background
- radial purple atmosphere
- input/button polish style if updating login page is in scope

Do not copy the component blindly.

Do not use its unrelated app name/copy.

Do not add fake Google sign-in.

Do not add forgot-password links unless already supported.

Do not break existing Supabase login behavior.

Do not replace working auth logic with demo state.

Do not add unnecessary dependencies just to match the reference.

The provided reference includes `framer-motion` and `lucide-react`; inspect current dependencies before adding anything.

If `framer-motion` is not already installed, only add it if the hero card motion clearly benefits and the bundle/build remains healthy.

Prefer CSS where possible.

If the existing login page is visually much weaker than the new landing page, it is acceptable to apply the same glass/card style to the real `/login` page, but preserve all existing auth behavior exactly.

## Build Loop Scroll Expansion Fix

The current Build Loop cards are too tall and expand on hover/focus/click.

Change the primary behavior:

- cards should expand one by one as the user scrolls
- scroll position should determine the active stage
- hover/focus/click may be retained only as secondary accessibility/direct manipulation
- scroll should be the main storytelling mechanic

The Build Loop is:

1. Plan
2. Prompt
3. Generate
4. Review
5. Verify
6. Explain
7. Commit/Reflect

Requirements:

- reduce card height
- match content amount to card size
- avoid huge empty panels
- active card should show richer detail
- inactive cards should compress cleanly
- active card changes as the user scrolls through the section
- section should feel like an instrument panel / scroll-driven product demo
- mobile fallback should be usable and not cramped

Review / Verify / Explain should be emphasized as Codize’s value.

Generate should be labeled as “your AI tool.”

Do not use stock images.

Do not use external image URLs.

Do not make it look like the architecture/wonders component demo.

## Centering Requirements By Section

Apply centered composition to:

- Hero
- Patch Loop scene
- Build Loop scene
- Project Defense scene
- Report preview scene
- Closing CTA

Terminal/code/report UI can have internal left-aligned code text, but the section composition itself should be centered.

## Liquid Glass Guidance

Do not add `liquid-glass-js` by default.

The user is interested in liquid glass, but this pass should first improve:

- layout
- scroll behavior
- typography cohesion
- premium glass styling

Use CSS-simulated liquid glass unless there is a very strong reason.

CSS glass can include:

- backdrop blur
- translucent layered backgrounds
- edge highlights
- radial reflections
- traveling beams
- soft border glows
- pointer-responsive highlights

Only add `liquid-glass-js` if:

1. It is safe in Next.js.
2. It does not break SSR/build.
3. It does not cause scroll lag.
4. It respects reduced motion.
5. It is contained to one non-critical accent.
6. It is easy to remove.
7. CSS cannot achieve the desired card behavior.

Do not use liquid-glass-js in the navbar or sticky scroll sections.

## React Three Fiber Boundary

Do not add `react-three-fiber`.

Do not add `three`.

Do not add WebGL/3D in this pass.

The problem is scroll storytelling, layout, typography, and premium UI behavior — not lack of 3D.

Use CSS perspective/transforms instead.

## Copy / Density Requirements

Reduce text density.

Use fewer words per viewport.

Keep Codize-specific copy:

- “AI built your first 80%. Now you’re stuck fixing the rest.”
- “Stop debugging blindly.”
- “Review AI like a teammate, not a magic box.”
- “Be ready to defend what you shipped.”
- “Plan. Prompt. Review. Verify. Explain.”
- “Codize helps students stay the engineer.”
- “Your workflow is incomplete. Codize helps you fix it.”

Avoid generic SaaS copy.

Avoid fake customers/logos/testimonials.

Avoid overclaiming learning outcomes.

## Scope Boundary

This milestone may modify:

- public landing page
- landing-specific components
- landing/global CSS
- font setup
- login page styling only if preserving auth behavior exactly
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

The scroll-driven Build Loop must still be usable by keyboard and on mobile.

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
2. sections are centered
3. hero terminal has premium glass/tilt behavior
4. CTA routes to `/login`
5. Build Loop active stage changes on scroll
6. Build Loop cards are not overly tall
7. mobile layout has no horizontal overflow
8. keyboard focus is visible
9. reduced-motion mode is safe
10. no obvious console errors

If login page styling changed, smoke:

1. `/login` loads
2. existing auth form still works visually
3. no fake auth buttons appear unless they are actually supported
4. Supabase auth behavior is not changed

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `.claude/memory/frontend-conventions.md`
- `CLAUDE.md`

Only update docs if new landing-page conventions, fonts, scroll behavior, or dependencies should be remembered.

Do not rewrite product vision docs.

## End Requirements

At the end, output:

- user feedback addressed
- design fixes implemented
- files changed
- dependencies added/removed
- font changes
- whether login page styling was changed
- whether sign-in card reference was used and how
- whether liquid glass was CSS-simulated or dependency-based
- whether React Three Fiber was used
- how Build Loop became scroll-driven
- accessibility/performance notes
- commands run
- test/build results
- visual smoke result
- secret scan result
- known issues
- git commit hash
- next step: local visual review, then first pilot tester

Commit completed landing page fix pass.

Stop after commit.