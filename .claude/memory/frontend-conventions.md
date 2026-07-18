# Frontend conventions (Milestone 13C)

The frontend lives in `frontend/` — Next.js App Router, React 19, TypeScript
strict, vitest. It is the v3 **AI Workflow Workspace** (see [[product-vision-v3]]),
built as an engineering cockpit, NOT a roadmap/checklist/quiz app.

**Architecture is non-negotiable: Frontend → FastAPI → external services.**
Supabase is used for **AUTH ONLY** (`lib/supabase.ts`, lazy singleton so
importing never throws at build/prerender without env). All product data flows
through `lib/api.ts`, which attaches the Supabase Bearer JWT to every call. The
anon/publishable key is public by design; RLS + backend enforce access. Never
add a service-role or provider key to any `NEXT_PUBLIC_*` value — it bundles
into client JS. Env contract: `frontend/.env.example` (URL, anon key, API base).

`lib/api.ts` is the single boundary: 4xx `{error:{message}}` bodies are safe
client strings by backend design and shown as-is; 5xx bodies are never
surfaced (generic message). `lib/types.ts` mirrors the backend response shapes
as-built — do not invent fields the backend doesn't send. `useWorkflowSection`
is the shared load/save state machine for the four Build Loop artifact pages
(409 → `notReady`, points at intake).

Reconnection invariant carried into the shell (`app/app/layout.tsx`): GET
`/reconnection` FIRST, then acknowledge — immediately when not needed, on the
"Let's keep building" click when it is. One check per browser session via a
`sessionStorage` flag; fail-open (never block the workspace). Modal is
dismissed only by the button — no timer/click-outside/Escape (see
[[reconnection-conventions]]).

Prompt Builder is deterministic and CLIENT-SIDE (`lib/promptBuilder.ts`, pure,
unit-tested) — no LLM call; output is pasted into the student's own AI tool.
The four artifact pages save via `PUT /workflow/{phase}/{section}` full-section
replace and prefill from `GET /workflow/{phase}` (see
[[workflow-artifact-conventions]]). Slice inputs to the backend caps
(300/2000/8000) client-side too.

M13C.1 scope done: landing (80% Trap), auth, protected shell, intake, cockpit,
phase board, Prompt Builder, Review Board, Evidence Panel, Verification Lab,
API client, honest async states.

**M13C.2 done — the Build Loop is now walkable end-to-end.** Two headline
surfaces went from placeholder to live:

- **Project Defense gate** (`app/app/gate/page.tsx`): the full M9 flow —
  `POST /gate/start` → `turn1` (anchor) → `turn2`/`turn3` (submit prior answer,
  get next question) → `evaluate` (verdict). The page's local `gate` state IS the
  `GateCurrent` shape and is advanced from each POST response (no full reload,
  no transcript flash); `GET /gate/current` is used only on load, which makes
  **resume free** (turns[] + next_action restore the transcript — live-verified).
  `next_action` drives the whole state machine: turn1=anchor input, else the last
  (unanswered) turn is the pending question and its endpoint = next_action. 422
  (bad anchor) and 502 (LLM fail) leave the session where it was, so the typed
  input is kept and the same step is retryable. The PASS screen shows the
  evaluator's one-sentence reason + any `new_unlocks`; do NOT reload after
  evaluate (a non-final PASS advances current_phase, so GET would show the *next*
  phase). Gate is **not evidence-aware** — workflow artifacts are reference-only,
  never evaluator input (spec-guardian-gated future change). v3 language:
  "Project Defense", "defend what you built", never "quiz"/"cheating".
- **Project Defense Report** (`app/app/report/page.tsx` + pure `lib/report.ts`,
  unit-tested like `promptBuilder.ts`): client-assembled from evaluation + intake
  answers + current-phase workflow sections + `GET /gate/current` + current phase.
  No report endpoint (client-assembled per the M13 plan). Export = copy Markdown
  (+ download .md). **Honesty rules baked in**: missing artifacts say "missing",
  verification is labelled self-reported, and `defenseStatus` reflects the CURRENT
  phase's gate state ONLY — a prior-phase pass shows as a separate "latest gate
  note", never conflated into "this phase passed" (the project-level "passed any
  gate?" signal lives in the Skills section, keyed off `completed_phases`).
  Interview questions are derived client-side (no LLM). Archetype id→name is a
  fixed 3-entry map (never a fourth). Never renders raw HTML; artifacts are plain
  text; no score/evaluator-reasoning/threshold/key ever appears in the export.

