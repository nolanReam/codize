# Codize Product Vision Reset — Context Update Only

Do not implement product code in this session.

Do not build frontend screens.

Do not modify backend behavior.

Do not create migrations.

Do not start Milestone 13.

This is a context/spec reset after Milestone 12. The goal is to update Codize’s product direction before M13 frontend work begins.

## Current State

Milestones M1–M12 are complete.

Completed milestones:

- M1 Repository foundation + pre-build artifacts — `98ad004`
- M2 Supabase schema + RLS — `5db4744`
- M3 Authentication foundation — `1075d2f`
- M4 FastAPI core — `d6e55be`
- M5 Archetype template engine — `53d6aa0`
- M6 Intake engine — `0aacfae`
- M7 Roadmap generation engine — `6a1c9c8`
- M8 Phase workspace — `d38f642`
- M9 Interrogation Gate — `9b46f7e`
- M10 Functional unlocks — `4400f71`
- M11 Reconnection system — `9012a52`
- M12 Evaluation system — `44442b0`

## Product Direction Shift

The product vision has been clarified.

Codize should no longer be framed mainly as:

- roadmap generation
- task checklist
- understanding gate
- generic student progress dashboard

That framing is too narrow and makes Codize feel like a roadmap + quiz app.

Codize should now be framed as:

> An AI coding workflow trainer that helps student builders escape the 80% trap, use AI tools properly, verify what AI generated, and defend the projects they ship.

This is not a random pivot.

It is a correction back toward the original master spec’s thesis: Codize solves a workflow problem, not a laziness problem. Students need to learn where AI belongs in the software development process and where human judgment must remain in control.

## Read First

Read:

- `CLAUDE.md`
- `docs/context/codize_product_vision_v3.md` if it already exists
- `docs/context/codize_master_spec_v2.1.md`
- `docs/context/codize_roadmap_v2.html`
- `.claude/memory/product-vision-v3.md` if it already exists
- `.claude/memory/` files related to roadmap, phase workspace, gate, unlocks, reconnection, and evaluation

Do not read `conversations.json` unless needed.

## Task 1 — Create or Update Product Vision v3

Create or update:

`docs/context/codize_product_vision_v3.md`

This document is the current product-direction source for Milestone 13+.

If the file already exists, review it and improve it instead of duplicating it.

It should define Codize as:

- an AI coding workflow trainer
- not an AI coding assistant
- not a browser IDE
- not an AI news app
- not just a quiz/gate platform
- not a replacement for Claude Code, Cursor, GitHub Copilot, Replit, Codex, or ChatGPT

## Required v3 Product Thesis

Codize helps student builders stop blindly vibe coding by guiding them through a disciplined AI-assisted engineering loop:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

The main user pain is the 80% Trap:

AI can generate the first 80% of an app quickly, but the project collapses when the user adds features, hits bugs, or needs to explain architecture they never understood.

The main product payoff is the Project Defense Report:

A student leaves with evidence that they planned, prompted, reviewed, verified, and explained their AI-assisted project work.

## MVP v0.1 Scope

Define the narrow MVP as:

One student.
One project.
One phase/workflow loop.
One Project Defense Report.

MVP should include:

1. Landing page around the 80% Trap
2. Project Cockpit
3. Prompt Builder
4. Review Board
5. Evidence Panel
6. Verification Lab
7. Evidence-Based Understanding Gate
8. Project Defense Report
9. Basic pilot analytics/survey hooks if feasible

MVP should not include:

- browser IDE
- full GitHub OAuth
- AI news digest
- community/social features
- tool marketplace
- random XP/streak gamification
- elementary/Scratch version
- full automated verification of arbitrary projects
- AI coding agent
- hosted coding runtime

Manual evidence is acceptable for v0.1:

- repo URL
- commit hash
- changed files
- pasted terminal output
- screenshot link/notes
- what AI generated
- what the user accepted/rejected/edited

## Task 2 — Create or Update Claude Memory

Create or update:

