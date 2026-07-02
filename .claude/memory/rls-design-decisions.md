# RLS design: read-only tables and the hidden score column

Two deliberate deviations from plain owner-CRUD policies (Milestone 2):

1. `gate_sessions` and `unlocks` have ONLY owner-select policies. All writes go through the backend service role — students must never author their own verdicts or forge unlocks. Do not "fix" the missing insert/update policies.
2. `gate_sessions.score` is hidden from client roles via column-level grants (`revoke all` then `grant select` listing every column EXCEPT score). Spec: functional-unlock thresholds must not be observable by the student. Consequence: a PostgREST `select=*` on gate_sessions fails for clients — clients must name columns, but the frontend goes through the backend anyway. If a column is ever added to gate_sessions, the grant list in a new migration must be updated deliberately.

Verify with `scripts/verify_rls.sql` (behavioral two-user test simulates PostgREST via `set local role` + `request.jwt.claims`; expected-error sections must run as separate statement batches).
