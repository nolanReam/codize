# Beginner Entry and Adaptive Guidance Conventions

> [!WARNING]
> **Current/legacy V1 product or lifecycle record.** Use this file only to understand or maintain the implemented V1 subsystem. It is not V2 product or architecture authority.

M17 adds orientation to the existing Codize workflow; it is not a new product
mode. Project Home remains the anchor, the five intake questions remain the
project-definition contract, and M16N remains the sole navigation lifecycle.

## Entry profile

The authenticated `GET/PUT /intake/entry-profile` seam stores one reserved
top-level `_entry_profile` object in the current project's existing
`workflow_artifacts` JSONB. When no project row exists yet, the PUT uses the
same ProjectRepository creation seam as intake Q1. It must never create a
beginner/recovery project alongside the real project.

Clients write only `current_situation`, `coding_confidence`, and conditional
`ai_changed_files`. The backend always re-derives completion, recommended
start, guidance depth, and recovery emphasis. The mapping is deterministic:

- starting fresh → Prompt Builder;
- already building + AI changed files or unsure → Bring Back What Changed;
- already building + no changes yet → Prompt Builder;
- stuck in the 80% Trap → Quick Start, whose action is Bring Back What Changed.

New-to-code gets more explanation, knows-basics gets standard, and comfortable
gets minimal. These change explanation depth only—never requirements, truth,
evaluation, or saved progress. Preference updates patch only the reserved key.

## Shared guidance and navigation

`AdaptiveStepGuide` is the only adaptive explanation component. Its content
comes from typed static `lib/workflowGuidance.ts` entries for Prompt, Import,
Change Map, Review, Verification, Evidence, Defense, and Report. Do not call an
LLM for guidance, examples, recommendations, entry, or classification. The
disclosure preference may persist only as a boolean scoped by authenticated
user, active-project placeholder, and stage; never store project content.

Entry recommendations are initial orientation, not lifecycle authority. Apply
them only on an untouched first phase. Saved workflow artifacts, staleness,
gate state, and the established M16N dependency priority win. Import-first
recovery continues to Change Map and leaves Prompt for the next change instead
of forcing duplicate retrospective work.

## Compatibility and truth

Missing or malformed legacy profiles mean standard collapsed guidance and the
existing Project Home behavior. Returning students do not repeat entry unless
they explicitly update preferences. Quick Start is a five-step explanation of
the existing Import → Change Map → Review → Verification → continue flow; it
must not add inputs, artifacts, completion flags, or alternate routes. Nothing
in M17 changes providers, prompts, classification, evaluator behavior,
PASS/FAIL, hidden scores/thresholds, retries, cooldowns, Report truth, or the
database schema.