Favicon added at `app/icon.svg` (Next serves it as the tab icon — kills the
benign 404). Sidebar/cockpit gate label is now "Project Defense" (v3).

Live browser smoke (2026-07-04, real FastAPI + Supabase): full walk — SQL test
user → intake (5 Qs) → roadmap (personalized, 7-phase full-stack) → save a
Prompt Builder artifact → **full gate PASS** (anchor + 3 real Gemini turns +
temp-0 evaluate; also verified mid-flow resume) → report shows real data with
corrected defense status → copy Markdown (verified clean: no score/service-role/
Gemini/JWT leakage) → logout. All green; the one oddity (flash-lite leaking
"valid anchor…" preamble into the Turn 1 question text) is a backend gate-prompt/
model quirk, NOT a frontend bug and out of M13C.2 scope — the UI faithfully shows
whatever the backend returns. Historical M13C.1 note: a gate "start" button with
no turn UI would strand the user — that constraint is now satisfied by the full
flow.

Backend touch during M13C.1 (only one): `intake_service._build_status` now
returns an `answers` dict keyed by question key (purpose/scope/…) — owner-scoped
data the cockpit "mission" card and intake transcript echo. No other backend
change; the cockpit REQUIRES the intake purpose, and evaluation deliberately
doesn't carry it (see [[evaluation-conventions]], [[intake-engine-conventions]]).

Live smoke pass (2026-07-03, after commit `03e3c1f`): drove the full flow in a
real browser (Playwright) against the live FastAPI backend + Supabase — all 20
steps green, zero 500s, **no frontend/API integration bugs found**. Run the
backend with the repo-root `.env` via `uvicorn app.main:app --env-file ../.env`
from `backend/`; the frontend needs `frontend/.env.local` (public Supabase URL +
publishable key + `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`). Email
confirmations are ON, so create a login-capable test user directly via SQL (the
[[gotrue-sql-test-users]] pattern), and clean it up after.

