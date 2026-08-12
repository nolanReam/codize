# Repository instruction authority

**Status:** Standing repository guidance. No release or implementation milestone is active in this file.

The prior M18H.1 production-release instructions are superseded and are not an active task.

For every task:

1. Follow the current user instruction for task scope, permissions, deliverables, and stop conditions.
2. Use `docs/context/context_authority.md` to route persistent product and implementation questions.
3. Treat `docs/context/v2/codize_v2_product_thesis.md` as the highest V2 product authority.
4. Use the Exact UX Specification for behavior and the Character System Blueprint only for its subsystem.
5. Use code, tests, migrations, Git history, and verified deployment evidence for what is implemented now.
6. Treat old V1 product documents and mechanics as historical/current-implementation context, never future V2 requirements.
7. Preserve durable security, RLS/ownership, validation, provenance, secret-handling, prompt-injection, accessibility, and engineering-process guidance.
8. Do not invent unresolved V2 architecture.

The repository currently implements V1. Documentation must not claim that V2 architecture, current-change persistence, Build chat, GitHub integration, learner modeling, or characters already exist.

Do not read `conversations.json` unless the user explicitly requests and authorizes it.
