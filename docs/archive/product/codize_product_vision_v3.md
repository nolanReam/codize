> [!NOTE]
> **Archived historical product vision.** This document is superseded for
> product direction by `docs/context/codize_product_operating_brief_v2.md`.
> Its historical body is preserved below and must not be treated as current
> implementation or product authority.

# Codize Product Vision v3

## Status

This document is the current product-direction source for Codize after the product vision reset (2026-07-03, immediately after Milestone 12 — backend M1–M12 complete at commit `44442b0`). See `docs/context/context_authority.md` for where this document sits in the context hierarchy.

It supersedes older UX/product-positioning assumptions that framed Codize mainly as:

- roadmap generation
- task checklist
- understanding gate
- generic student progress dashboard

Those pieces may still exist, but they are not the product thesis by themselves.

Codize is now framed as:

> An AI coding workflow trainer that helps student builders stop blindly vibe coding, escape the 80% trap, verify what AI generated, and defend the projects they ship.

This is not a random pivot. It is a correction back toward Codize’s original thesis: students do not only need code output. They need a workflow for directing, reviewing, verifying, and explaining AI-assisted code. The master spec itself states it verbatim: “This is not a laziness problem. It is a workflow problem. No one ever showed them where AI belongs in a professional development process and where it doesn't. Codize fixes that.”

---

## One-Sentence Product Thesis

Codize helps student builders use AI like engineers: plan before prompting, review what AI changed, verify behavior, explain the implementation, and leave with a Project Defense Report.

---

## Sharp Positioning

AI coding tools help students generate code.

Codize teaches them how to stay the engineer.

Codize does not compete with Claude Code, Cursor, GitHub Copilot, Replit, Codex, or other AI coding tools.

Codize sits above them as the workflow, verification, and project-defense layer.

Those tools help users produce code.

Codize teaches users how to direct, review, verify, and defend that code.

---

## The Main User Pain: The 80% Trap

The core pain is not abstract “learning.”

The pain is:

> AI built the first 80% quickly. Now one new feature broke everything, and the student does not understand the codebase well enough to fix it.

Typical 80% Trap pattern:

1. Student gives AI a vague prompt.
2. AI produces a working-looking app.
3. Student asks for one more feature.
4. AI rewrites files the student does not understand.
5. The app breaks.
6. Student pastes errors back into AI.
7. AI adds more patches.
8. The codebase becomes bloated, fragile, and harder to reason about.
9. Student is no longer building. They are negotiating with a codebase they never really learned.

Codize exists to prevent or rescue this situation.

---

## Main Product Promise

Codize helps students regain control of AI-assisted projects.

It helps them answer:

- What am I trying to build?
- What should AI do?
- What should I decide myself?
- What did AI change?
- What assumptions did AI make?
- Did I verify that the code works?
- Could I explain this project to a teacher, interviewer, hackathon judge, or admissions reader?
- What should I do next?

---

## Target User

Primary MVP user:

CS students or beginner/intermediate developers with roughly 1–3 years of coding experience who have used AI coding tools and feel uneasy because they can make projects but cannot confidently explain the architecture.

They are not total beginners.

They know basic concepts like:

- variables
- loops
- functions
- classes or objects
- APIs
- frontend/backend basics at a surface level

But they struggle with:

- planning architecture before generating code
- knowing what context to give AI
- reviewing generated code
- tracing data flow
- verifying behavior
- checking security assumptions
- debugging without random patching
- explaining what they shipped

They open Codize when:

- they are starting a personal project and want to do it properly
- they are stuck in an AI-generated project
- they are preparing for a hackathon, interview, portfolio review, or college application
- they feel like AI helped them build something they cannot defend

They are not:

- complete beginners who need a full coding curriculum
- senior engineers
- users who only want the fastest possible AI-generated output and do not care about understanding

---

## Product Category

Codize is not:

- an AI coding assistant
- a browser IDE
- a generic chatbot
- an AI news app
- a tool marketplace
- a school LMS
- a quiz platform
- a LeetCode clone
- a full GitHub Classroom replacement

