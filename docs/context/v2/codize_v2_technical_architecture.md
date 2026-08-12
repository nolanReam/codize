# Codize V2 Technical Architecture and State Model

## Status

**Document type:** Canonical V2 technical architecture and state-model baseline.

**Stage:** V2.0B architecture approved and canonicalized in V2.1. The subordinate [V2 Schema and Persistence Design](codize_v2_schema_design.md) fixes the physical MVP design. Application code, migrations, Supabase configuration, prompts, cutover, and deployment have not begun.

**Authority:** This document implements the [Codize V2 Product Thesis](codize_v2_product_thesis.md), the [Codize V2 Exact UX Specification](codize_v2_exact_ux_specification.md), and the character boundary in the [Codize V2 Character System Blueprint](codize_v2_character_system_blueprint.md). Those sources remain higher authority for product behavior and character behavior.

**V1 boundary:** Current code, tests, migrations, [backend/README.md](../../../backend/README.md), [frontend/README.md](../../../frontend/README.md), and [docs/db/schema.md](../../db/schema.md) describe the legacy implementation. They are implementation evidence, not V2 product architecture.

**Naming scope:** The eleven `public.v2_*` MVP table names are canonical. Fields below are the governing logical shape and invariants; the subordinate Schema and Persistence Design chooses their physical PostgreSQL shape for V2.2. Neither document is migration SQL. Illustrative API paths and internal PostgreSQL function names are not permanent public application contracts.

## Executive decision summary

Codize V2 is a separate, backend-mediated product domain built around one project, one Current Change, and one useful habit at a time.

- V2 uses `public.v2_*` tables and never reinterprets V1 rows or fields.
- The browser uses Supabase Auth, then sends the verified access token to FastAPI. It does not read or write V2 product tables through the Supabase Data API.
- The MVP has eleven persistent tables. It has no generic claim graph, copied History aggregate, event-sourced UI, materialized learner projection, universal command ledger, outbox, telemetry schema, or character economy.
- A project has at most one nonterminal Current Change, enforced by the database.
- Current Change has six lifecycle states. A persisted `resume_step` restores the finer UX position without making every card a lifecycle state.
- A deterministic backend orchestrator chooses legal transitions, teaching `mode`, and risk. The LLM supplies bounded wording or typed proposals only.
- Project truth uses a narrow Project Fact model with explicit source identity, status, freshness, and supersession.
- Chat supports presentation, resume, and useful history; structured domain rows remain source truth.
- Completion is one database transaction. A backend-only PostgreSQL function/RPC is the current FastAPI-to-PostgREST mechanism, not a permanent architectural requirement.
- Manual external-agent handoff/return is the first Build slice. GitHub is an early later read-only observation slice with no initial webhooks.
- Codybara and presentation preferences are enough for the initial character architecture. Entitlements, catalogs, and achievements wait until there is something real to own or earn.

# A. Architecture invariants

## A.1 Explicit identity and ownership

Every stateful V2 command identifies:

- the authenticated user from a verified access token;
- `workflow_version = v2`;
- an explicit project ID;
- the aggregate ID when relevant;
- the expected mutable version;
- a unique command ID when the command is retry-sensitive.

The API never trusts a user ID supplied in a request body. Every project lookup constrains both the explicit project ID and the authenticated owner. No project is selected by newest-row-wins behavior.

## A.2 One project, one Current Change, one useful habit

- A project can have many Plan Items.
- A project can have many terminal Current Changes.
- A project has at most one Current Change in `PREPARING`, `AWAITING_AGENT`, `REVIEWING`, or `RECOVERING`.
- Teaching normally targets at most one unfamiliar habit or concept at a time.
- `risk = SLOWDOWN` can add the minimum safety friction required by a consequential change; it does not turn the product into a gate.

## A.3 Deterministic state, generative wording

The backend orchestrator determines:

- the authoritative lifecycle state and `resume_step`;
- legal commands and transitions;
- teaching `mode = SKIP | ASK | REMIND | TEACH`;
- `risk = NORMAL | SLOWDOWN`;
- the allowed structured UI component;
- help progression;
- generation input and target versions;
- whether a generated result is current and valid;
- whether completion is currently honest and legal.

The LLM may generate project-specific wording or a typed proposal inside that decision. It cannot advance workflow state, promote a Project Fact, create learner evidence, award anything, or declare completion.

## A.4 Source truth is structured

The source of truth is the current project, plan, Current Change, accepted Prompt Versions, Checks, Recovery Case, Project Facts, and Learner Evidence. Build turns render and explain that state. Replaying chat is never required to reconstruct project truth.

## A.5 Preserve epistemic honesty

Student statements, student observations, coding-agent claims, repository observations, system observations, and Codize inferences are not interchangeable. An external agent saying “done” does not establish working behavior. Repository content can establish what exists at a revision; it does not prove runtime behavior.

## A.6 Backend mediation and least privilege

The durable boundary is:

~~~text
Browser
  -> Supabase Auth
  -> FastAPI with verified bearer token
  -> deterministic V2 application services
  -> PostgreSQL / LLM provider / later GitHub adapter
~~~

Provider keys, the Supabase server credential, GitHub installation tokens, internal inference details, and raw provider traces never enter frontend bundles, browser storage, or ordinary logs.

## A.7 Concurrency and retry are domain behavior

Mutable rows carry monotonically increasing versions. Commands compare expected versions. Stale clients receive a controlled conflict and reload current state; last-writer-wins is not accepted for plan ordering, Current Change state, prompt acceptance, recovery, or completion.

Retry-sensitive commands use operation-local unique command IDs. A general command-receipt table is not in the MVP.

## A.8 Untrusted content stays data

Student-pasted agent output, repository content, code, diffs, error messages, and model output are untrusted. Before model use they are bounded, redacted, delimited, and provenance-labeled. Generated outputs are schema-validated and rejected when malformed or stale.

## A.9 Privacy and deletion are architectural capabilities

Project content, raw conversational content, generation metadata, learner evidence, future repository observations, and future telemetry have distinct retention and deletion rules. Structured History must remain useful after expiring raw chat.

## A.10 Honest recovery and accessible presentation

Refresh and recoverable failures preserve accepted work and the authoritative Current Change. Animation, sound, and color never carry the only representation of state. Reduced motion, keyboard operation, semantic status, and text alternatives are presentation requirements independent of persistence.

# B. Delivery tiers

## B.1 MVP: first functional V2 Build loop

The canonical MVP persistence set is exactly:

1. `public.v2_projects`
2. `public.v2_plan_items`
3. `public.v2_current_changes`
4. `public.v2_prompt_versions`
5. `public.v2_checks`
6. `public.v2_project_facts`
7. `public.v2_build_turns`
8. `public.v2_generation_attempts`
9. `public.v2_recovery_cases`
10. `public.v2_learner_evidence`
11. `public.v2_user_preferences`

