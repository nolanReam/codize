# Codize Milestone Handoff Skill

## Purpose

Force Claude Code to build Codize in isolated, verified milestones so the project can survive context clearing with `/compact`.

Use this skill during every implementation session.

## Milestone Rule

Only work on one milestone per session.

Do not continue into the next milestone automatically.

Each milestone must end with:

1. Implementation completed
2. Relevant tests run
3. Verification results reported
4. Git commit created
5. Durable memory updated
6. User told to run `/compact`

## Required End-of-Milestone Format

At the end of every milestone, report:

```text
MILESTONE COMPLETE

Milestone:
Files changed:
Tests run:
Verification results:
Git commit:
Memory updates:
Known issues:
Next milestone:
Action for user:
Run /compact before continuing.