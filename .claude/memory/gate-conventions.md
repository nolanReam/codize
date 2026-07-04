# Interrogation Gate conventions (Milestone 9)

Turn sequencing is derived, not stored: `gate_sessions.turns` is
`[{"turn": 1|2|3, "question", "answer"}, …]` and the next expected call falls
out of the last entry's null answer (`[]`→turn1, q1 unanswered→turn2, …,
q3 unanswered→evaluate, `passed` non-null→completed). Every turn writes the
previous answer AND the next question in ONE session update, so an LLM
failure (502) leaves the session exactly where it was and the same call can
be retried — never split those writes.

Anchor is validated twice by design: a deterministic server-side
concrete-element check (`gate_service.anchor_names_concrete_element`, cheap
regexes for code-shaped tokens) runs BEFORE any LLM call, then the Turn 1
prompt composition instructs the model to re-validate and reply
`ANCHOR_REJECTED: <what's missing>` (→ 422) or the bare question text. The
composition tails appended to the prompt files at call time were live-tuned
in M9 — "respond with ONLY the text of the one question" is what stops
Gemini from prefixing validation commentary. Don't remove the tails.

Every user-facing generated question is passed through `clean_gate_question`
(M13C.2B) at the generation boundary — Turn 1 (after the ANCHOR_REJECTED
check), Turn 2, and Turn 3. It is a **deterministic** guard (no extra LLM
call): `sanitize_gate_question` unwraps code fences/quotes, removes an inline
"…here is the Turn 1 question:" hand-off, and drops leading meta/preamble
sentences (`_META_SENTENCE`: "the student…", "valid anchor", rubric/evaluator
language, "Step 2"/"Turn 1", "I will now ask", etc.) — but never a sentence
ending in `?` and never the last remaining sentence, so legitimate questions
(imperatives, anchor-referencing, gate_turn_2's "Good — you covered…"
phrasing) pass through byte-for-byte. If the result is empty or still all-meta,
it raises `GateGenerationError`, which the existing turn flow already treats as
retryable (nothing stored). The evaluator is NOT routed through it — verdicts
stay on `parse_evaluation`. This fixed the flash-lite "valid anchor…" preamble
leak found in the M13C.2 smoke; prompts were deliberately left unchanged (so
the adversarial/prebuild suites did not need re-running). Add a deterministic
unit test to `test_gate_service.py` for any change to the meta patterns.

The evaluator parse is strict AND fail-closed (`parse_evaluation`): verdict ∈
{PASS, FAIL}, non-empty one-sentence reason, score an int 0–10 (bool and
float rejected). Malformed → 502, the turn-3 answer is NOT stored, retry
re-runs the evaluation. Cooldown is derived from `gate_sessions.failed_at`
(no cooldown table — schema decision from M2); `passed_at` was added in M9
(migration `20260703040000`) and granted to authenticated; `score` stays
revoked and never appears in any response body — `gate_history_summary` (on
the client-readable projects table) therefore records attempt counts only,
never scores, so the hidden unlock thresholds stay unobservable. Since M10,
`evaluate_gate` takes an `UnlockRepository` and on PASS calls
`unlock_service.evaluate_unlocks` (RepositoryError swallowed + logged — see
[[unlock-conventions]] via .claude/memory/unlock-conventions.md); the PASS
response gains a `new_unlocks` list.

Since M12, `cooldown_remaining(latest_session)` is public — the evaluation
service reports cooldown state from the same derivation (see
[[evaluation-conventions]]); keep the 30-minute rule single-sourced here.

`current_phase` advances ONLY here, on PASS, by +1, never past the final
phase (a final-phase pass keeps `current_phase` and `GET /gate/current`
reports state "passed"; status stays 'active' — 'completed' is not M9's
decision to make). Live-verified against real Gemini + real Supabase in M9:
one full PASS gate (phase 1→2) and one full FAIL gate (textbook answer
auto-failed, 30-min cooldown enforced live with Retry-After).

Prompt-hole lessons from the live adversarial runs (all in
`docs/prebuild/adversarial_tests.md`): flash-lite counted generic role
descriptions ("the owner column") as implementation-specific → Condition 3
now demands the student's verbatim named elements; it also handed out an
answer-revealing hint for "idk" answers → gate_turn_2.md now forbids the
hint outside genuine wrong-claim cases. Re-run
`scripts/live_adversarial_tests.py` after ANY gate-prompt edit, and keep
`scripts/validate_prebuild_artifacts.py` passing (244 checks) — both
validators must stay in sync with prompt changes.
