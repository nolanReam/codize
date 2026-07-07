# Codize M13E.2 — Pilot Bugfix Pass 1

Fix the issues discovered during the first real friend test.

This is a focused pilot bugfix and UX clarity milestone.

Do not start M14.

Do not redesign the landing page.

Do not change database schema unless absolutely required and explained first.

Do not modify the gate evaluator scoring logic.

Do not make the gate evidence-aware.

Do not add analytics.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, hosted coding runtime, or gamification.

Do not implement full multiple-project support in this milestone.

## Current Context

A real tester used Codize and found several issues.

Known recent work:

- Deployment readiness completed.
- Core app usability pass was started/completed.
- Friend pilot testing has begun.
- The app is live enough for testing, but several core UX bugs are blocking trust.

## Tester Issues To Fix

### Issue 1 — Gate Anchor Rejection

The tester entered an anchor like:

> i built a variable that stores likes and a function to update them using some advanced python stuff. the variable is called likes_score

The UI rejected it with:

> You must name at least one concrete element from your implementation, such as a variable, function, or database field.

This should have passed because `likes_score` is a concrete identifier.

Fix the anchor validator so it accepts realistic student phrasing such as:

- `variable called likes_score`
- `variable named likes_score`
- `the variable is called likes_score`
- `` `likes_score` ``
- `function called update_likes_score`
- `function called update_likes_score()`
- `database field called likes_score`
- `field named likes_score`
- `tasks.user_id`
- `app/models.py`
- `routes/tasks.py`

The validator should not require perfect professional phrasing.

Keep anti-generic validation, but do not reject real identifiers.

Also improve the error message.

Better error copy:

> Name one exact thing from your code, like `likes_score`, `update_likes_score()`, `tasks.user_id`, or `app/models.py`.

Add tests.

### Issue 2 — Gate Question Formatting Leak

A screenshot shows the gate UI rendering raw model/meta text like:

> Therefore, it is a valid anchor. Now, I need to formulate the Turn 1 question...

This is unacceptable.

The user-facing gate question must never display:

- “Therefore”
- “valid anchor”
- “Now I need to”
- “Question Formulation”
- “Student’s Anchor”
- “Gate Targets”
- “Specificity”
- “Personalization”
- markdown section labels
- rubric language
- prompt-planning language
- quoted internal prompt text
- model reasoning/meta commentary

Only the final clean student-facing question should be shown.

Fix this at the backend boundary where gate questions are generated/cleaned.

Preferred behavior:

1. Detect meta/prompt-leak output.
2. Extract only the final direct question if safe.
3. If extraction is unsafe, reject and trigger the existing retryable generation path.
4. Store only the cleaned question.
5. Never show raw model output to the frontend.

Examples:

Raw bad output:

> Therefore, it is a valid anchor. Now I need to formulate the Turn 1 question... Let's craft the question: "You mentioned building a `likes_score` variable. Can you explain why you chose that?"

User should see only:

> You mentioned building a `likes_score` variable. Can you explain why you chose that?

If output contains multiple questions, prefer the final clean implementation-specific question only if it is safe.

Add tests for the exact leaked pattern from the screenshot.

Do not change final PASS/FAIL evaluator logic.

### Issue 3 — Unsaved Drafts Lost When Switching Tabs

Tester said:

> make sure when switching between tabs, the last thing typed in the boxes is saved even if it wasnt submitted or anything yet

Implement draft persistence for user input in workflow pages.

Affected areas likely include:

- Prompt Builder
- Review Board
- Evidence Panel
- Verification Lab
- Gate answer textareas if safe
- intake fields if technically safe

Requirements:

- if user types but does not submit/save, switching tabs/pages should preserve draft text
- use localStorage/sessionStorage if backend persistence is not appropriate
- drafts should be scoped by user/project/phase/section
- submitted/saved backend data should still be source of truth
- after successful save/submit, clear or reconcile the local draft
- do not accidentally leak one user/project’s draft into another project/user
- do not store secrets if the secret-content guard rejects them; handle carefully

Add tests if there is existing frontend test structure for this.

### Issue 4 — High-Resolution Workspace Blank Space

Tester used a higher-resolution monitor and saw large unused blank space after logging in.

Fix the protected app workspace so it uses large screens better.

Requirements:

- avoid narrow/smushed main content on desktop/wide monitors
- use full available width intelligently
- preserve readable text widths
- add useful side/context panels where helpful
- no horizontal overflow
- dashboard, phase, and workflow pages should feel like a workspace/cockpit, not a narrow mobile layout stretched onto desktop

Possible improvements:

- wider app shell max-width
- responsive grid layouts
- side panel with current project/phase/help/next actions
- two-column layouts for form + guidance
- better large-screen spacing

Do not just stretch paragraphs to unreadable widths.

