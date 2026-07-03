# M13 — AI Workflow Workspace MVP: Implementation Plan

Planning artifact from the M13A session (2026-07-03). Backend state: M1–M12
complete at `44442b0`; product vision reset at `139d898`. Authority: product
direction from `codize_product_vision_v3.md`, backend/security/gate invariants
from `codize_master_spec_v2.1.md` (see `context_authority.md`).

This document contains **no implementation** — it is the plan for the milestone
sessions that follow it.

## Bottom line

**M13 needs a small backend mini-milestone first.** Recommended split:

- **M13B — Workflow Artifact Store (backend mini-milestone):** one JSONB
  column on `projects` (`workflow_artifacts`, following the M8 `task_progress`
  precedent), one service, one router with two routes
  (`GET /workflow/{phase}`, `PUT /workflow/{phase}/{section}`). No LLM, no new
  table, no new RLS policies, no change to any existing service.
- **M13C — AI Workflow Workspace frontend (Next.js on Vercel):** all twelve
  surfaces, calling the existing backend plus the M13B routes.

Reason: four of the new v3 surfaces (Prompt Builder output, Review Board,
Evidence Panel, Verification Lab) produce student-authored artifacts that are
the **raw material of the Project Defense Report — the product's main payoff**.
Client-only storage (localStorage) would make the payoff ephemeral: lost on
device change or cache clear, invisible to pilot measurement, and gone from
any future evidence-aware gate. Everything else in M13 works against existing
routes unchanged.

---

## 1. Surface-by-surface analysis

Persistence-decision key: **(1)** client-only for v0.1 · **(2)** stored in
existing backend fields · **(3)** small backend addition before frontend ·
**(4)** deferred past v0.1.

