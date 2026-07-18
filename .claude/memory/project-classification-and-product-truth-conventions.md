# Project classification and product-truth conventions

M18A separates product capability from the student's experience using AI.
Intake Q1–Q3 (purpose, scope, stack) are project evidence. Q4 is a learning-
context self-assessment and may calibrate explanations only; provider names,
AI-generated-code language, multi-file confusion, and use of ChatGPT, Claude,
Codex, Cursor, or similar tools never independently make the product AI-powered.
No provider call performs classification.

## Classification and exclusions

Positive AI-product evidence must describe intended behavior: calling an LLM,
an AI assistant/chatbot, or generating/summarizing/analyzing content through a
model. Bounded explicit exclusions cover AI features, accounts/auth, database,
backend/API, notifications, and calendar integration. A clear exclusion wins a
conflict deterministically; do not implement keyword stripping.

StudyFlow is the permanent regression: a plain HTML/CSS/JavaScript homework
tracker using browser local storage, with no accounts/backend/database/AI/
notifications/calendar, remains archetype id 3 but is labeled `Browser App`.
Its deterministic seven-phase roadmap contains no LLM/provider/API key,
Python/FastAPI, backend, auth, conversation history, database, or invented
framework. The rule is capability-based and must also hold for differently
named local browser apps. Legitimate product-focused AI behavior remains
archetype 1.

The roadmap prompt explicitly marks self-assessment as student context only.
For browser-local projections, the projected template is the strict structural
source of truth and an additive scope validator rejects excluded systems.
Structural/provenance/schema validation is never weakened; invalid provider
output is discarded and the existing deterministic fallback path is used.

## Journey and Defense truth

`frontend/lib/workflowJourney.ts` owns the exact canonical Journey:

Prompt Builder → Bring Back What Changed → Change Map → Review → Verification
→ Evidence → Project Defense → Defense Report.

All student-facing workflow summaries must derive from it or preserve that
exact order. External AI generation is between Prompt and Import, not a Codize
route or ninth stage. Do not present obsolete Plan, Generate, Explain, or
Commit/Reflect entries as implemented routes.

Formal Defense vocabulary is: `not_ready`, `ready`, `in_progress`, `cooldown`,
`retry`, `complete`. Route availability is not readiness. Before a new attempt,
the backend requires typed Import, compatible/current Change Map, Review,
Verification, Evidence, and all phase build tasks. Import-first recovery may
omit a retrospective Prompt. Blocked direct routes show prerequisites and the
real shared Continue action; they do not render Begin. No separate early
practice action exists in M18A. A created attempt remains stable/resumable;
questions, evaluator, scoring, thresholds, PASS/FAIL, retries, and cooldowns
are unchanged.

## Change Map recovery

Generation failure must preserve Import, any readable existing map, local
student drafts, and every downstream readiness boundary. UI recovery is one
focused alert with the smallest safe correction, explicit retry, Import review,
and—only when no map exists—explicit manual creation. Manual recovery starts
empty, is bound to the saved Import, has no AI claims or fabricated source
references, refuses overwrite, and requires a student-authored item before
confirmation. It never creates Review/Verification/Evidence or unlocks Defense.

## Exact M18B seam

M18B may begin the information-architecture work that M18A deliberately leaves
alone: merge Phase Workspace into Project Home and bind Prompt Builder to an
explicitly selected phase assignment/task. It must consume the M18A classifier,
canonical Journey, Defense-readiness, and Change Map recovery contracts rather
than redefining them. M18A does not remove routes, redesign the tutorial, add a
learning system, or implement assignment selection.