This set supports new-idea setup, already-building setup, recovery-first setup, the manual Build loop, recovery, Learning, derived History, and initial Codybara/presentation preferences.

There is no separate Project Runtime or Project Plan aggregate. Project setup/runtime fields live on `v2_projects`; ordered Plan Items plus the project's `plan_version` are the plan.

## B.2 Early later slice: repository observation

GitHub is intentionally outside the first manual Build-loop schema. The first GitHub slice adds the smallest model needed for:

- a GitHub App installation reference;
- an explicit project-to-repository binding;
- a baseline observation at handoff;
- a head observation on return;
- a bounded comparison between those revisions.

It does not require webhooks, background synchronization, repository writes, branch creation, or broad permissions. Section L defines this boundary.

Multiple-project navigation, concept detail, richer inspection, and more advanced adaptive fading may also arrive in early later slices. The MVP IDs and evidence model already support them without new core aggregates.

## B.3 Deferred: not allowed to shape the MVP schema

The following are explicitly absent from the canonical MVP model:

- Project Runtime;
- a separate Project Plan aggregate;
- Plan Dependency and Plan Revision records;
- Change Completion Candidate;
- a generic Claim / Evidence Reference graph;
- copied History Entry / History Amendment records;
- Conversation Summary;
- Learner Support Projection or mastery score;
- Help Episode / Help Step tables;
- Recovery hypothesis, diagnostic, or correction child tables;
- materialized read models;
- universal command receipts;
- transactional outbox;
- telemetry tables;
- character catalog, entitlement, accessory, and achievement tables;
- GitHub webhook infrastructure.

These may be reconsidered only when a demonstrated need cannot be met safely by the smaller model. A deferred system cannot reserve generic JSON structures or abstractions in the first schema merely because it might exist later.

# C. System and database boundary

## C.1 Runtime components

~~~mermaid
flowchart LR
    UI["Authenticated frontend"] -->|"Bearer token + explicit IDs"| API["FastAPI"]
    UI -->|"Authentication only"| AUTH["Supabase Auth"]
    API --> ORCH["Deterministic V2 orchestrator"]
    ORCH --> DB["public.v2_* through server role"]
    ORCH --> GEN["Generation adapter"]
    GEN --> LLM["LLM provider"]
    ORCH -. "early later" .-> GH["GitHub App read adapter"]
    LLM -. "validated proposal" .-> ORCH
    GH -. "bounded observations" .-> ORCH
~~~

FastAPI is the product boundary. It authenticates the token, derives the owner, authorizes the explicit project, validates input, invokes deterministic domain logic, and returns a versioned response.

## C.2 `public.v2_*` access rule

`public` can be exposed through the Supabase Data API, and automatic grant defaults vary by project and platform rollout. Table placement or a platform default therefore never substitutes for explicit access design.

The browser does not read or write V2 product tables through the Supabase Data API.

For every V2 product table:

- revoke all table privileges from `anon` and `authenticated`;
- inspect existing/default privileges and do not rely on whichever exposure default the Supabase project currently has;
- do not create browser-facing Data API policies;
- enable RLS as defense in depth and preserve owner scoping;
- grant only the minimum backend role privileges required by FastAPI;
- verify with negative tests that `anon` and `authenticated` cannot select, insert, update, or delete V2 rows.

Supabase Auth remains the explicit frontend exception. The browser may manage its auth session with the publishable/anon credential, but it cannot use that credential to access V2 product state.

## C.3 Service boundaries

The initial backend may continue using PostgREST internally. That transport does not become the domain architecture. Application services own validation, authorization, version checks, and transition rules; repositories own persistence details; provider adapters own LLM and later GitHub calls.

No external provider call occurs while database locks are held.

# D. Canonical MVP data model

All IDs are opaque. All timestamps are server-authored. All mutable aggregate rows have `created_at`, `updated_at`, and a monotonically increasing `version` unless the entity is explicitly immutable.

## D.1 `v2_projects`

Purpose: V2 project identity, lightweight setup state, plan concurrency root, and project lifecycle.

Minimum logical shape:

- `id`;
- `owner_user_id` referencing the authenticated user;
- immutable `workflow_version = v2`;
- `display_name`;
- `lifecycle_state = DRAFT | TEMPORARY_RECOVERY | ACTIVE | ARCHIVED | DELETION_PENDING`;
- `setup_resume_step` for coarse setup restoration, such as idea capture, first-version shaping, guided resistance, plan proposal, existing-project context, or ready;
- a bounded current-step setup draft when refresh must preserve unaccepted work;
- optional project-level coding-agent preference key;
- `plan_version`;
- optional `first_version_completed_at`;
- deletion request / purge timing metadata;
- operation-local creation or deletion command IDs when needed for retry safety;
- row `version`.

`setup_resume_step` is not a generic workflow engine. It only resumes the bounded project-entry flow. Accepted idea, First Version, and “not yet” knowledge is promoted to Project Facts and Plan Items; the corresponding setup draft is then cleared rather than becoming a duplicate source of truth.

## D.2 `v2_plan_items`

Purpose: the editable ordered build plan.

Minimum logical shape:

- `id`, `project_id`;
- stable label and intended outcome;
- `scope_band = FIRST_VERSION | LATER`;
- `status = PROPOSED | READY | DEFERRED | DONE | REMOVED`;
- stable ordering key;
- optional completion timestamp and terminal Current Change reference;
- row `version`.

The plan is the ordered set of nonremoved items plus `v2_projects.plan_version`. Reordering or editing changes plan versions atomically. Dependencies are warnings calculated from current project context, not persisted graph edges.

## D.3 `v2_current_changes`

Purpose: the single authoritative piece of work currently being prepared, handed off, reviewed, or recovered.

Minimum logical shape:

- `id`, `project_id`;
- optional `plan_item_id`;
- `change_kind = BUILD | RECOVERY`;
- `lifecycle_state` from section E;
- persisted `resume_step` from section E;
- immutable-at-start `goal_snapshot`;
- accepted `done_condition_snapshot`;
- accepted boundary / “leave alone” snapshot;
- current mutable prompt draft and prompt-draft version until acceptance;
- current coding-agent key and student-facing effort choice;
- latest accepted Prompt Version reference;
- `teaching_mode`, `teaching_target`, `teaching_policy_version`;
- `risk`, risk reason key, and risk-policy version;
- current Need Help context and disclosed support level;
- student-reported return outcome;
- accepted outcome summary and unresolved uncertainty summary;
- completion or cancellation timestamp and reason;
- operation-local creation, handoff, and completion command IDs where needed;
- row `version`.

