# Functional unlock conventions (Milestone 10)

The hidden rule is pinned by the spec's resolved decisions: quality score >= 7
(`unlock_service.QUALIFYING_SCORE`, server-only) on two consecutive phases'
PASSED gates. Only the passing attempt's score counts (spec: "no retry
deductions — only the final Turn 3 quality matters"), so earlier failed
attempts neither help nor hurt; a phase never passed contributes nothing, and
phase 1 alone can never qualify. Qualifying at phase N grants roadmap phase
N's `functional_unlock` (`unlock_key = "phase-{N}-functional-unlock"`) — the
template rewards are already the spec's two MVP example types
(skip-configuration and pre-built component), so no reward catalog exists in
code; the roadmap JSONB is the catalog.

Evaluation is RECOMPUTE-THEN-INSERT-MISSING from the full passed-gate history
(`GateSessionRepository.list_passed_sessions`), which makes it idempotent and
self-healing by construction: `gate_service.evaluate_gate` calls it after
every PASS (never FAIL) and swallows `RepositoryError` with a log warning —
the pass is already stored, so an unlock storage error must not 500 the
verdict; the next PASS backfills the missed grant. Do not "fix" that swallow
into a hard failure. The DB backstops races: unique `(project_id, unlock_key)`
plus PostgREST `Prefer: resolution=ignore-duplicates` (+ `on_conflict` param)
makes a duplicate insert return no row (`create_unlock` → None = "not new").
Live-verified against real Supabase in M10 (10/10 smoke checks incl. the
ignore-duplicates behavior and RLS client reads).

Client surface: `GET /unlocks` only — there is deliberately NO
`/unlocks/available` route because every phase view already exposes its
`functional_unlock` description; a catalog route would add nothing. Unlock
views carry exactly {id, unlock_key, project_id, phase, description,
unlocked_at}; the threshold, the consecutive rule, and raw scores never
appear in any response (see [[gate-conventions]] — `gate_sessions.score`
stays revoked from client roles, `unlocks` is owner read-only from M2, no
migration was needed for M10). Unlocks never mutate the roadmap and never
advance `current_phase` — the gate remains the only phase-advancer.

Not yet built (v2 / later milestones, spec Section 4): the return-rate and
vocabulary-growth triggers; only the gate-score trigger is in the MVP.
