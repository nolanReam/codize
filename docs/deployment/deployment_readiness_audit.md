# Codize — Deployment Readiness Audit (M13D)

> [!NOTE]
> **Current/historical V1 deployment snapshot.** Preserve its secret and hosting-boundary lessons, but re-verify every version, provider, command, and deployed state before use. It does not define V2 product behavior or architecture.

Snapshot of what it takes to run Codize for a first 3–5 tester pilot. No real
secret values appear here — only variable **names** and where they belong.

**As-built at:** commit `5fd7d9b` (pilot kit) · backend + frontend MVP complete.

---

## 1. Stack & commands (as they actually are in the repo)

### Frontend — `frontend/` (Next.js 15, App Router, React 19, TypeScript)

| Purpose | Command (run from `frontend/`) |
|---|---|
| Install | `npm install` |
| Dev server | `npm run dev` → `http://localhost:3000` |
| Type check | `npm run typecheck` (`tsc --noEmit`) |
| Lint | `npm run lint` (`next lint`) |
| Unit tests | `npm test` (`vitest run`) |
| Production build | `npm run build` |
| Production start | `npm run start` (serves the built app) |

No custom rewrites/proxy (`next.config.ts` is intentionally empty) — the browser
calls the FastAPI backend directly with a Supabase Bearer JWT.

### Backend — `backend/` (FastAPI, async, uvicorn)

| Purpose | Command (run from `backend/`) |
|---|---|
| Create venv | `python -m venv .venv` |
| Install | `.venv\Scripts\pip install -r requirements.txt` |
| Dev server | `.venv\Scripts\uvicorn app.main:app --env-file ../.env --reload` |
| Tests | `.venv\Scripts\python -m pytest` |
| Prod-style start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (env vars supplied by the host) |

Deps (`requirements.txt`): `fastapi`, `uvicorn[standard]`, `pydantic-settings`,
`PyJWT[crypto]`, `httpx`, `pytest`. LLM calls use `httpx` directly — **no vendor
SDK to install**. Python **3.11+** recommended (code uses `list[str]` / modern
typing; there is no pinned `runtime.txt` yet — see Blockers).

> **Env-loading gotcha (important):** `core/config.py` sets `env_file=".env"`,
> resolved **relative to the working directory**. The real secrets live in the
> **repo-root** `.env`, so launching from `backend/` needs `--env-file ../.env`
> (or shell/host env vars). Without them the backend silently runs in no-key
> mode (LLM stub + unconfigured Supabase).

---

## 2. Environment variables

### Frontend (all **public** — bundled into client JS by design)

| Var | Meaning |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (auth only) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Publishable/anon key (public; RLS + backend enforce access) |
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI base URL, **no trailing slash** (`http://localhost:8000` locally) |

Contract file: `frontend/.env.example` → copy to `frontend/.env.local`.

### Backend

**Server-only SECRETS — never in any `NEXT_PUBLIC_*` value, never in docs/logs:**

| Var | Meaning |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Service/secret key; **bypasses RLS**; backend↔Supabase only |
| `GEMINI_API_KEY` | Gemini (primary LLM) |
| `OPENROUTER_API_KEY` | OpenRouter (fallback LLM) |

**Non-secret backend config:**

| Var | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `development` exposes `/docs`; set `production` when hosted |
| `SUPABASE_URL` | — | Project URL; JWKS URL is derived (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) |
| `SUPABASE_ANON_KEY` | — | Anon key (also fine server-side) |
| `LLM_PROVIDER` | `gemini` | `gemini` \| `openrouter` \| `stub` |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Stronger model → better roadmap personalization |
| `OPENROUTER_MODEL` | `cohere/north-mini-code:free` | Fallback model |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated exact origins; **never `*`** |

Contract file: repo-root `.env.example` → copy to repo-root `.env`.

### Public vs secret — the one rule

`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` are **secret**
and live only in the backend environment. Everything a `NEXT_PUBLIC_*` name
touches is **public**. The anon key is public *by design* (RLS + backend
enforce). (OWASP A02.)