A partial unique index enforces one nonterminal row per `project_id` where lifecycle state is `PREPARING`, `AWAITING_AGENT`, `REVIEWING`, or `RECOVERING`.

The goal snapshot does not change when its Plan Item is edited. Terminal Current Change snapshots are retained as the stable core of derived History.

## D.4 `v2_prompt_versions`

Purpose: exact immutable snapshots of accepted coding-agent prompts.

Minimum logical shape:

- `id`, `current_change_id`;
- monotonically increasing ordinal within the change;
- `purpose = FEATURE | DIAGNOSTIC | CORRECTION`;
- exact accepted prompt content and content hash;
- the Current Change input version from which it was prepared;
- generation-attempt reference when generated;
- selected coding-agent key;
- student-facing effort choice;
- provider mapping key/version used at handoff;
- accepted timestamp;
- optional handed-off timestamp and handoff command ID.

Prompt content is immutable after insertion. Editing occurs in the Current Change draft; accepting an edit inserts a new Prompt Version. Handoff can stamp metadata without changing prompt content. A stale generated draft cannot be accepted after the target Current Change version has changed.

## D.5 `v2_checks`

Purpose: proposed and performed checks without overstating verification.

Minimum logical shape:

- `id`, `project_id`, `current_change_id`;
- concise check plan;
- `plan_source = CODIZE | STUDENT`;
- `status = PROPOSED | PERFORMED | NOT_RUN`;
- `result = WORKED | PARTLY_WORKED | DID_NOT_WORK | UNSURE`, nullable until performed;
- student observation text, bounded and redacted;
- performed time;
- source Build Turn reference when relevant;
- optional superseded Check reference for a correction;
- row `version` where a proposed check may become performed.

A Check records what was actually proposed and observed. It does not become “verified” solely because the external agent claimed success or because a repository changed.

## D.6 `v2_project_facts`

Purpose: narrow structured project memory with explicit provenance and correction.

Minimum logical shape:

- `id`, `project_id`;
- allowlisted `fact_type`;
- stable `subject_key` within that fact type;
- discriminated typed value;
- `source_kind` from section G;
- bounded source-record reference;
- `status = active | unresolved | contradicted | stale | superseded`;
- `observed_at`;
- optional `fresh_until`;
- optional `supersedes_fact_id`;
- optional separate student-confirmation status, time, and Build Turn reference;
- row `version` only for controlled status transitions.

The typed value is a constrained union such as text, boolean, number, or bounded text list, with exactly one value representation populated. `fact_type` is an allowlist of useful project concepts such as project goal, First Version scope, known working behavior, constraint, boundary, tool/stack fact, or unresolved behavior. It is not an arbitrary predicate.

## D.7 `v2_build_turns`

Purpose: the durable portion of Build conversation needed for resume, decisions, help progression, useful History, and safe debugging.

Minimum logical shape:

- `id`, `project_id`;
- optional `current_change_id` and `recovery_case_id`;
- monotonic sequence within the project or change;
- `turn_kind` from a bounded allowlist;
- `speaker = STUDENT | CODIZE | SYSTEM`;
- bounded content and, only where needed, schema-validated structured payload;
- related domain-record type/ID;
- help context / support level when the turn disclosed help;
- policy/config version when wording depended on policy;
- content retention class and optional expiry time;
- timestamps.

Persist only:

- accepted student answers and decisions;
- the mentor question needed to interpret an accepted answer;
- Need Help disclosures and the nudge/clue/teach progression;
- meaningful student overrides;
- final validated generated content that is useful beyond a Prompt Version;
- safe user-visible failure or retry context when needed for resume/debugging.

Do not persist as domain turns:

- typing indicators;
- animation or sound state;
- loading cards;
- toasts;
- derived card rendering;
- streaming tokens;
- ordinary navigation;
- transient “thinking” text.

## D.8 `v2_generation_attempts`

Purpose: safe generation retry, stale-result rejection, and operational visibility without making provider traces project truth.

Minimum logical shape:

- `id`, owner/project and target aggregate IDs;
- generation purpose;
- target aggregate version and policy/config version;
- `status = PENDING | SUCCEEDED | FAILED | SUPERSEDED`;
- provider/model identifiers and input hash;
- safe error category and retryability, never raw credentials or unredacted provider output;
- resulting domain-record reference when accepted;
- start/completion timestamps;
- unique attempt/command ID as required.

Raw streaming tokens and chain-of-thought are not stored. Successful output becomes authoritative only after validation and an explicit domain command, such as updating the prompt draft or inserting a Prompt Version.

## D.9 `v2_recovery_cases`

Purpose: one bounded recovery episode without a hierarchy of hypothesis, diagnostic, and correction tables.

Minimum logical shape:

- `id`, `project_id`, `current_change_id`;
- `status = OPEN | INVESTIGATING | CORRECTING | RECHECKING | RESOLVED | ABANDONED`;
- intended behavior;
- observed symptom;
- last-known-working statement and certainty;
- candidate relevant change, explicitly not assumed causal;
- current student hypothesis or proposed first check when present;
- investigation finding / cause summary when established;
- correction summary;
- resolution summary;
- opened/resolved timestamps;
- row `version`.

The detailed conversation stays in Build Turns, diagnostic/correction prompts stay in Prompt Versions, and performed rechecks stay in Checks. A partial unique index permits at most one open Recovery Case per Current Change.

## D.10 `v2_learner_evidence`

Purpose: append-oriented, user-level evidence for per-competency adaptation across projects.

Minimum logical shape:

- `id`, `owner_user_id`;
- nullable `source_project_id` and `source_current_change_id`;
- allowlisted `competency_key`;
- concrete observed behavior;
- `elicitation = SPONTANEOUS | ASKED | AFTER_HINT | TAUGHT`;
- `support_level = NONE | NUDGE | CLUE | TEACH`;
- bounded context key, such as change/risk/novelty class;
- typed source-record reference, not a copied transcript;
- `observed_at`;
- `status = ACTIVE | RETRACTED | INVALIDATED`;
- evidence-policy version.

Evidence is appended; corrections retract or invalidate prior evidence rather than silently rewriting it. There is no global level, mastery percentage, or materialized learner projection.

The Learning page derives `New`, `Guided`, `Practiced`, and `Recently Independent` on read using a versioned policy. These are human-readable descriptors, not grades. Exact qualification and fading thresholds belong to the future Learning / Teaching Policy.

## D.11 `v2_user_preferences`

Purpose: user-level presentation and convenience settings independent of projects.

Minimum logical shape:

