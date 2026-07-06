# Codize M13E.1 — Core App Usability + Beginner Guidance Pass

Fix the first-user experience inside the Codize app.

This is a protected-app usability, onboarding, intake, and prompt-builder clarity milestone.

Do not start M14.

Do not redesign the landing page.

Do not change gate evaluator logic.

Do not make the gate evidence-aware.

Do not create migrations unless a small safe migration is absolutely required, and explain first.

Do not add analytics.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, hosted coding runtime, or gamification.

Do not implement full multiple-project support in this milestone unless the backend already safely supports it end-to-end.

## Current State

Recent commits:

- M13D.4 landing page scroll fix: `833e48b76890cce9c58f1f94ef54b00e96631659`
- M13D.5 landing page precision fix: `0dc6b34ddc9399470bab858a7db53f9e5865d8ab`

The landing page is now improved enough to pause visual polish.

The next problem is inside the app:

- the post-login app feels smushed
- there is unused space on the right
- new users feel overwhelmed
- intake questions are confusing
- prompt builder assumes the user already knows what to ask AI
- phase language feels too technical
- user needs examples and guidance
- user wants a dashboard/projects experience
- user may eventually need a way to ask Codize what they are confused about

## User Feedback To Address

Fix these concrete issues:

1. After logging in, the app leaves a chunk of unused space on the right; use the full screen better.
2. The protected app feels smushed.
3. The user wants a dashboard where they can view current projects.
4. The user wants a plus button to create a project, then go through intake for that project.
5. The user may want multiple projects, but this needs an architecture audit before full implementation.
6. The user wants a way to ask about things they are confused on.
7. Intake asks about frameworks, but the user only knows AP CSA Java and some Python and does not understand whether “framework” means language, stack, library, etc.
8. The deadline question is unclear: does it mean MVP deadline, feature deadline, first working version, final product?
9. Intake questions should allow going back and editing before completion if technically safe.
10. Text boxes should show response examples.
11. The app needs a tutorial because the workflow feels overwhelming.
12. Prompt Builder currently assumes the user knows what to tell AI to do.
13. Prompt Builder should explain the current phase in beginner-friendly language.
14. Prompt Builder should give examples/starter suggestions for what to ask AI.
15. Prompt Builder should not just say “Building for Phase 1: API Design & Resource Modeling” without explaining what that means.

## Goal

Make Codize feel usable for a student builder who is not already comfortable with professional engineering terminology.

The app should teach the workflow while the user uses it.

The user should always understand:

- what page they are on
- what they are supposed to do next
- why the step matters
- what a good answer looks like
- what to write if they are unsure
- how this helps them use AI better

The user should not feel like they would rather just code without Codize.

## Read First

Read:

- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/workflow-artifact-conventions.md`
- frontend app shell/layout files
- frontend dashboard/cockpit files
- frontend intake files
- frontend prompt builder files
- frontend phase/workflow files
- backend project/intake/roadmap route contracts
- backend schemas only if needed

Do not read `conversations.json` unless genuinely needed.

## First Actions

Inspect current state:

```bash
git status
git log --oneline -8
```

Then inspect the protected app layout and current routes:

- `/app`
- `/app/intake`
- `/app/phase`
- `/app/phase/prompt`
- `/app/phase/review`
- `/app/phase/evidence`
- `/app/phase/verify`
- `/app/gate`
- `/app/report`

Identify the layout cause of the unused right-side space.

## Task 1 — App Layout / Full-Screen Usage

Fix the protected app layout so it uses the whole screen better.

Requirements:

- avoid the “smushed left with empty right side” feeling
- use responsive full-width layout
- keep readable max-widths for text, but use extra horizontal space for useful panels
- add or improve right-side/context panels where helpful
- no horizontal overflow
- desktop should feel like a cockpit/workspace, not a narrow form
- mobile should remain usable

Good use of extra space:

- current step guidance
- “what this means” panel
- next action panel
- project summary
- examples
- help/glossary cards

Do not just stretch paragraphs across the full width.

Use the extra space intentionally.

## Task 2 — Dashboard / Projects Audit

The user wants multiple projects and a dashboard with a plus button.

Before implementing, audit the current backend/frontend assumptions.

Answer in docs or memory:

- Does the backend currently support multiple projects per user?
- Does it support multiple active projects?
- Do routes assume “current project” instead of project id?
- Do workflow artifacts, gate sessions, evaluation, unlocks, and reconnection assume one current project?
- What would break if multiple active projects were added?
- What is the safest implementation plan?

If full multiple-project support is not already safe, do not implement it now.

Instead, implement a safer dashboard improvement:

- `/app` should feel like a dashboard
- show the current project clearly
- show “Continue project”
- show “Start first project” if no project exists
- show a disabled or clearly marked “New project” / “Multiple projects coming next” affordance only if useful
- do not create fake multi-project behavior

If the backend already supports project listing and multiple active projects safely, implement minimal dashboard support only after confirming route contracts.

Do not create a fragile partial multi-project system.

## Task 3 — First-Use Tutorial

Add a lightweight tutorial or “How Codize works” guide inside the app.

It should explain:

1. Start with a project idea.
2. Codize turns it into phases.
3. For each phase, use Prompt Builder before asking AI.
4. After AI helps, return to Codize.
5. Review what AI changed.
6. Submit evidence.
7. Verify behavior.
8. Defend what you built.
9. Export the Project Defense Report.

Requirements:

- non-overwhelming
- dismissible
- accessible from dashboard and/or app shell
- not a huge wall of text
- can be localStorage-based if backend persistence is unnecessary
- should not block returning users forever
- should be easy to reopen

Use beginner-friendly language.

## Task 4 — Intake Clarity

Improve intake questions so a student understands how to answer.

Requirements:

- add response examples/placeholders for each question
- add short helper text under confusing questions
- allow going back/editing previous answers before final completion if technically safe
- preserve backend contract and existing intake flow
- do not lose user input
- do not create invalid backend state

Specific clarifications:

### Frameworks / stack question

Explain that a “framework/stack” can mean:

- coding language: Java, Python, JavaScript
- framework/library: FastAPI, Flask, React, Next.js
- database/tool: Supabase, SQLite
- or “I’m not sure yet”

Examples:

- “AP CSA Java, no framework yet”
- “Python, maybe Flask or FastAPI”
- “Next.js + Supabase”
- “I only know basic Python and Java right now”

The user should not feel dumb for not knowing a framework.

### Deadline question

Clarify that this means:

> When do you want a first working version/demo, not the final polished product?

Examples:

- “tonight”
- “this weekend”
- “in 2 weeks”
- “before my hackathon demo”
- “no deadline, just learning”

If the backend expects a rough deadline, keep it rough.

## Task 5 — Prompt Builder Beginner Guidance

The Prompt Builder needs to teach the user what to ask AI.

Right now, “Building for Phase 1: API Design & Resource Modeling” is too abstract.

Improve Prompt Builder with:

- beginner-friendly phase explanation
- “What this phase means” panel
- “What you might ask AI to do” examples
- starter task suggestions
- example filled-in values
- guidance for users who are unsure
- clearer labels

For example, for a phase like API Design & Resource Modeling, explain:

> This phase is about deciding what data your app stores and what routes/actions the app needs before you ask AI to write random files.

Give examples like:

- “Help me design the data model for tasks, members, and study groups.”
- “Suggest database tables and explain what each field means.”
- “List the API routes I need before writing code.”
- “Ask me questions if the schema is missing ownership or permissions.”
- “Do not change my auth setup yet.”

Make fields less intimidating.

For each Prompt Builder field, add:

- a plain-English explanation
- an example placeholder
- optional starter chips/buttons where useful

Fields to improve:

- What are you building overall?
- What is this phase about?
- What exactly should the AI do?
- Files/components involved
- Constraints
- What must the AI not change?
- What are you least sure about?
- Ask for a plan before code
- Ask for manual verification steps

The prompt builder should help the user produce a better prompt even if they do not know what to ask yet.

## Task 6 — Confusion Help

Add a lightweight “I’m confused” / “What does this mean?” help pattern.

This should be static/contextual for now, not a full AI chatbot unless the repo already has a safe pattern.

Examples:

- help drawer
- tooltip
- inline glossary
- side panel
- “Not sure what to write?” examples
- “Use this if you only know Python/Java” helper

Do not add a new LLM chat assistant in this milestone unless it is already supported safely and explicitly trivial.

If an AI confusion assistant is desirable, create a short implementation plan for a future milestone.

The immediate goal is to reduce confusion now with static guidance.

## Task 7 — Copy Tone

Use supportive language.

Avoid making users feel behind.

Good tone:

- “Not sure yet is a valid answer.”
- “Use the tools you know.”
- “Codize will help you turn this into a clearer AI prompt.”
- “A first working version means something you can demo, not a perfect final product.”

Avoid:

- expert-only jargon
- unexplained acronyms
- “obviously”
- “simply”
- making students feel like they should already know professional engineering terms

## Scope Boundary

Allowed changes:

- protected app layout
- dashboard/cockpit UI
- intake UI
- prompt builder UI
- static help/glossary components
- tutorial/onboarding UI
- small frontend utilities
- small backend changes only if required for safe intake edit/back behavior and covered by tests
- docs/memory updates

Do not modify:

- gate evaluator logic
- gate scoring
- unlock thresholds
- workflow artifact validation
- roadmap generation logic
- database schema unless absolutely necessary
- landing page except shared style regressions
- real auth behavior

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

Run a local visual/product smoke:

1. login
2. dashboard uses screen width better
3. if no project, user understands how to start
4. tutorial/help is visible and dismissible
5. intake examples/helper text appear
6. intake can go back/edit if implemented
7. framework/stack question is understandable
8. deadline question is understandable
9. prompt builder explains the current phase
10. prompt builder gives example/starter guidance
11. prompt builder still saves/loads correctly
12. app has no horizontal overflow
13. mobile layout remains usable
14. no obvious console errors

Run a secret scan before commit.

Do not claim tests passed unless they actually ran.

## Documentation Updates

Update if needed:

- `frontend/README.md`
- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `docs/pilot/demo_checklist.md` only if user-facing pilot flow changed

If multiple projects are deferred, create or update:

- `docs/context/multi_project_dashboard_plan.md`

The multi-project plan should be concrete and honest about route/backend assumptions.

Do not rewrite the product vision docs.

## End Requirements

At the end, output:

- user feedback addressed
- layout/full-screen fixes
- dashboard/project handling changes
- whether multiple projects were implemented or deferred, and why
- tutorial/help added
- intake clarity fixes
- whether back/edit was implemented
- prompt builder guidance fixes
- confusion-help behavior
- files changed
- backend changes, if any
- tests/commands run
- visual/product smoke result
- secret scan result
- known issues
- git commit hash
- next step: local product review, then first pilot tester or multi-project milestone

Commit completed M13E.1 changes.

Stop after commit.