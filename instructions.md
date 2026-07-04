# Codize M13C.1 Recovery — Resume Frontend Foundation

Claude Code stopped midway through M13C.1 because of usage limits.

Continue from the current repository state.

Do not restart the frontend from scratch.

Do not discard partial work unless it is clearly broken, and explain why before replacing it.

Do not reset, checkout, stash, or delete uncommitted changes.

Do not start M13C.2.

Do not implement evidence-aware gate prompts.

Do not modify gate evaluator logic.

Do not create migrations.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, analytics dashboard, hosted coding runtime, or complex gamification.

## Current State

Milestones M1–M12 are complete.

Product vision reset is complete.

M13A planning is complete.

M13B workflow artifact backend is complete.

Relevant commits:

- M12 Evaluation system: `44442b0`
- Product vision reset: `139d898`
- M13A planning: `1d3e32b`
- M13B workflow artifact backend: `de42d5b`

M13C.1 was started but interrupted before completion.

## First Actions

Before coding, inspect the current state:

```bash
git status
git diff --stat
git log --oneline -5
```

Then inspect the frontend work already present.

If a frontend app exists, continue it.

If a frontend app was partially created, repair and complete it.

If no frontend app exists, create the minimal Next.js frontend required by M13C.1.

Do not duplicate files or create a second frontend app.

## Read First

Read:

- `CLAUDE.md`
- `docs/context/context_authority.md`
- `docs/context/codize_product_vision_v3.md`
- `docs/context/m13_ai_workflow_workspace_plan.md`
- `docs/context/codize_master_spec_v2.1.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/workflow-artifact-conventions.md`
- `.claude/memory/phase-workspace-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/reconnection-conventions.md`
- `.claude/memory/evaluation-conventions.md` if it exists
- frontend files already created during the interrupted M13C.1 run
- package/config files in the repo root and frontend directory

Do not read `conversations.json` unless genuinely needed.

## Goal

Finish M13C.1 only:

> Frontend Foundation + Core AI Workflow Workspace

M13C.1 should make the Codize v3 loop visible and usable:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

The frontend should feel like a serious AI engineering cockpit, not a generic roadmap/checklist/quiz app.

## Required M13C.1 Scope

Complete these surfaces enough for a working MVP foundation:

1. Landing page around the 80% Trap
2. Auth flow
3. Protected app shell
4. Intake flow
5. Project Cockpit
6. Phase Workflow Board
7. Prompt Builder
8. Review Board
9. Evidence Panel
10. Verification Lab
11. Basic API client and auth session handling
12. Basic loading, empty, and error states

Gate UI and Project Defense Report may remain skeletons/placeholders in M13C.1 if needed, but navigation should clearly show where they will fit in M13C.2.

Do not fully implement Interview Defense Mode.

Do not fully implement Rescue Mode.

## Backend Routes To Use

M13B added workflow artifact backend routes:

- `GET /workflow/{phase}`
- `PUT /workflow/{phase}/{section}`

Sections:

- `prompt_builder`
- `review_board`
- `evidence`
- `verification`

Frontend must call backend routes with a Supabase Bearer JWT.

Do not fake backend data when real routes exist.

Use honest placeholders only for unfinished M13C.2 surfaces.

## Required Frontend Env Vars

Document these in the frontend env example:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

Never expose service-role keys.

Never expose provider keys.

## Landing Page Requirements

Use the 80% Trap positioning.

Headline direction:

> AI built your first 80%. Now you’re stuck fixing the rest.

Core message:

> Generating code is easy. Understanding why it broke is the hard part. Codize helps student builders plan, prompt, review, verify, and defend AI-generated code before their projects collapse into patch loops.

Primary CTA:

> Stop Debugging Blindly

Tone:

- serious
- direct
- developer-focused
- non-shaming
- not childish
- not generic SaaS

Avoid calling users lazy, fake, or cheaters.

## Auth Requirements

Implement basic signup/login/logout using Supabase Auth.

After signup/login:

- if no project/intake exists, guide user to intake
- if project exists, guide user to Project Cockpit/current phase

Frontend must use Supabase client auth only.

Protected backend data must be requested with a valid Bearer JWT.

## API Client Requirements

Create or complete a frontend API client that:

- reads `NEXT_PUBLIC_API_BASE_URL`
- gets the current Supabase access token
- attaches `Authorization: Bearer <token>`
- handles 401, 403, 404, 409, 422, and 500 states cleanly
- avoids leaking sensitive backend details into the UI
- keeps implementation simple

Wire existing backend surfaces where practical:

- intake
- roadmap/project creation
- current phase / phase workspace
- workflow artifacts
- reconnection
- evaluation if useful for cockpit summary

## Intake Requirements

Build intake according to the master spec.

The first question must remain exactly:

> What problem do you want to solve, and who does solving it help?

The intake should feel conversational, not like a generic form.

After intake completion, move the user toward the project workspace/current phase according to existing backend behavior.

## Project Cockpit Requirements

Project Cockpit should show:

- project name
- purpose / who it helps
- current phase
- current workflow step
- next required action
- evidence status
- verification status
- gate status if available
- report progress placeholder
- reconnection modal/summary if backend says it is needed
- clear CTA into the current phase workspace

