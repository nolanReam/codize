# Codize Spec Guardian Skill

## Purpose

Ensure every Codize implementation decision stays aligned with the attached product specification, roadmap, conversation history, and Fable 5 prompting guide.

Use this skill before:

- creating architecture
- changing product logic
- writing system prompts
- changing gate behavior
- adding new features
- modifying roadmap/archetype logic

## Required Source Files

The durable context files live in:

- `docs/context/codize_master_spec_v2.1.pdf`
- `docs/context/codize_roadmap_v2.html`
- `docs/context/conversations.json`
- `docs/context/fable_5_prompting.md`

Read relevant sections before making product decisions.

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

1. Is this explicitly required by the spec?
2. Is this required for the current milestone?
3. Can this be done more simply?

If the answer is no, do not build it.

## Self-Improvement Rule

If a spec interpretation is clarified, update this skill with the specific rule.

Write specific corrections, not vague reminders.