---

## 3. Supabase auth assumptions

- Supabase is used for **auth only**; all product data flows Frontend → FastAPI →
  Supabase (service-role key, RLS-enforced ownership).
- The frontend sends `Authorization: Bearer <access token>`; `require_user`
  verifies signature via **JWKS/ES256**, `exp`, and `aud == "authenticated"`.
- **Email confirmations are ON.** Real self-signup requires an email round-trip;
  for pilot demos, create login-capable users directly via SQL (see the runbook
  and `scripts/verify_auth.sql`).
- Project ref (existing): `tadkbymxkdncqahzshml` (per `CLAUDE.md`).

## 4. CORS requirements

`main.py` configures `CORSMiddleware`:

- `allow_origins` = `CORS_ORIGINS` (exact origins, never `*`)
- `allow_credentials=True`
- `allow_methods=["GET","POST","PUT","PATCH","DELETE"]`
- `allow_headers=["Authorization","Content-Type"]`

**When hosted:** add the deployed frontend origin (e.g.
`https://codize.vercel.app`) to `CORS_ORIGINS`. Wildcard is forbidden and is
invalid alongside `allow_credentials=True` anyway.

## 5. Local ports

| Service | Port |
|---|---|
| Frontend (Next dev) | 3000 |
| Backend (uvicorn) | 8000 |
| Health check | `GET http://localhost:8000/health` → `{"status":"ok","service":"codize-backend","environment":"development"}` |

## 6. Known deployment blockers / gaps

1. **No hosted-deploy config committed** (no Procfile/Dockerfile/vercel.json/
   railway config). Not a bug — greenfield. `hosted_deployment_plan.md` provides
   ready-to-drop start commands; nothing is committed until you pick a host.
2. **Backend env-file is cwd-relative** (§1 gotcha). Hosts must inject env vars
   directly (they do by default) or you pass `--env-file`.
3. **CORS + API base URL are environment-coupled:** deployed frontend origin must
   be in backend `CORS_ORIGINS`, and `NEXT_PUBLIC_API_BASE_URL` must point at the
   deployed backend. A mismatch is the most likely first-deploy failure.
4. **No pinned Python version** (`runtime.txt`/`.python-version` absent). Pin
   3.11+ on the host to avoid a default-runtime surprise.
5. **Email confirmations ON** ⇒ real testers can't self-signup without email
   delivery. Pilot uses SQL-seeded test users; a public pilot would need
   confirmation email delivery configured in Supabase.
6. **LLM dependency for the gate:** roadmap generation has a deterministic
   fallback (never blocks onboarding), but the **Interrogation Gate needs a live
   provider** — a provider outage returns a retryable 502, not a fallback. Keep
   `GEMINI_API_KEY` valid for pilots.

None of these block a **local** pilot today; items 1–5 are the hosted-deploy
checklist.

## 7. Recommended path for the first pilot

**Run it locally, facilitator-hosted** (fastest, zero new infra, already
live-verified end-to-end in M13C.2). Use `local_demo_runbook.md` +
`pre_pilot_smoke_checklist.md`. Move to hosted (`hosted_deployment_plan.md`) only
when you want testers to self-serve without you present.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Secret leaks into the frontend bundle | Only `NEXT_PUBLIC_*` (public) values in `frontend/`; secret scan before commit; never import server keys in `frontend/`. |
| CORS/API-URL mismatch on deploy | Set both together; smoke-test `/health` and one authed call right after deploy. |
| flash-lite roadmap drift | Deterministic template fallback keeps onboarding unblocked (M13C.1B); optionally set a stronger `GEMINI_MODEL`. |
| Gate LLM outage mid-pilot | Retryable 502 leaves the session intact; verify the provider key in the smoke check before inviting testers. |
| Test users linger in the DB | Delete via `scripts/verify_auth.sql` CLEANUP after the pilot. |
| Runtime version drift on host | Pin Python 3.11+ and Node 20+ on the hosts. |
