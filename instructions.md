# Codize Active Session Instructions — Milestone 3

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
* Live adversarial prompt testing is still pending because no `ANTHROPIC_API_KEY` is available

Milestone 2 is complete.

* Commit: `5db4744`
* Codize Supabase schema exists.
* RLS is enabled on all Codize tables.
* Ownership policies use `auth.uid() = user_id`.
* Behavioral RLS verification passed through Supabase MCP.
* Wrong-user isolation verified.
* Deny tests passed.
* Legacy schema was removed with user approval.
* Security advisors are clean except leaked-password protection, which must be toggled in Milestone 3.

## Before Beginning Milestone 3

Do a quick continuity check:

1. Read `CLAUDE.md`.
2. Read `.claude/skills/spec-guardian/SKILL.md`.
3. Read `.claude/skills/security-test/SKILL.md`.
4. Read `.claude/skills/milestone-handoff/SKILL.md`.
5. Read `.claude/memory/auth-milestone-todos.md`.
6. Read `.claude/memory/supabase-project-state.md`.
7. Read `.claude/memory/rls-design-decisions.md`.
8. Confirm `git status` is clean.
9. Confirm Supabase MCP access is available.
10. Confirm the current Supabase Auth configuration and security advisor status.

Do not begin implementation until this continuity check is complete.

## Milestone 3 Only — Authentication

Begin Milestone 3 only.

Milestone 3 goal:

Create and verify Codize's authentication foundation using Supabase Auth, without implementing the full FastAPI application yet and without building the frontend UI yet.

## Required Work

### 1. Supabase Auth Configuration Audit

Use Supabase MCP where possible.

Verify and document:

* Email/password auth is enabled.
* Signup flow is available.
* User profile auto-creation trigger exists and works.
* `profiles` rows are created on signup.
* `profiles.user_id` correctly references `auth.users.id`.
* RLS still protects `profiles`.
* Leaked-password protection status.

If leaked-password protection cannot be enabled through MCP/CLI and requires dashboard action, clearly report the exact dashboard step the user must take. Do not claim it is enabled unless verified.

### 2. Auth Environment Contract

Create or update environment documentation.

Document required variables without values:

* Supabase project URL
* Supabase anon key
* Supabase service-role key, server-only
* database URL if needed
* future Anthropic API key, server-only

Make sure `.env.example` exists if appropriate.

Never put real secrets in committed files.

### 3. Auth Verification Scripts

Create lightweight verification scripts if useful.

They should verify:

* signup creates a profile
* authenticated user can read own profile
* authenticated user cannot read another user's profile
* anon cannot read protected profile/project data
* RLS behavior from Milestone 2 still holds

Prefer scripts that are repeatable and safe.

Clean up test users/data when possible.

### 4. Backend Auth Design Prep

Because FastAPI architecture is Milestone 4, do not build the full backend yet.

However, document the intended backend auth enforcement design:

* frontend sends Supabase JWT to FastAPI
* FastAPI verifies JWT server-side
* protected endpoints reject missing/invalid tokens with 401
* ownership checks return 403 or 404 for wrong-user resources
* service-role key is only used server-side when needed
* UI hiding is never treated as security

Put this in docs, not runtime app code, unless a tiny helper or placeholder is explicitly needed for validation.

### 5. Update Durable Repo Knowledge

Update:

* `CLAUDE.md` with any new commands created
* `.claude/memory/` with any durable auth lessons
* relevant skill files only if a reusable correction is learned

## Pending Live Prompt Tests

If an `ANTHROPIC_API_KEY` is available in the environment, run the pending live adversarial prompt tests and update `docs/prebuild/adversarial_tests.md`.

If the key is not available, do not block Milestone 3. Keep live prompt testing marked pending. Do not ask the user to paste secrets into chat.

## Out of Scope for This Session

Do not implement FastAPI application routes.

Do not build frontend UI.

Do not implement roadmap generation runtime.

Do not implement the Interrogation Gate runtime.

Do not implement the unlock system.

Do not begin Milestone 4.

Do not continue beyond Milestone 3.

## End-of-Milestone Requirements

At milestone end:

1. Run relevant auth/RLS validation.
2. Run `python scripts/validate_prebuild_artifacts.py` as regression.
3. Run secret scan on changed files.
4. Verify Supabase Auth/security advisor status where possible.
5. Commit changes.
6. Update memory.
7. Output:

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