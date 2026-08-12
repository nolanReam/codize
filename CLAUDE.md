# CLAUDE.md

Guidance for Claude Code in this repository.

## Authority

Read `docs/context/context_authority.md` first. Then read the repository-local V2 Product Thesis and the relevant Exact UX / Character documents under `docs/context/v2/`.

The Product Thesis is the highest persistent V2 product authority. The authority file routes to sources; it does not override the thesis. Approved Figma controls visual composition only.

Do not read `conversations.json` unless the user explicitly asks for authorized historical research.

## V2 direction and current implementation

Codize V2 is a beginner-first, project-based AI coding mentor organized around **one project, one current change, one useful habit at a time**. Chat is the Build interface; constrained system logic owns state and legal transitions. Codize guides, teaches just in time, preserves student agency and uncertainty, and becomes quieter as the student improves.

The repository still implements V1. Its five-question intake, three archetypes, seven-phase roadmap, `current_phase`, visible Prompt/Import/Change Map/Review/Verification/Evidence/Defense journey, mandatory Defense, PASS/FAIL gate, cooldown, gate advancement, functional unlocks, and phase-scoped assignments are current implementation truth only. Preserve them when maintaining V1; never elevate them into V2 product requirements.

`backend/README.md` and `frontend/README.md` document the current V1 system. Code, tests, migrations, Git history, and verified deployments outrank stale milestone summaries for implementation truth.

## Architecture is unresolved

No accepted V2 Technical Architecture / State Model or V2 Learning / Teaching Policy exists yet. Do not infer V2 storage, APIs, current-change state, chat persistence, learner evidence, GitHub integration, compatibility, privacy/retention, or character-entitlement architecture from V1 structures. Those require explicit decisions.

## Durable constraints

- External-service secrets remain backend-only.
- Authentication and authorization are server-enforced.
- Ownership filters and RLS remain mandatory; verify new boundaries.
- Product data follows the existing Frontend → FastAPI → external-service boundary unless an accepted architecture changes it.
- Validate untrusted input and model output; use fail-closed behavior where integrity or claims are at risk.
- Preserve provenance, uncertainty, write boundaries, idempotency, concurrency safety, staleness, and prompt-injection defenses.
- Never turn student claims, agent output, or suggested checks into verified facts.
- Preserve accessibility, responsive behavior, keyboard support, reduced motion, and honest status/error states.
- Report only what was actually verified.

## Working rules

- Inspect and preserve the working tree; do not reset, clean, stash, or discard unrelated work.
- Historical V1 product docs and memories are non-authoritative for V2. Use them only for current/legacy maintenance or durable technical lessons.
- Do not rewrite implementation documentation to pretend V2 exists.
- Do not create migrations, deployments, commits, pushes, or external-service changes without authorization.
- Old milestone/release instructions are historical unless the current user explicitly activates them.

## Skills

Use the relevant repo skill. `spec-guardian` controls source routing; `ui-ux` and `codize-ui-ux` follow V2 UX authority; `security-test` preserves durable trust/security practices; `milestone-handoff` is process-only and cannot create product requirements.