`.claude/memory/product-vision-v3.md`

This should be a concise durable reminder, not the full product spec.

It should record:

- the vision shifted before M13
- old roadmap + checklist + gate framing is incomplete
- current thesis is AI Workflow Trainer / Project Defense Workflow
- the Codize Build Loop is Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect
- M13 should become AI Workflow Workspace MVP
- browser IDE, full GitHub OAuth, AI news, community, and tool marketplace are out of scope for v0.1
- `docs/context/codize_product_vision_v3.md` is the current product-direction source

## Task 3 — Update Context Authority

Create or update:

`docs/context/context_authority.md`

This file should clearly define source authority.

Use this hierarchy:

1. `instructions.md`
   - Controls the active Claude Code task/process only.
   - Does not permanently redefine product vision unless it explicitly updates context docs.

2. `docs/context/codize_product_vision_v3.md`
   - Controls current product positioning, UX direction, MVP scope, and M13+ frontend direction.

3. `docs/context/codize_master_spec_v2.1.md`
   - Controls backend invariants, core architecture, intake, archetypes, security constraints, RLS/auth requirements, and gate mechanics unless explicitly superseded by v3.

4. `CLAUDE.md`, `.claude/skills/`, and `.claude/memory/`
   - Control durable implementation conventions and operational memory.

5. `docs/context/codize_roadmap_v2.html`
   - Legacy build/learning roadmap.
   - Useful historical context.
   - Not current product direction.
   - Do not use it to define M13 unless explicitly instructed.

6. `docs/context/conversations.json`
   - Historical product-debate archive only.
   - Not authoritative.
   - Do not read unless explicitly needed.

## What “Legacy” Means

Do not delete legacy files.

Do not rename legacy files unless necessary.

Marking a file as legacy means:

- future Claude sessions should know it is old context
- it can still be referenced for history
- it must not override the current v3 product direction
- it should not drive M13 frontend decisions

Do not edit `codize_roadmap_v2.html` heavily.

If adding a note is safe, add only a small comment near the top saying it is legacy. If that risks breaking the HTML, do not edit the HTML file; rely on `context_authority.md`, `CLAUDE.md`, and memory instead.

## Task 4 — Update CLAUDE.md

Update `CLAUDE.md` so future sessions know:

- Codize v3 product direction is AI Workflow Trainer / Project Defense Workflow.
- The old “roadmap + gate” framing is incomplete.
- `docs/context/codize_product_vision_v3.md` is the current product-direction source for M13+.
- `docs/context/codize_master_spec_v2.1.md` still controls backend/security/gate invariants.
- `docs/context/codize_roadmap_v2.html` is legacy build/learning context.
- `conversations.json` is historical archive only.
- M13 must not be started from the old three-screen frontend plan.
- M13 should implement the AI Workflow Workspace MVP.
- Browser IDE, AI news, full GitHub OAuth, community, and tool marketplace are out of scope for v0.1.

## M13 Direction To Record

Milestone 13 should be renamed/reframed from generic frontend integration to:

> AI Workflow Workspace MVP

M13 should not simply create old screens for:

- intake
- roadmap
- phase checklist
- gate modal

M13 should create a frontend experience around:

- Landing page
- Project Cockpit
- Prompt Builder
- Review Board
- Evidence Panel
- Verification Lab
- Evidence-Based Gate
- Project Defense Report / Evaluation Summary

Existing backend routes may still be used, but the UX language and flow should match the v3 product direction.

## Do Not

Do not implement frontend code.
Do not modify backend behavior.
Do not create migrations.
Do not start M13.
Do not delete old context files.
Do not rewrite the entire master spec.
Do not overbuild the product vision into a huge platform.
Do not add AI news, browser IDE, GitHub OAuth, community, or tool marketplace to the MVP.

## End Requirements

At the end:

- list files created/updated
- explain the new authority hierarchy
- explain what is now legacy
- explain how M13 changes
- run a quick secret scan if files were changed
- commit changes
- output the git commit hash
- stop