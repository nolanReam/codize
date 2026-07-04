# Codize M13D.1 — Local Pre-Pilot Smoke

Run the final local pre-pilot smoke test before inviting real testers.

This is a verification and blocker-fix pass only.

Do not start M14.

Do not add new product features.

Do not redesign the frontend.

Do not modify gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations unless a true smoke-blocking issue requires it, and explain first.

Do not invent pilot results.

Do not run the real pilot yet.

## Current State

Relevant commits:

- M13C.2 Gate UI + Project Defense Report: `8161dce`
- M13C.2B Gate Question Cleanliness Hotfix: `c0320f5`
- Pilot prep docs: `5fd7d9b`
- Pre-pilot deployment/demo prep: `a33b5a9`

Codize is now documented as ready for a local facilitator-hosted pilot.

This milestone should confirm that readiness with one final local smoke.

## Goal

Verify the full local pilot flow works on this machine using the deployment docs.

Fix only true blockers.

At the end, I should know whether Codize is ready to show to 3 testers.

## Read First

Read:

- `docs/deployment/pre_pilot_smoke_checklist.md`
- `docs/deployment/local_demo_runbook.md`
- `docs/deployment/deployment_readiness_audit.md`
- `docs/pilot/demo_checklist.md`
- `frontend/README.md`
- `backend/README.md`
- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/roadmap-llm-conventions.md`

Do not read `conversations.json` unless genuinely needed.

## First Actions

Inspect current state:

```bash
git status
git log --oneline -8
```

Confirm working tree is clean before starting.

## Run Local App

Start the backend according to the current docs.

Start the frontend according to the current docs.

Confirm required env vars exist without printing their values.

Do not expose `.env` contents.

Do not print secret values.

## Smoke Flow

Run the full pre-pilot smoke from the checklist:

1. Landing page loads.
2. Login/signup page loads.
3. Test account can authenticate.
4. Protected `/app` route works.
5. Intake starts.
6. First intake question is exactly:

   What problem do you want to solve, and who does solving it help?

7. Intake completes.
8. Roadmap generation reaches an active project without manual seeding.
9. Cockpit loads.
10. Phase board loads.
11. Prompt Builder saves and reloads.
12. Review Board saves and reloads.
13. Evidence Panel saves and reloads.
14. Verification Lab saves and reloads.
15. Gate starts.
16. Gate question text is clean, direct, and free of meta-preamble.
17. Gate can complete or safely reach the furthest valid test state.
18. Project Defense Report loads real collected data.
19. Markdown copy/export works.
20. Logout works.
21. Test data cleanup is completed if test data was created.

## Fix Scope

Allowed fixes:

- broken local setup docs
- incorrect command in docs
- missing env example
- CORS config/doc mismatch
- broken route
- frontend cannot call backend
- auth/session bug
- artifact save/load blocker
- gate page blocker
- report export blocker
- obvious typo/error that would confuse testers

Not allowed:

- new feature work
- UI redesign
- analytics
- hosted deployment
- M14
- evidence-aware gate changes
- evaluator prompt/scoring changes

If no blockers are found, do not change product code.

## Verification Commands

Run frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Run backend tests only if backend code changed:

```bash
cd backend
pytest
```

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## End Requirements

At the end, output:

- smoke flow result
- whether Codize is ready for 3 pilot testers
- blockers found
- fixes made, if any
- files changed
- commands run
- test/build results
- secret scan result
- test data cleanup result
- git commit hash if changes were committed
- next step: invite 3 testers using docs/pilot

If fixes are needed, commit them.

If no fixes are needed, do not make a fake code commit. Report a no-code smoke pass and stop.