**M13D.2 (2026-07-05) — landing page signature redesign.** The public landing
page (`app/page.tsx`) is now the "cinematic devtool" version: hero patch-loop
terminal simulation (`components/TrapTerminal.tsx` — scripted React state
machine + CSS keyframes, NO real AI calls, loops until a Codize
"Review required" overlay stamps in), git-log-style 80% Trap transcript with
scroll reveal (`components/Reveal.tsx` — IO-based, visible-by-default so SSR/
no-JS/reduced-motion never hide content), and the Build Loop as a CI-style
pipeline rail (`.pipeline`, horizontal ≥900px / vertical timeline below;
Review/Verify/Explain marked as Codize's value, Generate tagged "your AI
tool"). **Zero new dependencies** — framer-motion was considered and skipped;
CSS was enough. Fonts are now actually loaded via built-in `next/font/google`
(DM Sans, IBM Plex Mono, Space Grotesk display for h1/h2) exposed as
`--font-sans/--font-mono/--font-display` on `<html>` — before this the CSS
only *named* the families and users saw Segoe UI. Reduced-motion contract:
components check `matchMedia` and render the finished static frame (full
transcript + overlay), and globals.css has a global animation/transition kill
switch. `.trap-steps` CSS is still shared by the gate + report pages — the
landing no longer uses it but do not delete it. Landing container widened to
1020px; app shell untouched. Windows dev gotcha hit during smoke: a stale
`next dev` on port 3000 while `next build` runs corrupts `.next` (webpack
module-not-found 500s) — kill the server, delete `.next`, rebuild.

**M13D.3 (2026-07-05) — landing spatial + scroll experience pass.** The landing
is now six full-screen scenes (hero → patch loop → build loop → defense →
report → closing), each `min-height: 100svh` desktop with one dominant visual
and minimal copy. New landing-only components: `PatchLoopScene.tsx` (the 80%
Trap as a 300vh scroll track with a sticky glass git-log panel — lines surface
by scroll progress, a "control" meter drains green→amber→red, Codize
interrupts at the end; static all-visible block under reduced motion / no-JS)
and `BuildLoopPanel.tsx` (expanding cards: activeIndex via
hover/focus/click, desktop flex-grow 1→4.2 horizontal rail with vertical-rl
compressed titles, <900px vertical accordion via max-height; each card is a
system panel with mono sample lines; Review/Verify/Explain = CODIZE badge,
Generate = "your AI tool"). **Liquid glass is CSS-simulated** (`.glass`:
translucent gradient + backdrop-blur + top-edge border highlight + radial
sheen) — no liquid-glass-js, no three/R3F, still zero runtime deps. Editorial
type: Cormorant Garamond via next/font as `--font-editorial` → `--editorial`,
used ONLY for big landing headlines (h1/scene h2/closing, with italic `em`
accents); app interior keeps Space Grotesk/DM Sans. **Two hard-won gotchas:**
(1) adding a next/font variable is not enough — the `--editorial` token must
also be defined in `:root`, or `font-family: var(--editorial)` is invalid at
computed-value time and silently inherits the body sans (all headlines
rendered DM Sans until fixed; verify with `getComputedStyle(...).fontFamily`,
not by eyeballing screenshots); (2) content appearing inside a sticky panel
triggers browser scroll anchoring → self-scrolling feedback loop — fix is
`overflow-anchor: none` on the track subtree PLUS a fixed `min-height` on the
line container so the panel never resizes. Old `.pipeline`/`.trap-log` CSS is
gone; `Reveal` now staggers direct children via inline `--i`; `.trap-steps` is
still shared by gate/report pages — do not delete.

**M13D.4 (2026-07-05) — landing fix pass (user visual review of D.3).** Four
user-driven corrections: (1) **Cormorant Garamond is gone** — the editorial
serif was not wanted; landing headlines are Space Grotesk (`--display`, same
direction as the UI type), sized down (hero clamp→50px, scenes→46px,
closing→58px), with `em` emphasis rendered as violet (`--accent`), NOT italic
(Space Grotesk has no real italic). The `--editorial` token and the next/font
Cormorant import were both removed. Hero h1 uses `text-wrap: balance`.
(2) **Every scene is centered** (hero is a stacked centered column with the
terminal below the copy; scene-heads, trap panel, defense grid, report, footer
all centered). (3) **The Build Loop is scroll-driven**: `BuildLoopPanel` now
owns its whole scene — a 320vh `.bl-track` with a sticky 100svh panel, same
pattern + `overflow-anchor: none` fix as the patch loop; scroll progress
selects the active card (`floor(p * 7)`); click/focus still activate a card
directly and **stick until the scroll bucket actually changes** (`bucketRef` —
only re-assert active on a bucket *change*, or incidental scroll events from
click/focus instantly snap the selection back). Hover activation exists only
in static mode (cards move under a stationary cursor while scrolling →
oscillation). Static mode = reduced motion (desktop, hover/click) or ≤900px
(tap accordion); a matchMedia change listener drops scroll mode if the
viewport narrows. Cards are ~264px (hidden detail is `position: absolute` on
desktop so compressed cards stay short). (4) **Hero terminal is a premium
tilt card**: `TiltCard.tsx` wraps `TrapTerminal` — pointer tilt via CSS vars
(`--rx/--ry`, max 6°, rAF-throttled, return-to-neutral on leave), traveling
edge beams (`.tcard-edge::before/::after`), breathing glow, pointer-following
sheen (`--mx/--my`). Behavior adapted from the user's 21stdev sign-in card
reference (`sign_in_prompt.txt`, NOT committed) — inspiration only, no
framer-motion/lucide added, `/login` untouched. **Gotcha:** decorative
`::before` glows with negative horizontal insets cause real horizontal
overflow on mobile (pseudo-elements don't show up in element-scan debugging —
found via `document.documentElement.scrollWidth`); clamp them in the narrow
media query. **Gotcha:** an occluded/backgrounded automation browser throttles
rAF + paint (2 frames in 1.8s), making transitions/computed styles look broken
— verify with direct DOM `.click()` + forced `getComputedStyle`, not timed
screenshots.

Two live observations (NOT M13C.1 bugs, left as-is): (1) roadmap generation
drifted and returned 502 three times in a row with `GEMINI_MODEL=
gemini-2.5-flash-lite` at temp 0.7 — the fail-closed validator + the intake
page's retry message handled every 502 correctly, but flash-lite preserves the
template structure poorly. **FIXED in M13C.1B**: roadmap generation now falls
back to a deterministic template-backed roadmap on drift/failure, so a real
tester is no longer blocked (no manual seeding) — see
[[roadmap-llm-conventions]]. (2) Missing `favicon.ico` logs a benign 404 on
every page — cosmetic, deferred.

**M13D.5 (2026-07-05) landing precision fix pass conventions.** (1) **One
type family on the landing**: `.landing { --display: var(--sans); }` makes
every display-font usage inside the landing resolve to DM Sans (headlines are
just bigger/bolder body type, weight 700, -0.025em) while the app interior
keeps Space Grotesk. The user rejects headlines that read as a *different*
typeface from body text. (2) **Full-bleed landing**: `.landing` has no
max-width; header/footer bars span the viewport; every scene carries the
shared gutter rule (`.landing .hero, .scene, .closing, .proof, .trap-sticky,
.bl-sticky, .gate-sticky { padding-inline: clamp(20px, 4vw, 52px) }`). When a
static-mode rule needs to zero a sticky panel's vertical padding, use
`padding-top/bottom: 0`, never the `padding: 0` shorthand — it would kill the
gutter (specificity/order traps). (3) **Build Loop anti-jank**: the card row
is a fixed-height flex row (`.bl { height: 276px }`) so cards trade width but
the row can never grow-then-shrink; the scroll mapping has hysteresis (dead
zone H=0.22 stage units around boundaries, track 460vh so each stage holds
~50vh). (4) **GateScene** simulates the defense as a scroll-revealed chat
(labels turn_01/your_answer/follow_up/explain_implementation/defense_status/
recorded_in_report, "simulated preview" pill, no scores/evaluator reasoning);
the body reserves the exact full-content height (min-height) so the panel
never resizes as messages surface. **Gotcha:** a styled bubble must not be a
plain inline `span` — inline boxes fragment border/background per line and
the text overflows the visual box; set `display: inline-block`. (5) **Login**
is `.auth-screen` (min-height 100svh, flex-centered, fits one viewport so no
scroll can carry over) + `.glass .auth-card`, plus a `window.scrollTo(0, 0)`
on mount; auth logic untouched. (6) **80% Trap proof band** (`.proof`): the
trap is presented as a named pattern, not a statistic, with two compact
arXiv citations (Perry et al. 2211.03622, Fu et al. 2310.02059) — keep claims
hedged ("research has found…can carry"), never claim proven Codize outcomes.

**M13E.1 (2026-07-05) — core-app usability conventions.** (1) **App layout**:
`.main` is uncapped (`flex: 1; min-width: 0`) with a centered `.main-inner`
(max 1460px) — the old `max-width: 1060px` directly on `.main` was the cause
of the "smushed left, dead right half" complaint (flex kept it left-aligned).
Pages that need contextual help use `.workspace` (grid: content column +
330px sticky `.ws-rail`, collapsing ≤1150px) — the rail is where extra width
goes (GuideCard cards: what the page is, examples, glossary), never
full-width paragraphs. The shell had NO mobile rules before M13E.1; ≤840px
the sidebar is now a wrapping top bar (`.shell` column, footer inline via
`margin-left: auto`). (2) **Tutorial**: `components/Tutorial.tsx` (originally 9
steps in M13E.1; now derived from the canonical eight-stage Journey),
auto-opens once per browser (`codize:tutorial-seen` in localStorage), sidebar
Help section reopens it. It deliberately closes via button/Escape/backdrop —
do NOT copy the reconnection modal's locked-dismissal pattern, which is
spec-mandated only for reconnection; the tutorial must never trap a user.
Render order: `{!reconnection && showTutorial && <Tutorial/>}` — the
reconnection modal always wins. (3) **Intake edit-until-finish**: the backend
(`intake_service.submit_answer`) accepts an already-answered question until
`intake_completed_at` is set; first-answers stay strictly sequential so gaps
can never appear. The frontend REMOVED the auto-`completeIntake()` after Q5 —
completion is an explicit "Finish intake" review card, otherwise the edit
affordance would be unreachable exactly when users want it most. Q4 edits
re-render the option buttons, not a textarea. (4) **Chips**: `button.chip`
fills (replaces) the target field's state — tap-to-use starters for Q3/Q5 and
the Prompt Builder. Q1/Q2 get placeholder examples only, NOT chips: everyone
tapping the same purpose would defeat intake. (5) **phaseGuide**:
`lib/phaseGuide.ts` is the static beginner layer — keyword-matched on phase
titles (order matters: `integration` before `frontend`, `llm integration`
before both; `persistence|history` after `conversation ui`), covers all 21
template titles (unit-tested against the list) with a generic fallback for
personalized drift. No LLM anywhere; a future AI confusion assistant is a
separate spec-guardian-gated milestone. (6) **Multi-project is deferred**:
`get_project` is newest-row-wins, so a second `projects` row would silently
orphan the first (no error!) — never ship a working "+ New project" until
`docs/plans/deferred/multi_project_dashboard_plan.md` is implemented; the disabled
affordance + honest rail note is the M13E.1 ceiling.

**M13E.4 (2026-07-12) — UI system polish conventions** (skill-driven pass;
Impeccable/Taste/Emil-motion were requested but not installed — the installed
`ui-ux` + `frontend-design` skills served as the critics). The system, all in
globals.css: (1) **`.card.primary`** is the app's visual signature — a 2px
accent LEFT RAIL (never a full violet outline) marking the ONE primary card
per screen (cockpit hero, phase next-step, prompt Step 1, gate active step,
evidence add, verify checks, intake current question); it's the only card
with a hover lift, and the sidebar's active link echoes it via
`inset 2px 0 0 var(--accent)`. Never use inline
`style={{borderColor:"var(--accent)"}}` again. (2) **No resting glow**:
`.btn.primary` is a crisp solid; depth (shadow+lift) appears on hover only;
all buttons get `:active scale(0.98)` press feedback. (3) **Softened status
color**: pills/notices use `color-mix(... 35–40%, transparent)` borders over
full-strength ones; **cooldown is `warn` (amber), never `danger`** — red is
reserved for genuine errors and honest recorded "fail" data. (4) **Fewer
boxes**: `details.help` and `.loop .step` are borderless (tint-on-surface);
`.card:hover` border change removed; generic cards don't react. (5) **Type
scale**: page-title 26px display; textareas are SANS 14px (mono is only for
code-like output — pre.output, .mono, code); page-sub max 62ch. (6) **Motion
budget** (all transform/opacity, all neutralized by the global
prefers-reduced-motion kill switch at the end of globals.css): `reveal`
(disclosure bodies, 180ms), `rise` (pre.output — the prompt payoff, 240ms),
primary-card hover lift, button/chip press scale. Do not add ambient or
looping animation to the protected app. (7) Focus: inputs use a 3px
color-mix ring (box-shadow), buttons/links keep the 2px outline.

**M13E.3 (2026-07-07) — cognitive-load / text-density conventions** (root
cause of the pilot's "overwhelming" feedback — see [[pilot-ux-lessons]]).
(1) **GuideCard is a `<details>`** — collapsed by default, `defaultOpen` prop
for rare must-see cards; never revert it to an always-open card, and never
put load-bearing instructions ONLY inside one. (2) **Density rule**: max 1–2
explanatory sentences visible at the top of a screen; everything else behind
`details.help`/GuideCard; prefer chips + placeholders over hint paragraphs;
don't repeat the same workflow explanation across pages. (3) **One primary
action per screen**: an accent-bordered card (`borderColor: var(--accent)`)
with one `btn primary` — cockpit's "Do this next" (state-aware target:
gate_ready → gate, else phase), the phase page's "Next step" (first
null workflow section in Build Loop order, else the gate), Prompt Builder's
Step 1. (4) **Prompt Builder is the hero surface** (pilot 5/5): Step 1 = the
ask + starter chips (guide.asks + roadmap AI tasks merged into one chip row),
Steps 2/3 = optional context/guardrails with short labels and no hint
paragraphs; guardrail quick-add chips ("Plan first" → planFirst,
"Give manual verification steps" → wantChecks, others append via
`addConstraint` — append, never overwrite, dedupe by `includes`).
(5) **Evidence = "one small piece is enough"**: 5 primary kind chips
(screenshot/terminal/test/changed-files/note), technical kinds behind "More
types", explicit "skip for now →" escape hatch; honesty fine print lives in
the collapsed rail card, never deleted. (6) **Gate copy is coaching, never
punishment**: "not a test of intelligence", "you can keep your code open",
fail = "review and try again"; example anchors + "what makes a good answer"
are collapsed details on ReadyView; strictness stays server-side only.
(7) `LoopOverview` (components/) is the reusable 8-line "what you'll actually
do" answer — collapsed `details.help`, currently on the cockpit hero; reuse
it instead of writing new onboarding walls. (8) `button.chip.active` marks a
selected chip (evidence kind picker).