- `owner_user_id`;
- optional active V2 project ID as convenience, never authorization;
- optional default coding-agent key;
- `selected_character_key`, initially `codybara`;
- dialogue sound preference;
- `motion_preference = SYSTEM | FULL | REDUCED`;
- row `version` and timestamps.

The operating-system reduced-motion signal still takes precedence where it requests less motion. This table is not a catalog, entitlement, or achievement system.

## D.12 Deliberately absent command-receipt table

The MVP first uses unique command fields on the affected resource:

- creation command on the created project/change;
- prompt acceptance or handoff command on the Prompt Version / Current Change;
- completion command on the terminal Current Change;
- deletion command on a logically deleted project when a recovery window applies.

For immediate temporary-project purge, repeated discard of an already absent resource returns the same safe success response without revealing whether the resource existed.

Add a narrowly scoped `v2_command_receipts` table only if an operation must replay a result after all affected rows are gone, or one command spans resources in a way that operation-local uniqueness cannot make retry-safe. That is an implementation finding, not an MVP assumption.

# E. Current Change state machine

## E.1 Primary lifecycle states

| State | Meaning | Typical persisted `resume_step` |
|---|---|---|
| `PREPARING` | Confirm the change, choose the agent when needed, teach one useful habit, prepare and accept a prompt. | `confirm_change`, `choose_agent`, `intervention`, `prompt`, `effort` |
| `AWAITING_AGENT` | The accepted prompt has been handed to an external coding agent and Codize is waiting for the student to return. | `return_outcome` |
| `REVIEWING` | The student returned; Codize is checking, inspecting, or supporting a tiny understanding interaction. | `return_outcome`, `check`, `inspect`, `understand` |
| `RECOVERING` | Codize is narrowing a symptom, investigating, preparing a diagnostic/correction, or rechecking. | `recovery_symptom`, `recovery_investigate`, `recovery_correct`, `recovery_recheck` |
| `COMPLETED` | The change closed successfully or with honestly recorded bounded uncertainty. Terminal. | none |
| `CANCELLED` | The student explicitly stopped or replaced the change. Terminal. | none |

The lifecycle describes durable work posture. `resume_step` describes the finer UX position. Component types such as Prompt Preview, Check Card, Learning Card, or uncertainty summary are rendered from this state; they are not extra lifecycle states.

## E.2 Legal transition outline

~~~mermaid
stateDiagram-v2
    [*] --> PREPARING
    PREPARING --> PREPARING: confirm / choose / intervene / draft / accept
    PREPARING --> AWAITING_AGENT: hand off accepted prompt
    AWAITING_AGENT --> REVIEWING: return worked or unsure
    AWAITING_AGENT --> RECOVERING: return broken
    REVIEWING --> REVIEWING: check / inspect / understand
    REVIEWING --> RECOVERING: failed or unexplained result
    RECOVERING --> RECOVERING: observe / investigate / prepare correction / recheck
    RECOVERING --> AWAITING_AGENT: hand off diagnostic or correction prompt
    AWAITING_AGENT --> RECOVERING: return while recovery case is open
    RECOVERING --> REVIEWING: resolution ready for final review
    REVIEWING --> COMPLETED: atomic completion command
    RECOVERING --> COMPLETED: atomic recovery completion when review is already satisfied
    PREPARING --> CANCELLED: explicit cancel
    AWAITING_AGENT --> CANCELLED: explicit cancel
    REVIEWING --> CANCELLED: explicit cancel
    RECOVERING --> CANCELLED: explicit cancel
~~~

An open Recovery Case disambiguates a return from a diagnostic/correction handoff. Prompt Version `purpose` identifies whether the handoff was feature, diagnostic, or correction work.

## E.3 Start, resume, and replace

- Starting a change inserts the Current Change with a goal snapshot inside a transaction that relies on the one-nonterminal unique constraint.
- A losing concurrent start receives a conflict and the existing Current Change.
- Refresh loads the Current Change, `resume_step`, relevant structured records, and only the durable Build Turns needed for context.
- “Choose something else” cancels or explicitly replaces the current change; it never creates two active changes.

## E.4 Plan editing while a change is active

The Current Change owns its goal, done-condition, and boundary snapshots. Editing or reordering the linked Plan Item does not rewrite them.

If the student removes the linked Plan Item, the backend requires one explicit command:

1. **Keep active change:** detach the Current Change from the item, then remove or defer the Plan Item. The Current Change continues from its snapshots.
2. **Cancel active change:** cancel the Current Change, then remove the Plan Item.

There is no cascade that silently cancels the change and no plan edit that silently changes the active goal.

## E.5 Return outcomes and completion

- `It worked` enters review/check behavior.
- `I'm not sure` enters inspection/check behavior and preserves uncertainty.
- `Something's wrong` enters recovery.
- A failed or partial Check enters or continues recovery.
- A Check or understanding interaction can be omitted when deterministic teaching policy says it is redundant and risk allows that omission.

Completion is not a V1-style gate or exam. The backend recomputes whether the change has an honest outcome appropriate to its done condition and risk decision. It never requires Defense, PASS/FAIL, a score, or the same ceremony for every change.

# F. Teaching, Need Help, and learner adaptation

## F.1 Two-axis policy

The deterministic decision is:

~~~text
TeachingDecision {
  mode: SKIP | ASK | REMIND | TEACH
  risk: NORMAL | SLOWDOWN
  target_competency?: competency_key
  reason_key
  policy_version
}
~~~

`SLOWDOWN` modifies the selected mode. It is not a fifth mutually exclusive teaching mode.

Policy inputs include current change context, accepted Project Facts, recent per-competency evidence, support previously used, novelty, user-provided answers, and versioned high-risk classification. Policy outputs are persisted on the Current Change so refresh does not produce a different intervention mid-step.

The LLM receives the decision and generates project-specific wording inside a validated component. It does not select the decision.

## F.2 Deterministic minimum decisions

The rules engine must decide at least:

- whether an observable “done” condition is missing;
- whether a working boundary is relevant;
- whether the student already supplied the target behavior;
- whether to supply a check, ask the student for one, or omit explicit prompting;
- whether Need Help moves from nudge to clue to direct teaching;
- whether a high-risk change requires a minimum slowdown;
- whether an observed behavior qualifies as learner evidence;
- whether support may fade or should return because of novelty/risk;
- whether completion is currently honest and legal;
- whether agent-effort mapping is current enough to use.

Exact thresholds and high-risk content are versioned Learning / Teaching Policy, not invented by the LLM or inferred from a chat tone.

## F.3 Need Help without Help tables

The current help context and highest disclosed support level live on the Current Change. Each durable nudge, clue, or teach exchange is a typed Build Turn. Evidence records the support actually used.

This is enough to resume the ladder, avoid repeating help, and qualify evidence. A Help Episode / Help Step hierarchy is unnecessary until the product demonstrates a query or retention need it cannot satisfy.

