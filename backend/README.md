# Codize backend (FastAPI)

Async FastAPI service. Architecture rule: **Frontend → this backend → external
services (Supabase, LLM providers)** — the frontend never calls external
services directly except Supabase Auth. Route handlers stay thin; product logic lives in
`app/services/` (from Milestone 5 on).

## Layout

```
app/
├── main.py        app factory + CORS + error handlers
├── core/
│   ├── config.py    centralized settings (SecretStr for server-only values)
│   ├── errors.py    consistent JSON error shape, no internal detail leaks
│   └── security.py  Supabase JWT verification (JWKS / ES256)
├── deps/auth.py   require_user dependency → 401 on missing/invalid token
├── routers/       thin route handlers (health; archetypes — auth-required, read-only;
│                  intake — auth-required five-question flow, M6;
│                  roadmap — auth-required generation + read, M7;
│                  phases — auth-required phase workspace, M8;
│                  gate — auth-required Interrogation Gate, M9;
│                  unlocks — auth-required earned-unlock listing, M10;
│                  reconnection — auth-required 72h reconnection state, M11;
│                  evaluation — auth-required progress evaluation, M12;
│                  workflow — auth-required workflow artifact store, M13B)
├── services/      product logic (template_service.py: archetype template engine, M5;
│                  intake_service.py + project_repository.py: intake engine, M6
│                  — project_repository.py also holds the gate_sessions
│                  repository since M9;
│                  llm_service.py + roadmap_service.py: provider-agnostic LLM
│                  layer and roadmap generation with fail-closed validation, M7;
│                  phase_service.py: phase workspace over the stored roadmap, M8;
│                  gate_service.py: 3-turn Interrogation Gate + evaluator, M9;
│                  unlock_service.py: hidden-threshold functional unlocks, M10;
│                  reconnection_service.py: Yeager reconnection engine, M11;
│                  evaluation_service.py: deterministic progress evaluation, M12;
│                  workflow_service.py: workflow artifact store, M13B;
│                  change_map_service.py: reviewed Change Map lifecycle, M15C;
│                  review_service.py: confirmed-map Review integration, M16A.1;
│                  verification_service.py: Review-linked suggestions, M16B.1)
├── schemas/       request/response models (intake.py, phases.py, gate.py, workflow.py)
├── templates/     the three archetype JSON templates (Milestone 1)
└── prompts/       the six system prompts (Milestone 1)
tests/             pytest suite
```

## Setup & run