| # | Surface | User job-to-be-done | Existing backend support | Missing backend support | MVP persistence | Frontend components | Build now? | Risk | Recommendation |
|---|---------|--------------------|--------------------------|-------------------------|-----------------|--------------------|-----------|------|----------------|
| 1 | Landing page (80% Trap) | Understand what Codize is and why I need it; sign up | None needed | None | None (static) | Hero, problem/solution/payoff sections, CTA → signup | **Yes** | Low | Build in M13C. Copy per v3 doc ("Stop Debugging Blindly"); no backend calls |
| 2 | Auth flow | Sign up / log in and land in my workspace | Complete: Supabase Auth direct from frontend (the one allowed exception, publishable key); backend verifies JWT via JWKS; signup trigger creates profile with `last_login_at` default | None | None (Supabase session) | supabase-js client, signup/login forms, session provider, route guard | **Yes** | Low | Build in M13C. Spec invariant: signup goes **straight to intake Q1** — no dashboard/homepage between |
| 3 | Project Cockpit | See where I am, what state my project is in, and what to do next | Strong: `GET /evaluation` (readiness state + next_action), `GET /reconnection` (modal contract), `GET /phases/current`, `GET /unlocks` | Loop-step position (which of the 7 Build Loop steps I'm on) | **(2)+(3)** — derived client-side from evaluation state + M13B artifact completeness | Cockpit shell, state banner, next-action card, loop-step indicator, unlock list, reconnection modal | After M13B | Med | Core M13C screen. Loop-step position is **derived, not stored**: evaluation state machine + which artifact sections exist for the current phase |
| 4 | Intake | Answer the five questions and get my project classified | Complete: `GET /intake/questions`, `GET /intake/status`, `POST /intake/answers`, `POST /intake/complete` (sequential enforcement, 409/422 handled server-side) | None | Already on `projects` | Conversational question UI, answer input, progress dots, completion → roadmap generation call | **Yes** | Low | Build in M13C. Keep the spec's conversational framing (Q1 verbatim, unskippable). v3 reframes copy only ("project setup and build context") |
| 5 | Phase Workflow Board | See my roadmap phases, current phase content, and tick tasks | Complete: `GET /phases`, `GET /phases/current`, `GET /phases/{n}`, `PATCH /phases/{n}/tasks/{task_id}`; `POST /roadmap/generate` + `GET /roadmap` | None | Already on `projects` (`roadmap`, `task_progress`) | Phase nav, phase detail (concept, AI/human task lists with checkboxes, security constraints, gate target), loop-step framing around the tasks | **Yes** | Low | Build in M13C. Presentational reframe: phases are laps of the Build Loop, not a checklist page. Task ticking never advances phases (gate does) — UI must reflect that |
| 6 | Prompt Builder | Turn my phase context into a strong prompt for my external AI tool | None | Storage for generated prompt + plan inputs (feeds Defense Report) | **(3)** — M13B `plan`/`prompt` sections. Generation itself is **client-side and deterministic** — no LLM | Structured input form (goal, files, constraints, what-not-to-change, checks wanted), template assembler, output card with copy button, "why this is stronger" explainer | After M13B | Med | **Deterministic template assembly, no LLM call**: first-value in minutes, zero provider cost, no new prompt file (prompt files are spec-governed artifacts), no new adversarial surface. Optional LLM polish is a v2 idea |
| 7 | Review Board | Record what the AI tool changed and what I accepted/rejected/edited | None | Storage for review answers (feeds Defense Report now, evidence-aware gate later) | **(3)** — M13B `review` section | Structured form (files changed, generated/accepted/rejected/edited, AI assumption, least-confident area, out-of-scope changes), saved-state display | After M13B | Med | The pivotal v3 surface — turns passive prompting into active engineering. Pure form + storage; no backend logic beyond validation |
| 8 | Evidence Panel | Attach manual evidence (repo URL, commit hash, pasted output, screenshots-as-links) | None | Storage for evidence entries | **(3)** — M13B `evidence` section (list of typed entries) | Evidence list, add-entry form (type + content), per-entry display | After M13B | Med | Manual, self-reported evidence only — consistent with the spec's anchor-statement caveat (code submission is explicitly v2). Strict server-side size caps on pasted content |
| 9 | Verification Lab | Prove the code works: run the phase-appropriate checks and record results | None | Storage for checklist results + notes | **(3)** — M13B `verification` section | Checklist UI (generic engineering checks per v3 doc: runs locally, smoke test, one failure case, secrets check, wrong-user check where relevant), result + note per check, link to evidence | After M13B | Med | v0.1 verifies **workflow behavior, not code correctness** — checklist + self-reported results. No automated verification of arbitrary projects |
| 10 | Evidence-Based Gate | Defend what I built and unlock the next phase | Complete: full M9 gate flow (`POST /gate/start`, turn1–3, evaluate, `GET /gate/current`) incl. anchor validation, cooldown with Retry-After, resume-in-flight, `new_unlocks` on PASS | Feeding review/evidence into gate prompt context (deliberately absent) | Already on `gate_sessions` | Gate conversation UI (anchor prompt → 3 turns → verdict), cooldown timer, resume view, pass celebration with unlock reveal | **Yes** | Med | Use the M9 gate **as-is**. "Evidence-based" in v0.1 = UX framing ("defend the work you just reviewed") + the student naturally anchoring on their own evidence. Wiring artifacts into gate prompts is **deferred** — spec-guardian-gated backend change (see v3 doc) |
| 11 | Project Defense Report / Evaluation Summary | Leave with shareable evidence that I planned, prompted, reviewed, verified, and explained | Strong: `GET /evaluation` (state, counts, recent_gate, next_action), `GET /phases`, `GET /unlocks`, `GET /intake/status` | Aggregated report endpoint (not needed — composable client-side); workflow artifacts (M13B) | **(2)+(3)** — assembled **client-side** from existing GETs + `GET /workflow/{phase}`; nothing new stored | Report view (project summary, per-phase workflow artifacts, gate outcomes, unlocks, readiness, interview-style questions derived from anchors/review answers), copy-as-markdown button | After M13B | Med | No new backend endpoint for v0.1 — the report is a **view over data that already exists** once M13B lands. Backend already guarantees no scores/thresholds can leak into it. PDF export deferred |
| 12 | Pilot analytics / survey hooks | (Operator) measure pilot usage; (student) give feedback | Implicit: pilot metrics are **already derivable from existing tables** — projects started, gates attempted/passed (`gate_sessions` rows), unlocks granted, artifact completeness (M13B column) | Product analytics/event pipeline (not worth building) | **(1)** survey link client-side + **(2)** operator SQL over existing data | Feedback link (external form) in the cockpit footer | **Yes** (survey link) | Low | **Defer product analytics.** Ship a documented operator SQL script (`scripts/pilot_metrics.sql`) + a static survey link. Before/after-confidence questions live in the external survey, not the product |

---

## 2. Backend route map

Every route is JSON over HTTPS with `Authorization: Bearer <supabase access
token>` (except `/health`); CORS is configured in `main.py`; the standard
error shape is `core/errors.py`'s. **All are directly callable from the
frontend** — no proxy or BFF layer needed.

| Route | Currently supports | M13 surface(s) | Gaps | Frontend calls directly? |
|-------|--------------------|----------------|------|--------------------------|
| Supabase Auth (direct, publishable key) | Signup, login, session refresh, JWT issuance; signup trigger creates profile | Auth flow (2) | None | Yes — the one documented exception to Frontend→Backend-only |
| `GET /health` | Liveness (public) | Deploy checks | None | Yes |
| `GET /archetypes`, `GET /archetypes/{id}` | Read-only archetype templates | Optional: intake result display, phase board context | None | Yes |
| `GET /intake/questions` | The five spec-verbatim questions | Intake (4) | None | Yes |
| `GET /intake/status` | Which questions answered, verbatim answers, classification | Intake (4), Cockpit (3), Defense Report (11) | None | Yes |
| `POST /intake/answers` | Sequential answer submission (409 out-of-order, 422 bad input) | Intake (4) | None | Yes |
| `POST /intake/complete` | Completion + deterministic classification | Intake (4) | None | Yes |
| `POST /roadmap/generate` | LLM generation, fail-closed validation, status flip to 'active' (409/502) | Intake→workspace transition (4→5) | None. UI must handle 502-then-retry as a normal path (live-observed in M8) | Yes |
| `GET /roadmap` | The stored personalized roadmap | Phase Workflow Board (5) | None | Yes |
| `GET /phases`, `GET /phases/current`, `GET /phases/{n}` | Phase views incl. tasks with completion, functional_unlock description, gate target | Board (5), Cockpit (3), Report (11) | None | Yes |
| `PATCH /phases/{n}/tasks/{task_id}` | Task ticking (never advances phases) | Board (5) | None | Yes |
| `POST /gate/start` | Eligibility + cooldown check (409 + Retry-After), session creation | Gate (10) | None | Yes |
| `POST /gate/{id}/turn1` | Anchor validation (422) → Turn 1 question | Gate (10) | None | Yes |
| `POST /gate/{id}/turn2`, `/turn3` | Answer storage + next question, one write per turn (retryable on 502) | Gate (10) | None | Yes |
| `POST /gate/{id}/evaluate` | Temp-0 verdict (PASS/FAIL + one-sentence reason, `new_unlocks` on PASS); score never returned | Gate (10), unlock reveal (3) | Evidence-aware prompt context — **deliberately deferred**, spec-guardian-gated | Yes |
| `GET /gate/current` | Gate state: not started / in-progress with transcript / cooldown / passed | Gate resume (10), Cockpit (3) | None | Yes |
| `GET /unlocks` | Earned unlocks, safe fields only (empty list pre-roadmap) | Cockpit (3), Report (11) | None | Yes |
| `GET /reconnection` | Four controlled states; safe summary with verbatim purpose (pure read) | Reconnection modal (in 3) | None | Yes — **contract: GET first on every login, then acknowledge** |
| `POST /reconnection/acknowledge` | Sets `last_login_at` (the only writer) | Reconnection modal | None | Yes — immediately when not needed; on "Let's keep building" click when needed |
| `GET /evaluation` | Deterministic readiness state + counts + recent_gate + next_action (pure read, controlled 200s) | Cockpit (3), Report (11) | None. Does not know about workflow artifacts (fine for v0.1 — loop-step position derives client-side) | Yes |
| *(missing)* `GET /workflow/{phase}` | — | Prompt Builder (6), Review Board (7), Evidence (8), Verification (9), Report (11) | **The M13B gap** | Will be |
| *(missing)* `PUT /workflow/{phase}/{section}` | — | Same | **The M13B gap** | Will be |

**Gap summary:** the entire existing API surface carries surfaces 1–5 and
10–12 with no changes. The only gap is durable storage for student-authored
workflow artifacts (surfaces 6–9), which also unlocks the full Defense Report
(11). Nothing else is missing.

---

## 3. The persistence decision (surfaces 6–9)

Options considered for Prompt Builder outputs, Review Board answers, Evidence
entries, and Verification results:

- **Client-only (localStorage)** — rejected for core artifacts. The Defense
  Report is the product's main payoff and must survive devices/sessions;
  pilot measurement needs the data; a future evidence-aware gate needs it
  server-side. (Fine for in-progress form drafts before save.)
- **Existing backend fields** — rejected. No existing column fits:
  `task_progress` has a pinned shape and convention (completed ids only),
  `roadmap` is immutable by invariant, intake fields are spec-defined.
  Overloading any of them would violate documented conventions.
- **New `workflow_artifacts` table** — workable but bigger than needed:
  migration + RLS policies + grants + a new repository. Typed rows buy
  nothing at MVP scale (one student, one project, one loop per phase).
- **`workflow_artifacts` JSONB column on `projects`** — **chosen.** Exact
  precedent: M8's `task_progress` column (`20260703015217` migration —
  "same ownership model as every other projects column: RLS owner policies").
  Ownership, RLS, and client read access are inherited; artifacts live
  outside the `roadmap` JSONB so they can never mutate roadmap structure;
  one milestone-sized change.

