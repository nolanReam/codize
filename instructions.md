# Codize Pilot Prep — Tester Script, Survey, Demo Checklist

Prepare Codize for a small real-user pilot.

This is a documentation, research, and pilot-readiness milestone.

Do not start M14.

Do not add new product features.

Do not modify backend behavior.

Do not modify gate evaluator logic.

Do not create migrations.

Do not add GitHub OAuth, AI news, browser IDE, community features, tool marketplace, analytics dashboard, hosted coding runtime, or complex gamification.

Do not run a real pilot yet.

## Current State

Relevant commits:

- M13C.2 Gate UI + Project Defense Report: `8161dce`
- M13C.2B Gate Question Cleanliness Hotfix: `c0320f5`

Codize now has:

- landing page
- auth
- intake
- roadmap generation with deterministic fallback
- cockpit
- phase workflow board
- prompt builder
- review board
- evidence panel
- verification lab
- live gate UI
- Project Defense Report
- Markdown copy/download export
- clean gate-question sanitizer

## Goal

Create a small pilot kit that lets the user test Codize with 3–10 student builders.

The pilot should answer:

1. Can users understand what Codize is for?
2. Can users complete the core workflow without help?
3. Does Codize help users write better AI prompts?
4. Does Codize help users review what AI changed?
5. Does Codize make users complete verification steps they normally skip?
6. Does Codize make users feel more able to defend/explain their project?
7. Where does the app feel confusing, slow, annoying, or unnecessary?

## Read First

Read:

- `CLAUDE.md`
- `docs/context/context_authority.md`
- `docs/context/codize_product_vision_v3.md`
- `docs/context/m13_ai_workflow_workspace_plan.md`
- `.claude/memory/product-vision-v3.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/gate-conventions.md`
- frontend README
- current frontend routes if needed

Do not read `conversations.json` unless genuinely needed.

## Pilot Target Users

The first pilot should target:

- AP CSA students
- high school CS students
- hackathon friends
- older TheCoderSchool students if allowed
- Spark Code volunteers/instructors
- peers who have used Claude Code, Cursor, Replit, ChatGPT, or Copilot for coding

Do not design this first pilot for elementary Scratch students.

Do not collect sensitive personal information.

Do not require full names, school names, addresses, phone numbers, or private account credentials.

Use first name or nickname only if needed.

## Task 1 — Create Pilot Folder

Create:

`docs/pilot/`

Add these files:

1. `docs/pilot/pilot_plan.md`
2. `docs/pilot/tester_script.md`
3. `docs/pilot/pre_survey.md`
4. `docs/pilot/post_survey.md`
5. `docs/pilot/observation_notes_template.md`
6. `docs/pilot/bug_report_template.md`
7. `docs/pilot/demo_checklist.md`
8. `docs/pilot/results_summary_template.md`

## Task 2 — Pilot Plan

`pilot_plan.md` should define:

- pilot goal
- target tester profile
- number of testers: 3–10 for first pilot
- estimated time: 30–45 minutes
- what testers need before starting
- what project type testers should use
- what data to collect
- what not to collect
- success criteria
- failure criteria
- how to summarize results honestly

The pilot should be framed around one core task:

> Build or continue one AI-assisted project phase using Codize, then generate a Project Defense Report.

Success is not “tester liked the app.”

Success is whether Codize helped the tester:

- create a better prompt
- identify what AI changed
- verify something they normally skip
- explain the project more clearly
- produce a useful Project Defense Report

## Task 3 — Tester Script

`tester_script.md` should be a step-by-step script the user can give testers.

It should include:

1. What Codize is
2. What the tester will do
3. How long it takes
4. What they should not worry about
5. Start at landing page
6. Sign up/log in
7. Complete intake
8. Open current phase
9. Use Prompt Builder
10. Use their preferred AI coding tool externally
11. Return to Codize
12. Fill Review Board
13. Fill Evidence Panel
14. Complete Verification Lab
15. Complete Gate if ready
16. Open Project Defense Report
17. Copy/export report
18. Complete post-survey

Tone should be simple and non-technical enough for high school CS students.