## F.4 Derived learner descriptors

On read, a versioned policy derives:

- **New:** no qualifying evidence for the competency;
- **Guided:** evidence primarily after hint or direct teaching;
- **Practiced:** repeated relevant behavior with some prompting or support;
- **Recently Independent:** recent relevant behavior produced spontaneously without support.

These definitions express direction, not fixed thresholds. Conservative fading and reintroduction rules remain a teaching-policy decision. Learner evidence is product adaptation data, not telemetry.

# G. Project Fact and provenance model

## G.1 Source kinds

Every Project Fact has exactly one source identity:

- `student_stated`;
- `student_observed`;
- `agent_claimed`;
- `repository_observed`;
- `system_observed`;
- `codize_inferred`.

Student confirmation is separate. Confirming a repository observation does not rewrite its source as student-observed; it records confirmation metadata or a confirming Build Turn. If the student supplies a new observation, that is a new fact with its own source.

## G.2 Status and supersession

- `active`: currently usable within its source limits;
- `unresolved`: plausible or relevant but not established;
- `contradicted`: conflicting evidence exists;
- `stale`: freshness has expired or repository context moved;
- `superseded`: a newer fact replaces it.

Corrections insert a new fact and link `supersedes_fact_id`; the prior fact becomes superseded. Contradictory evidence remains visible to the orchestrator until resolved. Freshness applies only where time or repository revision can invalidate usefulness.

## G.3 Promotion rules

- An accepted student description may create `student_stated` facts.
- A performed Check may create `student_observed` facts no stronger than the observed result.
- Pasted external-agent output creates `agent_claimed` facts, normally unresolved until supported.
- A future GitHub observation creates `repository_observed` facts at a named repository revision.
- Deterministic product actions may create `system_observed` facts.
- Model interpretation creates `codize_inferred` facts and retains uncertainty.

Changing status never changes source identity. A stronger source generally creates a superseding fact instead of laundering the weaker source.

## G.4 Narrowness guardrails

Project Fact is not a knowledge graph:

- no arbitrary subject-predicate-object triples;
- no fact-to-fact dependency graph;
- no generic Evidence Reference table;
- no open-ended value object accepted without a fact-type schema;
- no attempt to store every sentence from chat or code;
- no claim that a fact is true outside its source, observation time, and freshness boundary.

Only facts that reduce repeated questions, support honest prompts/checks, explain History, or improve recovery belong here.

# H. Build persistence, History, and generation

## H.1 Refresh and resume

A Build read assembles:

1. project/setup state;
2. ordered Plan Items;
3. the nonterminal Current Change, if any;
4. its accepted Prompt Versions, Checks, and open Recovery Case;
5. relevant active/unresolved Project Facts;
6. recent durable Build Turns;
7. derived teaching and learner descriptors where appropriate.

The client does not replay a generic event stream to discover the state. Transient rendering is reconstructed from the authoritative response.

## H.2 History is a derived read

MVP History is built from:

- completed/cancelled Current Changes;
- the immutable accepted Prompt Version(s) associated with each change;
- proposed/performed Checks;
- the Recovery Case when applicable;
- Project Facts created, contradicted, or superseded by the change;
- Learner Evidence associated with the change;
- future repository observations when GitHub exists.

No `HistoryEntry` is copied at completion and no `HistoryAmendment` table exists.

Stable display values are snapshotted only where later edits would mislead:

- Current Change goal, done condition, boundary, outcome, and terminal time;
- exact accepted prompt text;
- exact check plan and observed result;
- recovery symptom, finding, resolution, and recheck;
- coding-agent and effort selections used for that handoff.

Project display-name changes and Plan Item edits therefore cannot rewrite what a completed change was understood to mean. Later fact supersession or evidence retraction changes the derived interpretation without rewriting terminal records.

## H.3 Generation lifecycle

1. The orchestrator snapshots bounded inputs and their versions.
2. It creates a Generation Attempt.
3. The provider call occurs outside a database transaction.
4. The backend validates structure, safety, and output bounds.
5. It compares the current target version with the recorded target version.
6. If stale, it marks the attempt superseded and does not apply the output.
7. If current, a short domain transaction applies the validated proposal to the mutable draft or inserts the accepted record.

A browser retry reuses or safely supersedes the unique attempt. Partial streams never become Prompt Versions or Project Facts.

# I. Recovery architecture

## I.1 Investigation before patching

Recovery always narrows observed behavior before preparing a correction:

~~~text
symptom
  -> relevant recent change or last-known-working context
  -> known / unknown summary
  -> hypothesis or first useful check
  -> diagnostic prompt when needed
  -> finding
  -> bounded correction when needed
  -> recheck original symptom
  -> resolve or continue
~~~

Hypotheses remain inferences. Temporal sequence does not become causation. The same Project Fact source/status rules govern recovery summaries.

## I.2 Existing-project recovery

“Something broke” can convert the active Current Change to `RECOVERING` or start a recovery Current Change if none exists. It cannot create a second nonterminal change. The Recovery Case holds the bounded episode; diagnostic and correction handoffs reuse Prompt Versions and `AWAITING_AGENT`.

## I.3 Recovery-first temporary project

When a user chooses **Something broke** before a normal project exists:

1. Create `v2_projects.lifecycle_state = TEMPORARY_RECOVERY` with minimal accepted project context.
2. Create a recovery Current Change without requiring a Plan Item.
3. Run the standard Recovery Case flow.
4. After resolution, ask whether to keep the project.

**Keep building with Codize** promotes the project to `ACTIVE`, captures any missing minimal project/plan context, and retains its structured records.

**Not now** immediately hides and purges the temporary project and its project-scoped Plan Items, Current Changes, Prompt Versions, Checks, Project Facts, Build Turns, Generation Attempts, and Recovery Cases. Repeating the discard returns safe success. It does not delete `v2_user_preferences`.

Valid cross-project Learner Evidence is not deleted solely because the temporary project is discarded. Section N defines how its project reference and source content are minimized.

# J. Transaction, concurrency, and retry strategy

## J.1 Normal command contract

A mutating command contains:

~~~text
Command {
  command_id
  project_id
  aggregate_id?
  expected_aggregate_version?
  expected_plan_version?
  payload
}
~~~

FastAPI derives the owner from the verified token. The service loads by owner and explicit IDs, validates the state/step, performs the smallest transaction possible, increments versions, and returns the new authoritative representation.

## J.2 Atomic completion invariant

> Completion happens in one database transaction.

In the current FastAPI-to-PostgREST architecture, the implementation mechanism is a backend-only PostgreSQL function exposed as an internal RPC. The architectural requirement is atomicity; a future direct PostgreSQL driver may implement the same transaction without preserving an RPC-shaped application boundary.