Proposed shape (keyed by phase number, sections named after Build Loop steps):

```json
{
  "1": {
    "plan":         { "goal": "...", "constraints": "...", "not_building": "..." },
    "prompt":       { "generated_prompt": "...", "inputs": { }, "created_at": "..." },
    "review":       { "files_changed": [], "ai_generated": "...", "accepted": "...",
                      "rejected": "...", "edited": "...", "ai_assumption": "...",
                      "least_confident": "...", "out_of_scope_changes": "..." },
    "evidence":     [ { "kind": "repo_url|commit|terminal_output|screenshot_note|api_response|note",
                        "content": "...", "added_at": "..." } ],
    "verification": { "checks": [ { "id": "runs_locally", "result": "pass|fail|skipped", "note": "..." } ] },
    "reflection":   { "what_changed": "...", "ai_helped": "...", "i_decided": "...",
                      "i_verified": "...", "still_weak": "...", "commit_message": "..." }
  }
}
```

Exact field lists are M13B's decision — the plan pins only: keyed by phase,
one object per Build Loop section, strict Pydantic validation with hard size
caps (user input reaching the DB is a validation boundary; pasted terminal
output needs a length ceiling, evidence lists a count ceiling).

**M13B guarantees (mirroring existing conventions):**

- Writing artifacts never mutates `roadmap`, `task_progress`, gate state, or
  unlocks, and never advances phases — storage only.