**M14C (2026-07-12) — artifact-aware Project Defense UI.** The gate page now
consumes `GET /gate/context-summary` (metadata-only — see
[[artifact-aware-defense-ui-conventions]] for the full rules): a separate
non-blocking fetch on mount (never gates the page or the Begin button),
`lib/defenseContext.ts` pure helpers (grouping, deterministic prep tips,
missing-note phrasing — unit-tested), compact `span.pill ok` source chips +
one "Project context" pill, missing artifacts phrased as optional with links,
truncation as one muted line, two new collapsed `details.help` disclosures on
ReadyView, a static "Grounded in your project" eyebrow on active questions
(never per-question source attribution), and the stale "gate doesn't read
your saved artifacts" rail copy corrected (questions draw on recorded work;
pass/fail stays about the student's own explanation). Refresh = fetch on
mount; no polling, no query library.

**M15B (2026-07-13) — "Bring Back What Changed" page.** The fifth
workflow-section page (`app/app/phase/import`) — see
[[implementation-import-ui-conventions]] for the full rules. Frontend-only:
one `WorkflowSectionName` extension + pure `lib/implementationImport.ts`
helpers (unit-tested — testable copy/logic lives in the lib because vitest
is node-only); the page rides the existing useWorkflowSection/drafts/SaveBar
machinery (SaveBar gained an optional `disabled` prop). New CSS primitives:
`label.chip` (semantic radio chips with `:has(input:focus-visible)` ring)
and `textarea.code` (mono pasted-material box). The Build Loop is 8 steps
("Bring Back" after Generate); phase/cockpit progress reads "Workflow: N/5
captured" — the backend has returned five section keys since M15A, so any
hardcoded /4 would display 5/4. Imported material is sent VERBATIM with an
honest counter and save-blocking over-limit messages, never a maxLength
clip; secret-like drafts show a visible "not kept on this device" warning.