Conceptual completion input:

- authenticated owner ID supplied only by trusted backend context;
- project ID and Current Change ID;
- expected Current Change version;
- expected project plan version and linked Plan Item version when linked;
- unique completion command ID.

The function performs, in fixed order:

1. Return the existing terminal result when the same completion command ID already succeeded.
2. Lock the owned V2 Project.
3. Lock the named Current Change under that project.
4. Lock the linked Plan Item, if any.
5. Verify lifecycle, ownership, one-current-change identity, expected change version, expected plan/item versions, and command uniqueness.
6. Recompute completion eligibility from durable state, current teaching/risk policy, performed Checks where required, accepted uncertainty, and any open Recovery Case.
7. Mark the Current Change `COMPLETED`, store terminal snapshots and the completion command ID, and increment its version.
8. Mark the still-linked Plan Item `DONE` and increment item/project plan versions when the command chose to complete that item.
9. Insert only the accepted Project Facts justified by the completion inputs and evidence.
10. Insert only qualifying Learner Evidence with elicitation and support context.
11. Resolve the Recovery Case when applicable.
12. Commit and return the canonical result.

The lock order is always Project -> Current Change -> Plan Item, with deterministic ID order if more than one row of a class is ever involved. The function makes no LLM, GitHub, analytics, notification, or other network call.

If any validation fails, no completion, plan progress, fact promotion, or learner evidence is committed. A different completion command against an already terminal change receives a controlled conflict rather than duplicating evidence.

## J.3 Completion is not a gate

Eligibility prevents internally inconsistent or dishonest state; it does not grade the student. The policy may omit explicit checks or understanding interactions when they are redundant and safe. Completion can retain bounded uncertainty. It never depends on PASS/FAIL, cooldown, Defense, a score, or a phase advancement rule.

## J.4 Other concurrency invariants

- **Start change:** partial unique index plus expected project version prevents two nonterminal changes.
- **Plan reorder/edit:** one transaction checks `plan_version`, updates affected order keys/items, then increments `plan_version`.
- **Remove linked item:** only the two explicit commands in E.4 are legal.
- **Prompt acceptance:** expected Current Change and prompt-draft versions prevent accepting stale generated text.
- **Handoff:** accepted Prompt Version plus unique handoff command prevents duplicate handoff state.
- **Generation:** target version prevents late output from overwriting new student input.
- **Recovery update:** expected Recovery Case and Current Change versions prevent two tabs from advancing different hypotheses.
- **Temporary discard:** purge is scoped by authenticated owner and exact temporary project ID.

# K. Authorization, database security, and input safety

## K.1 Access matrix

| Actor | Supabase Auth | V2 product tables | Completion RPC | LLM / GitHub credentials |
|---|---:|---:|---:|---:|
| Anonymous browser | public auth flows only | none | none | none |
| Authenticated browser | own auth session | none | none | none |
| FastAPI server role | token verification support | least required | execute | server only |
| Migration/owner role | administration only | schema management | schema management | none by default |

FastAPI still authorizes every read and write even though browser roles have no table privileges. A service credential is never sent to the client.

## K.2 RLS and grants

The physical schema/migration must:

- enable RLS on every `public.v2_*` table;
- define ownership defense consistent with server-only access;
- revoke table and sequence privileges from `anon` and `authenticated`;
- avoid policies that grant browser product access merely because a user is authenticated;
- grant the backend role only the statements it needs;
- test cross-user, stale-ID, deleted-ID, and direct-Data-API denial behavior.

The API returns the same safe not-found result for absent, deleted, and unauthorized IDs so project existence is not leaked.

## K.3 Completion function security

The completion function must:

- revoke `EXECUTE` from `PUBLIC`;
- revoke `EXECUTE` from `anon`;
- revoke `EXECUTE` from `authenticated`;
- grant `EXECUTE` only to the backend server role that needs it;
- use a safe fixed `search_path` and schema-qualified objects;
- verify the project and Current Change owner inside the transaction;
- use fixed lock ordering;
- enforce expected Current Change and plan versions;
- enforce the unique completion command ID;
- avoid dynamic SQL and validate bounded inputs.

Prefer invoker security under the already-privileged server role. If a later implementation proves `SECURITY DEFINER` is necessary, it requires a nonlogin owner, the same revocations, an explicitly safe search path, fully qualified objects, and a focused security review. Privilege escalation is not a fix for an ownership bug.

## K.4 Model and imported-content safety

- Provider outputs must match a typed schema and size limits.
- Repository/pasted content is delimited as untrusted data and stripped of credential-shaped content before model use.
- Source references and hashes are retained without copying unnecessary raw content.
- Safe errors contain categories and correlation IDs, not prompts, code, tokens, or secrets.
- Malformed output fails closed when applying it could corrupt workflow state, facts, or learner claims.

# L. Early later GitHub slice

## L.1 Integration choice

Use a GitHub App because it supports explicit repository selection, fine-grained read permissions, installation-scoped access, and short-lived installation tokens. Do not store installation access tokens durably.

The initial permission intent is read-only repository metadata and contents needed for the selected repository. Codize does not silently write code, commit, push, merge, or broaden repository access.

## L.2 Minimal later persistence

The later slice may add narrowly named tables for:

- **Installation reference:** owning user, GitHub installation ID, account identity, status, and last authorization check.
- **Repository binding:** V2 project, explicit repository ID/name, selected branch, and binding status.
- **Repository observation:** immutable repository/branch/commit SHA, capture purpose, capture time, freshness, and bounded metadata.
- **Repository comparison:** Current Change, baseline observation, head observation, bounded changed-file metadata, redacted diff/summary retention class, and uncertainty.

These are observation records, not Project Facts by default. Accepted observations may produce narrow `repository_observed` Project Facts with revision provenance.

## L.3 First flow

~~~text
Install/authorize GitHub App
  -> explicitly select repository
  -> confirm branch
  -> read baseline revision at handoff
  -> read head revision on return
  -> compare the bounded revisions
  -> ask for student judgment where relevant
~~~

If GitHub is unavailable, stale, disconnected, or lacks access, the manual Build loop remains available and the UI labels repository knowledge stale or unavailable.

## L.4 Explicit omissions

The first GitHub slice has no webhook ingestion, background synchronization, repository write token, hidden branch selection, whole-repository embedding requirement, or assumption that a code change worked. Webhooks are added only if a later product need requires freshness while the user is away and the worker/retry/dead-letter/monitoring design is explicitly accepted.

# M. V1 / V2 compatibility strategy

## M.1 Parallel versioned domains