## Task 4 — Pre-Survey

`pre_survey.md` should include short questions using mostly 1–5 scales.

Include questions like:

- How often do you use AI tools for coding?
- How confident are you writing prompts for coding help?
- How confident are you reviewing AI-generated code?
- How often do you verify AI-generated code before moving on?
- How confident are you explaining a project AI helped you build?
- Have you ever gotten stuck in an AI patch loop?
- What AI coding tool do you usually use?

Do not ask for sensitive personal data.

## Task 5 — Post-Survey

`post_survey.md` should measure whether Codize helped.

Include questions like:

- Did Codize help you write a better AI prompt?
- Did Codize help you notice something AI changed?
- Did Codize make you verify something you might normally skip?
- Did the gate feel useful, annoying, confusing, or fair?
- Did the Project Defense Report feel useful?
- How confident are you now explaining the project?
- What was the most useful part?
- What felt like unnecessary friction?
- Where did you get confused?
- Would you use Codize again on another project?
- What one thing should be improved first?

Include a before/after comparison section.

## Task 6 — Observation Notes Template

`observation_notes_template.md` should help the user observe testers without over-directing them.

Track:

- where tester hesitated
- where tester asked for help
- what page confused them
- what wording confused them
- whether they understood the 80% Trap positioning
- whether they used the generated prompt
- whether they completed verification honestly
- whether they could explain their code better after the gate/report
- any bugs or crashes

## Task 7 — Bug Report Template

`bug_report_template.md` should collect:

- page/route
- what tester was doing
- expected behavior
- actual behavior
- screenshot/log if available
- severity
- whether it blocked completion
- browser/device
- account/tester label, not full personal identity

## Task 8 — Demo Checklist

`demo_checklist.md` should be the checklist the user runs before showing Codize to testers or recording a demo.

Include:

- backend running
- frontend running
- env vars present
- test account ready
- Supabase email confirmation handling known
- roadmap generation works without manual seeding
- intake works
- artifact save/load works
- gate flow works
- report export works
- logout works
- no secrets in frontend
- clean working tree
- known issues listed

## Task 9 — Results Summary Template

`results_summary_template.md` should help convert the pilot into useful evidence.

Include sections:

- pilot date
- number of testers
- tester profiles, non-identifying
- projects attempted
- completion rate
- average pre/post confidence explaining AI-generated code
- how many generated a prompt
- how many completed review board
- how many submitted evidence
- how many completed verification
- how many attempted/passed gate
- how many exported report
- top 3 useful moments
- top 3 friction points
- bugs found
- changes to make next
- honest conclusion

It should include a sample sentence structure for college-app-style evidence, but it must warn not to overclaim.

Example:

“In an early pilot with X student builders, Y completed a verification step they said they normally would skip, and average confidence explaining an AI-assisted project changed from A/5 to B/5.”

## Task 10 — Optional Pilot README

If useful, create:

`docs/pilot/README.md`

It should briefly explain how all pilot files fit together.

## Boundaries

Do not modify product code unless there is a tiny docs link or typo fix that is clearly necessary.

Do not create a survey backend.

Do not create analytics tracking.

Do not create a Google Form.

Do not create external accounts.

Do not collect real tester data in the repo.

Do not invent pilot results.

## Optional Final Smoke Note

If time and env are available, run a quick no-code smoke check of the existing app and note whether it is ready for pilot.

Do not block the docs milestone if live env is unavailable.

## Verification

Run a secret scan before commit.

No frontend/backend tests are required unless product code changes.

If product code changes accidentally, run the relevant tests.

## Documentation Updates

Update if needed:

- `CLAUDE.md`
- `.claude/memory/frontend-conventions.md`
- `.claude/memory/product-vision-v3.md`

Only update them if the pilot workflow should be remembered.

Do not rewrite the whole product vision.

## End Requirements

At the end, output:

- files created/updated
- pilot plan summary
- recommended first tester group
- what metrics to track
- what not to claim yet
- secret scan result
- git commit hash
- next step: run pilot with 3–5 testers or do final deployment/demo prep

Commit completed pilot prep docs.

Stop after commit.