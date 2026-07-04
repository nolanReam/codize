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
API client, honest async states. **Gate and Report pages are honest
placeholders** — they do REAL backend reads (`GET /gate/current`, evaluation +
workflow) but defer the interactive gate turn flow and full report assembly to
**M13C.2**. Do not add a gate "start" button in M13C.1 — starting a session
with no turn UI strands the user mid-flow.

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
template structure poorly; consider a stronger model for roadmap gen (M7
concern, not frontend). To unblock downstream smoke steps, seed a valid roadmap
by writing the archetype template (read as UTF-8!) into `projects.roadmap` +
`status='active'` via the real repo. (2) Missing `favicon.ico` logs a benign
404 on every page — cosmetic, deferred.