V1 remains in its current tables and semantics. V2 begins in `public.v2_*`. No V2 row foreign-keys to or embeds V1 workflow state.

The following remain V1-only implementation facts:

- five-question intake and archetypes;
- seven phases and `current_phase`;
- V1 task progress and workflow artifacts;
- gate sessions and PASS/FAIL;
- mandatory Project Defense;
- cooldowns;
- phase/score-based unlocks.

No V2 transition, teaching decision, completion, History view, learner descriptor, or character preference depends on those structures.

## M.2 Versioned references and APIs

A cross-version UI reference is:

~~~text
ProjectRef {
  workflow_version: v1 | v2
  project_id
}
~~~

V2 APIs use a versioned route namespace and explicit project ID. Collection operations may list/create; resource operations always name the project. Browser cache/draft keys include user, workflow version, project ID, aggregate ID, and aggregate version where relevant.

An active-project preference is convenience only. A stale preference clears safely and returns to selection; it never authorizes access or falls back to the newest project.

## M.3 Combined project switcher constraint

The current V1 repository behavior loads the newest V1 project for a user, and parts of the V1 frontend assume one active project. Until V1 gains safe explicit project-ID loading, a combined switcher may show only the V1 project that the maintained V1 application can actually open. It must not advertise multiple selectable legacy projects that all resolve to the same newest row.

V2 projects can be listed explicitly from their first implementation even if the first UI exposes only one-project navigation.

## M.4 No semantic dual write

- V1 services query and mutate only V1 storage.
- V2 services query and mutate only V2 storage.
- Creating V2 state never updates V1 `current_phase`, tasks, artifacts, gates, or unlocks.
- V1 rows are not backfilled into V2 automatically.
- A future import creates a new V2 project with new IDs and provenance-labeled copied facts; it does not transform or dual-write the V1 source.

The product policy for when to stop creating new V1 projects is still a cutover decision, not a schema coupling.

# N. Retention and deletion

## N.1 Data classes

At minimum, retention distinguishes:

- project identity/setup/plan/current-change state;
- immutable accepted prompts and performed Checks;
- Project Facts and terminal recovery summaries;
- raw/bounded Build Turn content;
- safe Generation Attempt metadata and any separately secured raw provider trace;
- user-level Learner Evidence;
- user preferences;
- later repository observations/comparisons;
- later telemetry, if adopted.

The physical schema includes expiry/purge metadata where a configurable duration applies. Expiry redacts or purges the raw payload while retaining only the minimal noncontent tombstone/source metadata needed by still-valid structured references. Domain reads behave honestly if raw content has expired.

## N.2 Standard project deletion

A standard deletion request immediately hides/disables the owned project, cancels its nonterminal Current Change and pending generations, clears an active-project preference that points to it, and prevents future external synchronization. Physical purge follows the configured recovery policy.

No transactional outbox is assumed. Before delayed purge or external revocation ships, its owning worker/process, retry policy, dead-letter behavior, and monitoring must be designed explicitly.

## N.3 Temporary recovery discard

The **Not now** path is intentionally stronger: it purges the temporary recovery project and project-specific rows instead of leaving an unexplained account project. It has no project recovery window unless a later UX decision explicitly introduces one.

## N.4 Learner Evidence after project deletion

Minimal valid user-level evidence may survive project deletion because adaptation crosses projects. When the source project is permanently purged:

- set the source project/current-change references to null or a nonidentifying tombstone;
- delete project-specific source text, code, prompt excerpts, chat excerpts, and repository content;
- retain only competency key, concrete behavior in generalized form, elicitation, support level, bounded context class, observed time, status, and policy version;
- invalidate evidence that cannot remain meaningful or honest after source minimization.

Deleted project content is never retained merely to justify a learner label. Preferences also survive project deletion because they are user-level.

## N.5 Account deletion ordering

Before account deletion ships, its orchestrator must revoke sessions and later GitHub access, disable owned projects, purge project-scoped content, apply the learner-evidence account policy, and then remove the auth user in a recoverable and observable order. Deleting the auth row first must not strand unowned private data or live external access.

# O. Failure modes and required behavior

| Failure | Required behavior |
|---|---|
| Two tabs start a change | Database uniqueness accepts one; the other receives the existing change/conflict. |
| Stale plan edit | Expected `plan_version` fails; client reloads without overwriting. |
| Linked Plan Item removed | Backend requires keep-and-detach/defer or cancel-and-remove. |
| Generation returns late | Target-version mismatch marks it superseded; no draft or fact is changed. |
| Provider fails | Generation Attempt records a safe failure; accepted student work and resume step remain. |
| Handoff is retried | Unique handoff command returns the same accepted handoff state. |
| Completion is retried | Same command returns the terminal result; a conflicting command cannot duplicate facts/evidence. |
| External agent claims success | Stored as claim/turn context only; checking/review policy still applies. |
| Recovery hypothesis is uncertain | Remains inference/unresolved; UI shows known vs unknown. |
| Refresh during recovery | Current Change resume step + Recovery Case + relevant turns restore the episode. |
| Temporary project is declined | Exact owned temporary project and children are purged; preferences/minimal valid cross-project evidence survive. |
| Direct Data API attempt | Table grants and RLS deny browser access. |
| Unauthorized or deleted ID | Same safe not-found response; no existence leak. |
| GitHub unavailable later | Observation is labeled stale/unavailable; manual flow continues. |
| Raw chat expires | Structured project, change, check, fact, recovery, evidence, and derived History remain usable. |

# P. Remaining decisions

## P.1 True MVP schema blockers

**None remain at the architecture or physical-schema design level.** The entity cut, V2 namespace, server-only access boundary, Current Change lifecycle, one-change constraint, completion mechanism, Project Fact model, learner-evidence deletion behavior, temporary-project behavior, PostgreSQL types/bounds, controlled values, foreign-key actions, indexes, and transaction-test requirements are resolved by this architecture plus the canonical Schema and Persistence Design.

V2.2 must translate that design into reviewed DDL and prove it with migration, catalog, transaction, ownership, RLS/grant, and adversarial tests. An implementation finding may refine mechanics only when it preserves the canonical contracts or is recorded as an explicit amendment.

## P.2 Remaining founder or policy decisions

The following values or later-slice choices remain open but must not reshape the MVP entity model:

- exact retention duration for raw Build Turn content and separately secured raw provider traces;
- standard-project deletion recovery window;
- exact competency qualification, fading, reintroduction, and evidence-freshness thresholds;
- exact high-risk classification and required minimum slowdowns;
- the supported coding-agent keys, effort mappings, mapping owner, review cadence, and stale fallback;
- when new V1 project creation stops and how long maintained V1 writes remain available;
- whether and when an explicit V1-to-V2 copy/import tool is offered;
- timing and scope of the early GitHub slice, including organization/minor accounts and branch-confirmation policy;
- any future telemetry event list and retention policy;
- any future achievements, accessories, additional characters, and their earning/ownership rules.

