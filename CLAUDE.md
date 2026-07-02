# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Codize is an educational platform that helps students understand the projects they build with AI — it teaches real dev workflows and reasoning about your own code, using AI as a tool rather than a crutch. It is a benign educational product about architecture understanding and project reasoning. It is **not** a cybersecurity, exploit, malware, or offensive-security tool.

**Current state: Milestone 6 complete** (intake engine, on top of M5's template engine, M4's FastAPI core, M3's auth foundation, M2's schema+RLS and M1's pre-build artifacts). The FastAPI backend lives in `backend/app/` (see `backend/README.md`): app factory + CORS + consistent error shape (`main.py`, `core/errors.py`), centralized `Settings` with SecretStr server-only values (`core/config.py`), Supabase JWT verification via JWKS/ES256 (`core/security.py`), and the `require_user` auth dependency → 401 (`deps/auth.py`). The template engine (`services/template_service.py`) loads and validates the three archetype templates at startup (fail-fast; rejects any fourth archetype), serves them as copies (no runtime mutation), and holds the spec's deterministic classification tiebreaker (`resolve_archetype`). The intake engine (`services/intake_service.py`) holds the five spec-verbatim questions, enforces sequential answering (Q1 unskippable), normalizes answers, stores them on the `projects` row via the `ProjectRepository` seam (`services/project_repository.py` — PostgREST with the service-role key, every query ownership-filtered by `user_id`; **live writes unverified**, business rules tested with an in-memory fake), and on completion classifies the project via a deterministic keyword fallback into `resolve_archetype` (the temp-0 LLM classification call replaces `_derive_classification_signals` in a later milestone). Routes: `GET /health` (public); auth-required: read-only `GET /archetypes` + `GET /archetypes/{id}` (`routers/archetypes.py`) and the intake flow `GET /intake/questions`, `GET /intake/status`, `POST /intake/answers`, `POST /intake/complete` (`routers/intake.py`; out-of-order/premature/duplicate actions → 409, bad input → 422). The three archetype JSON templates live in `backend/app/templates/` and the six system prompts in `backend/app/prompts/` (see its README for call parameters). The database schema (4 tables: `profiles`, `projects`, `gate_sessions`, `unlocks`) is live in Supabase project `tadkbymxkdncqahzshml` with RLS verified — see `docs/db/schema.md` and `supabase/migrations/`. Supabase Auth is verified end-to-end with real JWTs (signup trigger, password login, RLS through PostgREST) — see `docs/auth.md` for the audit and the backend auth enforcement design; env contract in `.env.example`.

## Commands

- `python scripts/validate_prebuild_artifacts.py` — validates templates + prompts against the spec's invariants (run after any edit to either).
- `scripts/verify_rls.sql` — RLS/ownership audit queries; run via Supabase MCP `execute_sql` after any schema change (sections 6–8 expect permission errors; run per-section).
- `scripts/verify_auth.sql` + `python scripts/verify_auth.py` — end-to-end auth/RLS check over the real Auth+PostgREST APIs with real JWTs: run the SQL SETUP via MCP, run the script with `SUPABASE_URL`/`SUPABASE_ANON_KEY` set, then run the SQL CLEANUP. Run after any auth or RLS change.
- Backend tests: from `backend/`, `.venv\Scripts\python -m pytest` (venv setup: `python -m venv .venv` then `.venv\Scripts\pip install -r requirements.txt`). Run after any backend change.
- Backend dev server: from `backend/`, `.venv\Scripts\uvicorn app.main:app --reload`.

## Where the durable context lives

Read these before making product or architecture decisions:

- **`docs/context/codize_master_spec_v2.1.md`** — the authoritative product specification (Master Spec, content v1.2). This is the definitive blueprint. **The spec wins** over implementation and over your own assumptions. Note: it is a Markdown file despite some skill references to a `.pdf`.
- **`docs/context/codize_roadmap_v2.html`** — the concrete build/learning roadmap for Codize itself. Pins down technical decisions (async FastAPI, service-layer structure, gate temperatures, RLS policy shape).
- **`docs/context/conversations.json`** — raw product-debate history (large, ~1.4MB; grep it, don't read whole).
- **`docs/context/fable_5_prompting.md`** — Claude Fable 5 / Mythos 5 prompting and scaffolding guidance.
- **`instructions.md`** — a **pre-flight orchestrator**, not the product spec. (Its current content only directs the creation of this CLAUDE.md.) Do not treat it as the source of architecture or milestone order.
- **`.claude/skills/*/SKILL.md`** — project skills (see Skill usage below).
- **`README.md`** — product pitch.

## Planned architecture

Built strictly back-to-front through external services — **never Frontend → External Service directly.**

- **Frontend (Next.js, deployed on Vercel) → Backend (FastAPI, deployed on Railway) → External Service (Supabase, Anthropic API).**
- **Supabase** for database + auth. **FastAPI** (async — required, every LLM call is I/O-bound) for the API. **Anthropic API** (Claude) for the AI engines.
- Backend structure: a **`services/` layer holds all AI calls, gate logic, and template loading — never in route handlers.** A `templates/` folder holds the three archetype JSON files, loaded at startup.
- MCP tooling is available for filesystem, git, github, supabase, and playwright — use the supabase MCP to *verify* schema/RLS rather than assuming.

## Build order & milestone workflow (important)

Do not build the whole product in one session. Work **exactly one milestone at a time.**

**Pre-build gate (spec "Pre-Build Artifacts Required"):** before *any* backend/schema code, both must exist —
1. The **three archetype JSON templates** (full phase structure for all three archetypes).
2. The **six system prompts** (per the spec's "System Prompt Architecture"), drafted in full and manually tested against adversarial inputs.

After the pre-build artifacts, a reasonable milestone sequence (derived from spec Section 5 in-scope items) is: Repository foundation → Supabase schema + RLS → Auth → FastAPI core → Archetype template engine → Intake → Roadmap generation → Phase workspace → Interrogation Gate → Functional unlocks → Reconnection → Evaluation → Frontend integration → Security audit → Deployment (Vercel + Railway).

For each milestone: **Implement → Test → Verify → Commit → Update memory → Stop.** Then output `MILESTONE COMPLETE` with files changed, tests run, verification results, and the git commit hash, and instruct the user to `/compact`, start a fresh session, and paste the continuation prompt. Do **not** auto-continue into the next milestone.

Maintain lessons in `.claude/memory/` (one specific lesson per file; update or remove stale ones); consult it before major architectural decisions.

## Domain invariants that must not drift

Fixed by the spec — do not add, remove, or reorder:

- **Intake:** exactly five mandatory, sequential, conversational questions. Question 1 is verbatim "What problem do you want to solve, and who does solving it help?" and cannot be skipped. Store all five answers (purpose, scope, stack, self-assessed understanding, timeline). Signup goes straight to question 1 — no form/dashboard/homepage.
- **Archetypes:** exactly three — (1) AI-Powered App, (2) REST API Backend, (3) Full-Stack Web App. No fourth, ever. Structure comes from hardcoded JSON templates; the LLM personalizes wording only and may never add, remove, or reorder phases, change AI-vs-human task labels, or alter gate targets/unlock conditions. Classification is a temperature-0 call. Tiebreaker: LLM API is a core feature → Archetype 1; else has frontend/database → Archetype 3; else → Archetype 2. Default stack for Archetype 1 is fixed: Python + FastAPI + Vanilla HTML/JS.
- **Interrogation Gate:** mandatory, cannot be skipped (student may choose Option A explanation / Option B bug-hunt format; A is the MVP default). Requires a self-reported anchor statement, then Turn 1 (implementation-specific question, temp 0.3), Turn 2 (probe the weakest of accuracy/specificity/completeness), Turn 3 (fresh hypothetical from anchor + prior answers + implementation, not answerable from generic knowledge). On failure: no immediate retry, **30-minute cooldown**.
- **Evaluation:** a **separate** LLM call at **temperature 0**, binary PASS/FAIL + one-sentence reason + a 0–10 quality score, against three conditions (Structural Identification, System Ripple Effect, Implementation Specificity — all three required). **Auto-fail any textbook/generic answer** that could apply to any codebase regardless of technical correctness.
- **Gate eval is a two-call pattern:** Call 1 (temp 0.3) generates the Turn 3 hypothetical; Call 2 (temp 0) evaluates the answer. (Phase explanations use temp ~0.7.)
- **Functional unlocks:** triggered by performance thresholds the student cannot observe (e.g. quality score ≥7 across two consecutive gates), never by phase completion. No badges/XP/streaks/leaderboards.
- **Reconnection:** in-app modal only (no email). Triggers on login when `last_login` delta > 72h; shows the student's verbatim intake purpose; dismissed only by clicking "Let's keep building" (no timer, no click-outside, no Escape).

## Security constraints (non-negotiable)

Encoded into every archetype template from Phase 1, not bolted on at the end:

- **Secrets stay server-side.** Never expose Anthropic keys, Supabase service-role keys, or DB secrets to the frontend — `.env` values get bundled into JS. Frontend calls the backend; the backend calls external APIs with the real key. (OWASP A02.)
- **RLS on every Supabase table before any other DB code.** Each table has a `user_id` column and an ownership policy (`USING (auth.uid() = user_id)`). "User is logged in" is not ownership. Verify with the supabase MCP. (OWASP A01.)
- **Auth enforced server-side on every protected endpoint** — UI hiding/redirects are not security. Return 401 unauthenticated, 403 for another user's resource. (OWASP A01.)
- **Input validation** (parameterized queries, output escaping) on any user input reaching the DB or the UI. (OWASP A03.)
- Every archetype ends with a mandatory, gate-checked **pre-deployment security checklist** phase.
- At each milestone, run a living audit of tables, policies, and ownership checks; record findings. Advanced hardening (rate limiting, DDoS, full OWASP audit, pentest, CSP) is explicitly out of scope for the MVP.

## Engineering style

Build the simplest robust thing that satisfies the current task — no speculative abstractions, premature optimization, hypothetical scaling layers, or future-proofing. Trust framework guarantees; validate only at system boundaries (user input, external APIs). Escalate reasoning effort only for gate logic/prompts/rubrics, security audits, and evaluation systems.

Before adding anything, check it against the spec: is it explicitly required, is it needed for the current milestone, can it be done more simply? If no, don't build it. The "temptation to add a fourth archetype will come — resist it."

Report only verified work: audit each completion claim against actual test/tool/MCP output. If something is unverified or failed, say so — never fabricate progress.

## Skill usage

Before implementation, read the relevant local skill files under `.claude/skills/`:

- `.claude/skills/spec-guardian/SKILL.md` — product invariants and spec alignment (read before any product-logic change).
- `.claude/skills/security-test/SKILL.md` — validation, pytest, secret scanning, RLS checks, Playwright checks.
- `.claude/skills/ui-ux/SKILL.md` — Codize visual style (dark, high-contrast, violet accent), layout, and interface rules.
- `.claude/skills/milestone-handoff/SKILL.md` — milestone completion, git commit, memory update, and `/compact` handoff protocol.

If a reusable correction or durable engineering lesson is learned, update the relevant skill file or create/update one concise, specific file in `.claude/memory/` (one lesson per file — no vague notes).