Codize is:

> A project-based AI coding workflow trainer.

It teaches a repeatable workflow for building real software with AI assistance.

---

## The Codize Build Loop

The core product loop is:

> Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

This loop is the product.

The roadmap, gate, unlocks, reconnection, and evaluation systems exist to support this loop.

The gate is not the product by itself.

The roadmap is not the product by itself.

The dashboard is not the product by itself.

The loop is the product.

---

## Step 1 — Plan

Goal:

Teach the student to think before prompting.

The student should define:

- what problem they are solving
- who the project helps
- what the feature should do
- what the AI should not build yet
- what architecture or data structure may be needed
- what constraints matter
- what success looks like

Codize should teach:

- plan architecture before generating
- human decides structure, AI fills it
- scope one phase at a time
- avoid giant vague prompts
- define acceptance criteria before asking for code

Example planning questions:

- What feature are you building in this phase?
- What data does it need?
- What user action starts the flow?
- What should happen after that action?
- What could go wrong?
- What should AI avoid changing?

---

## Step 2 — Prompt

Goal:

Help the student write better AI prompts.

Codize should not just provide a blank chat box.

It should provide a structured Prompt Builder.

Prompt Builder should help the user include:

- project context
- current phase
- goal of this request
- files or components involved
- constraints
- what not to change
- request for a plan before code
- request for tests or checks
- request for explanation
- security requirements when relevant

Prompt Builder should produce:

1. a strong prompt to use in Claude Code, Cursor, Replit, Copilot, or another tool
2. a short explanation of why the prompt is stronger
3. optionally, a “bad prompt to avoid” comparison

Example good prompt:

> I’m building a task tracker with Supabase and FastAPI. I’m currently designing the data model. First propose a schema and explain each table. Do not write frontend code yet. Include ownership fields and RLS policies. Tell me what I should manually verify before moving on.

Immediate usefulness matters. A user should get value from Codize within the first few minutes by receiving a better AI prompt.

---

## Step 3 — Generate

Goal:

The student uses an external AI coding tool to generate or modify code.

Codize does not need to replace the coding tool.

The user may use:

- Claude Code
- Cursor
- GitHub Copilot
- Replit
- Codex
- ChatGPT
- Gemini
- any other AI coding workflow

Codize should remain tool-agnostic.

Codize’s job is not to generate all the code.

Codize’s job is to make the student use AI deliberately and verify the result.

---

## Step 4 — Review

Goal:

Teach the student to inspect AI output before accepting it.

After using an AI coding tool, the student returns to Codize and fills out a Review Board.

Review Board should ask:

- What files changed?
- What functions, classes, routes, tables, or components were added?
- What did AI generate?
- What did you accept?
- What did you reject?
- What did you edit manually?
- What assumption did AI make?
- What part are you least confident about?
- Did AI change anything outside the requested scope?

This step turns passive prompting into active engineering.

The Review Board creates context for the Evidence-Based Gate.

---

## Step 5 — Verify

Goal:

Teach the student to prove the code works instead of trusting AI output.

Verification Lab should ask for evidence that the project or feature behaves correctly.

For MVP, verification is mostly manual and checklist-based.

Codize should not try to fully verify arbitrary projects automatically in v0.1.

Instead, Codize should verify generic engineering behaviors:

- Can the app run locally?
- Did the user run at least one smoke test?
- Did the relevant route or UI flow work?
- Did the user test one failure case?
- Did the user check for exposed secrets?
- Did the user verify user-specific data cannot be accessed by the wrong user when auth/RLS is involved?
- Did the user paste or describe test output?
- Did the user provide a screenshot, terminal output, repo link, or commit hash?

Verification evidence may include:

- repo URL
- commit hash
- changed file names
- pasted terminal output
- screenshot link or note
- manual checklist result
- test result
- app run confirmation
- API response example
- short explanation of what was verified

Verification should be practical, not impossible.

Codize should not claim to prove everything automatically.

---

## Step 6 — Explain

