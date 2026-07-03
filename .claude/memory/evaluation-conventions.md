# Evaluation conventions (Milestone 12)

The load-bearing decision: the evaluation is DETERMINISTIC and COMPUTED ON
READ — no LLM call, no persistence, no schema change, one route
(`GET /evaluation`). The spec defines no student-facing evaluation snapshot,
fields, or routes (its "Evaluation" language is the M9 gate evaluator), and
its "What Gets Tracked" section is explicit that process metrics "are not
shown to the student as numbers or scores" — so there is nothing to store and
nothing an LLM could add. Do not add an evaluation table, an LLM-worded
summary, or numeric progress scores later without a spec change.

Readiness states (every one a controlled 200, never an error), decided in the
same order as `phase_service.load_active_project`'s eligibility conditions:
`not_started` (no project row) → `intake_needed` → `roadmap_needed` → then,
on an active project, from the current phase's newest gate session:
`complete` (latest passed=True — only reachable on the final phase, since any
earlier pass advances current_phase), `gate_ready` when a session is
mid-flight (passed=None → next_action says RESUME, decided by an explicit
flag, not by task state — a mid-flight gate can coexist with all tasks done),
`cooldown` (via `gate_service.cooldown_remaining`, made public in M12 so the
30-minute rule stays single-sourced), `gate_ready` again when all tasks are
checked off, else `in_progress`. `completed_phases` is derived
(current_phase − 1; total when complete) because gates pass strictly in
order, one at a time — no extra query.

Safe content sources only (all already client-visible): the phase view via
`phase_service.current_phase_view` + the public `phase_service.incomplete_tasks`
(moved there from reconnection's private helper in M12), unlock views via
`unlock_service.unlock_views`, and `recent_gate` = {outcome, summary} where
summary is the newest `gate_history_summary` line for passes (attempt counts
only by construction) or the evaluator's one-sentence `reason` for fails
(already shown at evaluate time and in GET /gate/current). Raw scores, the
unlock threshold/rule, prompt names/bodies, and keys appear nowhere — leak
tests assert it at service and route level.

Evaluation is a PURE READ by construction: it never mutates
roadmap/task_progress/gate_sessions/unlocks, never advances phases, never
grants unlocks, and cannot touch reconnection's `last_login_at` because it
takes no ProfileRepository at all. It deliberately does NOT report
reconnection state — that has its own route and ordering contract (see
[[reconnection-conventions]]); duplicating it here would invite the
acknowledge-before-GET trap. Reconnection's simpler `_next_action` predates
the evaluation's gate-aware one; they word things differently on purpose
(reconnection doesn't read gate sessions).

Live-verified in M12 (12/12 smoke, `docs/db/schema.md`): lifecycle state
walk, live task tick, consecutive-quality unlock surfaced safely, cooldown
after a FAIL, leak-free JSON, before/after project-row equality (pure read),
per-user isolation.
