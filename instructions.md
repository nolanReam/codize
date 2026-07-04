# Codize M13C.1 Live Smoke Pass — Browser/API Integration Fixes Only

M13C.1 is committed as `03e3c1f`.

Do not start M13C.2 yet.

This is a short live smoke/fix pass for the M13C.1 frontend foundation.

Do not add major new features.

Do not implement the full gate flow.

Do not implement the full Project Defense Report.

Do not make the gate evidence-aware.

Do not modify evaluator logic.

Do not create migrations.

Do not add GitHub OAuth, AI news, browser IDE, community, marketplace, analytics dashboard, hosted coding runtime, or gamification.

## Goal

Verify that the M13C.1 frontend actually works in a browser against the existing backend and Supabase auth flow.

Fix only frontend/API integration bugs that block the M13C.1 flow.

## Current State

Relevant commits:

- M13B workflow artifact backend: `de42d5b`
- M13C.1 frontend foundation: `03e3c1f`

M13C.1 implemented:

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

## First Actions

Inspect current state:

```bash
git status
git log --oneline -5
```

Then read:

- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/workflow-artifact-conventions.md`
- `frontend/README.md`
- frontend API client/auth files
- backend route docs if needed

## Run Locally

Start backend according to existing README.

Start frontend according to `frontend/README.md`.

Use the required frontend env vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

Do not print secret values.

Do not expose `.env` contents.

## Smoke Test Flow

Verify this flow manually or with the available browser/dev tooling:

1. Landing page loads.
2. CTA routes to login/signup.
3. Login/signup page renders.
4. Supabase auth session is handled.
5. Protected app redirects unauthenticated users.
6. Authenticated user can reach `/app`.
7. If no project/intake exists, user is guided to intake.
8. Intake first question is exactly:

   > What problem do you want to solve, and who does solving it help?

9. Intake can be completed.
10. User reaches cockpit.
11. Cockpit shows project purpose / mission.
12. Phase page loads.
13. Prompt Builder loads existing workflow data and saves to backend.
14. Review Board loads/saves to backend.
15. Evidence Panel loads/saves to backend.
16. Verification Lab loads/saves to backend.
17. Refreshing the page preserves saved workflow artifacts.
18. Gate page does not 404 and honestly shows placeholder/current gate status.
19. Report page does not 404 and honestly shows real collected source statuses.
20. Logout works.

## Fix Scope

Fix only issues that block or seriously degrade the above flow.

Allowed fixes:

- broken route paths
- bad redirects
- missing loading/error states
- incorrect API client call shape
- missing Bearer token
- frontend type mismatch with backend response
- workflow artifact save/load bugs
- unsafe rendering bug
- obvious UX dead-end

Not allowed:

- full gate implementation
- full report implementation
- evidence-aware gate changes
- major redesign
- new backend features unless absolutely required to fix a bug introduced by M13C.1

If a backend issue is discovered, explain it clearly and make the smallest safe fix only if necessary.

## Verification Commands

Run:

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

## End Requirements

At the end, output:

- smoke flow results
- bugs found
- fixes made
- files changed
- commands run
- test/build results
- secret scan result
- known issues
- git commit hash
- next step: M13C.2 Gate UI + Project Defense Report + pilot polish

Commit fixes if any.

If no fixes are needed, commit only if docs or notes changed; otherwise report no-code-change smoke pass and stop.