Goal:

Make sure the student can explain the actual implementation.

This is where the Interrogation Gate belongs.

The gate should be evidence-based.

Old gate framing:

> Answer questions about this phase.

Better gate framing:

> Defend the code and evidence you just submitted.

Gate questions should use:

- project intake
- current phase
- roadmap/template targets
- review board answers
- changed file names
- function/table/component names
- verification evidence
- known weak spots
- previous gate history

The gate should ask implementation-specific questions such as:

- You said AI changed `tasks.ts`. What responsibility does that file have?
- You added a `user_id` field. How does it prevent users from seeing each other’s data?
- You said the endpoint works. What request did you test, and what response proved it?
- What assumption did AI make that you had to verify?
- What would break if this field or route changed?

The gate should not ask generic textbook questions.

The gate should not expose hidden scores, thresholds, private evaluator reasoning, or internal prompt text.

The gate should be strict but not insulting.

The user should feel like they are preparing to defend a project, not being punished.

---

## Step 7 — Commit / Reflect

Goal:

Help the student convert the work into durable understanding and portfolio evidence.

Commit/Reflect should ask:

- What changed in this phase?
- What did AI help with?
- What did you personally decide?
- What did you verify?
- What do you understand better now?
- What still feels weak?
- What would you say in a commit message?

Optional output:

- suggested commit message
- phase reflection
- project defense notes
- next action

This step feeds the Project Defense Report.

---

## Main Payoff: Project Defense Report

The primary reward is not points.

The primary reward is a Project Defense Report.

This report helps the student prepare for:

- interviews
- portfolio reviews
- hackathon judging
- college applications
- teacher/mentor check-ins
- personal confidence

The report should show:

- project overview
- purpose / who it helps
- phase completed
- prompt used
- files changed
- what AI generated
- what the student accepted/rejected/edited
- verification checks completed
- security checks completed
- evidence submitted
- gate result, without hidden score
- skills demonstrated
- weak areas
- recommended next action
- interview-style questions the student can now answer

The report should avoid unsupported claims.

Do not call it cryptographic or verified unless Codize actually has repo evidence, timestamps, commit hashes, or signatures to support that claim.

Preferred language:

> Project Defense Report

Avoid overclaiming:

> cryptographic proof
> guaranteed proof
> cheat-proof verification

---

## Secondary Payoff: Defense Readiness

Codize may show a Defense Readiness state or score, but it must be serious and tied to real workflow completion.

Good:

- Prompt Quality
- Review Completeness
- Verification Coverage
- Security Awareness
- Explanation Strength
- Evidence Submitted

Bad:

- random XP
- streaks for logging in
- leaderboards
- shallow badges
- gamification disconnected from competence

Defense Readiness should help answer:

> Am I ready to explain and defend this project?

It should not reveal hidden gate scores or evaluator thresholds.

---

## Build Mode

Build Mode is for users starting a project or feature.

Flow:

1. User defines project or feature goal.
2. Codize helps plan architecture/scope.
3. Codize generates a strong AI prompt.
4. User builds externally.
5. User returns to review what changed.
6. User verifies behavior.
7. User passes an evidence-based gate.
8. User adds reflection.
9. Codize updates the Project Defense Report.

Build Mode should feel like:

> Build with AI without losing control.

---

## Rescue Mode

Rescue Mode is for users already stuck in an AI-generated project.

This may be the strongest hook because the pain is immediate.

Rescue Mode starts with:

- What were you trying to add?
- What broke?
- What files changed?
- What error are you seeing?
- What did AI already try?
- What part do you not understand?

Then Codize guides:

1. Stop patch-looping.
2. Map the failure.
3. Identify changed files.
4. Identify AI assumptions.
5. Define the smallest verification check.
6. Generate a better debugging prompt.
7. Ask the user to explain the likely cause.
8. Produce a recovery note for the Project Defense Report.

Rescue Mode should feel like:

> Stop debugging blindly.

For MVP, Rescue Mode can reuse the same core workflow as Build Mode.

