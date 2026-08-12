# Codize — Friend Pilot Deployment Guide (M13F.1)

> [!NOTE]
> **Current/historical V1 deployment guide.** It does not define a V2 deployment or pilot flow.

The canonical step-by-step for hosting Codize so friends can test it
self-serve. Supersedes the outline in `hosted_deployment_plan.md` (kept for
history). Companion docs: `env_var_matrix.md` (every variable, where it
lives) and `hosted_smoke_checklist.md` (post-deploy verification).

**No real secret values appear in this doc.** Nothing here executes
automatically — every deploy is a manual action you take in a host dashboard.

---

## 1. Architecture

```
Browser ──HTTPS──> Next.js frontend (Vercel)
                       │ fetch() + Supabase Bearer JWT
                       ▼
                   FastAPI backend (Railway — recommended)
                       │ service-role key + LLM keys (server-only)
                       ▼
        Supabase (existing project: auth + DB) · Gemini / OpenRouter
```

Invariant preserved: **Frontend → Backend → external services.** The browser
holds only public values; every secret lives in the backend host.

## 2. Backend host — recommendation and why

**Recommended: Railway.** It matches the architecture planned in `CLAUDE.md`
("FastAPI, deployed on Railway"), needs zero code changes (the committed
`backend/Procfile` + `backend/.python-version` are picked up automatically),
and — decisive for a pilot — **does not sleep the service**, so a friend's
first request never hits a 30–60 s cold start. Cost: Hobby plan ~$5/month
(usage-based; a friend pilot stays well under it).

| Option | Verdict | Why |
|---|---|---|
| **Railway** | **Use this** | No sleep, Procfile auto-detected, simple root-directory setting, matches planned architecture |
| Render (free tier) | Zero-cost fallback | Works identically, but free instances **spin down after ~15 min idle** → 30–60 s cold start on a friend's first visit; fine if you accept that |
| Fly.io | Works, more setup | Needs a Dockerfile/`fly.toml`; no benefit at this scale |
| Vercel Python functions | **Not for this repo** | Would need restructuring into `api/` handlers; per-request time limits are risky for the ~30 s roadmap generation call; separates the backend from its Procfile/uvicorn layout for no gain. Don't force it |

### Railway setup (backend)

1. New project → "Deploy from GitHub repo" → pick this repo.
2. Service settings → **Root Directory: `backend`**.
3. Build: auto-detected from `requirements.txt`
   (`pip install -r requirements.txt`). Python version: from the committed
   `backend/.python-version` (3.12). If the builder ignores it, set the
   `PYTHON_VERSION` variable to `3.12` explicitly.
   *(Note: local dev currently runs Python 3.14 and the full test suite
   passes there; the code targets 3.11+, so any 3.11–3.14 runtime is fine.)*
4. Start command: auto-detected from `backend/Procfile` —
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Variables: set the **backend** list from `env_var_matrix.md`
   (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
   `GEMINI_API_KEY`, `APP_ENV=production`, `LLM_PROVIDER=gemini`,
   `GEMINI_MODEL`, optionally `OPENROUTER_API_KEY`/`OPENROUTER_MODEL`, and —
   after step 4 below — `CORS_ORIGINS`).
6. Settings → Networking → **Generate Domain**. You get
   `https://<service>.up.railway.app` — this is the backend URL.
7. Health check path: `/health`. Verify in a browser:
   `https://<service>.up.railway.app/health` →
   `{"status":"ok","service":"codize-backend","environment":"production"}`.
   (`/docs` must 404 — that confirms `APP_ENV=production`.)

Render equivalent: New Web Service → root dir `backend`, build
`pip install -r requirements.txt`, start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set `PYTHON_VERSION`,
same env vars, health check `/health`, URL `https://<service>.onrender.com`.

## 3. Frontend — Vercel

1. New Project → import the repo → **Root Directory: `frontend`**.
2. Framework preset: Next.js (auto). Install: `npm install`. Build:
   `npm run build`. Output: managed by Vercel (no config needed —
   `next.config.ts` is intentionally empty, no rewrites/proxy).
3. Environment variables (Production **and** Preview):
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_BASE_URL` = the backend URL from §2 step 6,
     **https, no trailing slash, no `/health` path**.
4. Deploy → note the production URL (`https://<app>.vercel.app`).

**Preview vs production:** previews get the same values unless you scope
them. That's fine for a pilot — but every preview URL that should work must
also be in backend `CORS_ORIGINS` and Supabase redirect URLs, so for
simplicity **test on the production URL** and treat previews as
frontend-only visual checks (login/API calls from previews will be blocked
by CORS unless you add them).

### Common `NEXT_PUBLIC_API_BASE_URL` mistakes

| Symptom | Cause | Fix |
|---|---|---|
| "The API is not configured" error in the app | Variable missing on Vercel | Add it, **redeploy** (build-time value) |
| Changed the var, nothing happened | Next.js inlines it at build | Trigger a redeploy after any change |
| "Couldn't reach the Codize backend" | Wrong URL / trailing slash / `http://` | Exact https backend origin, no trailing slash |
| Browser console shows CORS errors | Backend `CORS_ORIGINS` missing the Vercel origin | §4 below |

## 4. The two links that must agree (deploy order)

1. Deploy the **backend** first → note its URL.
2. Deploy the **frontend** with `NEXT_PUBLIC_API_BASE_URL` = that URL.
3. Note the frontend URL → set backend
   `CORS_ORIGINS=https://<app>.vercel.app,http://localhost:3000,http://localhost:3001`
   → restart/redeploy the backend.
