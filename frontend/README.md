# Codize frontend (M13C)

The Codize v3 **AI Workflow Workspace** — a Next.js (App Router) frontend that
makes the Codize Build Loop visible and usable:

**Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect**

It is an engineering cockpit, not a roadmap/checklist/quiz app. Design language:
high-contrast dark, violet accent, mono for technical text (see `app/globals.css`
and the `ui-ux` skill).

## Architecture

Strictly **Frontend → Backend → External services**. The frontend never talks to
Supabase data tables or LLM providers directly.

- **Supabase is used for auth only** (`lib/supabase.ts`). The publishable/anon key
  is public by design; RLS and the FastAPI backend enforce all access.
- **All product data flows through the FastAPI backend** (`lib/api.ts`), which is
  called with a Supabase Bearer JWT. Backend 4xx messages are safe client strings
  by backend design and are shown as-is; 5xx bodies are never surfaced.

## Layout

```
app/
  page.tsx              Landing page (the 80% Trap) — static, no auth; full-
                        bleed header/footer with centered scenes: tilt-card
                        patch-loop terminal hero, scroll-driven trap
                        transcript, research-citation proof card, scroll-
                        driven expanding Build Loop panel (with hysteresis),
                        scroll-driven simulated gate exchange (GateScene)
  login/page.tsx        Supabase email/password sign-up + sign-in
  app/
    layout.tsx          Protected app shell: session guard, sidebar nav (top bar
                        on mobile), reconnection check (GET /reconnection →
                        acknowledge), first-visit "How Codize works" tutorial
                        (localStorage; reopenable from the sidebar Help section)
    page.tsx            Project Cockpit — the project dashboard (evaluation +
                        workflow + intake purpose, Continue project, guidance
                        rail; "+ New project" is a disabled affordance —
                        multi-project is deferred, see
                        docs/context/multi_project_dashboard_plan.md)
    intake/page.tsx     Conversational five-question intake → roadmap generation
                        (per-question helper text + example chips; answers are
                        editable until the explicit "Finish intake" review step)
    phase/
      page.tsx          Phase Workflow Board (Build Loop + tasks + gate summary)
      prompt/page.tsx   Prompt Builder (deterministic, client-side; beginner
                        phase explanation + starter-ask chips via lib/phaseGuide)
      review/page.tsx   Review Board
      evidence/page.tsx Evidence Panel
      verify/page.tsx   Verification Lab
    gate/page.tsx       Project Defense — live Interrogation Gate flow
                        (anchor → 3 turns → evaluate → pass/fail), resume-safe
    report/page.tsx     Project Defense Report — full client-assembled report
                        with Markdown copy/download
  icon.svg              App favicon (served by Next as the tab icon)
components/             Async, NotReady, SaveBar, WorkflowSteps, ReconnectionModal,
                        Tutorial (How Codize works), GuideCard (guidance rail),
                        TrapTerminal + TiltCard + PatchLoopScene + BuildLoopPanel
                        + GateScene + Reveal (landing-only, scripted, no AI calls)
lib/                    api client, supabase client, types, prompt builder + test,
                        report builder + test, phase guide + test (static beginner
                        explanations — no LLM), useWorkflowSection hook, drafts +
                        test (localStorage draft persistence — unsubmitted text
                        survives tab switches; user/phase/section-scoped keys,
                        secret-marker guard, cleared on successful save)
```

## Backend routes consumed

Intake (`/intake/*`), roadmap (`/roadmap/generate`, `/roadmap`), phases
(`/phases*`), workflow artifacts (`GET /workflow/{phase}`,
`PUT /workflow/{phase}/{section}`), reconnection (`GET /reconnection`,
`POST /reconnection/acknowledge`), evaluation (`GET /evaluation`), and the full
gate flow (`GET /gate/current`, `POST /gate/start`,
`POST /gate/{id}/turn1|turn2|turn3|evaluate`). The Project Defense Report is
assembled client-side from these routes — no dedicated report endpoint.

## Environment

Copy `.env.example` to `.env.local` and fill in:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — publishable/anon key only
- `NEXT_PUBLIC_API_BASE_URL` — FastAPI backend base URL, no trailing slash

**Never** put service-role keys or LLM provider keys here — every `NEXT_PUBLIC_*`
value is bundled into the client JS.