From `backend/`:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # (Windows; use .venv/bin/pip elsewhere)
.venv\Scripts\uvicorn app.main:app --env-file ../.env --reload
```

Configuration comes from environment variables or a `.env` file. The real
secrets live in the **repo-root** `.env` (see the repo-root `.env.example` for
the contract). Note `Settings` reads `env_file=".env"` **relative to the current
working directory**, so running uvicorn from `backend/` will NOT pick up the
repo-root `.env` on its own — pass `--env-file ../.env` (as above) so uvicorn
loads it into the process environment. (Alternatively set the vars in your shell
or host environment, or place a `.env` in `backend/`.) Without them the backend
runs in no-key mode: the LLM falls back to the deterministic stub and Supabase
calls are unconfigured. Never commit a real `.env`; server-only values
(`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`) exist only
in the backend environment.

## LLM providers (M7)

All LLM calls go through `services/llm_service.py`. Provider order: Gemini
primary (`GEMINI_API_KEY`, `GEMINI_MODEL`), OpenRouter fallback
(`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`), deterministic stub when no live key
is configured (tests and local no-key mode only — never a silent fallback for a
failing live provider). `LLM_PROVIDER` names the primary. Anthropic is
intentionally not supported. Whatever the provider, a generated roadmap is
validated against the source archetype template and discarded on any
structural drift.

## Phase workspace (M8)

`services/phase_service.py` serves phases straight from the stored roadmap
JSONB (the personalized content generated in M7) — no LLM call; the
`phase_explanation.md` prose call is deliberately not wired up yet. Eligibility
is intake complete + archetype + roadmap + status `active`. Task completion is
tracked per phase in the separate `projects.task_progress` column as
`{"<phase>": ["ai-1", "human-2", …]}` (1-based index into the phase's task
lists), so marking tasks complete can never mutate the fixed roadmap
structure. `current_phase` is advanced by the Interrogation Gate (M9), never
by ticking tasks. Routes: `GET /phases`, `GET /phases/current`,
`GET /phases/{n}`, `PATCH /phases/{n}/tasks/{task_id}` (body
`{"completed": bool}`); workspace not ready → 409, unknown phase/task → 404.

## Interrogation Gate (M9)

`services/gate_service.py` runs the spec's 3-turn gate for the student's
current phase. Flow: `POST /gate/start` (eligibility: active project + roadmap
+ current phase; 30-minute cooldown after a failed attempt, derived from
`gate_sessions.failed_at`) → `POST /gate/{id}/turn1` (body
`{"anchor_statement"}`; anchor validation is two-tier since M13E.2 — an
anchor containing a code-shaped identifier ("strong": backticks, snake_case,
`tasks.user_id`, `app/models.py`, "the variable is called likes_score") is
validated server-side and the model is told not to re-reject it (a model
rejection anyway becomes a retryable 502, never a 422), while an anchor that
only names an element type ("the users table", "weak") keeps the M9 model
re-validation; anchors with no concrete element at all are rejected
deterministically with example-bearing copy — the gate never starts without
an anchor) → `POST /gate/{id}/turn2` and `/turn3` (body `{"answer"}`;
each stores the previous answer and returns the next question in one write, so
LLM failures are retryable with nothing lost) → `POST /gate/{id}/evaluate`
(separate temperature-0 call; strict fail-closed JSON parse). Turns run at
temperature 0.3, prompts from `app/prompts/gate_turn_*.md` /
`gate_evaluation.md`. Every generated question passes through the
deterministic cleanliness guard (`clean_gate_question`, M13C.2B, hardened in
M13E.2): markdown/label lines, inline hand-offs ("Let's craft the question:
…"), and leading meta/reasoning sentences ("Therefore, it is a valid anchor.
Now I need to formulate…") are stripped, and output still carrying internal
vocabulary (rubric/evaluator/gate-target language) is rejected as a retryable
502 — raw model output never reaches the client. On PASS: `passed_at` set, `projects.current_phase`
advances (never past the final phase), `gate_history_summary` appended. On
FAIL: `failed_at` set, cooldown starts, no advancement. `GET /gate/current`
reports the current phase's gate state (not started / in progress with
transcript / cooldown with remaining seconds / passed). The evaluator's 0–10
quality score is stored for the hidden unlock thresholds (consumed server-side
by M10's unlock service) and never appears in any response; the DB
additionally revokes the column from client roles.
Errors: not ready / in progress / already passed / out of order / cooldown →
409 (cooldown adds Retry-After), unknown session → 404, invalid anchor → 422,
LLM failure or malformed verdict → 502 with nothing stored.
Since M14B the three turn questions are **grounded in the student's recorded
workflow**: each turn call builds the M14A context pack and appends a
delimited artifact-context block (untrusted-data rules + per-turn grounding
hints) to the composed prompt — the prompt `.md` files are unchanged, and
the **evaluator prompt carries no artifact context** (artifacts guide
questions, never PASS/FAIL). Generated questions are held, after the M13E.2
sanitizer, to deterministic grounding validation
(`services/grounding_service.py`): every code-shaped identifier must be
supported by the pack, the anchor, or prior answers; proof-claims about
self-reported evidence/verification, accusatory framing, and describing a
skipped/failed/n-a check as "passed" are rejected. A rejection triggers
exactly one corrective regeneration, then the existing retryable 502 with
nothing stored. Derived grounding metadata ({source_ids, grounding_terms})
is stored inside the turns JSONB and never reaches the client (the
transcript view whitelists turn/question/answer). Adversarial matrix:
`docs/testing/m14b_grounded_defense_adversarial.md`.
Since M14C, `GET /gate/context-summary` exposes a **metadata-only** view of
the same pack for the current phase (`defense_context_service.
build_context_summary` → `summarize_defense_context`): which sources exist,
which are missing (optional — never an error), per-source truncation flags,
and human display labels (`SUMMARY_LABELS`) — never artifact content, intake
answers, rendered context, or grounding terms. Pure read, no LLM call, no DB
write; ownership rides the same authenticated-identity path (another user
gets their own empty workspace → 409, never the owner's data). Workspace not
ready → 409, corrupt phase → 404.

## Functional unlocks (M10)

`services/unlock_service.py` implements the spec's variable-reward mechanic:
after every gate PASS (never a FAIL), the gate flow calls the unlock
evaluation, which recomputes earned unlocks from the project's passed-gate
history — the hidden rule is a quality score at the qualifying threshold on
two consecutive phases' passed gates (spec: ≥7; only the passing attempt's
score counts). Qualifying at phase N grants roadmap phase N's
`functional_unlock` reward (template content that skips configuration work or
provides a pre-built component). Grants are idempotent (recompute + the DB's
unique `(project_id, unlock_key)` with PostgREST ignore-duplicates) and
self-healing — an unlock storage error never fails the PASS response; the
next PASS backfills. Unlocks never mutate the roadmap and never advance
phases. Routes: `GET /unlocks` lists what the user earned on their current
project (safe fields only: id, unlock_key, phase, description, unlocked_at,
project_id); a PASS's `new_unlocks` appears in the evaluate response. The
threshold, the rule, and raw scores are server-only and appear in no response
(the `unlocks` table itself is owner read-only with client writes revoked).

## Reconnection (M11)

`services/reconnection_service.py` implements the spec's Yeager reconnection
mechanic server-side (the modal itself is frontend work, M13). Timestamp
semantics: `profiles.last_login_at` means "last acknowledged presence" — it is
initialized by the signup trigger's `default now()` (so a brand-new user never
sees the modal) and thereafter written ONLY by
`POST /reconnection/acknowledge`. `GET /reconnection` is a pure read that
returns one of four controlled states: `new_user` (no profile/timestamp),
`recently_active` (away < 72h), `workspace_not_ready` (away 72h+ but no
active project/roadmap yet), or `reconnection` (away 72h+) with a safe,
deterministic summary — the verbatim intake purpose (spec requirement),
current phase number/title/concept reminder, the incomplete current-phase
tasks, the newest gate-history line (attempt counts only — never scores),
earned unlock views, and a recommended next action. No LLM call. Frontend
contract: GET first on every login, then acknowledge — immediately when
`reconnection_needed` is false, on the "Let's keep building" click when true
(acknowledging before the GET would suppress the modal). Reconnection never
mutates the roadmap, never advances phases, never grants unlocks, and its
responses carry no scores, thresholds, prompts, or server-only keys.

## Evaluation (M12)

`services/evaluation_service.py` produces a student-facing progress
evaluation for the caller's current project: `GET /evaluation` returns one
controlled 200 state — `not_started`, `intake_needed`, `roadmap_needed`,
`in_progress`, `gate_ready` (all tasks checked off, or a gate session
mid-flight), `cooldown` (with `cooldown_seconds_remaining`), or `complete`
(final phase's gate passed) — never an error. The evaluation is deterministic
and computed on read: no LLM call, no persistence, no schema change (the spec
defines no evaluation snapshot, and its tracking section forbids showing
process metrics as numbers or scores). Content is derived only from
client-visible state via the shared safe-view seams: the current phase view
(`phase_service.current_phase_view` / `incomplete_tasks`), phase/task counts,
the newest `gate_history_summary` line or the evaluator's one-sentence reason
as a `recent_gate` label (never a score), earned unlock views
(`unlock_service.unlock_views`), and a recommended `next_action`. Cooldown
state reuses the gate's own derivation (`gate_service.cooldown_remaining`).
Evaluation is a pure read — it never mutates the roadmap, task progress,
gates, or unlocks, never advances phases, and never touches reconnection's
`last_login_at`.

## Workflow artifacts (M13B; implementation import M15A; Change Map M15C; linked Review M16A.1; linked Verification M16B.1)

`services/workflow_service.py` stores the student-authored v3 Build Loop
sections — `prompt_builder`, `review_board`, `evidence`, `verification`, and
since M15A `implementation_import` — phase-scoped, in the
`projects.workflow_artifacts` JSONB column (task_progress precedent: outside
the roadmap jsonb, so storing artifacts can never mutate the fixed
structure). Storage only: no LLM call, no gate involvement, no report
generation — the M13C frontend assembles the Project Defense Report
client-side from this route plus the existing ones. Routes:
`GET /workflow/{phase}` (all five sections, `null` when unset) and
`PUT /workflow/{phase}/{section}` (idempotent full-section replace; payloads
validated fail-closed by `schemas/workflow.py` — extra fields forbidden,
strings/lists capped, URL and commit-hash evidence format-checked, free text
that looks like an API key rejected, 30 KB total-size cap; the server stamps
`saved_at`). Eligibility mirrors the phase workspace (active project +
roadmap; unknown phase/section → 404, workspace not ready → 409, invalid
payload → 422). A write touches exactly one column; unknown keys in stored
data are dropped on read.

### Database write boundary (M16S.1)

FastAPI is the only product-data writer. The browser uses Supabase directly
for Auth, then sends its access token to these routes; it never writes
`projects` through the Data API. The forward migration
`20260714064425_harden_workflow_artifact_write_boundary.sql` makes that trust
boundary effective in Postgres: `authenticated` retains owner-scoped project
reads (`SELECT` plus RLS) but has no project insert/update/upsert/delete
privilege. The trusted backend credential retains its existing access, and
every `SupabaseProjectRepository` read/write remains filtered by the
JWT-derived `user_id` because that credential bypasses RLS.

This database rule protects the complete `workflow_artifacts` JSONB value,
including Prompt Builder, Implementation Import, Change Map, linked Review,
linked Verification, Evidence, server timestamps, ids, source bindings, and
lifecycle state. FastAPI validation remains the semantic layer; database
grants prevent clients from bypassing it. Verify a deployed migration with
`scripts/verify_workflow_artifact_write_boundary.sql` and
`scripts/verify_workflow_artifact_write_boundary.py`.

### Implementation import (M15A — "Bring Back What AI Changed")

`implementation_import` is the student's own record of what an external AI
tool produced: a pasted AI response, git diff, code snippet, changed-file
list, and/or a plain-language summary. Schema
(`ImplementationImportArtifact`): required `source_kind` enum (`ai_response`
/ `git_diff` / `changed_files` / `code_snippet` / `manual_summary` /
`other`), optional `content` (≤ 40,000 chars), `changed_files` (≤ 100
entries × 300 chars, deduplicated, empties dropped), `student_summary`
(≤ 4,000), `tool_name` (≤ 100) — at least one of content / changed_files /
student_summary must be present. Normalization is edges-only: internal
indentation, line breaks, diff markers, and Markdown are preserved verbatim
(leading blank lines and trailing whitespace trimmed; first-line indentation
kept). The section's serialized-body belt is 100 KB (`MAX_IMPORT_SECTION_CHARS`;
the other sections keep 30 KB) — the per-field caps stay authoritative and
nothing is ever silently truncated. The same secret-marker guard applies
(`sb_secret_` / `sk-or-` / `AIza` / PEM); a rejected save persists nothing
and never echoes the value. **Untrusted-data boundary:** imports are
student-provided, self-reported material — never verified, never proof of
correctness, never an instruction source. M15A stores them inertly (no LLM,
no extraction, no correctness analysis) and raw imports are deliberately NOT
part of the M14 Defense Context Pack (its source manifest is fixed; a future
M15C/M16 may add a *normalized* Change Map via the spec-guardian process).
Future seams: M15B frontend uses the existing routes; M15C reads through
`workflow_service.get_implementation_import(project, phase_number)` →
`StoredImplementationImport | None` (validated + `saved_at`; corrupt data
returns `None`, never raw JSON).

### Change Map (M15C.1 — provenance-aware extraction foundation)

`services/change_map_service.py` (+ `schemas/change_map.py` +
`prompts/change_map_extraction.md`) converts a saved implementation import
into an AI-generated, editable DRAFT of what *appears* to have changed —
never a correctness claim. It persists as a SIBLING key beside the five
student sections (`workflow_artifacts[phase]["change_map"]`, no migration)
but is NOT a workflow section: the generic section PUT 404s on it,
`stored_sections` filters it out (so it can never reach the M14 defense
context — manifest still fixed at 8 sources), and `GET /workflow/{phase}`
returns it top-level with a server-computed `stale` flag.

Generation (`POST /workflow/{phase}/change-map/generate`, the only LLM path
here, temperature 0): the typed M15A import is redacted field-by-field with
the M14A `redact_secrets` patterns BEFORE deterministic truncation (summary
4k / changed-files 12k whole entries / content 20k head+tail, visible
`[TRUNCATED…]` markers, cuts never split the redaction marker — the stored
import is never mutated), rendered inside explicit untrusted-data delimiters,
then the output is parsed fail-closed (`GeneratedChangeMap`: ≤ 40 items,
≤ 600-char draft text, ≤ 5 refs × 300-char excerpts, extra fields forbidden)
and held to deterministic validation the model cannot talk its way past:
every source reference must target a field the import contains with a
verbatim excerpt of the sanitized view (whitespace-only excerpts rejected),
file paths must exist in the material, and every code-shaped identifier in
draft text must be supported (reusing `grounding_service`
term extraction — M14B behavior untouched). One corrective regeneration
(validation categories only — never raw output or import material), then the
retryable 502 with nothing stored. The server assigns everything the model
must not control: `item_id` (deterministic hash, no timestamps),
`origin=ai_inferred`, `student_decision=pending_review`, `generated_at`,
`status=draft`, `source_import_saved_at` (binds the map to the exact import
version — replacing the import makes the map stale, derived on read, never
client-controlled).

Lifecycle (no LLM): `PUT /workflow/{phase}/change-map` edits ONLY
student-owned state (decisions / edited text / notes on AI items by id;
`student_added_items` as a full replacement set with `origin=student_added`
and required student text) — server-owned provenance is not accepted by the
schema and any successful update returns the map to draft.
`POST /workflow/{phase}/change-map/confirm` blocks on pending items and
staleness, allows rejected/uncertain/needs-inspection honestly, and stamps
`confirmed_at` server-side; confirmation means "reviewed", never "correct".
An existing map (draft or confirmed) is only replaced with an explicit
`{"replace_existing": true}`. The M16A.1 Review integration consumes the
typed `workflow_service.get_change_map` →
`change_map_service.confirmed_items` / `unresolved_items` seams only
(deterministic effective text: confirmed→draft_text,
edited/student_added→student_text, rejected→excluded). Adversarial matrix:
`docs/testing/m15c_change_map_adversarial.md`.

### Confirmed Change Map → Review (M16A.1)

`services/review_service.py` deterministically initializes the existing
`review_board` section from an owned phase's current, confirmed, non-stale
Change Map. The distinction is permanent: Change Map confirmation records
that a description of the apparent change was reviewed; Review records the
student's separate implementation judgment. Initialization never decides for
the student and makes no Gemini, OpenRouter, or stub-provider call.

`POST /workflow/{phase}/review/from-change-map` accepts no body or only
`{"replace_existing": bool}`. The server filters, in fixed priority order,
`behavior_change`, `implementation_decision`, `out_of_scope_change`,
`security_sensitive_area`, `unresolved_risk`, and `unverified_behavior`;
`changed_file` and `question_to_understand` remain context. Rejected/pending
items never become targets. Uncertain/needs-inspection items become cautious
targets with `source_resolution=unresolved`, never confirmed facts.

Each target stores a deterministic `rv-...` id, the Change Map item id,
category/origin/student-decision snapshot, bounded effective-text snapshot,
and an initial student decision of `pending`. The Review binds to the exact
Change Map `generated_at` + `confirmed_at`; `GET /workflow/{phase}` exposes
the linked artifact through `sections.review_board` with server-computed
`initialized_from_change_map=true` and `stale`. Staleness covers a missing,
draft, regenerated, reconfirmed, or import-stale Change Map and is never
persisted or client-controlled. Manual/legacy Review artifacts keep their
original read/write shape.

The existing `PUT /workflow/{phase}/review_board` remains the only update
route. Its old payload is still accepted; linked Reviews additionally accept
`target_updates` containing only server-issued target id + student-owned
`review_decision` (`pending`/`keep`/`revise`/`remove`/
`needs_verification`/`uncertain`), rationale, and revision. Source ids,
snapshots, provenance, timestamps, and stale state are absent from the write
schema and copied from storage. `revise` requires rationale or a proposed
revision. Existing Review work returns 409 during initialization unless the
caller deliberately sends `replace_existing=true`; replacement resets the
single active linked draft and creates no history. Same JSONB column, same
owner-scoped project repository, same phase validation, **no migration**.

Future seams: M16A.2 uses the POST above, the existing workflow GET, and
Review PUT `target_updates`. M16B uses
`review_service.needs_verification_targets(review)`; M16A.1 creates no
Verification or Evidence records and does not feed linked target data into
Defense Context, Project Defense, the evaluator, or the report.

### Review decisions → Verification suggestions (M16B.1)

`services/verification_service.py` converts only the current saved linked
Review targets whose exact decision is `needs_verification` into deterministic,
category-aware proposed checks. A Review decision ("I need to test this") is
not a Verification result ("I performed this check"). Initialization makes no
Gemini, OpenRouter, or stub-provider call, executes no code, and creates no
Evidence. Suggestions embed the bounded effective Review text in one of six
explicit templates; they never invent project identifiers or initialize a
completed result.

`POST /workflow/{phase}/verification/from-review` is explicit only and accepts
no body or `{"replace_existing": bool}`. It requires an owned active project,
a real roadmap phase, and a saved, complete, current linked Review. Source
targets come only from `review_service.needs_verification_targets(review)`;
the client cannot submit ids, categories, source snapshots, suggestions,
bindings, timestamps, or results. A completed Review with no needs-testing
decisions succeeds with a valid linked artifact containing zero targets—it is
not automatically complete. Any existing manual or linked Verification blocks
with 409 unless deliberate replacement is requested; replacement rebuilds one
active artifact and creates no merge/history.

Each linked target stores a deterministic timestamp-free `vt-...` id derived
from its server-issued Review target id, the Review/Change Map ids, category,
bounded source text and optional rationale snapshots, deterministic suggestion,
and nullable `student_check`, `result`, and `result_notes`. Null result is the
unperformed state. The only completed result vocabulary remains the legacy
`pass`/`fail`/`skipped`/`not_applicable`; M16B.1 initializes none of them.
The source binding records the Change Map generation/confirmation timestamps,
the saved Review timestamp, and a SHA-256 fingerprint of ordered server target
identity/decisions (never raw source text as the version key).

`GET /workflow/{phase}` remains the only read path. A linked
`sections.verification` adds `initialized_from_review=true`, its binding and
targets, plus server-computed `stale`. It becomes stale when Review is missing,
corrupt, stale, rebuilt, incomplete, re-saved, reidentified, changes relevant
decisions/target membership, or changes its Change Map binding. Stale work stays
readable and is never rewritten. Manual/legacy artifacts retain their exact
M13B read shape.

The existing `PUT /workflow/{phase}/verification` keeps accepting the current
frontend's `checks + explanation` payload. For a linked artifact it preserves
all server-owned fields and additionally accepts `target_updates` containing
only a server-issued Verification target id plus student-owned check wording,
result, and notes. Forged provenance/snapshots/suggestions/ids/bindings/
timestamps/stale state are rejected with 422. Typed helpers expose pending,
performed (pass/fail), failed, unresolved (anything not pass), and the future
M16B.3 Evidence handoff view; no helper creates Evidence. Same JSONB column,
owner-filtered repository, phase validation, and **no migration**.

Exact M16B.2 frontend seam: explicitly call the POST above after a saved current
Review, consume linked metadata from the existing workflow GET, and save only
`target_updates` through the existing Verification PUT. Never infer checks in
the browser or treat a suggestion as performed. Exact future M16B.3 seam:
`verification_service.evidence_handoff_targets(stored_verification)` returns
ids, effective check wording, recorded result/notes, and category; it creates
no Evidence record and skipped/N/A never count as pass.

## Defense context pack (M14A)

`services/defense_context_service.py` (+ `schemas/defense_context.py`) builds
the deterministic, ownership-safe context pack the artifact-aware Project
Defense grounds its questions in (**consumed by the live gate since M14B**;
still no API route — nothing raw is exposed to clients). The seam is
`build_defense_context(project_repo, user_id, phase_number)` →
`DefenseContextPack`, then `render_defense_context(pack)` → the deterministic
string (untrusted-data header + sorted-key JSON). Properties: read-only
(ProjectRepository only — gates/unlocks/profiles unreachable by
construction, no LLM import, no DB write); ownership through the shared
`phase_service.load_active_project` path with the existing
WorkspaceNotReady/PhaseNotFound error conventions; purpose-built normalized
shapes for project, phase, build-task progress, intake, and the four
workflow sections; explicit provenance (`SourceType` per source — student
claims/evidence/verification are labeled self-reported, never verified
facts); missing artifacts are first-class (`missing_sources` + manifest
`present=false`, never a failure); value-shaped secret redaction
(`[REDACTED_SECRET]`, applied recursively before truncation — env-var names
survive); deterministic per-source + total character budgets with visible
truncation metadata (`…[TRUNCATED]`, priority squeeze order keeps the phase
identity and the built prompt longest); and zero account-level data (no user
id, email, tokens, or profile fields — tested).

## Tests

```bash
.venv\Scripts\python -m pytest
```

Auth tests sign tokens with a locally generated ES256 key and stub only the
JWKS fetch, so the full verification path runs offline. Live verification of a
real Supabase JWT additionally requires `SUPABASE_URL` (used to derive the
JWKS URL: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`).

## Auth model (docs/auth.md)

- Frontend sends `Authorization: Bearer <supabase access token>` on every request.
- `require_user` verifies the token server-side (signature via JWKS, `exp`,
  `aud == "authenticated"`) and exposes `CurrentUser` with `user_id = sub`.
- Missing/invalid token → **401**. Wrong-user resource → **403/404**, decided
  per endpoint in the service layer (the backend uses the service-role key,
  which bypasses RLS, so every user-scoped query must filter by
  `user_id == sub` itself).
- UI hiding is never security; every protected endpoint enforces this
  dependency.
