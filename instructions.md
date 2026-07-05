# Codize M13D.2 — Landing Page Signature Redesign

Upgrade Codize’s landing page from “flat MVP page” to a distinctive, premium, product-specific landing experience.

This is a focused frontend visual/product-polish milestone.

Do not start M14.

Do not change backend behavior.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations.

Do not add new product features.

Do not add analytics.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, hosted coding runtime, or gamification.

Do not redesign the protected app unless tiny shared style fixes are necessary.

## Current State

Codize is locally pre-pilot verified.

Relevant recent commits:

- M13C.2 Gate UI + Project Defense Report: `8161dce`
- M13C.2B Gate Question Cleanliness Hotfix: `c0320f5`
- Pilot prep docs: `5fd7d9b`
- Pre-pilot deployment/demo prep: `a33b5a9`
- Local pre-pilot smoke pass: `acf5687`

The current landing page works, but visually feels too flat: mostly text on dark background, not enough depth, motion, or memorable Codize-specific product moment.

## Goal

Make the public landing page feel like Codize has a strong product point of view.

The page should communicate:

> AI can get students to the first 80% fast. Codize helps them stay the engineer when the project starts breaking.

The landing page should feel:

- premium
- serious
- developer-focused
- cinematic but usable
- closer to Linear / Vercel / GitHub / high-end devtool pages than school LMS
- not generic SaaS
- not childish
- not purple-gradient AI slop

## Important Design Direction

The page needs one signature visual moment:

> The 80% Trap should be demonstrated, not just explained.

Build a hero experience where the user immediately sees the AI patch-loop problem.

Preferred concept:

- a fake terminal / IDE / AI coding panel in the hero
- vague prompt appears
- AI patch appears
- error appears
- user pastes error back
- warnings/diff noise increase
- Codize interrupts with a “REVIEW REQUIRED” / “DEFENSE WORKFLOW NEEDED” style overlay
- the visual should feel like a controlled simulation, not a real coding environment

This can be implemented with simple React state, CSS, and Framer Motion if appropriate.

Do not use real AI calls.

Do not use real code execution.

Do not make it technically heavy.

## Library / Dependency Guidance

Do not add `react-three-fiber` in this milestone.

Do not add `three`.

Do not add `liquid-glass-js`.

Do not add WebGL effects.

Do not add a heavy animation stack.

Allowed dependencies only if they fit the existing frontend:

- `framer-motion` for tasteful animation
- `lucide-react` only if already installed or genuinely useful
- small shadcn-style primitives only if the project already uses that structure

Before installing anything, inspect the existing frontend dependencies.

If Framer Motion is already installed, use it.

If not installed, install only if it clearly improves the landing page and does not bloat the app unnecessarily.

Prefer CSS transitions/keyframes where they are enough.

Respect `prefers-reduced-motion`.

## 21stdev Component Guidance

A 21stdev component prompt was provided for a container scroll animation and hero section.

Use it as inspiration only.

Do not blindly copy generic SaaS sections.

Do not use generic customer logo grids.

Do not use external stock screenshots.

Do not use “Modern Solutions for Customer Engagement” or any unrelated copy.

Do not create fake customer logos.

Do not add images from random external URLs.

If a container-scroll style interaction is useful, adapt the concept into a Codize-native visual:

- Codize terminal panel
- Build Loop pipeline
- Project Defense workflow
- report preview
- cockpit preview

The result should look custom-built for Codize.

## Required Landing Page Improvements

Implement these landing-page upgrades:

### 1. Signature Hero

Replace or substantially upgrade the current hero with:

- strong headline around the 80% Trap
- mono eyebrow line, e.g. `// the 80% trap`
- highlighted `80%` or `stay the engineer`
- primary CTA: “Stop Debugging Blindly”
- secondary CTA: “View Project Defense Workflow” or similar
- animated terminal/IDE simulation showing the patch-loop problem
- Codize overlay/intervention that makes the product point clear

Keep the existing core positioning, but make it feel sharper.

### 2. Build Loop Pipeline

Create a strong visual for:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

Do not render it as a plain text string only.

Render it like a CI/CD pipeline or engineering workflow rail:

- connected nodes
- status dots
- hover/focus states
- Review / Verify / Explain emphasized as Codize’s added value
- short one-liner per stage

It should be responsive and accessible.

### 3. 80% Trap Transcript

Turn the “80% Trap” explanation into a terminal/git-log style transcript.

Example tone:

- `feat: generate first version`
- `fix: paste error back into AI`
- `fix: patch the patch`
- `fix: why is auth broken now`
- `warning: no clear mental model`
- `Codize: review required`

Make it visually memorable.

Do not make it too jokey.

It should feel painfully familiar to student builders who use AI coding tools.

### 4. Background Atmosphere

Add subtle depth:

- faint blueprint/dot grid
- soft violet or blue glow
- top-edge gradient
- card shadows/borders
- careful layering

No heavy images required.

Do not reduce readability.

### 5. CTA Polish

Make the main CTA feel like the obvious action:

- stronger button treatment
- hover lift
- subtle glow
- keyboard focus state
- no inaccessible contrast

### 6. Closing Section

Promote the idea:

> Your workflow is incomplete. Codize helps you fix it.

Make it a real closing section, not a muted footer whisper.

Include CTA back to login/signup.

## App-Wide Tiny Polish Allowed

Only if easy and safe:

- global card hover transitions
- button hover polish
- focus-ring consistency
- minor copy cleanup on app shell if obviously inconsistent

Do not redesign the app interior in this milestone.

## Accessibility / Performance Requirements

Must support:

- mobile layout
- keyboard navigation
- visible focus states
- good color contrast
- no raw HTML rendering
- no layout-breaking animation
- `prefers-reduced-motion`

Animations should be decorative and not block usage.

The page should still work if motion is reduced.

## Copy Requirements

Use Codize-specific language.

Use phrases like:

- “AI built your first 80%. Now you’re stuck fixing the rest.”
- “Stop debugging blindly.”
- “Review AI like a teammate, not a magic box.”
- “Be ready to defend what you shipped.”
- “Plan. Prompt. Review. Verify. Explain.”
- “Codize helps students stay the engineer.”

Avoid:

- “revolutionary”
- “unlock your potential”
- “modern customer engagement”
- fake enterprise claims
- fake customers
- fake testimonials
- overclaiming learning outcomes

## Testing / Verification

Run:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

If backend code changes accidentally, stop and explain.

Run a quick visual/local smoke if possible:

1. landing page loads
2. CTA goes to login
3. page works on desktop width
4. page works on mobile width
5. no obvious console errors
6. reduced-motion behavior is safe if implemented

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `.claude/memory/frontend-conventions.md`
- `CLAUDE.md`

Only update docs if new landing-page conventions or dependencies should be remembered.

Do not rewrite product vision docs.

## End Requirements

At the end, output:

- design direction implemented
- files changed
- dependencies added/removed
- landing sections changed
- accessibility/performance notes
- commands run
- test/build results
- visual smoke result if run
- secret scan result
- known issues
- git commit hash
- next step: run local visual review, then pilot testers

Commit completed landing-page redesign.

Stop after commit.