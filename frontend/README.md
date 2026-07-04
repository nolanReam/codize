# Codize frontend (M13C)

The Codize v3 **AI Workflow Workspace** — a Next.js (App Router) frontend that
makes the Codize Build Loop visible and usable:

**Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect**

It is an engineering cockpit, not a roadmap/checklist/quiz app. Design language:
high-contrast dark, violet accent, mono for technical text (see `app/globals.css`
and the `ui-ux` skill).

## Architecture

Strictly **Frontend → Backend → External services**. The frontend never talks to
Supabase data tables or LLM providers directly.

- **Supabase is used for auth only** (`lib/supabase.ts`). The publishable/anon key
  is public by design; RLS and the FastAPI backend enforce all access.
- **All product data flows through the FastAPI backend** (`lib/api.ts`), which is
  called with a Supabase Bearer JWT. Backend 4xx messages are safe client strings
  by backend design and are shown as-is; 5xx bodies are never surfaced.

## Layout

```
app/
  page.tsx              Landing page (the 80% Trap) — static, no auth
  login/page.tsx        Supabase email/password sign-up + sign-in
  app/
    layout.tsx          Protected app shell: session guard, sidebar nav,
                        reconnection check (GET /reconnection → acknowledge)
    page.tsx            Project Cockpit (evaluation + workflow + intake purpose)
    intake/page.tsx     Conversational five-question intake → roadmap generation
    phase/
      page.tsx          Phase Workflow Board (Build Loop + tasks + gate summary)
      prompt/page.tsx   Prompt Builder (deterministic, client-side)
      review/page.tsx   Review Board
      evidence/page.tsx Evidence Panel
      verify/page.tsx   Verification Lab
    gate/page.tsx       Interrogation Gate — status view (interactive flow: M13C.2)
    report/page.tsx     Project Defense Report — sources placeholder (full: M13C.2)
components/             Async, NotReady, SaveBar, WorkflowSteps, ReconnectionModal
lib/                    api client, supabase client, types, prompt builder + test,
                        useWorkflowSection hook
```

## Backend routes consumed

Intake (`/intake/*`), roadmap (`/roadmap/generate`, `/roadmap`), phases
(`/phases*`), workflow artifacts (`GET /workflow/{phase}`,
`PUT /workflow/{phase}/{section}`), reconnection (`GET /reconnection`,
`POST /reconnection/acknowledge`), evaluation (`GET /evaluation`), and gate status
(`GET /gate/current`). The interactive gate turn flow is not yet wired (M13C.2).

## Environment

Copy `.env.example` to `.env.local` and fill in:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — publishable/anon key only
- `NEXT_PUBLIC_API_BASE_URL` — FastAPI backend base URL, no trailing slash

**Never** put service-role keys or LLM provider keys here — every `NEXT_PUBLIC_*`
value is bundled into the client JS.

## Commands

```bash
npm install
npm run dev        # local dev server
npm run lint
npm run typecheck
npm run build
npm test           # vitest — deterministic prompt builder
```

## Status (M13C.1)

Complete: landing, auth, app shell + reconnection, intake, cockpit, phase board,
Prompt Builder, Review Board, Evidence Panel, Verification Lab, API client, and
honest loading/empty/error states. Placeholders (real backend reads, deferred
interactive UI): Interrogation Gate and Project Defense Report → **M13C.2**.
