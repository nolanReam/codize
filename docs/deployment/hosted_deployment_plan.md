# Codize — Hosted Deployment Plan (first pilot)

The simplest hosted path for a small pilot, so testers can use Codize without the
facilitator running it locally. **Nothing here is executed automatically** — no
external accounts are created and **no deploy happens without your explicit
confirmation.** No real secret values appear in this doc.

> For the first 3–5 testers, hosting is optional — `local_demo_runbook.md`
> (facilitator-hosted) is faster and already verified. Use this when you want
> self-serve testers.

---

## 1. Recommended architecture

```
Browser ──HTTPS──> Frontend (Next.js on Vercel)
                       │  fetch() with Supabase Bearer JWT
                       ▼
                   Backend (FastAPI, any simple Python host)
                       │  service-role key (server-only)
                       ▼
             Supabase (existing project) + Gemini/OpenRouter APIs
```

- **Frontend:** Vercel (or any Next.js host). Auto-detects `npm run build`.
- **Backend:** a simple FastAPI host — **Render**, **Railway**, or **Fly.io**.
  All have a **free/hobby tier**, so a paid service is never the *only* path.
- **DB/Auth:** the existing Supabase project — no new database needed.

This preserves the non-negotiable rule: **Frontend → Backend → external
services.** The browser never holds a service-role or provider key.

## 2. Backend host setup

No Procfile/Dockerfile is committed (greenfield). Provide the host a **start
command** — drop-in, not yet committed so it can match your chosen host:

```bash
# Start command (host injects $PORT):
uvicorn app.main:app --host 0.0.0.0 --port $PORT
# Build/install:
pip install -r backend/requirements.txt
# Root/working directory: backend/
# Pin runtime: Python 3.11+  (add runtime.txt "python-3.11" or set the host's runtime)
```

If your host wants a `Procfile`, this is the whole file:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these in the host's **environment** (not in the repo):

| Var | Notes |
|---|---|
| `SUPABASE_URL` | project URL |
| `SUPABASE_ANON_KEY` | anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | **secret** |
| `GEMINI_API_KEY` | **secret** |
| `OPENROUTER_API_KEY` | **secret** (optional fallback) |
| `APP_ENV` | `production` (hides `/docs`) |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_MODEL` | e.g. `gemini-2.5-flash-lite` (or stronger) |
| `CORS_ORIGINS` | the deployed **frontend** origin, e.g. `https://codize.vercel.app` |

> Hosts inject env vars into the process directly, so the `env_file` cwd caveat
> from local dev doesn't apply — do **not** ship a `.env` file to the host.

## 3. Frontend host setup (Vercel)

- Project root: `frontend/`. Build: `npm run build`. Output: managed by Vercel.
- Environment variables (all **public** `NEXT_PUBLIC_*`):

| Var | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon/publishable key |
| `NEXT_PUBLIC_API_BASE_URL` | the deployed **backend** URL, **no trailing slash** (e.g. `https://codize-api.onrender.com`) |

## 4. The two links that must agree (most common deploy failure)

1. **Backend `CORS_ORIGINS`** must contain the exact deployed **frontend** origin
   (scheme + host, no path). Update it *after* you know the Vercel URL, then
   redeploy/restart the backend.
2. **Frontend `NEXT_PUBLIC_API_BASE_URL`** must point at the deployed **backend**
   base URL. Rebuild the frontend after changing it (Next reads it at build time).

Deploy order that avoids chicken-and-egg: deploy backend → note its URL → deploy
frontend with that `NEXT_PUBLIC_API_BASE_URL` → note the frontend URL → set it in
backend `CORS_ORIGINS` → restart backend.

## 5. Post-deploy smoke test

1. `GET https://<backend>/health` → `{"status":"ok",...,"environment":"production"}`.
2. Open `https://<frontend>` — landing page renders.
3. Sign in with a SQL-seeded test user (email confirmations are ON).
4. Complete intake → roadmap reaches **active** (no manual seeding).
5. Save one artifact; reload; it persists.
6. Run the gate: anchor → 3 turns → verdict (question text is clean).
7. Open the report; export Markdown; confirm **no secrets / scores** in it.
8. Log out.
9. Open DevTools → Network/Sources: confirm no `SUPABASE_SERVICE_ROLE_KEY`,
   `GEMINI_API_KEY`, or `sb_secret_*` string appears in any frontend asset.

(This mirrors `pre_pilot_smoke_checklist.md`, run against the deployed URLs.)

## 6. Rollback plan

- **Frontend (Vercel):** each deploy is immutable — "Promote"/"Rollback" to the
  previous deployment in the dashboard. Instant.
- **Backend (Render/Railway/Fly):** redeploy the previous commit, or revert the
  offending commit and push. Keep the last-known-good commit hash noted before a
  deploy.
- **Config-only break** (CORS/API URL/env): revert the env value in the host and
  restart — no code change needed.
- **Data:** the pilot only creates disposable test users; if seed state gets
  messy, delete test users via `scripts/verify_auth.sql` CLEANUP and reseed. No
  destructive schema changes are part of this milestone.

## 7. Security checklist (before inviting anyone)

- [ ] No secret in any `NEXT_PUBLIC_*` value or in `frontend/` source.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` / provider keys set **only** in the backend host.
- [ ] `CORS_ORIGINS` is the explicit frontend origin — **never `*`**.
- [ ] `APP_ENV=production` on the backend (hides `/docs`).
- [ ] HTTPS on both hosts (default on Vercel/Render/Railway/Fly).
- [ ] RLS still enforced on all Supabase tables (unchanged this milestone; the
      backend also filters every query by `user_id`).
- [ ] Frontend bundle scanned (step 5.9) — no leaked keys.
- [ ] Test users are disposable and will be deleted after the pilot.
- [ ] `.env` / `.env.local` are gitignored and were never committed.

Out of scope for this pilot (per spec): rate limiting, DDoS/WAF, full OWASP
audit, pentest, CSP hardening.
