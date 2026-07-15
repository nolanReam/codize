# Codize frontend (M13C)

The Codize v3 **AI Workflow Workspace** — a Next.js (App Router) frontend that
makes the Codize Build Loop visible and usable:

**Plan → Prompt → Generate → Bring Back → Change Map → Review → Verify → Explain → Commit/Reflect**

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
                        phase explanation + starter-ask chips via lib/phaseGuide;
                        after a save, hands off to "bring back what changed")
      import/page.tsx   Bring Back What AI Changed (M15B) — the implementation
                        import: source-kind radio chips, verbatim pasted
                        material (mono textarea, honest 40k counter — never
                        clipped), optional changed files / own summary / tool
                        name, phase-scoped local draft, secret-guarded save
      change-map/       Review Your Change Map (M15C.2) — explicit draft
        page.tsx        generation, category-grouped student review, source
                        disclosures, corrections/rejections/uncertainty,
                        student-added items, save + confirmation, stale-map
                        regeneration, and scoped local review drafts
      review/page.tsx   Review What Changed (M16A.2) — explicit confirmed-map
                        initialization, grouped linked targets, student-owned
                        decisions, scoped drafts, stale rebuild, plus the
                        preserved legacy/manual Review form
      evidence/page.tsx Evidence Panel
      verify/page.tsx   Linked + legacy/manual Verification
    gate/page.tsx       Artifact-aware Project Defense — metadata-only project-
                        record readiness, then the unchanged anchor → 3 turns →
                        evaluate → pass/fail flow; resume-safe
    report/page.tsx     Authoritative Project Defense Report from GET /report/{phase}:
                        snapshot/current-workflow provenance, workflow records,
                        transcript, outcome, and safe Markdown copy/download
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
                        secret-marker guard, cleared on successful save),
                        implementationImport + test (pure M15B helpers: source-
                        kind labels, form ↔ payload shaping, save-blocking rules,
                        page copy constants), changeMap + test (exact types,
                        labels, grouping, progress, student-only PUT payload,
                        confirmation readiness, stale state, local drafts, and
                        phase next-step logic), review + test (M16A.2 linked/
                        legacy detection, labels, grouping, validation,
                        student-only payloads, dirty state, drafts, progress)
