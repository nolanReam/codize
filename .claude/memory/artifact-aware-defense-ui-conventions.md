# Artifact-aware defense UI conventions (Milestone 14C)

M14C makes the M14B grounding VISIBLE without exposing it: the student learns
what Codize can draw on, never what the pack contains.

**The endpoint is metadata-only, forever:** `GET /gate/context-summary`
(gate router) → `defense_context_service.build_context_summary(repo, user_id)`
→ `summarize_defense_context(pack)` → `DefenseContextSummary`
(schemas/defense_context.py). It carries source ids, display labels
(`SUMMARY_LABELS` — deliberately separate from the honesty-bearing manifest
labels the LLM sees), source types, present/missing state, per-source
truncation flags, `has_truncation`, `phase_number`, `artifact_aware`. It must
NEVER carry artifact text, intake answers, generated prompts, rendered
context, grounding terms, question metadata, or identity/profile data —
`test_context_summary.py` asserts serialized output against every
content-bearing fixture string. Phase is server-derived (`current_phase`, the
phase the gate defends) — no client phase input. Pure read, no LLM (the route
takes only the ProjectRepository dependency), no migration. Errors reuse the
workspace conventions: not ready → 409, corrupt phase → 404.

**Ownership by construction:** no project/user id parameter exists; the
summary is always for the authenticated user's own newest project. Another
user hitting the route gets THEIR workspace state (usually 409), never the
owner's metadata.

**No source-completeness gating:** missing artifacts are optional and phrased
as such ("not added yet — optional, you can still continue", links to the
workflow pages). Never "incomplete"/"failed"/"not ready", never red styling,
and the Begin button is NEVER disabled by summary state — gate readiness is
the backend's 409, not the summary's contents. A summary fetch error is a
non-blocking muted fallback line; the gate stays fully usable.

**No evidence-as-proof language:** the UI says questions "draw from the work
you recorded"; the personalization disclosure states recorded notes are
self-reported and don't prove correctness. Never imply Codize verified the
implementation.

**No per-question provenance:** the active-question label is a static
"Grounded in your project" eyebrow — the frontend must never infer or claim
WHICH source produced a question (grounding metadata is server-internal). If
per-question attribution is ever wanted, that's a new deliberate backend
change, not a frontend inference.

**Frontend helpers are pure** (`lib/defenseContext.ts`, unit-tested like
promptBuilder/report): `groupSummary` (workflow chips in Build Loop order —
prompt → review → evidence → verification; system sources collapse into ONE
"Project context" pill, never eight cards), `preparationTips` (deterministic
per-source prep lines + the sparse fallback "Your anchor and phase context
are enough to begin."), `missingNote`, `WORKFLOW_PAGE_LINKS`. No LLM.

**Refresh model:** no polling and no query library — the gate page fetches
the summary fresh on every mount (separate effect from the gate load, so a
slow summary never blocks the page), which covers "updated after workflow
saves" because saves happen on other pages. Chips are `span.pill ok` (✓ +
label — readable without color); progressive disclosure holds: one short
visible line + collapsed `details.help` ("How are my questions
personalized?", "Prepare in 30 seconds"); truncation surfaces as one muted
line ("Some long notes were shortened…"), never limits or alarm.

**Stale-copy fix worth remembering:** the gate rail said "The gate doesn't
read your saved artifacts" — true in M13, false since M14B. It now reads:
questions can draw on recorded work, pass/fail is decided only by how well
YOU explain your implementation (the evaluator is artifact-blind — keep both
halves of that sentence together in any rewrite).
