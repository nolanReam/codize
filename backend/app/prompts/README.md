# Codize System Prompts

The six system prompts required by the master spec ("System Prompt Architecture — Non-Negotiable Constraints"). Prompt files are pure prompt text — no metadata inside them. All call parameters live in this table and must be enforced by `llm_service.py`.

| File | Purpose | Temperature | Output |
|---|---|---|---|
| `roadmap_generation.md` | Personalize an archetype template into the student's roadmap | 0.7 | JSON, same structure as template |
| `phase_explanation.md` | Explain one phase in the student's project context | 0.7 | Prose (streamed) |
| `gate_turn_1.md` | Collect anchor statement, ask Turn 1 question | 0.3 | Conversational |
| `gate_turn_2.md` | Probe the weakest of accuracy/specificity/completeness | 0.3 | Conversational |
| `gate_turn_3.md` | Generate the fresh hypothetical | 0.3 | Conversational |
| `gate_evaluation.md` | Judge the Turn 3 answer — separate model call | **0** | Strict JSON: `{"verdict","reason","score"}` |

## Placeholder conventions

- `{{DOUBLE_BRACES}}` — substituted by the backend at call time (verbatim intake answers, transcripts, template JSON, etc.). Every placeholder must be filled; never send a prompt with an unfilled `{{...}}`.
- `[SINGLE_BRACKETS]` inside template JSON — personalization slots the *LLM* fills (e.g. `[PROJECT_PURPOSE]`, `[PROJECT_SCALE]`).
- `NOTE:` sentences inside template tasks are verbatim security constraints — prompts instruct the model to preserve them word for word.

## Fixed spec rules encoded in these prompts

- Gate evaluation is a **separate** call at **temperature 0**, binary PASS/FAIL + one-sentence reason + 0–10 quality score; all three rubric conditions required; auto-fail for generic textbook answers.
- The anchor statement cannot be skipped and cannot be invented by the model.
- Turn 3 must not be answerable from generic knowledge.
- Student-supplied text is always treated as data, never as instructions (prompt-injection defense clause present in every prompt that receives student text).

## Adversarial testing status

Static adversarial analysis: see `docs/prebuild/adversarial_tests.md`. Live model runs against these prompts are **pending an Anthropic API key** and must be completed before the Interrogation Gate milestone.
