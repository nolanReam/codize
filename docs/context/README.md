# Codize context directory

This directory contains the repository's product-authority router and canonical context. Start with [context_authority.md](context_authority.md).

## Canonical V2 product documents

The canonical repository-local sources live in `docs/context/v2/`:

1. [Codize V2 Product Thesis](v2/codize_v2_product_thesis.md) — highest product authority.
2. [Codize V2 Exact UX Specification](v2/codize_v2_exact_ux_specification.md) — behavior and interaction authority, subordinate to the thesis.
3. [Codize V2 Character System Blueprint](v2/codize_v2_character_system_blueprint.md) — character/customization authority only.

The approved V2 Figma is visual-composition authority only. See the router for the complete hierarchy.

## Not yet defined

The repository does not yet have an accepted:

- V2 Technical Architecture / State Model;
- V2 Learning / Teaching Policy.

Do not use V1 implementation structures as substitutes. In particular, do not assume that phases, gates, cooldowns, workflow JSONB, assignments, Defense, or functional unlocks define V2 architecture.

## Historical V1 context still stored here

- `codize_product_operating_brief_v2.md` is a superseded V1 product-direction record.
- `codize_master_spec_v2.1.md` is a historical V1 product specification with reusable technical/security lessons.

Their headers classify their current role. Neither governs V2 product behavior.

## Where other material belongs

- `docs/decisions/` — accepted V2 decisions or explicitly labeled historical V1 decisions.
- `docs/learning/` — future accepted V2 teaching policy or labeled historical learning references.
- `docs/auth.md`, `docs/db/`, `docs/testing/`, `docs/prebuild/`, and `docs/deployment/` — current implementation evidence or durable technical references; not V2 product authority.
- `docs/releases/`, `docs/pilot/`, and completed/deferred plans — historical snapshots until replaced for V2.
- `docs/archive/` — non-authoritative history.
- `.claude/memory/` — implementation records and durable lessons, classified by its README; never product authority.

## Context-file rule

Add a new active context file only when its authority and conflict behavior are explicit. Avoid duplicate summaries, milestone logs, transcripts, and speculative architecture in this directory.

Do not read `conversations.json` by default.