```

## Backend routes consumed

Intake (`/intake/*`), roadmap (`/roadmap/generate`, `/roadmap`), phases
(`/phases*`), workflow artifacts (`GET /workflow/{phase}`,
`PUT /workflow/{phase}/{section}`), Change Map
(`POST /workflow/{phase}/change-map/generate`,
`PUT /workflow/{phase}/change-map`,
`POST /workflow/{phase}/change-map/confirm`), linked Review
(`POST /workflow/{phase}/review/from-change-map`, with explicit replacement
only, plus the existing Review GET/PUT paths), reconnection (`GET /reconnection`,
`POST /reconnection/acknowledge`), evaluation (`GET /evaluation`), and the full
gate flow (`GET /gate/current`, `POST /gate/start`,
`POST /gate/{id}/turn1|turn2|turn3|evaluate`), plus the metadata-only
`GET /gate/context-summary` (M16C.1 — source ids, labels, exact workflow-source
states, and truncation flags, **never artifact content**; fetched non-blocking
on gate-page mount, so it can never gate the defense). The Defense Report is
read only from `GET /report/{phase}`. The browser supplies only the phase path
parameter; the server owns the workflow snapshot/current-workflow fallback,
curated records, transcript, evaluator outcome, and truth notice.

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

## Status (M16C.2)

Project Defense and Defense Report now consume the reviewed M16C.1 contracts.
The Defense ready state loads `GET /gate/context-summary` independently from
the gate lifecycle and renders Change Map, Review, Verification, and Evidence
as current, missing, incomplete, stale, manual, or unavailable, with honest
truncation copy. The summary is metadata-only: it never renders artifact text,
internal ids, bindings, fingerprints, or snapshot internals. A failed summary
load stays retryable and never disables **Begin defense**. The page explains
that the server keeps a stable record when a new attempt starts, while every
answer remains empty and student-owned. Anchor, three-turn ordering, draft
persistence, request limits, evaluation, PASS/FAIL, cooldown, and retry behavior
remain on the existing gate endpoints.

The Report page is no longer client-assembled from mutable workflow screens.
It requests `GET /report/{phase}` and renders the server-owned attempt snapshot
or the explicitly labeled current-workflow fallback for legacy attempts.
Change Map provenance and uncertainty, Review decisions, student-recorded
Verification outcomes, linked/manual/stale/unavailable Evidence, the student-safe
Defense transcript, exact PASS/FAIL outcome, source states, truncation, and the
backend truth notice remain separate. Evidence and Verification are never
called proof. HTML-like values render as text; only validated HTTP(S) Evidence
URLs become `noopener noreferrer` links. Loading, prerequisite, unavailable,
retry, malformed-source, long-content, 390/768/1080/1920, keyboard, focus, and
reduced-motion states are covered. Cockpit and phase handoffs can now complete
the core workflow at Project Defense/Report without changing workflow **N/5**.
No backend, migration, prompt, provider, evaluator, or model change was needed.

## Status (M16B.3B)

The existing `/app/phase/evidence` route now consumes the M16B.3A handoff
without changing the manual Evidence path. A pure preview GET renders the
server's prerequisite state and eligibility decisions; nothing is created on
mount, no result is preselected, and only an explicit student selection is
posted. Passed and failed Verification results remain source context rather
than Evidence. Skipped, not-applicable, unrecorded, and otherwise ineligible
results stay visible in a secondary disclosure and cannot be selected.

Linked Evidence keeps each saved Verification check, result, and notes
read-only above the student's own choice: not addressed, add supporting
Evidence, or record why Evidence is unavailable. Recorded targets require at
least one of the existing nine Evidence entry kinds and may include a bounded
explanation; unavailable targets require a reason and never masquerade as
Evidence. Saves send only changed student-owned target updates. Server-owned eligibility,
source snapshots, bindings, stale state, and completion never echo back in a
write. Completion copy is driven only by the returned
`evidence_record_complete` field and means the Evidence record is addressed,
not that the implementation is correct.

Linked drafts reuse the existing secret-guarded local layer and are scoped by
authenticated user, active project, phase, and a safe initialization/target
fingerprint that contains no source text. Stale work stays readable and
disabled; rebuilding fetches a current preview with nothing selected and sends
`replace_existing=true` only after an explicit warning. Manual Evidence is
preserved unless the student deliberately replaces it. Build Loop and phase
next actions distinguish unavailable, ready, in progress, complete, and stale
Evidence while workflow capture stays exactly **N/5**. Defense, Report, gate,
evaluation, backend, schema, prompts, and providers are unchanged pending M16C.

## Status (M16B.2)

The existing `/app/phase/verify` route now supports both M16B.1 linked
Verification and the original manual Verification Lab. No artifact is created
on mount: a current, complete saved linked Review presents **Start
Verification**, while missing, incomplete, and stale Review states point back
to the exact prerequisite. The explicit initializer uses
`POST /workflow/{phase}/verification/from-review`; only a confirmed rebuild
sends `replace_existing=true`.

Linked targets render in the backend's six-category order and visibly separate
the saved Review snapshot, optional Review rationale, server suggestion,
editable student check, result, and notes. A suggestion is never shown as a
performed test. Exact results are Passed, Failed, Skipped, and Not applicable;
all explicit outcomes count as recorded, but only Passed counts as passed and
even that applies to one check only. Saves use the existing Verification PUT
with changed `target_updates` containing only the server target identifier and
`student_check`, `result`, and `result_notes`. Canonical payload comparison
prevents hidden notes from causing false dirty state.

Linked drafts reuse the existing secret-guarded local layer, scoped by user,
active project, phase, and a safe Review-binding/ordered-target fingerprint.
Stale work stays readable and disabled; rebuilding requires an inline warning
and clears the incompatible draft only after success. Zero targets stay
neutral. Recorded completion appears only after every outcome is server-saved,
then **Continue to Evidence** is navigation only—no Evidence is created or
prefilled. Build Loop and phase next actions distinguish ready, in progress,
results recorded, stale, and zero-target states while workflow capture remains
exactly **N/5**. No backend, provider, prompt, schema, or migration changed.

## Status (M16A.2)

The existing `/app/phase/review` route now supports both reviewed-contract
modes. A confirmed, current Change Map shows **Start Review** and initializes
only after that click; missing, draft, and stale maps get calm prerequisite
states. Linked Review groups the six backend-selected implementation categories
in fixed order and keeps each bounded source snapshot visibly separate from the
student's decision: Keep, Revise, Remove, Needs testing, or I'm not sure.
Revision/rationale validation mirrors the backend's 2,000-code-point rules;
the PUT contains only `target_updates` with the server target reference and the
three student-owned fields. Canonical payload comparison prevents hidden
revision text from creating false dirty state or contradictory updates.

Progress is `N of M items reviewed`, never correctness. Needs-testing and
uncertain decisions count honestly; a zero-target Review stays neutral. Local
drafts reuse the existing secret-guarded system and are scoped by user, active
project, phase, and a safe Change Map/ordered-target fingerprint. Stale Reviews
remain readable but not editable; rebuilding requires an inline destructive
warning and is the only UI path that sends `replace_existing=true`. Existing
manual Review artifacts keep their original fields, save path, draft key, and
UI unless the student explicitly starts over. Completion links to Verification
only—no suggestions, checks, evidence, or downstream records are created.
Build Loop Review status and phase next actions distinguish ready/in-progress/
complete/stale while the existing `Object.values(sections)` **N/5** count is
unchanged. No backend or migration change was needed.

## Status (M15B)

The **Bring Back What AI Changed** page (`app/app/phase/import`) completes the
loop's missing middle: after using their prompt in an external AI tool, the
student brings the result back — pasted AI response, git diff, code snippet,
changed-file list, and/or their own summary — before reviewing it.
Prevention-first framing ("keep track of what changed before moving on", "you
do not need every item"), with recovery as a quiet rail card ("Already
stuck?"). One primary card: a semantic radio-chip source picker (six
plain-language kinds mapped to the M15A enum, never shown raw), the
kind-relevant main field emphasized, everything else behind "Add more detail
(optional)". Material is sent **verbatim** (the backend preserves formatting);
over-limit input blocks the save naming the field — nothing is ever silently
clipped. Saves go through the existing generic workflow client
(`PUT /workflow/{phase}/implementation_import`, full-section replace with a
plain-language "replaces this phase's previous save" note when editing);
drafts use the existing scoped localStorage layer with the secret-marker
guard (credential-like drafts are not kept locally, with a visible warning;
the backend's 422 never echoes the value). The Build Loop strip, sidebar,
phase "Next step" ordering, and cockpit/phase progress ("Workflow: N/5
captured") all carry the new step; the Prompt Builder hands off to it after a
save. No automatic LLM call; after save, the explicit next action opens the
M15C.2 Change Map page. Raw imports stay out of the Defense Context by backend
construction.

## Status (M15C.2)

The student-facing Change Map is complete at `/app/phase/change-map`. It reads
the top-level M15C.1 map from the existing workflow fetch, never as a sixth
artifact. Generation happens only after **Create Change Map**; a safe 502 keeps
the saved import unchanged and offers retry/import review. The page groups only
populated categories, labels AI drafts separately from student-added items,
renders bounded source excerpts as plain text, and supports Looks right,
correction, rejection, uncertainty, and needs-inspection decisions. Review
progress saves explicitly through the student-only PUT shape; compatible
unsaved review state uses the existing secret-guarded, user/phase/map-version
local draft layer. Confirmation records review—not correctness—and unresolved
items remain visible. Stale maps remain readable, cannot confirm, and require a
deliberate `replace_existing=true` regeneration warning. Build Loop/navigation,
phase next-step logic, and the import handoff include Change Map while workflow
progress remains **N/5**. Review Board, Evidence, Verification, Project Defense,
Defense Context, and Defense Report data flow remain unchanged pending M16.

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

Since M14B the gate's **questions** draw on the student's recorded workflow
artifacts (server-side grounding), and since M14C the UI says so: the gate
ready screen shows compact source chips from `GET /gate/context-summary`
(missing artifacts are optional, never blocking), active questions carry a
subtle "Grounded in your project" label, and `lib/defenseContext.ts` derives
deterministic preparation tips. The **evaluation stays artifact-blind** —
recorded artifacts never decide pass/fail, and the UI never claims Codize
verified anything. Raw gate scores, evaluator reasoning, hidden thresholds,
internal prompts, raw context, and grounding metadata never reach the client.

## Status (M16N)

The protected app now uses one state-aware guided project shell. `/app` keeps
its route identity but is visibly named **Project Home**. Desktop and mobile
both consume `lib/guidedProjectNavigation.ts`: one saved-state **Continue**
action, the exact eight-stage Journey, and a secondary **Project Record** for
saved/completed/stale work. Future stages are readable non-links; completed
Journey rows are progress markers; stale Review, Verification, and Evidence
remain readable under Project Record with `Needs update` language.

Navigation loads existing `/evaluation`, `/workflow/{phase}`, `/gate/current`,
and intake status through `GuidedProjectNavigationProvider`. Prompt/Import use
their saved sections, Change Map uses confirmed/stale state, linked Review and
Verification use saved target decisions/results, Evidence trusts only the
server `evidence_record_complete` flag, and Defense/Report use the exact gate
lifecycle. Local drafts, route presence, and optimistic state never advance
the shell. Existing routes, manual/legacy records, workflow N/5, save/rebuild
flows, backend lifecycle, and Report truth rules are unchanged. The mobile
version is a focus-managed modal drawer with Escape, trapped Tab focus, return
focus, and the same model as desktop.
