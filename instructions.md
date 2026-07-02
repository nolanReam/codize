# Codize Active Session Instructions — Milestone 2

Continue the Codize build per `CLAUDE.md`, `.claude/skills/`, and the durable context files.

## Authority

* `instructions.md` controls the active Claude Code session task.
* `CLAUDE.md` and `.claude/skills/*/SKILL.md` control durable repo workflow.
* `docs/context/codize_master_spec_v2.1.md` controls Codize product requirements.
* If these appear to conflict, stop and report the conflict before implementing.

## Current State

Milestone 1 is complete.

* Commit: `98ad004`
* Three archetype JSON templates exist in `backend/app/templates/`
* Six system prompts exist in `backend/app/prompts/`
* Static validator passed: `python scripts/validate_prebuild_artifacts.py` → `244/244 checks`
* Static adversarial test log exists at `docs/prebuild/adversarial_tests.md`
* Live adversarial prompt testing is still pending because no `ANTHROPIC_API_KEY` was available

## Before Beginning Milestone 2

Do a quick continuity check:

1. Read `CLAUDE.md`.
2. Read `.claude/skills/spec-guardian/SKILL.md`.
3. Read `.claude/skills/security-test/SKILL.md`.
4. Read `.claude/skills/milestone-handoff/SKILL.md`.
5. Read `.claude/memory/live-prompt-testing-pending.md`.
6. Confirm `git status` is clean.
7. Confirm Supabase MCP access is available.
8. Confirm whether Postgres/Supabase direct schema verification is possible through MCP.

Do not begin implementation until this continuity check is complete.

## Milestone 2 Only — Supabase Schema + RLS

Begin Milestone 2 only.

Milestone 2 goals:

* Design the Supabase schema required for Codize.
* Create migration files or schema documentation as appropriate.
* Enable RLS on every table.
* Create ownership policies using `auth.uid() = user_id` where applicable.
* Verify RLS policies using Supabase/Postgres MCP rather than assuming.
* Add validation tests or verification scripts if useful.
* Update `CLAUDE.md` with any new commands created during this milestone.
* Update `.claude/memory/` with any durable database/RLS lessons.

## Tables to Consider

Use the product spec as the final authority, but the schema will likely need tables for:

* user profiles
* projects
* intake answers
* archetype classification
* roadmap/phase progress
* gate attempts
* gate transcripts or summaries
* cooldowns
* functional unlocks
* session/logging metadata
* reconnection tracking

Do not overbuild. Use the simplest schema that supports the current product requirements.

## Security Requirements

Non-negotiable:

* RLS enabled on every Supabase table.
* Ownership policies must verify resource ownership, not merely login status.
* Service-role secrets must never appear in frontend files.
* Auth is enforced server-side later; for this milestone, schema must support server-side ownership verification.
* Wrong-user data access should be impossible under RLS.

Expected ownership policy shape where applicable:

`USING (auth.uid() = user_id)`

If a table is system-owned or read-only, explicitly document why its policy differs.

## Pending Live Prompt Tests

If an `ANTHROPIC_API_KEY` is available in the environment, also run the pending live adversarial prompt tests and update `docs/prebuild/adversarial_tests.md`.

If the key is not available, do not block Milestone 2. Keep live prompt testing marked pending and continue only with database/RLS work.

Do not ask the user to paste secrets into chat.

## Out of Scope for This Session

Do not implement FastAPI application logic.

Do not implement frontend UI.

Do not implement authentication flows.

Do not implement the Interrogation Gate runtime.

Do not begin Milestone 3.

Do not continue beyond Milestone 2.

## End-of-Milestone Requirements

At milestone end:

1. Run relevant validation.
2. Audit RLS/policies.
3. Run secret scan if files changed.
4. Commit changes.
5. Update memory.
6. Output:

MILESTONE COMPLETE

Include:

* milestone name
* files changed
* tests run
* verification results
* git commit hash
* memory updates
* known issues
* next milestone

Then tell the user:

Run `/compact`.
Start a fresh session.
Paste the next continuation prompt.
