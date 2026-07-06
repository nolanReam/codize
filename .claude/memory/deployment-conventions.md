# Deployment conventions (M13F.1)

- **Canonical hosted-deploy docs:** `docs/deployment/friend_pilot_deployment.md`
  (+ `env_var_matrix.md`, `hosted_smoke_checklist.md`).
  `hosted_deployment_plan.md` is the superseded M13D outline — don't extend it.
- **Variable names are fixed:** allowed origins is **`CORS_ORIGINS`** (never
  invent `ALLOWED_ORIGINS`), and there is **no `SUPABASE_JWT_SECRET`** — JWT
  verification is JWKS/ES256 derived from `SUPABASE_URL`.
- **Committed deploy config:** `backend/Procfile`
  (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) and
  `backend/.python-version` (`3.12` — a HOST pin only; local dev runs 3.14,
  code targets 3.11+; plain Windows venv ignores the file).
- **CORS default** is `http://localhost:3000,http://localhost:3001` when
  `CORS_ORIGINS` is unset; an explicit env value (e.g. repo-root `.env`)
  **overrides** the default — local `.env` files that pin only 3000 won't
  serve 3001 until updated. Never `*` (also invalid with credentials).
- **Signup email redirect:** `login/page.tsx` passes
  `emailRedirectTo: ${window.location.origin}/login`. Any origin that hosts a
  signup must be listed in Supabase Auth → URL Configuration → Redirect URLs
  (dashboard-only change; deliberately no script for auth settings).
- **Backend host choice:** Railway recommended (no sleep, Procfile
  auto-detect, matches CLAUDE.md architecture); Render free tier acceptable
  with ~30–60 s cold starts; Vercel Python functions rejected (repo layout +
  ~30 s roadmap call vs function limits).
- **Pilot spend is bounded without rate limiting** by existing invariants:
  auth on every LLM route, one LLM attempt per provider per call (no retry
  loops), gate cooldown + single in-flight session, roadmap generated once
  per project, input caps (intake 4000 / gate 2000·8000 / workflow 30 KB).
  Per-user quotas/IP rate limiting are spec-deferred — don't add them ad hoc.
