# Codize M13D — Pre-Pilot Deployment + Demo Prep

Prepare Codize to be demoed and piloted with real testers.

This is a deployment-readiness, demo-readiness, and operational-prep milestone.

Do not start M14.

Do not add major product features.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations unless an existing deployment blocker absolutely requires it, and explain first.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, analytics dashboard, hosted coding runtime, or gamification.

Do not invent pilot results.

Do not run the real pilot yet.

## Current State

Relevant commits:

- M13C.2 Gate UI + Project Defense Report: `8161dce`
- M13C.2B Gate Question Cleanliness Hotfix: `c0320f5`
- Pilot prep docs: `5fd7d9b`

Codize now has:

- frontend MVP
- backend MVP
- Supabase auth/data
- roadmap fallback reliability
- workflow artifacts
- live gate
- Project Defense Report
- pilot kit in `docs/pilot/`

## Goal

Make Codize ready for a first 3–5 tester pilot.

At the end, I should know exactly:

1. How to run a clean local demo.
2. How to deploy or prepare deployment.
3. Which environment variables are needed.
4. Which secrets must never go to the frontend.
5. How to create or use a test account safely.
6. How to run the pre-pilot smoke test.
7. What known issues remain.
8. Whether the app is ready for testers.

## Read First

Read:

- `CLAUDE.md`
- `frontend/README.md`
- `backend/README.md`
- `docs/pilot/README.md`
- `docs/pilot/demo_checklist.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/roadmap-llm-conventions.md`
- root package/config files if present
- frontend deployment config if present
- backend deployment config if present
- CORS configuration
- env examples

Do not read `conversations.json` unless genuinely needed.

## First Actions

Inspect current state:

```bash
git status
git log --oneline -8
```

Then inspect:

- frontend app config
- backend app config
- env examples
- CORS settings
- deployment-related docs/config
- gitignore rules for `.env`, `.env.local`, `.next`, `node_modules`, Playwright artifacts, logs

## Task 1 — Deployment Readiness Audit

Create:

`docs/deployment/deployment_readiness_audit.md`

Include:

- current frontend framework and start/build commands
- current backend framework and start command
- required frontend env vars
- required backend env vars
- which env vars are public vs secret
- Supabase auth assumptions
- CORS requirements
- local ports
- known deployment blockers
- recommended deployment path for first pilot
- risks and mitigations

Do not include real secret values.

Do not print `.env` contents.

## Task 2 — Local Demo Runbook

Create:

`docs/deployment/local_demo_runbook.md`

This should be a step-by-step guide for running Codize locally for a demo or pilot.

Include:

1. Start backend.
2. Start frontend.
3. Confirm env vars exist without printing values.
4. Confirm Supabase auth works.
5. Create or use a test account safely.
6. Complete intake.
7. Generate roadmap.
8. Fill Prompt Builder.
9. Fill Review Board.
10. Fill Evidence.
11. Fill Verification.
12. Run Gate.
13. Export Project Defense Report.
14. Logout.
15. Clean up test data if needed.

Include troubleshooting for:

- missing env vars
- frontend cannot reach backend
- CORS issue
- Supabase email confirmation issue
- roadmap fallback path
- gate provider/model issue
- report shows missing sections

## Task 3 — Hosted Deployment Plan

Create:

`docs/deployment/hosted_deployment_plan.md`

This should explain the simplest hosted path for a small pilot.

Recommended default unless repo constraints suggest otherwise:

- frontend: Vercel or equivalent Next.js host
- backend: a simple FastAPI host
- database/auth: existing Supabase project

Do not actually create external accounts.

Do not deploy without explicit user confirmation.

Do not require paid services as the only path.

Include:

- recommended architecture
- required environment variables for each service
- CORS origin update needed for deployed frontend URL
- backend base URL needed by frontend
- smoke test after deployment
- rollback plan
- security checklist

## Task 4 — Env Example / Docs Cleanup

Review env examples and docs.

If needed, update:

- `frontend/.env.example`
- backend `.env.example`
- frontend README
- backend README
- root README if present

Make sure docs clearly distinguish:

Frontend public vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

Backend secret/server vars may include:

- Supabase service/server key if used
- Gemini/OpenRouter provider keys
- database/Supabase URLs
- model config

Never put secret values into docs.

## Task 5 — Pre-Pilot Smoke Checklist

Create or update:

`docs/deployment/pre_pilot_smoke_checklist.md`

This should be the final checklist before inviting testers.

Include:

- clean working tree
- backend starts
- frontend starts
- landing page loads
- login works
- intake works
- roadmap reaches active project without manual seeding
- artifacts save and reload
- gate runs with clean question text
- report exports Markdown
- logout works
- no console errors except known harmless ones
- no secrets in frontend bundle/source
- test data cleanup completed
- known issues recorded

## Task 6 — Demo Script

Create:

`docs/deployment/demo_script.md`

This is the script I can use when showing Codize to a mentor, tester, or recording a short demo.

It should be concise and persuasive.

Structure:

1. Problem: AI gets you to 80%, then you get stuck.
2. Codize promise: learn to plan, prompt, review, verify, and defend.
3. Show landing.
4. Show intake.
5. Show cockpit.
6. Show phase workflow.
7. Show Prompt Builder.
8. Show Review/Evidence/Verification.
9. Show Gate.
10. Show Project Defense Report.
11. Close with what pilot is measuring.

Keep it natural, not salesy.

## Task 7 — Optional Small Fixes

Allowed only if quick and clearly deployment/demo related:

- fix broken README command
- fix missing env example
- fix incorrect CORS method/origin documentation
- fix favicon/document metadata if still broken
- fix obvious typo in demo-facing copy
- add missing `.gitignore` entry for local deployment artifacts

Do not redesign UI.

Do not add features.

## Verification

Run docs/code checks as appropriate.

At minimum:

```bash
git status
```

If frontend docs/config changed, run:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

If backend code/config changed, run:

```bash
cd backend
pytest
```

If only docs changed, tests are optional, but say clearly that no product code changed.

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `docs/pilot/demo_checklist.md`

Only update these if deployment/demo workflow should be remembered.

Do not rewrite the whole product vision.

## End Requirements

At the end, output:

- files created/updated
- whether product code changed
- deployment readiness summary
- recommended first deployment path
- local demo command summary
- pre-pilot smoke checklist location
- known blockers
- commands run
- test/build results if run
- secret scan result
- git commit hash
- next step: run local pre-pilot smoke, then invite 3–5 testers

Commit completed deployment/demo prep.

Stop after commit.