It does not need a totally separate backend system at first.

---

## Landing Page Direction

Hero:

> AI built your first 80%. Now you’re stuck fixing the rest.

Subheadline:

> Generating code is easy. Understanding why it broke is the hard part. Codize helps student builders plan, prompt, review, verify, and defend AI-generated code before their projects collapse into patch loops.

Primary CTA:

> Stop Debugging Blindly

Secondary CTA:

> View a Project Defense Report

Problem section:

> The 80% Trap

Explain:

- You prompt.
- The app appears.
- You ask for one more feature.
- AI rewrites files you do not understand.
- The bug gets worse.
- Now you are negotiating with a codebase you never really learned.

Solution section:

> Review AI like a teammate, not a magic box.

Codize gives users a workflow:

- Plan architecture before generating.
- Prompt with constraints.
- Review what changed.
- Verify behavior.
- Explain decisions.
- Leave with a Project Defense Report.

Payoff section:

> Be ready to defend what you shipped.

Use strong but non-shaming language.

Do not imply the user is lazy, cheating, or fake.

Preferred tone:

> AI can help you ship faster. Codize helps you stay in control when the code starts to matter.

Avoid:

> Prove you are not just a prompter.

---

## MVP v0.1 Scope

The MVP is:

> One student. One project. One AI workflow loop. One Project Defense Report.

MVP must include:

1. Landing page around the 80% Trap
2. Basic authenticated project workspace
3. Project Cockpit
4. Prompt Builder
5. Review Board
6. Evidence Panel
7. Verification Lab
8. Evidence-Based Understanding Gate
9. Project Defense Report
10. Basic pilot analytics/survey hooks

MVP may include lightly:

- Defense Readiness indicator
- Reconnection summary
- simple next-action recommendation

MVP must not include:

- browser IDE
- AI news digest
- tool marketplace
- community/social features
- full GitHub OAuth
- automated verification for arbitrary projects
- elementary/Scratch version
- random XP/streak gamification
- multi-user classrooms
- full course marketplace
- broad AI news dashboard

---

## Manual Evidence First

For v0.1, manual evidence is acceptable.

Accepted evidence types:

- repo URL
- commit hash
- changed file names
- pasted terminal output
- pasted test output
- screenshot link or note
- app URL
- API response example
- short written explanation
- “what AI generated”
- “what I edited manually”
- “what I rejected”

This keeps the product feasible.

Future versions may add:

- GitHub OAuth
- repo scanning
- commit diff analysis
- GitHub Actions/test status
- PR summaries
- automated security checks

But full GitHub integration is not required for v0.1.

---

## Evidence-Based Gate Requirements

Note on current state: the shipped M9 gate (anchor statement → 3 turns at temp 0.3 → separate temp-0 evaluator, 30-minute cooldown, hidden 0–10 score) already satisfies the spec's gate mechanics and is live-verified. Wiring review-board answers and evidence-panel entries into the gate's prompt context is a FUTURE backend change: it must go through spec-guardian review, must not alter the turn structure, temperatures, cooldown, fail-closed evaluator parsing, or score secrecy, and is not part of this vision reset.

The gate must use submitted evidence when available.

The gate should not rely only on roadmap text.

Gate prompt context should include:

- current phase
- gate targets
- review board answers
- evidence panel entries
- changed files
- user-stated uncertainty
- verification checklist results
- previous gate history

The gate should probe:

- structural identification
- system ripple effect
- implementation specificity
- verification understanding
- AI assumption awareness

Auto-fail patterns:

- generic textbook answer
- answer not connected to submitted evidence
- answer that could apply to any codebase
- answer that cannot name a file/function/table/component when evidence claims one exists
- answer that ignores a failed or missing verification check

---

## Verification Lab Requirements

Verification Lab should be practical and phase-aware.

It should not pretend to prove everything.

It should guide users through checks like:

- app runs locally
- endpoint responds
- UI flow works
- data persists
- auth boundary checked
- wrong-user access blocked when relevant
- environment variables are not exposed
- one failure case tested
- one AI assumption checked
- deployment checklist reviewed if near shipping