The user should never wonder:

> What do I do next?

## Reconnection Requirements

Preserve existing reconnection invariant:

- call `GET /reconnection` first
- if reconnection is not needed, acknowledge appropriately
- if reconnection is needed, show the reconnection summary
- only acknowledge after the user clicks the equivalent of “Let’s keep building”

Do not turn `GET /reconnection` into an action that suppresses the modal.

## Phase Workflow Board Requirements

The phase page should be framed around the Codize Build Loop:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

Do not show it only as a task checklist.

It should include:

- current phase title
- phase purpose
- existing phase tasks from backend
- workflow step navigation
- status for Prompt Builder / Review / Evidence / Verification
- CTA to proceed through the loop

Existing task progress can still be visible, but the UX should emphasize workflow.

## Prompt Builder Requirements

Implement deterministic client-side Prompt Builder.

No LLM call is required.

Inputs should include:

- current project goal
- current phase goal
- what the user wants AI to do
- files involved, if any
- constraints
- what AI should not change
- whether to ask for a plan before code
- whether to ask for tests/checks
- confusion/uncertainty

Output should include:

- generated prompt text
- short explanation of why the prompt is stronger
- optional bad-prompt comparison if easy

Save to:

- `PUT /workflow/{phase}/prompt_builder`

Load from:

- `GET /workflow/{phase}`

## Review Board Requirements

Implement Review Board form.

It should ask:

- What files changed?
- What did AI generate?
- What did you accept?
- What did you reject?
- What did you edit manually?
- What assumptions did AI make?
- What are you least confident about?
- Did AI change anything outside the requested scope?

Save to:

- `PUT /workflow/{phase}/review_board`

Load from:

- `GET /workflow/{phase}`

## Evidence Panel Requirements

Implement Evidence Panel form.

Manual evidence is acceptable for v0.1.

Fields may include:

- repo URL
- commit hash
- changed files
- terminal output
- test output
- screenshot note/link
- app URL
- API response example
- evidence summary

Do not fetch GitHub data.

Do not verify external URLs automatically.

Do not implement GitHub OAuth.

Save to:

- `PUT /workflow/{phase}/evidence`

Load from:

- `GET /workflow/{phase}`

## Verification Lab Requirements

Implement Verification Lab form/checklist.

It should support:

- app runs locally
- smoke test completed
- API/route checked
- UI flow checked
- failure case tested
- auth boundary checked when relevant
- secret exposure checked
- RLS/wrong-user access checked when relevant
- user explanation of what the verification proves

Do not claim full automated verification.

This is manual verification evidence.

Save to:

- `PUT /workflow/{phase}/verification`

Load from:

- `GET /workflow/{phase}`

## Gate Boundary

Do not make the gate evidence-aware yet.

Do not change evaluator prompts.

Do not change gate pass/fail logic.

If showing a gate entry point, use existing M9 gate backend behavior as-is.

If full gate UI is too large for M13C.1, create a clear placeholder and defer full gate UI to M13C.2.

## Project Defense Report Boundary

Do not build a full Project Defense Report if it would make M13C.1 too large.

At minimum, create a placeholder showing that the report will assemble from:

- project/intake
- phase
- prompt_builder artifact
- review_board artifact
- evidence artifact
- verification artifact
- gate status
- evaluation summary

Full report generation can be M13C.2.

## UX / Design Requirements

Design should be:

- sharp
- serious
- high-contrast
- developer-focused
- workflow-oriented
- closer to Linear / GitHub / VS Code than school LMS
- not childish
- not generic SaaS
- not purple-gradient AI slop

The app should feel like an engineering cockpit, not a quiz app.

Avoid fake polish that hides incomplete functionality.

Every incomplete feature should have an honest placeholder.

## Security Requirements

Do not expose:

- service-role keys
- provider keys
- raw gate scores
- hidden unlock thresholds
- evaluator reasoning
- internal prompts
- `.env` content

Frontend must not assume user ownership.

Backend remains source of truth.

Handle errors safely.

Do not render raw untrusted HTML from user artifacts.

Treat all workflow artifact text as plain text.

## Testing / Verification

Add or update frontend tests if the frontend test setup exists.

If there is no frontend test setup, create only a minimal practical one if it does not derail the milestone.

At minimum, run:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

If a command is unavailable because scripts do not exist, say so clearly.

Run backend tests only if backend code changed.

Run the prebuild validator if relevant.

Do not claim tests passed unless they actually ran.

Run a secret scan before commit.

## Documentation Updates

Update as needed:

- `frontend/README.md` if frontend is created
- `CLAUDE.md` if the frontend structure should be remembered
- `.claude/memory/product-vision-v3.md` only if needed
- `docs/context/m13_ai_workflow_workspace_plan.md` only if implementation materially changes the plan

Do not rewrite the whole product vision.

## End Requirements

At the end, output:

- what partial work was found
- files changed
- frontend app created or updated
- routes/screens implemented
- backend routes consumed
- env vars required
- commands run
- test/build results
- secret scan result
- known issues
- git commit hash
- next step: M13C.2, likely Gate UI + Project Defense Report + polish/pilot flow

Commit all completed M13C.1 changes.

Stop after commit.