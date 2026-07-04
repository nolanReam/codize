# Codize M13C.2 — Gate UI + Project Defense Report + Pilot Polish

Implement the next frontend milestone for Codize’s v3 AI Workflow Workspace MVP.

This milestone should complete the user-facing loop after M13C.1:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

M13C.2 focuses on:

1. Live Interrogation Gate UI using the existing M9 backend
2. Full client-assembled Project Defense Report
3. Pilot-readiness polish
4. Small cosmetic fixes such as favicon if quick

Do not start M14.

Do not implement evidence-aware gate prompts yet.

Do not modify gate evaluator logic.

Do not weaken gate validation.

Do not create migrations.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, analytics dashboard, hosted coding runtime, or complex gamification.

## Current State

Relevant commits:

- M13B workflow artifact backend: `de42d5b`
- M13C.1 frontend foundation: `03e3c1f`
- M13C.1 live smoke pass: `3cb6275`
- M13C.1B roadmap reliability hotfix: `6eb7e57`

M13C.1 implemented the frontend foundation:

- landing page
- login/signup
- protected app shell
- intake
- cockpit
- phase board
- prompt builder
- review board
- evidence panel
- verification lab
- gate placeholder
- report placeholder

M13C.1B fixed the roadmap-generation pilot blocker by adding deterministic template fallback.

## Read First

Read:

- `CLAUDE.md`
- `docs/context/context_authority.md`
- `docs/context/codize_product_vision_v3.md`
- `docs/context/m13_ai_workflow_workspace_plan.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/workflow-artifact-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/evaluation-conventions.md` if it exists
- `.claude/memory/roadmap-llm-conventions.md`
- frontend files from M13C.1
- backend gate router/service/schemas
- backend workflow router/service/schemas
- backend evaluation route/service/schemas

Do not read `conversations.json` unless genuinely needed.

## First Actions

Inspect current state:

```bash
git status
git log --oneline -5
```

Then inspect existing frontend routes:

- `/app/gate`
- `/app/report`
- app shell/sidebar/nav
- frontend API client
- frontend auth/session handling
- workflow artifact components

Do not duplicate existing pages.

Extend the current frontend.

## Goal

Make Codize’s main MVP loop feel complete enough for a pilot user:

1. User builds/reviews/verifies a phase.
2. User opens Gate.
3. User completes a live defense flow.
4. User opens Project Defense Report.
5. User sees a useful report assembled from real collected data.
6. User can copy/export the report text for portfolio/interview prep.

## Part 1 — Live Interrogation Gate UI

Replace the current `/app/gate` placeholder with a real UI around the existing M9 gate backend.

Use existing backend route shapes.

Do not invent route names if backend already has gate routes.

Inspect backend gate router/schemas before coding.

The UI should support the existing M9 flow:

- show current gate status
- show current phase
- show readiness/cooldown state
- start or resume gate session if backend supports it
- display the anchor prompt/anchor step if backend uses one
- collect user answers turn by turn
- submit answers to backend
- show the next question/turn from backend
- show final pass/fail outcome
- show cooldown if failed
- avoid exposing raw scores, evaluator reasoning, hidden thresholds, or internal prompts

If the backend route model differs from the above, follow the actual backend contract.

## Gate UI Requirements

The gate page should feel like:

> Defend what you built.

Not:

> Take a random quiz.

Use v3 language:

- “Project Defense”
- “Explain the implementation”
- “Show you understand what changed”
- “Be ready to defend this project”

Do not shame the user.

Do not say they are cheating or fake.

The gate should clearly explain:

- why the gate exists
- what the user is defending
- what happens if they pass
- what happens if they fail
- that the gate currently uses the existing M9 backend and is not yet evidence-aware

## Gate Boundaries

Do not make the gate evidence-aware.

Do not send workflow artifacts into the evaluator unless the backend already does this.

Do not alter evaluator prompts.

Do not alter pass/fail logic.

Do not expose hidden score.

Do not expose private evaluator reasoning.

Do not expose internal LLM prompt text.

If workflow artifact context is shown on the side of the UI, make it read-only helper context for the student, not backend evaluator input.

## Gate UX Details

Add practical UI states:

- loading
- not ready / no active project
- ready to defend
- active session
- awaiting next answer
- passed
- failed with cooldown
- backend error
- retry-safe error message

If failed/cooldown:

- show cooldown time if backend returns it
- explain that the user should review their work before trying again
- link back to Review / Evidence / Verification pages

If passed:

- show next step
- link to Project Defense Report
- link back to cockpit/current phase

## Part 2 — Project Defense Report

