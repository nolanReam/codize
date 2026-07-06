# Codize — Environment Variable Matrix (M13F.1)

Every variable the system uses, where it lives, and whether it is secret.
**No real values appear in this file — names and placement only.**

The one rule: anything named `NEXT_PUBLIC_*` is **bundled into public client
JS**. Secrets therefore exist only in the backend host's environment.
(OWASP A02.)

---

## Frontend — Vercel project env vars (all PUBLIC by design)

Set in Vercel → Project → Settings → Environment Variables. Locally these go
in `frontend/.env.local` (gitignored; contract file `frontend/.env.example`).

| Variable | Secret? | Value | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | No | `https://<project-ref>.supabase.co` | Auth only — the frontend never reads data tables |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | No (public by design) | `sb_publishable_...` or legacy anon key | RLS + the backend enforce all access |
| `NEXT_PUBLIC_API_BASE_URL` | No | Deployed backend URL, **no trailing slash** | Read at **build time** — changing it needs a redeploy. `http://localhost:8000` locally |

**Never** set on Vercel or in any `frontend/` file: `SUPABASE_SERVICE_ROLE_KEY`,
`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `sb_secret_*`, or any other server key.

## Backend — backend host env vars (Railway/Render/Fly service settings)

Locally these come from the repo-root `.env` (gitignored; contract file
`.env.example`) via `--env-file ../.env`. Hosts inject env vars directly into
the process — **never ship a `.env` file to a host.**

### Secrets (host's env settings only; never in the repo, logs, or frontend)

| Variable | Secret? | Notes |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | **YES** | `sb_secret_...` or legacy service_role key. Bypasses RLS — backend↔Supabase only |
| `GEMINI_API_KEY` | **YES** | Primary LLM provider. Use a **separate key for production** (see friend_pilot_deployment.md §6) |
| `OPENROUTER_API_KEY` | **YES** (optional) | Fallback provider; omit to run Gemini-only |

### Non-secret backend config

| Variable | Default | Hosted value | Notes |
|---|---|---|---|
| `APP_ENV` | `development` | `production` | `production` hides `/docs`; echoed by `GET /health` |
| `SUPABASE_URL` | — | project URL | JWKS URL is derived from it — no separate variable |
| `SUPABASE_ANON_KEY` | — | anon/publishable key | Also fine server-side |
| `LLM_PROVIDER` | `gemini` | `gemini` | `gemini` \| `openrouter` \| `stub` (stub = tests/no-key only) |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | same or stronger | Stronger model → higher roadmap personalization rate |
| `OPENROUTER_MODEL` | `cohere/north-mini-code:free` | same | Only used if the fallback key is set |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | exact deployed frontend origin(s), comma-separated | **Never `*`.** e.g. `https://<app>.vercel.app,http://localhost:3000` |

> The repo's actual variable name for allowed origins is **`CORS_ORIGINS`**
> (not `ALLOWED_ORIGINS`) and there is **no `SUPABASE_JWT_SECRET`** — JWT
> verification uses JWKS/ES256 derived from `SUPABASE_URL`.

## Not used anywhere

- `DATABASE_URL` — commented out in `.env.example`; the backend talks to
  Supabase only through PostgREST.
- Any Anthropic key — Anthropic is intentionally not supported.

## Quick audit commands

```powershell
# No secret names referenced anywhere in frontend source:
Select-String -Path frontend -Pattern "SERVICE_ROLE|GEMINI_API|OPENROUTER_API|sb_secret_" -Recurse
# (must return only comments in .env.example warning against them)

# .env files are gitignored and never committed:
git check-ignore .env frontend/.env.local
git log --all --oneline -- .env frontend/.env.local   # must be empty
```