Use versioned policy/config values and configurable expiry timestamps so these choices can be made without introducing speculative MVP aggregates.

# Q. Implementation dependency order

This is sequencing guidance, not authorization to implement.

1. Implement the canonical Schema and Persistence Design as reviewed DDL and security tests for the eleven MVP tables, ownership, RLS/grants, constraints, indexes, transition guards, and internal transaction primitives.
2. Implement authenticated V2 project/setup/plan reads and commands behind FastAPI.
3. Implement Current Change start/resume/plan-edit invariants and deterministic teaching decision persistence.
4. Implement safe generation attempts, mutable prompt drafts, immutable Prompt Versions, manual handoff, and return outcomes.
5. Implement Checks, Project Fact promotion, Learner Evidence, and the atomic completion transaction/RPC.
6. Implement bounded Recovery Cases, recovery-first temporary projects, promotion, and discard purge.
7. Implement derived Project Home, Learning, History, settings, empty/error/loading, and accessible presentation states.
8. Validate the complete manual Build loop before adding the GitHub App observation slice.
9. Add deferred systems only in response to demonstrated requirements and a separate accepted decision.

# Validation audit

## UX state to backing-state coverage

| Canonical UX area | Durable backing / behavior |
|---|---|
| Landing and authentication | No V2 product row required before intent; Supabase Auth remains the frontend auth boundary. |
| First-time entry choice | Creates the appropriate draft, active existing-project, or temporary recovery project only after accepted input. |
| New idea, First Version, guided resistance | `v2_projects` setup snapshots/resume step, accepted Build Turns, then narrow Project Facts. |
| Build Plan proposal/edit | `v2_plan_items` + project `plan_version`; no Plan aggregate/dependency graph. |
| Project Home and Build Plan page | Derived from project, plan, one nonterminal change, and active/unresolved facts. |
| Current-change confirmation / choose another | `PREPARING` + `confirm_change`; explicit cancel/replace command. |
| Coding-agent selection | project preference plus Current Change selection; `choose_agent` resume step. |
| Habit/concept intervention and high risk | persisted teaching mode + independent risk modifier + policy versions. |
| Need Help | Current Change help context plus typed Build Turns and supported Learner Evidence. |
| Prompt preparation/preview/edit/why | mutable Current Change draft; immutable accepted `v2_prompt_versions`; explanation in bounded Build Turns. |
| Effort teaching | Current Change choice and immutable handoff snapshot with versioned agent mapping. |
| Agent handoff / waiting / return | Prompt Version, unique handoff command, `AWAITING_AGENT`, and `return_outcome`. |
| Worked / unsure / broken | deterministic transition to `REVIEWING` or `RECOVERING`; external-agent claim is not proof. |
| Check | `v2_checks`, performed observation, and optional learner evidence. |
| Connected change summary / diff inspection | early GitHub observations/comparison; manual flow remains valid before that slice. |
| Tiny understanding interaction | `REVIEWING/understand`, durable accepted answer/help turns, learner evidence when qualified. |
| Change completion | one atomic transaction; terminal Current Change snapshots; no gate or copied History row. |
| Something broke during Build | same Current Change enters `RECOVERING`; one open Recovery Case. |
| Recovery symptom/evidence/hypothesis/diagnostic/correction/recheck | one Recovery Case + Build Turns + Prompt Versions + Checks; known/unknown provenance retained. |
| Recovery-first entry | `TEMPORARY_RECOVERY`; promote on keep, purge project domain on **Not now**. |
| Ask About My Project | read-only answer from scoped Project Facts/history with uncertainty; no generic chatbot authority. |
| Learning and concept detail | descriptors derived on read from append-oriented evidence; no mastery score/projection. |
| History and change detail | derived from terminal structured records and immutable snapshots; no duplicate History aggregate. |
| First-Version completion | plan state + terminal changes + `first_version_completed_at`; expansion remains student choice. |
| Project switcher | explicit versioned ProjectRef; legacy entries limited to what V1 can actually open. |
| Settings / Character | `v2_user_preferences`; Codybara default; no entitlement/catalog requirement. |
| Loading, error, retry, empty, refresh | transient UI state plus safe Generation Attempt/domain responses; no UI-event persistence. |
| Reduced motion and sound | user preference + OS signal; never workflow state or sole status cue. |

## Required separation checks

1. **Canonical V2 UX coverage:** Passed by the mapping above. GitHub-dependent states are explicitly supported by the early later slice rather than contaminating the manual-loop schema.
2. **V1/V2 separation:** Passed. V2 uses `public.v2_*`, explicit versioned references, no semantic dual writes, and no V1 foreign keys.
3. **No legacy workflow dependency:** Passed. V2 state does not depend on archetypes, seven phases, `current_phase`, V1 task progress, workflow artifacts, gates, Defense, cooldowns, or V1 unlocks.
4. **Chat not source truth:** Passed. Authoritative state is structured; durable turns are bounded context/presentation.
5. **Project Fact remains narrow:** Passed. Allowlisted types, typed values, one source identity, status, and supersession replace a generic graph.
6. **History does not duplicate the domain:** Passed. History is a read assembled from terminal structured records and minimal immutable snapshots.
7. **Atomic completion:** Passed at design level. One transaction, fixed locks, expected versions, ownership, command idempotency, and all-or-nothing writes are specified.
8. **One nonterminal Current Change:** Passed at design level through a partial unique index plus command handling.
9. **Recovery-first behavior:** Passed. Temporary lifecycle, promotion, purge, preference survival, and minimized learner-evidence survival are explicit.
10. **Active Plan Item edits:** Passed. Current Change snapshots are stable and removal requires one of two explicit commands.
11. **Learner evidence vs telemetry:** Passed. Learner Evidence is an MVP product domain; telemetry tables are deferred.
12. **GitHub/webhooks/achievements cut:** Passed. Manual Build is first; read-only GitHub is later; webhooks and character economy are deferred.
13. **Sensitive V2 state not exposed to the frontend Data API:** Passed at architecture level. Browser roles have no V2 table/RPC privileges; FastAPI is the product boundary.
14. **Physical schema handoff:** Passed at design level through the canonical Schema and Persistence Design. No migration or runtime verification is claimed.

## Verification boundary

This audit verifies internal design consistency against the canonical V2 product/UX sources and the resolved founder decisions. It does not claim that schema, RLS, RPC security, application behavior, accessibility, or deletion has been implemented. Those claims require migrations, tests, and rendered/runtime verification in the authorized implementation phase.