4. Do the Supabase URL configuration (§5).

Keeping the localhost origins in `CORS_ORIGINS` keeps local dev working
against the hosted backend if you ever want that; they are harmless.

## 5. Supabase Auth URL configuration

Dashboard → Authentication → **URL Configuration** (project
`tadkbymxkdncqahzshml`). Do this in the dashboard — there is no repo script
for auth settings, and none should be added.

- **Site URL:** `https://<app>.vercel.app` (the production frontend).
- **Redirect URLs** (additional allow-list) — signup confirmation emails now
  link back to the origin the user signed up from
  (`emailRedirectTo = <origin>/login`, added in M13F.1), so list every
  origin that can host a signup:
  - `http://localhost:3000/login` and `http://localhost:3001/login` (dev)
  - `https://<app>.vercel.app/login` (production)
  - optionally `https://*-<team-slug>.vercel.app/**` if you want preview
    deployments to complete signups (wildcards are supported here)

**Email confirmations are ON** for this project. That's correct for a
hosted pilot (friends self-signup with real emails), but note Supabase's
built-in email sender is rate-limited to a handful of mails per hour — fine
for ~5 friends, not for a public launch. No SMTP setup needed for this
pilot. There is no OAuth in the product (email/password only), so no other
redirect surface exists.

## 6. LLM key safety and scaling (friend pilot)

- **Backend-only, always.** Gemini/OpenRouter keys exist solely in the
  backend host's variables. Nothing in `frontend/` references them; the
  hosted smoke checklist re-verifies the shipped bundle.
- **Use a separate production key.** Create a new Gemini API key for the
  deployment; keep the local-dev key local. Then a leak of either
  invalidates only one environment.
- **Restrict the key.** In Google Cloud console (or AI Studio key
  settings), restrict the production key to the **Generative Language API**
  only, so a leaked key can't touch other Google services.
- **Monitor usage** in Google AI Studio / Cloud console during the pilot
  week; `gemini-2.5-flash-lite` usage for a handful of friends should stay
  within the free tier.
- **Rotate on exposure.** If a key ever appears in a log, screenshot, or
  commit: revoke it in the provider console, issue a new one, update the
  backend host variable, restart. No code change needed.
- **Provider quota exhausted mid-pilot:** roadmap generation silently falls
  back to the deterministic template roadmap (never blocks onboarding); the
  gate returns a retryable 502 with the session intact — the student
  retries the same turn later. If Gemini quota dies for a while, set
  `OPENROUTER_API_KEY` as the fallback (note: the OpenRouter path is still
  live-unverified — verify one gate turn after enabling it).
- **Changing the Gemini model needs no code deploy (M13E.2 review).** The
  model is read from env at startup: set the Railway backend variable
  `GEMINI_MODEL=<model>` and restart/redeploy the service — that's the whole
  change. The committed default stays `gemini-2.5-flash-lite` (known-working
  with the fail-closed roadmap validator and gate flow). A stronger
  currently-available **Flash** model mainly raises the roadmap
  personalization rate; before switching, confirm in Google AI Studio that
  your key can call it and check its free-tier daily limits. Do **not** rely
  on a model upgrade for gate question cleanliness — leaked meta/preamble
  output is stripped or rejected (retryable) server-side regardless of model
  (`gate_service.clean_gate_question`, hardened in M13E.2).

## 7. Safety limits — present vs deferred

Already enforced in the backend (verified in code, nothing new needed):

- **Input caps on everything that reaches an LLM prompt or the DB:** intake
  answers 4000 chars (`intake_service.MAX_ANSWER_LENGTH`), gate anchor 2000
  / answers 8000 chars (`schemas/gate.py`), workflow artifacts 30 KB per
  section with per-field caps and secret-content rejection
  (`schemas/workflow.py`).
- **No unlimited retries on provider failure:** `llm_service` makes exactly
  one attempt per configured provider per call — no retry loop, no
  exponential hammering. Roadmap generation additionally has a
  deterministic no-LLM fallback.
- **Natural rate ceilings:** the gate allows one session at a time per
  project with a 30-minute cooldown after a FAIL; roadmap generation runs
  once per project (409 on duplicates). These bound LLM spend per user.
- **Auth on every LLM-touching route** — anonymous traffic can't spend a
  single token.

Deferred (documented, not built — per spec, rate limiting/DDoS/WAF are out
of MVP scope):

- Per-user daily request quotas and IP rate limiting. For a ~5-friend pilot
  the auth requirement + gate cooldown + input caps bound the spend; add
  real rate limiting before any public launch.
- Distinguishing "provider quota hit" from other 502s in the client. Today
  the frontend shows the generic retry message for all 5xx — acceptable for
  the pilot; changing the error contract is product-behavior work.
- Billing/usage dashboards — monitor in the provider console instead.

## 8. Rollback

- **Frontend:** Vercel deployments are immutable — "Instant Rollback" to
  the previous deployment in the dashboard.
- **Backend:** Railway/Render keep previous deploys — redeploy the prior
  build, or revert the commit and push.
- **Config-only break** (CORS / API URL / keys): fix the env var in the
  host and restart — no code change. Remember `NEXT_PUBLIC_*` changes need
  a frontend **redeploy**, not just a variable edit.

## 9. After deploying

Run `hosted_smoke_checklist.md` top to bottom against the live URLs before
sending anyone the link. Then send friends the Vercel URL and the tester
script (`docs/pilot/tester_script.md`).