- `PUT /workflow/{phase}/{section}` is an idempotent full-section replace
  (simplest correct semantics; no merge/PATCH logic).
- Eligibility reuses `phase_service.load_active_project` (workspace not ready
  → 409, unknown phase → 404, invalid body → 422), like every workspace route.
- Artifacts are the student's own words — nothing hidden, nothing derived from
  scores. No leak surface is created; leak tests still assert no
  score/threshold/prompt strings.
- No LLM call anywhere in M13B.

---

## 4. Recommended M13 scope

### M13B Must Build (backend mini-milestone, one session)

1. Migration: `alter table public.projects add column workflow_artifacts
   jsonb not null default '{}'::jsonb` (follow the `task_progress` migration
   precedent, including its grant/RLS notes; verify with supabase MCP +
   `verify_rls.sql` after).
2. `services/workflow_service.py` + repository accessor on
   `ProjectRepository` (read column / patch column, ownership-filtered like
   every other query).
3. `routers/workflow.py`: `GET /workflow/{phase}`, `PUT
   /workflow/{phase}/{section}`; `schemas/workflow.py` with per-section
   models and size caps.
4. Tests (service + routes: lifecycle, validation caps, 409/404/422,
   pure-storage row comparison for non-artifact columns, leak test,
   cross-user isolation) + live smoke against real Supabase.