Hosted deploys (Vercel) set the same three variables in the project settings —
see `docs/deployment/friend_pilot_deployment.md` and
`docs/deployment/env_var_matrix.md`. `NEXT_PUBLIC_API_BASE_URL` is read at
**build time**: changing it on Vercel requires a redeploy.

## Commands

```bash
npm install
npm run dev        # local dev server
npm run lint
npm run typecheck
npm run build
npm test           # vitest — deterministic prompt builder + report builder
```

## Status (M13E.4)

Skill-driven UI polish pass (visual system only — zero behavior change): a
`.card.primary` accent-left-rail signature marks each screen's one primary
card (with the app's only hover lift, echoed by the sidebar active state);
primary buttons lost their resting glow (depth on hover, press feedback on
all buttons/chips); status pills and notices soften their borders and
cooldown reads amber, never red; help disclosures and the Build Loop strip
are borderless tints instead of more boxes; the type scale rose (26px
titles, sans textareas — mono reserved for code-like output); and three
subtle transform/opacity motions (disclosure reveal, generated-prompt rise,
focus rings) live inside the existing `prefers-reduced-motion` kill switch.

## Status (M13E.3)

Cognitive-load reduction pass from the first tester's qualitative feedback
("overwhelming, text-heavy"): **progressive disclosure everywhere** — GuideCard
is now a collapsed `<details>`, every screen keeps at most 1–2 visible
explanatory sentences with the rest behind "What does this mean?" disclosures,
and every core screen has **one accented primary action** (cockpit "Do this
next", phase "Next step" pointing at the first uncaptured Build Loop artifact,
Prompt Builder "Step 1"). The Prompt Builder (the pilot's favorite surface) is
now three short steps with starter + quick-add guardrail chips; the Evidence
Panel is "proof you checked something — one small piece is enough" with five
tap-to-pick kinds and a "skip for now" path; Verification reads as a quick
honesty check; the gate is framed as coaching (example anchors, "what makes a
good answer", softened fail/cooldown copy — evaluator strictness unchanged).
`components/LoopOverview.tsx` answers "what am I about to do" in 8 collapsed
lines. See `.claude/memory/pilot-ux-lessons.md` for the density rule.

## Status (M13E.2)

Pilot bugfix pass from the first real friend test: **local draft persistence**
on every text surface (workflow pages, gate answers, intake — typed-but-unsaved
text survives switching tabs; backend data stays the source of truth and a
successful save clears the draft), **wide-screen workspace** (every core page
now uses the two-column `.workspace` grid with a guidance rail; `.main-inner`
widened, larger rail ≥1800px), **Verification Lab result-specific prompts**
(pass→"how did you check", fail→"what broke", skipped/n/a→optional reason with
"no evidence needed" — and the report labels skipped/n/a honestly), and
**progress clarity** ("Build tasks: X/Y" vs "Workflow: N/4 captured" — saving
artifacts never ticks a build task). Backend M13E.2 changes (anchor validator
tiers + gate question leak hardening) are documented in `backend/README.md`.

## Status (M13E.1)

The core-app usability pass (M13E.1) made the protected app beginner-friendly:
full-width workspace layout with a guidance rail (content + contextual help,
no more dead right half; the sidebar becomes a top bar on mobile), a
dismissible/reopenable first-use tutorial, intake helper text + example chips
+ **edit-until-finish** (one small tested backend change: an answered intake
question can be revised before completion — first-answer order and the
five-question contract unchanged), a Prompt Builder that explains the current
phase in plain language with tap-to-use starter asks, and static
glossary/confusion help throughout. Multiple projects were audited and
**deferred** (`docs/context/multi_project_dashboard_plan.md`); the cockpit is
an honest single-project dashboard.

## Status (M13C.2)

Complete: landing, auth, app shell + reconnection, intake, cockpit, phase board,
Prompt Builder, Review Board, Evidence Panel, Verification Lab, the **live
Project Defense (Interrogation Gate) flow**, the **full client-assembled Project
Defense Report** (Markdown copy/download), API client, favicon, and honest
loading/empty/error states. The whole Build Loop is now walkable end-to-end;
this was live-verified in a browser against the real FastAPI backend + Supabase
(intake → roadmap → phase artifact → full gate PASS → report → export → logout).

The gate is **not evidence-aware** by design (it uses the existing M9 evaluator;
saved workflow artifacts are the student's own reference and feed only the
client-assembled report, never the evaluator). Raw gate scores, evaluator
reasoning, hidden thresholds, and internal prompts never reach the client.
