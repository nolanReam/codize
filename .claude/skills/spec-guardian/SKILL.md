# Codize Spec Guardian Skill

## Purpose

Ensure every Codize implementation decision stays aligned with the active product direction, accepted decisions, and still-applicable architecture and safety invariants.

Use this skill before:

- creating architecture
- changing product logic
- writing system prompts
- changing gate behavior
- adding new features
- modifying roadmap/archetype logic

## Required Source Files

Read these before making product, workflow, or major UX decisions:

- `docs/context/context_authority.md`
- `docs/context/codize_product_operating_brief_v2.md`

Use `docs/context/codize_master_spec_v2.1.md` only for still-applicable architecture and safety invariants. Use code, tests, migrations, Git history, and deployment evidence for implementation state. Do not load archived plans, old product visions, model guides, or chat exports unless historical context is specifically required.

## Non-Negotiables

Codize is an educational platform that helps students understand projects they build with AI.

Codize is not:

- a general tutorial platform
- a code generator for students
- a plagiarism detector
- a generic chatbot
- Duolingo for coding
- a cybersecurity/offensive security tool

## Core Product Rules

- The first intake question must be: “What problem do you want to solve, and who does solving it help?”
- Intake has exactly five mandatory questions.
- Codize supports exactly three archetypes:
  1. AI-Powered App
  2. REST API Backend
  3. Full-Stack Web App
- Archetype templates are hardcoded JSON.
- LLMs may personalize language, but must never alter phase structure.
- The Interrogation Gate is mandatory.
- The gate uses a Turn 1 anchor, Turn 2 weakest-criterion probe, and Turn 3 hypothetical.
- Gate evaluation is binary PASS/FAIL at temperature 0.
- Generic textbook answers fail even if technically correct.

## Scope Discipline

Do not add features just because they are interesting.

Before adding anything, ask:

1. Is this consistent with the active operating brief and accepted decisions?
2. Is this required for the current milestone?
3. Can this be done more simply?

If the answer is no, do not build it.

## Self-Improvement Rule

If a spec interpretation is clarified, update this skill with the specific rule.

Write specific corrections, not vague reminders.
