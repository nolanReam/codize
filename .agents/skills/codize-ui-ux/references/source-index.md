# Source Index

Use this file to resolve authority and trace synthesized guidance. The skill is self-contained: do not load raw transcripts for normal BUILD or AUDIT work.

## Active authority

Resolve conflicts using `docs/context/context_authority.md`:

1. Current user instruction and active task scope
2. Repository reality: code, tests, migrations, Git history, and relevant deployed evidence
3. `docs/context/codize_product_operating_brief_v2.md` for stable product direction, shared workflow, trust, and UX
4. `docs/context/codize_master_spec_v2.1.md` only for still-applicable architecture and safety invariants
5. Accepted decisions, especially `docs/decisions/guided_workflow_navigation.md`
6. `CLAUDE.md`, relevant `.claude/memory/` files, repo-scoped skills, and current frontend conventions

`docs/archive/product/codize_product_vision_v3.md` is historical and is not current product authority.

## Codize implementation sources

- **A1** — `docs/context/codize_product_operating_brief_v2.md`
- **A2** — `.claude/memory/frontend-conventions.md`
- **A3** — `.claude/memory/change-map-ui-conventions.md`
- **A4** — `.claude/memory/change-map-review-integration-conventions.md`
- **A5** — `.claude/memory/linked-review-ui-conventions.md` and `.claude/memory/review-verification-integration-conventions.md`
- **A6** — `frontend/app/globals.css`, app shell, shared components, workflow navigation, typed helpers, and representative workflow pages
- **A7** — `docs/decisions/guided_workflow_navigation.md`
- **A8** — `docs/context/codize_master_spec_v2.1.md`, only where the authority file says its architecture or safety invariants still apply

Current code and rendered behavior outrank stale details in implementation memory.

## Pilot evidence

- **P1** — Codize pilot observations synthesized during this skill's research pass: users reported dashboard overload, homework-like text density, unclear first focus, Evidence complexity, strict Defense framing, wide-screen dead space, confused progress models, and lost drafts.
- **P2** — `.claude/memory/pilot-ux-lessons.md`

Pilot observations outrank general design advice, but never override accessibility, product truth, trust, or current repository contracts.

## Research sources

The following videos informed the synthesized reference files. Timestamps preserve attribution; their raw transcript files are intentionally not required or bundled with the skill.

| Code | Source | Useful spans | Applied guidance |
|---|---|---|---|
| **S1** | [3 Strategies for Managing Visual Complexity in Applications and Websites](https://www.youtube.com/watch/4oJ0rAeWIss) | 00:00–04:47 | predictable placement, grouping, hierarchy, progressive disclosure |
| **S2** | [Progressive Disclosure](https://www.youtube.com/watch/qlKWPNgPjmw) | 00:17–04:57 | reveal secondary options at the relevant step; account for interaction cost |
| **S3** | [Visibility of System Status](https://www.youtube.com/watch/cTtc90jCULU) | 00:06–02:08 | timely, useful feedback; show only actionable or reassuring state |
| **S4** | [Visual Design Principles in Action](https://www.youtube.com/watch/YUMdv4yFlQU) | 00:35–05:36 | scale, hierarchy, balance, contrast, Gestalt grouping, objective critique language |
| **S5** | [How to think like a GENIUS UI-UX designer](https://www.youtube.com/watch/HE4rLEQpiXY) | 00:00–05:14 | start from user intent, use familiar structure, design around real content, purposeful motion |
| **S6** | [4 levels of UI-UX design (and BIG mistakes to avoid)](https://www.youtube.com/watch/86PGRyQjdzQ) | 01:15–04:28; 11:12–13:44; 13:50–15:31 | clarity before flash, restrained emphasis, deliberate type/spacing, coherent journeys |
| **S7** | [The Little Details of UI Design](https://www.youtube.com/watch/EjEYTRD-W-M) | 09:09–12:38; 14:18–20:52; 26:49–33:54; 36:02–40:18 | focus states, scan hierarchy, spacing, action hierarchy, fewer borders, alignment |

Supplemental and excluded research dumps were not used. Do not copy transcript passages into product work or expand this skill by committing raw transcripts.

## Conflict examples

- If general advice asks for more visible guidance but pilot evidence says the page feels like homework, keep required instruction visible and disclose secondary help contextually. `[P1, P2 > S1, S2]`
- If a dashboard pattern exposes all modules equally, follow the shared workflow and guided-navigation decision. `[A1, A7 > S1, S5]`
- If a clean label hides uncertainty or self-reported status, preserve the honest qualifier. `[A1, A3–A6 > visual preference]`
- If motion competes with task completion, accessibility, or reduced motion, remove it. `[active authority > S5, S6]`
