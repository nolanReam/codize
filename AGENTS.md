# AGENTS.md

Guidance for agents working in this repository.

## Read authority first

Before product, workflow, architecture, learning, or major UX work, read:

1. `docs/context/context_authority.md`
2. `docs/context/v2/codize_v2_product_thesis.md`
3. `docs/context/v2/codize_v2_exact_ux_specification.md`
4. `docs/context/v2/codize_v2_character_system_blueprint.md` when character/customization work is relevant

The Product Thesis is the highest persistent V2 product authority. The authority file is a router, not a competing specification. Approved Figma governs visual composition only.

Do not read `conversations.json` unless the user explicitly requests historical research and authorizes it.

## Product direction

Codize V2 is a beginner-first AI coding mentor for students who build real projects with external coding agents. The defining principle is **one project, one current change, one useful habit at a time**. Chat is the primary Build interface, but deterministic product/state machinery—not free-form chat—is the architecture. Support should fade per competency as the student becomes more independent.

Do not turn V2 into a generic chatbot, a coding agent, a school dashboard, a rigid eight-stage workflow, or a mandatory Defense process.

## Current implementation boundary

The codebase currently implements the V1 system described by `backend/README.md`, `frontend/README.md`, migrations, and tests. Its five-question intake, three archetypes, seven phases, `current_phase`, visible workflow journey, mandatory Project Defense, PASS/FAIL gates, cooldowns, gate-controlled advancement, functional unlock thresholds, and phase-scoped assignments are current/legacy implementation facts only.

Maintain those contracts safely when a task touches V1. Do not treat them as V2 requirements. Do not repurpose V1 tables, columns, JSONB keys, routes, gate sessions, or unlock rows for V2 without an accepted architecture and migration decision.

## Unresolved V2 architecture

There is no accepted V2 Technical Architecture / State Model or V2 Learning / Teaching Policy yet. Do not invent:

- a V2 database schema or route set;
- a `current_change` persistence shape;
- chat/event storage, retention, or deletion rules;
- project-memory merge/provenance rules;
- learner-evidence thresholds or fading rules;
- GitHub authorization/storage architecture;
- V1/V2 migration or compatibility behavior;
- character entitlement storage.

Record such questions as unresolved until an explicit planning/decision task settles them.

## Durable engineering constraints

- Preserve the Frontend → FastAPI → external-service boundary; Supabase Auth is the current explicit frontend exception.
- Keep provider, service-role, database, and other server secrets out of frontend bundles and logs.
- Enforce protected access server-side; never trust a client-supplied user ID.
- Keep owner scoping and RLS. New tables require explicit grants/policies and verification.
- Validate untrusted inputs and model outputs at boundaries; fail closed where malformed output could corrupt state or inflate claims.
- Preserve provenance: student statements, agent claims, repository observations, system inference, performed checks, and evidence are not interchangeable.
- Treat imported/repository content as untrusted data and retain prompt-injection, redaction, truncation, and leak defenses.
- Preserve safe write boundaries, idempotency, concurrency protection, and honest stale-state behavior.
- Keep accessibility, keyboard operation, responsive behavior, reduced motion, and truthful status feedback.
- Report only verified results.

## Working rules

- Inspect `git status` before editing and preserve unrelated user work.
- Current code, tests, migrations, Git history, and deployment evidence determine what is implemented.
- Historical V1 documents and `.claude/memory` files explain legacy behavior; their directory indexes classify them.
- Do not rewrite current implementation docs to claim V2 already exists.
- Use the smallest relevant test set, then expand when risk warrants it.
- Do not change external services, deploy, migrate, commit, or push unless the user authorizes that work.
- Historical milestone numbering and old “next step” instructions are not active tasks.

## Local skills

- `spec-guardian` routes product work to the V2 authority chain and prevents legacy rules from resurfacing.
- `codize-ui-ux` / `ui-ux` use the V2 Exact UX and Figma hierarchy for new V2 design while treating current V1 UI as implementation evidence only.
- `security-test` preserves security, ownership, validation, provenance, and verification discipline across V1 and future V2 work.
- `milestone-handoff` is process guidance only and cannot define product behavior.