### Issue 5 — Verification `Skipped` / `N/A` Logic

Tester noticed:

> if something is selected as "skipped" it shouldnt be asking how it was checked. Also for n/a

Fix Verification Lab behavior.

Requirements:

- if a verification check is marked `passed` or equivalent, ask for evidence/how it was checked
- if a check is `failed`, ask what failed / what needs fixing
- if a check is `skipped`, do not require “how it was checked”; instead ask optional reason or show “skipped for now”
- if a check is `N/A`, do not require “how it was checked”; optionally ask why it does not apply
- generated report should label skipped/N/A honestly
- validation should not block skipped/N/A because the evidence field is empty
- UI should be clear and not contradictory

Add tests if existing report/verification tests cover this.

### Issue 6 — Phase Progress Confusion

Tester said:

> His phase tasks say 0/5 done and he said that he made the prompt and answered other stuff and did the other things

Clarify the difference between:

1. **Project/phase build tasks** from the roadmap
2. **Codize workflow artifacts** like Prompt Builder, Review Board, Evidence, Verification

Do not fake roadmap task completion just because the user filled Codize artifacts unless the product intentionally maps those actions.

Fix the UI so it is clear.

Possible approach:

- rename “0/5 tasks done” to “Build tasks: 0/5”
- add “Codize workflow: 4/4 captured” or similar
- show separate progress indicators:
  - Build tasks
  - Workflow evidence
  - Gate status
- explain that building tasks must be checked off separately if that is current behavior
- if there are existing task-completion controls, make them more visible
- if task-completion controls are missing/confusing, fix the UI enough for testers to understand

Do not mutate roadmap structure.

Do not automatically mark build tasks done just because user wrote a prompt.

### Issue 7 — Model Configuration Review

Review the current Gemini model configuration.

The user heard that a newer/free Flash model may be available with generous daily limits.

Do not blindly switch models.

Do this instead:

- inspect current `GEMINI_MODEL`
- document current model used in `.env.example` or docs if needed
- verify whether the app can safely use a stronger currently available Gemini Flash model by env var only
- do not hardcode a new model unless confident it is supported
- make model swapping easy through environment variables
- update docs to say model can be changed without code deploy if backend env changes
- if gate prompt leak is fixed by sanitization/retry, do not rely only on model upgrade

If a stronger model is recommended, state exactly where to change it:

- Railway backend env var `GEMINI_MODEL=...`

But do not require it for correctness.

## Read First

Read:

- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/workflow-artifact-conventions.md`
- `.claude/memory/deployment-conventions.md`
- backend gate service/router/schemas/tests
- frontend gate page
- frontend workflow pages
- frontend verification page
- frontend phase/dashboard/app shell layout
- frontend report builder/tests
- backend LLM service/config docs

Do not read `conversations.json` unless genuinely needed.

## First Actions

Inspect current state:

```bash
git status
git log --oneline -8
git diff --stat
```

Then identify files involved in:

- anchor validation
- gate question sanitization
- workflow form draft state
- verification form validation
- phase progress display
- app shell layout

## Testing Requirements

Run frontend tests/checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Run backend tests if backend code changes:

```bash
cd backend
pytest
```

Backend code will likely change for gate anchor/sanitization, so run backend tests.

## Product Smoke

Run a focused local or hosted smoke if possible:

1. login
2. open app on wide viewport
3. confirm layout uses space better
4. type into Prompt Builder, switch tab, return, confirm draft remains
5. verification skipped/N/A does not require checked evidence
6. phase progress clearly separates build tasks from workflow artifacts
7. submit anchor containing `likes_score`
8. confirm anchor passes
9. generate Turn 1 question
10. confirm no meta/prompt text leaks
11. answer gate as far as safe
12. no console errors

## Secret Scan

Run a secret scan before commit.

Search for:

```text
GEMINI_API_KEY
OPENROUTER_API_KEY
SUPABASE_SERVICE_ROLE_KEY
sb_secret_
sk-or-
AIza
service_role
private key
JWT
```

Do not commit real secrets.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `backend/README.md`
- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/gate-conventions.md`
- `.claude/memory/deployment-conventions.md`
- `docs/deployment/friend_pilot_deployment.md` if model env guidance changes

Do not rewrite the product vision docs.

## End Requirements

At the end, output:

- tester issues addressed
- gate anchor validator fix
- gate question leak fix
- draft persistence behavior
- wide-screen layout fixes
- verification skipped/N/A behavior
- phase progress clarity fix
- Gemini/model configuration notes
- files changed
- backend changes
- frontend changes
- commands/tests run
- smoke result
- secret scan result
- known issues
- git commit hash
- next step: redeploy backend/frontend, then resume friend testing

Commit completed M13E.2 pilot bugfix pass.

Stop after commit.