For arbitrary projects, Codize should verify workflow behavior first, not full correctness.

The minimum expectation is:

> The student performed a reasonable verification step and can explain what it proved.

---

## Project Cockpit Requirements

Project Cockpit is the main workspace.

It should show:

- project name
- purpose
- current mode: Build or Rescue
- current phase
- current workflow step
- next required action
- evidence status
- verification status
- gate status
- defense report progress
- earned unlocks if available
- reconnection summary if relevant

The user should never wonder:

> What do I do next?

Every screen should provide a clear next action.

---

## Prompt Builder Requirements

Prompt Builder should output a usable prompt and teach why it works.

Inputs may include:

- project goal
- current phase
- current task
- files involved
- constraints
- what not to change
- desired output type
- tests/checks needed
- confusion/uncertainty

Output should include:

- final prompt
- why this prompt is strong
- what it prevents
- optional bad-prompt comparison

Prompt Builder should be useful even before the rest of the product is complete.

This is a key first-value feature.

---

## Review Board Requirements

Review Board should capture what happened after the user used an AI coding tool.

It should ask:

- What files changed?
- What did AI generate?
- What did you accept?
- What did you reject?
- What did you edit manually?
- What assumption did AI make?
- What are you least confident about?
- Did AI go out of scope?
- What do you need to verify?

Review Board output should feed:

- gate context
- evaluation summary
- defense report
- future project evidence

---

## Project Defense Report Requirements

The report should be generated from actual user-submitted workflow artifacts.

It should include:

- project summary
- purpose
- workflow steps completed
- prompt generated
- review answers
- evidence submitted
- verification checks
- gate outcome
- safe gate summary
- unlocks earned
- current defense readiness
- recommended next action
- interview-style questions

It must not include:

- hidden gate scores
- hidden unlock thresholds
- evaluator private reasoning
- raw internal prompts
- service-role data
- provider keys

It should be exportable or copyable later, but PDF/export is not required for v0.1.

---

## Pilot and Metrics

Codize’s success depends on real users, not module count.

By pilot time, track:

- number of testers
- number of projects started
- number of prompts generated
- number of review boards completed
- number of verification checks completed
- number of gates attempted
- number of gates passed/failed
- number of reports generated
- before/after confidence explaining AI-generated code
- whether users identified an AI assumption they would have missed
- whether users completed a verification step they normally skip
- whether users would use Codize again when stuck

Best pilot users:

- AP CSA students
- high school CS students
- hackathon teammates
- older TheCoderSchool students if allowed
- Spark Code volunteers/instructors
- friends building projects with AI

Do not pilot first with elementary Scratch students unless building a separate Codize Lite.

---

## College Application Relevance

Codize becomes college-app-strong only if it produces evidence.

Weak version:

> I built a platform that teaches AI coding.

Stronger version:

> I built and piloted an AI coding workflow trainer that helped students plan, prompt, review, verify, and defend AI-assisted projects.

Strongest version:

> In an early pilot with student builders, Codize helped users identify AI assumptions, complete verification steps they normally skipped, and improve confidence explaining their projects.

The admissions strength comes from:

- real problem insight
- technical execution
- real users
- observed failure points
- product iteration
- connection to teaching/CS education
- measurable improvement

Do not overclaim.

Do not say Codize proves learning unless pilot data supports it.

---

## Relationship to Existing Backend Modules

Existing backend modules are still useful.

They should be reinterpreted through the v3 product vision:

- Intake = project setup and build context
- Roadmap = workflow plan
- Phase workspace = AI workflow loop workspace
- Gate = project defense check
- Unlocks = functional workflow boosts
- Reconnection = restore project context after time away
- Evaluation = defense readiness and next-action summary
- Future report = Project Defense Report

The backend is not wasted.

The frontend must now make the workflow visible and useful.

