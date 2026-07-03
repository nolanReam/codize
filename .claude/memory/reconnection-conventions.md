# Reconnection conventions (Milestone 11)

The load-bearing decision is the TIMESTAMP SEMANTICS: `profiles.last_login_at`
means "last acknowledged presence in the app", NOT auth login time. It is
initialized by the signup trigger's column `default now()` (so a brand-new
user is `recently_active` by construction and never sees the modal) and is
thereafter written by exactly one code path: `POST /reconnection/acknowledge`
(`reconnection_service.acknowledge`, an upsert on the profiles PK).
`GET /reconnection` is a PURE READ — this is deliberate, per the instructions'
warning about updating the timestamp too early: a state check can never
suppress the modal. Do not add a "touch on login" hook; the frontend contract
(for M13) is GET first on every login, then acknowledge — immediately when
`reconnection_needed` is false, on the "Let's keep building" click when true.
If the frontend ever acknowledges before GETting, the modal silently never
appears — that ordering is the one integration trap.

The GET returns four controlled 200 states, never errors: `new_user` (no
profile row/timestamp — only reachable with fakes; live, the trigger
guarantees a timestamp), `recently_active` (away < 72h), `workspace_not_ready`
(away 72h+ but `phase_service.load_active_project` raises — nothing to
reconnect to yet), and `reconnection` (away 72h+, summary attached). The
threshold check is `now - last_login_at >= 72h` (instructions: "at or after").

The summary is deterministic — NO LLM call — and built from already-client-
visible data only: verbatim `intake_purpose` (spec: shown in large text),
current phase number/title/`core_concept`, incomplete current-phase tasks
(via the public `phase_service.current_phase_view(project)` added in M11),
the newest `gate_history_summary` line (attempt counts only — gate_service
never writes scores into it, see [[gate-conventions]]), earned unlock views
(via the public `unlock_service.unlock_views` added in M11 — safe fields only,
see [[unlock-conventions]]), and a derived `next_action` string. Raw scores,
thresholds, prompts, and keys appear nowhere; the leak tests assert it.

Reconnection only READS project/gate/unlock state and only WRITES
`last_login_at` — it never mutates the roadmap, never advances
`current_phase` (the gate remains the only advancer), and never grants
unlocks. No schema change was needed (the M2 column carried M11); RLS on
profiles (owner select/insert/update) live-verified in the M11 smoke
(12/12, `docs/db/schema.md`). Not built by design: email notifications (spec:
in-app modal only), the "stuck on same phase > 1 week" trigger (spec pins the
implementation to the 72h last_login delta), and the modal UI itself (M13).