### M13C Must Build (frontend, likely 2–3 sessions)

Next.js (App Router) on Vercel, desktop browser only (spec: "no mobile
requirement"), visual style per `.claude/skills/ui-ux/SKILL.md` (dark,
high-contrast, violet accent — "engineering cockpit", not IDE):

1. Landing page (80% Trap copy per v3 doc) + auth (supabase-js), signup →
   straight to intake Q1.
2. Intake conversation UI → roadmap generation (with 502-retry UX).
3. Project Cockpit: evaluation-state banner, next-action card, loop-step
   indicator, unlocks, **reconnection modal** (spec invariants: renders
   before workspace when `reconnection_needed`, verbatim purpose in large
   text, dismissed only by "Let's keep building" — no timer/click-outside/
   Escape; GET-then-acknowledge ordering).
4. Phase Workflow Board (phases + task ticking, framed as Build Loop laps).
5. Prompt Builder (deterministic client-side assembly; saves via M13B).
6. Review Board, Evidence Panel, Verification Lab (forms over M13B routes).
7. Gate UI: anchor → 3 turns → verdict; cooldown timer from Retry-After;
   resume from `GET /gate/current`; unlock reveal on PASS.
8. Project Defense Report view (client-assembled; copy-as-markdown).
9. Survey link in footer.

### Should Build If Easy

- "Bad prompt to avoid" comparison in the Prompt Builder (static examples).
- Qualitative Defense Readiness indicator derived from evaluation state +
  artifact completeness (labels only — never numbers/scores, per spec).
- `scripts/pilot_metrics.sql` operator queries (counts over existing tables).
- Interview-style questions in the report derived from the student's own
  anchor statements and review answers (client-side text assembly).

### Defer (past v0.1)

- Evidence-aware gate prompt context (backend + spec-guardian review + new
  adversarial testing round — its own milestone if pursued).
- Rescue Mode as a distinct flow (v3 doc: reuse the core workflow for MVP).
- Product analytics/event pipeline; PDF/export beyond copy-as-markdown.
- GitHub OAuth, repo scanning, commit diff analysis, automated verification.
- LLM-assisted prompt generation or report wording.
- `phase_explanation.md` prose streaming (unchanged deferral since M8).
- Browser IDE, AI news, community, tool marketplace, mobile (v3 exclusions).

---

## 5. Frontend-only vs. backend mini-milestone: the answer

**Do the small backend mini-milestone (M13B) first.** Frontend-only M13 would
force the four artifact surfaces into localStorage, which hollows out the
Project Defense Report (the main payoff), loses pilot data, and creates a
migration problem later. The mini-milestone is deliberately tiny — one column
(exact `task_progress` precedent, no new table, no new RLS), one service, two
routes, no LLM — and it converts the Defense Report from "ephemeral demo" to
"durable evidence" for the cost of roughly one milestone session.

Suggested sequence: **M13B (workflow artifact store) → M13C (workspace
frontend) → M14 (security audit) → M15 (deployment)**, one session each per
the standard milestone workflow.

## Open items for the M13B/M13C sessions (not decided here)

- Exact per-section field lists and size caps (M13B, with spec-guardian read).
- Whether `GET /evaluation` should later surface artifact completeness
  (deferred — M12's evaluation stays untouched in M13; loop-step position
  derives client-side).
- Next.js data-fetching approach and component library choice (M13C, with
  `ui-ux` skill as the style authority).