**M13E.2 (2026-07-06) — pilot bugfix conventions.** (1) **Local drafts**
(`lib/drafts.ts`): unsubmitted text survives tab/page switches via
localStorage keys `codize:draft:<user id>:<surface>` (surface = section+phase,
gate session+step, or intake question — never unscoped; user id comes from the
Supabase session, so drafts can't cross accounts on a shared machine).
`useDraft` restores once AFTER the backend prefill (backend stays source of
truth; a `draftApplied`/`appliedFor` ref gates the overlay), debounce-writes
400ms (the pending write is deliberately NOT cancelled on unmount — that's
the tab-switch case), refuses to persist secret-marker content (same 4
markers as `schemas/workflow.py`), and is cleared on successful save/submit
— with a one-shot `skipDraftEcho` ref per page because a successful save
re-prefills state from the stored artifact and would otherwise instantly
rewrite the just-cleared draft. Pure helpers are unit-tested with a fake
storage (vitest runs in node — no jsdom, keep hook logic thin). Intake
"Cancel" on an edit clears that edit's draft (explicit discard). (2) **Every
core page uses `.workspace`** now (cockpit, intake, prompt, review, evidence,
verify, gate, phase); `.main-inner` is 1620px and ≥1800px widens the rail to
400px. The gate explainer and the phase page's roadmap/"Two kinds of
progress" cards live in the rail. (3) **Progress split language**: "Build
tasks: X/Y" (roadmap checkboxes, ticked manually) vs "Workflow: N/4 captured"
(saved artifacts) — never conflate them, never auto-tick a build task from an
artifact save; the phase page and cockpit both carry an explicit "saving
artifacts never ticks a build task" line. (4) **Verification notes are
result-specific** (`NOTE_PROMPTS`): pass→how checked, fail→what broke,
skipped/n/a→optional reason with a "no evidence needed" hint; the report
labels them honestly (`VERIFICATION_RESULT_LABELS`: "skipped — not checked
yet", "n/a — doesn't apply") and never prints the raw enum. Notes stay
optional for every result — nothing blocks a save.

**M15C.2 (2026-07-13) — Change Map review UI.** The frontend-only page is
`app/app/phase/change-map/page.tsx`, reached after Bring Back and before
Review. It extends the existing API/types/workflow-fetch/drafts/SaveBar/CSS
system—no second client, fetch state machine, persistence layer, or design
system. Exact pure logic lives in `lib/changeMap.ts` and is unit-tested:
student-facing mappings, category grouping, review progress, effective display,
student-only PUT shaping, validation, dirty/readiness/stale/page-state helpers,
local-draft compatibility, and phase next-step routing. Normal generation sends
no body and is explicit-click only; replacement alone sends
`replace_existing=true` after an inline warning. Source excerpts are rendered
only as React text in a bounded `<pre>` inside a collapsed native disclosure.
One primary `.card.primary` contains only populated category sections separated
by quiet rules; item rows are not nested cards. Semantic fieldsets/radios carry
decisions, status/error announcements use live regions, long paths/excerpts
wrap or scroll, and controls stack at 640px. Change Map is top-level workflow
state with its own not-created/draft/reviewed/stale status and is excluded from
the five-section count. See [[change-map-ui-conventions]].

**M16A.2 (2026-07-13) — linked implementation Review UI.** The existing
`app/app/phase/review/page.tsx` now branches only after the shared workflow GET:
strict `initialized_from_change_map=true` data uses the linked UI; an existing
manual artifact keeps the original fields/draft/save UI; no artifact uses the
Change Map prerequisite/explicit Start Review states. Initialization never runs
on mount and only deliberate replacement sends `replace_existing=true`.
`lib/review.ts` is the pure contract layer (exact labels/category order,
source-resolution copy, form initialization, Unicode-safe validation, canonical
target-only PUT, dirty/progress/completion, source-binding fingerprint, draft
restore, stale/replacement and Build Loop status), with React source safety in
`components/LinkedReviewTarget.tsx`. Linked drafts reuse `useDraft`; surface is
`linked_review:active-project:<phase>:<safe fingerprint>` and the existing hook
adds authenticated-user scope. The current one-project account contract makes
`active-project` the project scope until multi-project exposes a safe id. Stale
Review is readable/disabled and rebuilt only after an inline warning. Needs
testing and uncertainty count as honest decisions; zero targets stay neutral.
Continue to Verification is a link only. Workflow N/5, build tasks, Change Map,
Evidence, Verification records, Defense, evaluator, and report data flows are
unchanged. Full rules: [[linked-review-ui-conventions]].

**M16B.2 (2026-07-14) — linked Verification suggestions and student results
UI.** `/app/phase/verify` branches after the existing workflow GET: strict
`initialized_from_review=true` data uses linked Verification, an existing
manual artifact keeps its exact original checklist/explanation/draft/save UI,
and no artifact inspects the saved Review before offering an explicit start.
`lib/verification.ts` is the pure contract layer (exact categories/results,
runtime mode guard, prerequisite state, grouping, Unicode-safe validation,
canonical student-only target PUT, dirty/progress/summary/recorded completion,
safe binding fingerprint, draft restore, stale/replacement, zero-target, Build
Loop status). `components/LinkedVerificationTarget.tsx` keeps Review source and
server suggestion as escaped plain text, with a student-owned check textarea
and native result radios. Linked drafts use
`linked_verification:active-project:<phase>:<safe fingerprint>`; `useDraft`
adds authenticated-user scope and its existing debounce/storage-failure/secret
guard. Result changes clear result-specific notes before canonical comparison.
Stale work is readable and disabled, rebuild is explicit, and saved completion
links to Evidence only. Phase next actions now distinguish Start/Continue/
Rebuild Verification and Continue to Evidence. N/5 capture, build tasks,
manual Verification, Evidence data, Defense, and Report remain separate. Full
rules: [[linked-verification-ui-conventions]].

**M16B.3B (2026-07-14) — linked Evidence UI.** The existing Evidence page now
has a strict third mode in addition to the preserved manual form and its
prerequisite states. `lib/evidence.ts` is the pure contract layer: strict
linked/invalid-linked detection; exact backend enums and caps; server-only
eligibility interpretation; Unicode-code-point and request-belt validation;
canonical active-field-only target updates; changed-only save shaping;
server-completion progress; safe-link rendering; binding fingerprint/draft
scope; stale/rebuild rules; and Workflow/phase next-action status. The page
does one preview GET only when no linked artifact is mounted, never POSTs on
mount, starts with zero selected targets, and creates/rebuilds only after
explicit actions. Read-only Verification context stays visually above the
student's Evidence controls. Linked drafts use
`linked_evidence:active-project:<phase>:<safe fingerprint>` and contain target
ids plus student fields only—never source text or provenance. Stale work is
readable/disabled; replacement gets a fresh zero-selection preview and a
destructive warning. Completion trusts only saved
`evidence_record_complete`. Manual Evidence, N/5 capture, Defense, Report,
gate, and evaluator behavior are unchanged. Full rules:
[[linked-evidence-ui-conventions]].

**M16C.2 (2026-07-14) — Artifact-aware Defense/Report frontend.** Defense readiness is a non-blocking metadata consumer of `GET /gate/context-summary`; render the server's Change Map/Review/Verification/Evidence labels and exact current/missing/incomplete/stale/manual/malformed states, plus truncation, without reconstructing or displaying source content. A context error gets its own retry and never disables Begin. The stable-attempt explanation belongs only before a new attempt; active/resumed attempts use the existing gate contract and preserve empty student-owned answers, scoped drafts, limits, order, evaluation, PASS/FAIL, cooldown, and retry semantics. The Report is now an authoritative `GET /report/{phase}` view selected by `?phase=` so a just-passed phase remains reachable after advancement. Do not combine it from workflow/intake/gate client state. Render attempt-snapshot vs legacy-current provenance, the exact truth notice, curated Change Map/Review/Verification/Evidence, public transcript, and outcome as separate semantic sections. User values are React text; only `safeEvidenceHref` may produce HTTP(S) external links with `noopener noreferrer`. The cockpit's primary handoff may point to Defense or Report, but workflow capture remains N/5. See [[artifact-aware-defense-report-ui-conventions]].

**M16N (2026-07-14) — guided project shell.** `/app` remains the route and is
visibly Project Home. `lib/guidedProjectNavigation.ts` is the single typed,
pure lifecycle model used by desktop/mobile shell, Project Home, Phase
Workspace, compact Journey, Continue, and Project Record. The provider reads
saved evaluation/workflow/gate/intake state and refreshes after confirmed API
mutations; it never reads drafts or derives progress from pathname. Future
stages are non-links, current lifecycle and `aria-current=page` are separate,
and stale records remain readable under Project Record. Mobile uses the same
model in a modal drawer with focus entry/trap/Escape/return. See
[[guided-project-shell-conventions]].

**M17 (2026-07-15) — beginner entry and adaptive guidance.** Project Home owns
the short entry into the existing intake: situation, confidence, and a
conditional AI-change question, with no preselected answer. The server-derived
recommendation feeds the existing M16N provider; saved workflow truth always
wins. The 80% Trap recovery card links to the existing Import page and never
reimplements Import, Change Map, Review, or Verification. Use the single
`AdaptiveStepGuide` plus `lib/workflowGuidance.ts` across all eight Journey
stages; confidence changes initial detail, not workflow requirements. Browser
storage may remember only a scoped disclosure boolean. Legacy users get
standard collapsed guidance and can update preferences without reset. See
[[beginner-entry-adaptive-guidance-conventions]].

**M18A (2026-07-17) — product truth and lifecycle safety.**
`lib/workflowJourney.ts` is now the canonical exact eight-stage student-facing
Journey: Prompt Builder → Bring Back What Changed → Change Map → Review →
Verification → Evidence → Project Defense → Defense Report. Guided navigation,
tutorial, compact loop, and landing workflow panel derive from it; external AI
generation is an action between Prompt and Import, not a route/stage. Formal
Defense consumes backend `readiness`, uses neutral blocked styling, lists exact
prerequisites, and preserves the shared global Continue action; Begin is absent
when blocked. Active/cooldown/retry/complete stay distinct. Change Map 502 UI is
one focused alert with an exact source-matching correction, retry, Import review,
and explicit manual fallback only when no map exists. See
[[project-classification-and-product-truth-conventions]].
