# Codize Product Vision v3 — Durable Memory

Codize’s product vision shifted on 2026-07-03, after Milestone 12 (backend
M1–M12 complete at `44442b0`) and before Milestone 13.

The old framing was too narrow:

- roadmap generation
- task checklist
- understanding gate
- progress dashboard

That made Codize feel like a roadmap + quiz app.

The current framing is:

> Codize is an AI coding workflow trainer that helps student builders stop blindly vibe coding, escape the 80% trap, verify what AI generated, and defend the projects they ship.

## Current Product Thesis

AI coding tools help students generate code.

Codize teaches them how to stay the engineer.

Codize should sit above tools like Claude Code, Cursor, GitHub Copilot, Replit, Codex, and ChatGPT as the workflow, verification, and project-defense layer.

Do not frame Codize as an AI coding assistant or browser IDE.

## Core User Pain

The main user pain is the 80% Trap:

AI can generate the first 80% of an app quickly, but then one new feature or bug breaks everything because the student does not understand the architecture, data flow, or assumptions AI created.

Codize should help the student regain control.

## Core Product Loop

The Codize Build Loop is:

Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect

This loop is the product.

The roadmap, phase workspace, gate, unlocks, reconnection, and evaluation features exist to support this loop.

The gate is important, but it is not the whole product.

## Main Payoff

The main payoff is a Project Defense Report.

The user should leave with evidence that they:

- planned the work
- generated a strong AI prompt
- reviewed what AI changed
- submitted evidence
- verified behavior
- explained the implementation
- reflected on what they built

The report should help the user defend the project in a portfolio review, interview, hackathon, class, or college application.

## M13 Direction

Do not start M13 from the old generic frontend plan.

M13 should become:

> AI Workflow Workspace MVP

M13 should focus on:

- Landing page around the 80% Trap
- Project Cockpit
- Prompt Builder
- Review Board
- Evidence Panel
- Verification Lab
- Evidence-Based Understanding Gate
- Project Defense Report / Evaluation Summary

M13 should not merely create:

- intake form
- roadmap page
- checklist page
- gate modal

That would preserve the old narrow framing.

Backend-gap warning for M13 planning: the Prompt Builder, Review Board,
Evidence Panel, Verification Lab, Defense Report generation, and pilot
analytics have NO backend routes or tables as of M12. The existing API
surface is exactly intake/archetypes/roadmap/phases/gate/unlocks/
reconnection/evaluation (see [[gate-conventions]],
[[phase-workspace-conventions]], [[unlock-conventions]],
[[reconnection-conventions]], [[evaluation-conventions]]). Decide per
surface: client-side for v0.1, defer, or a small new backend milestone —
never assume backend support exists. Existing safety invariants (hidden
scores, thresholds, prompt secrecy, RLS, gate mechanics) are unchanged by
this vision reset.

## MVP Boundaries

Build the smallest useful workflow trainer:

One student.
One project.
One AI workflow loop.
One Project Defense Report.

Do not build these for v0.1:

- browser IDE
- full GitHub OAuth
- automatic repo scanning
- AI news digest
- tool marketplace
- community/social features
- class management
- elementary/Scratch version
- hosted coding runtime
- complex gamification
- leaderboard

Manual evidence is acceptable for v0.1:

- repo URL
- commit hash
- changed file names
- pasted test output
- screenshot note
- what AI generated
- what the user accepted/rejected/edited

## Authority

`docs/context/codize_product_vision_v3.md` is the current product-direction source for M13+.

`docs/context/codize_master_spec_v2.1.md` still controls backend invariants, intake, archetypes, security, RLS/auth, and gate safety unless explicitly superseded.

`codize_roadmap_v2.html` is now legacy build/learning context.

`conversations.json` is historical archive only.

`instructions.md` controls only the active Claude Code task.