Be honest about what has no backend yet: as of M12 there are NO backend routes or tables for the Prompt Builder, Review Board, Evidence Panel, Verification Lab, Project Defense Report generation, or pilot analytics. The existing API surface is exactly: intake, archetypes, roadmap, phases/tasks, gate, unlocks, reconnection, and evaluation. M13 planning must decide, per surface, whether v0.1 handles it client-side, defers it, or requires a small new backend milestone — do not assume backend support exists for the new v3 surfaces.

---

## M13 Direction

Milestone 13 should not be generic frontend integration.

Milestone 13 should become:

> AI Workflow Workspace MVP

M13 should create frontend screens around:

1. Landing page
2. Auth flow
3. Project Cockpit
4. Intake
5. Phase Workflow Board
6. Prompt Builder
7. Review Board
8. Evidence Panel
9. Verification Lab
10. Understanding Gate
11. Project Defense Report / Evaluation Summary

M13 should not just create:

- intake form
- roadmap page
- checklist page
- gate modal

That would preserve the old narrow framing.

The UI should make the Codize Build Loop obvious.

---

## Visual / Interface Direction

Codize should feel like:

- developer-focused
- sharp
- serious
- high-contrast
- workflow-oriented
- closer to Linear / GitHub / VS Code than a school LMS

It should not feel:

- childish
- gamified for its own sake
- like Duolingo for coding
- like a generic SaaS dashboard
- like a quiz app
- like a fake IDE

A VS Code-like feeling is acceptable as an aesthetic reference, but Codize should not build a real IDE in v0.1.

Preferred interface metaphor:

> engineering cockpit

Not:

> browser IDE

---

## Copy Tone

Tone should be direct, useful, and non-shaming.

Good copy:

- Stop debugging blindly.
- Be ready to defend what you shipped.
- Review AI like a teammate, not a magic box.
- AI can help you ship faster. Codize helps you stay in control.
- Your next prompt should not make the mess bigger.
- Generate code fast. Verify it like an engineer.

Avoid:

- You are cheating.
- You are not a real engineer.
- Prove you are not just a prompter.
- Learn responsibly because it is good for you.
- AI is bad.
- Vibe coders are lazy.

Codize should respect the user.

The message is:

> Your workflow is incomplete. Codize helps you fix it.

Not:

> You are bad for using AI.

---

## Out of Scope for v0.1

Do not build these before the core workflow works:

- browser IDE
- full GitHub OAuth
- automatic repo scanning
- AI news digest
- tool recommendations marketplace
- social/community features
- class management
- teacher dashboard
- elementary/Scratch version
- AI coding agent
- hosted coding runtime
- unrestricted agent sandbox
- complex gamification
- leaderboard
- mobile app

These may be future directions, but not MVP.

---

## Future v2 Directions

Future versions may add:

- GitHub OAuth
- repo diff analysis
- commit evidence
- GitHub Actions/test result ingestion
- automated security checks
- project defense report export
- interview defense mode
- rescue mode as a full separate flow
- AI workflow digest
- tool recommendation guide
- Codize Lite for younger students
- teacher/mentor review
- classroom pilot mode

These should only be built after the v0.1 workflow proves useful with real users.

---

## Current Authority Relationship

This document controls product positioning and M13+ frontend direction.

`codize_master_spec_v2.1.md` still controls:

- backend invariants
- intake question requirements
- three archetype system
- security constraints
- gate mechanics
- RLS/auth requirements
- no-hidden-score leakage
- mandatory security checklist concepts

If this document and the old spec conflict on UX positioning or frontend direction, this document wins.

If this document and the old spec conflict on backend security, auth, RLS, or gate safety invariants, the old spec still wins unless the user explicitly approves a new security design.

`codize_roadmap_v2.html` is now legacy build/learning context.

`conversations.json` is historical product-debate archive only.

`instructions.md` controls the active task/process for a Claude Code session, not the long-term product vision.

---

## North Star

One student.

One project.

One AI workflow loop.

One Project Defense Report.

If Codize can help one student build with AI while better planning, prompting, reviewing, verifying, and defending their work, the product is real.

Scale comes later.