Replace the `/app/report` placeholder with a full client-assembled report.

The report should assemble from real sources:

- intake/project purpose
- current project/phase
- phase tasks
- workflow artifacts:
  - prompt_builder
  - review_board
  - evidence
  - verification
- gate status/outcome
- evaluation summary
- unlocks if available
- reconnection/evaluation next-action data if useful

Use existing backend routes.

Do not create a new backend report endpoint in this milestone.

## Report Content Requirements

The report should include sections like:

1. Project Overview
   - project name
   - problem being solved
   - who it helps
   - archetype
   - current phase

2. AI Workflow Evidence
   - generated prompt
   - why the prompt is stronger
   - what files changed
   - what AI generated
   - what user accepted/rejected/edited
   - AI assumptions identified

3. Verification Evidence
   - checks completed
   - test output or terminal output
   - app/API/UI check notes
   - security/auth/RLS checks where relevant
   - what the verification proved

4. Project Defense Status
   - gate status/outcome
   - no raw hidden score
   - no evaluator private reasoning
   - cooldown if relevant
   - defense readiness label if already derivable safely

5. Skills Demonstrated
   - planning
   - prompting
   - reviewing
   - verification
   - explanation
   - security awareness if relevant

6. Weak Spots / Next Actions
   - missing evidence
   - incomplete verification
   - gate not attempted
   - failed gate/cooldown
   - recommended next action

7. Interview / Defense Questions
   - derived client-side from the project/phase/artifacts
   - no LLM required
   - examples:
     - “Walk me through your project’s data flow.”
     - “What did AI generate that you had to verify?”
     - “What would break if this route or table changed?”
     - “How do you know this feature works?”
     - “What assumption did AI make?”

## Report Export / Copy

Add at least one practical export method.

Preferred for M13C.2:

- copy report as Markdown to clipboard

Optional if easy:

- download `.md` file

Do not implement PDF export unless it is trivial and does not derail the milestone.

The copied report should be clean, readable Markdown.

Do not include raw private backend data.

Do not include hidden scores or evaluator reasoning.

## Report Honesty Requirements

The report must not overclaim.

If evidence is missing, say missing.

If gate has not been attempted, say not attempted.

If verification is self-reported, say it is self-reported.

Do not call the report cryptographic proof.

Do not say Codize guarantees the project works.

Use language like:

- “Submitted evidence”
- “Self-reported verification”
- “Defense status”
- “Ready to review”
- “Needs more evidence”

## Part 3 — Pilot Polish

Make the app ready for a small pilot with real testers.

Allowed pilot polish:

- fix favicon if quick
- improve obvious empty states
- improve obvious error copy
- make CTA paths clearer
- make cockpit next action clearer
- make sidebar/nav flow clearer
- make save confirmations clear
- add a simple “copied” state for report export
- add small links from report missing sections back to the relevant workspace pages

Do not redesign the whole frontend.

Do not add major new screens.

Do not add analytics dashboard.

Do not add AI news/tool recommendations.

## Optional Roadmap Fallback Note

M13C.1B made fallback silent server-side.

If it is easy and supported by backend data, the frontend may show a gentle note when a roadmap is template-backed.

If backend does not expose fallback metadata, do not add this.

Do not invent fake fallback status.

## Security Requirements

Do not expose:

- service-role keys
- provider keys
- raw gate scores
- hidden unlock thresholds
- evaluator private reasoning
- internal prompts
- `.env` content

Do not render raw untrusted HTML.

Treat all user-submitted workflow artifacts as plain text.

Keep frontend auth through Supabase publishable key only.

Backend remains source of truth for project ownership and protected data.

## Testing / Verification

Run:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

If backend code changes, run:

```bash
cd backend
pytest
```

If backend code does not change, backend tests are optional, but say whether they were run.

Run a focused browser smoke test if possible:

1. login
2. reach app
3. open phase
4. confirm artifacts still load
5. open gate
6. start/continue gate flow as far as test state allows
7. open report
8. verify report shows real collected data
9. copy/export report
10. logout

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update as needed:

- `frontend/README.md`
- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `docs/context/m13_ai_workflow_workspace_plan.md` only if implementation materially changes the plan

Do not rewrite the whole product vision.

## End Requirements

At the end, output:

- files changed
- routes/screens implemented
- gate backend routes consumed
- report data sources consumed
- export/copy behavior implemented
- pilot polish completed
- commands run
- test/build results
- browser smoke result if run
- secret scan result
- known issues
- git commit hash
- next step: pilot test prep / M13C.3 if needed

Commit completed M13C.2 changes.

Stop after commit.