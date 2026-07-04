# Frontend conventions (Milestone 13C)

The frontend lives in `frontend/` — Next.js App Router, React 19, TypeScript
strict, vitest. It is the v3 **AI Workflow Workspace** (see [[product-vision-v3]]),
built as an engineering cockpit, NOT a roadmap/checklist/quiz app.

**Architecture is non-negotiable: Frontend → FastAPI → external services.**
Supabase is used for **AUTH ONLY** (`lib/supabase.ts`, lazy singleton so
importing never throws at build/prerender without env). All product data flows
through `lib/api.ts`, which attaches the Supabase Bearer JWT to every call. The
anon/publishable key is public by design; RLS + backend enforce access. Never
add a service-role or provider key to any `NEXT_PUBLIC_*` value — it bundles
into client JS. Env contract: `frontend/.env.example` (URL, anon key, API base).

`lib/api.ts` is the single boundary: 4xx `{error:{message}}` bodies are safe
client strings by backend design and shown as-is; 5xx bodies are never
surfaced (generic message). `lib/types.ts` mirrors the backend response shapes
as-built — do not invent fields the backend doesn't send. `useWorkflowSection`
is the shared load/save state machine for the four Build Loop artifact pages
(409 → `notReady`, points at intake).

Reconnection invariant carried into the shell (`app/app/layout.tsx`): GET
`/reconnection` FIRST, then acknowledge — immediately when not needed, on the
"Let's keep building" click when it is. One check per browser session via a
`sessionStorage` flag; fail-open (never block the workspace). Modal is
dismissed only by the button — no timer/click-outside/Escape (see
[[reconnection-conventions]]).

Prompt Builder is deterministic and CLIENT-SIDE (`lib/promptBuilder.ts`, pure,
unit-tested) — no LLM call; output is pasted into the student's own AI tool.
The four artifact pages save via `PUT /workflow/{phase}/{section}` full-section
replace and prefill from `GET /workflow/{phase}` (see
[[workflow-artifact-conventions]]). Slice inputs to the backend caps
(300/2000/8000) client-side too.

M13C.1 scope done: landing (80% Trap), auth, protected shell, intake, cockpit,
phase board, Prompt Builder, Review Board, Evidence Panel, Verification Lab,
API client, honest async states.

**M13C.2 done — the Build Loop is now walkable end-to-end.** Two headline
surfaces went from placeholder to live:

- **Project Defense gate** (`app/app/gate/page.tsx`): the full M9 flow —
  `POST /gate/start` → `turn1` (anchor) → `turn2`/`turn3` (submit prior answer,
  get next question) → `evaluate` (verdict). The page's local `gate` state IS the
  `GateCurrent` shape and is advanced from each POST response (no full reload,
  no transcript flash); `GET /gate/current` is used only on load, which makes
  **resume free** (turns[] + next_action restore the transcript — live-verified).
  `next_action` drives the whole state machine: turn1=anchor input, else the last
  (unanswered) turn is the pending question and its endpoint = next_action. 422
  (bad anchor) and 502 (LLM fail) leave the session where it was, so the typed
  input is kept and the same step is retryable. The PASS screen shows the
  evaluator's one-sentence reason + any `new_unlocks`; do NOT reload after
  evaluate (a non-final PASS advances current_phase, so GET would show the *next*
  phase). Gate is **not evidence-aware** — workflow artifacts are reference-only,
  never evaluator input (spec-guardian-gated future change). v3 language:
  "Project Defense", "defend what you built", never "quiz"/"cheating".
- **Project Defense Report** (`app/app/report/page.tsx` + pure `lib/report.ts`,
  unit-tested like `promptBuilder.ts`): client-assembled from evaluation + intake
  answers + current-phase workflow sections + `GET /gate/current` + current phase.
  No report endpoint (client-assembled per the M13 plan). Export = copy Markdown
  (+ download .md). **Honesty rules baked in**: missing artifacts say "missing",
  verification is labelled self-reported, and `defenseStatus` reflects the CURRENT
  phase's gate state ONLY — a prior-phase pass shows as a separate "latest gate
  note", never conflated into "this phase passed" (the project-level "passed any
  gate?" signal lives in the Skills section, keyed off `completed_phases`).
  Interview questions are derived client-side (no LLM). Archetype id→name is a
  fixed 3-entry map (never a fourth). Never renders raw HTML; artifacts are plain
  text; no score/evaluator-reasoning/threshold/key ever appears in the export.

Favicon added at `app/icon.svg` (Next serves it as the tab icon — kills the
benign 404). Sidebar/cockpit gate label is now "Project Defense" (v3).

Live browser smoke (2026-07-04, real FastAPI + Supabase): full walk — SQL test
user → intake (5 Qs) → roadmap (personalized, 7-phase full-stack) → save a
Prompt Builder artifact → **full gate PASS** (anchor + 3 real Gemini turns +
temp-0 evaluate; also verified mid-flow resume) → report shows real data with
corrected defense status → copy Markdown (verified clean: no score/service-role/
Gemini/JWT leakage) → logout. All green; the one oddity (flash-lite leaking
"valid anchor…" preamble into the Turn 1 question text) is a backend gate-prompt/
model quirk, NOT a frontend bug and out of M13C.2 scope — the UI faithfully shows
whatever the backend returns. Historical M13C.1 note: a gate "start" button with
no turn UI would strand the user — that constraint is now satisfied by the full
flow.

Backend touch during M13C.1 (only one): `intake_service._build_status` now
returns an `answers` dict keyed by question key (purpose/scope/…) — owner-scoped
data the cockpit "mission" card and intake transcript echo. No other backend
change; the cockpit REQUIRES the intake purpose, and evaluation deliberately
doesn't carry it (see [[evaluation-conventions]], [[intake-engine-conventions]]).

Live smoke pass (2026-07-03, after commit `03e3c1f`): drove the full flow in a
real browser (Playwright) against the live FastAPI backend + Supabase — all 20
steps green, zero 500s, **no frontend/API integration bugs found**. Run the
backend with the repo-root `.env` via `uvicorn app.main:app --env-file ../.env`
from `backend/`; the frontend needs `frontend/.env.local` (public Supabase URL +
publishable key + `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`). Email
confirmations are ON, so create a login-capable test user directly via SQL (the
[[gotrue-sql-test-users]] pattern), and clean it up after.

Two live observations (NOT M13C.1 bugs, left as-is): (1) roadmap generation
drifted and returned 502 three times in a row with `GEMINI_MODEL=
gemini-2.5-flash-lite` at temp 0.7 — the fail-closed validator + the intake
page's retry message handled every 502 correctly, but flash-lite preserves the
template structure poorly. **FIXED in M13C.1B**: roadmap generation now falls
back to a deterministic template-backed roadmap on drift/failure, so a real
tester is no longer blocked (no manual seeding) — see
[[roadmap-llm-conventions]]. (2) Missing `favicon.ico` logs a benign 404 on
every page — cosmetic, deferred.
