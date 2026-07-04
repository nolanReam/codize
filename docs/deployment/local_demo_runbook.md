# Codize — Local Demo Runbook

Step-by-step to run Codize locally for a demo or a pilot session. This is the
"green environment" procedure; the fast pre-flight is
`pre_pilot_smoke_checklist.md` and the tester-facing walkthrough is
`docs/pilot/tester_script.md`.

**Never print secret values.** Confirm variables *exist*, don't echo them.

---

## 0. Prerequisites (once)

- Python 3.11+ and Node 20+ installed.
- Repo-root `.env` filled from `.env.example` (Supabase URL + keys, `GEMINI_API_KEY`).
- `frontend/.env.local` filled from `frontend/.env.example`.
- Backend venv created and deps installed (`backend/`:
  `python -m venv .venv` → `.venv\Scripts\pip install -r requirements.txt`).
- Frontend deps installed (`frontend/`: `npm install`).

## 1. Start the backend (from `backend/`)

```bash
.venv\Scripts\uvicorn app.main:app --env-file ../.env --reload
```

`--env-file ../.env` is required so the repo-root secrets load (see the runbook's
env note / `deployment_readiness_audit.md` §1). Leave it running.

## 2. Start the frontend (from `frontend/`, new terminal)

```bash
npm run dev            # http://localhost:3000
```

## 3. Confirm env vars exist (without printing values)

```bash
# backend — names present, values NOT shown:
grep -oE '^(SUPABASE_URL|SUPABASE_ANON_KEY|SUPABASE_SERVICE_ROLE_KEY|GEMINI_API_KEY|CORS_ORIGINS)=' .env
# frontend:
grep -oE '^NEXT_PUBLIC_(SUPABASE_URL|SUPABASE_ANON_KEY|API_BASE_URL)=' frontend/.env.local
```

Each expected name should print once. **Do not** run a command that prints the
value after the `=`.

## 4. Confirm the backend is healthy

```bash
curl -s http://localhost:8000/health
# → {"status":"ok","service":"codize-backend","environment":"development"}
```

If `environment` is missing or the call fails, the backend didn't start or env
didn't load — see Troubleshooting.

## 5. Confirm Supabase auth + create/use a test account safely

Email confirmations are ON, so **don't** rely on self-signup for a demo. Create a
login-capable, already-confirmed user directly via SQL using the **SETUP** block
in `scripts/verify_auth.sql` (run it through the Supabase MCP `execute_sql` or the
SQL editor). Safety rules:

- Use a **placeholder, non-personal email** (e.g. `pilot+demo@example.test`).
- Never use a tester's real email or any real credential.
- Note the password somewhere **outside** the repo.
- These are disposable — delete them in step 15.

Then in the browser (`http://localhost:3000` → Login) sign in with that user.
A fresh user should land directly in **intake** (no dashboard) — that's correct.

## 6–14. Walk the Build Loop

Drive the product exactly as a tester would (mirror `docs/pilot/tester_script.md`):

6. **Intake** — answer the five questions (Q1 first, unskippable).
7. **Roadmap** — completing intake generates the roadmap and flips the project to
   *active*. Personalized **or** template-fallback roadmap are both fine.
8. **Prompt Builder** — build a prompt for the current phase; save it.
9. **Review Board** — record what the AI changed; save.
10. **Evidence** — add a link/commit-hash/note; save.
11. **Verification Lab** — check the verification items you actually did; save.
12. **Project Defense (gate)** — Start → anchor → 3 turns → evaluate → verdict.
    (A fail triggers a 30-min cooldown — expected.)
13. **Project Defense Report** — open it, then **copy / download Markdown**.
14. **Logout.**

## 15. Clean up test data

- Delete the SQL test user(s) via the **CLEANUP** block in
  `scripts/verify_auth.sql`.
- Delete any name↔tester-label mapping you kept (outside the repo).

---

## Troubleshooting

**Missing env vars / backend in "no-key" mode.**
Symptoms: roadmap/gate behave oddly, LLM returns stub-like text, Supabase calls
fail. Cause: repo-root `.env` not loaded. Fix: relaunch with `--env-file ../.env`
(or export the vars). Re-check step 3.

**Frontend cannot reach backend.**
Symptoms: network errors on the first authed call. Check `NEXT_PUBLIC_API_BASE_URL`
in `frontend/.env.local` (must be `http://localhost:8000`, **no trailing slash**),
that the backend is actually up (step 4), and restart `npm run dev` after editing
`.env.local` (Next reads it at startup).

**CORS error in the browser console.**
Symptom: "blocked by CORS policy." The frontend origin must be in backend
`CORS_ORIGINS`. Locally that's `http://localhost:3000` (the default). If you
opened the app on a different port/host, add that exact origin to `CORS_ORIGINS`
and restart the backend. Never use `*`.

**Supabase email-confirmation issue.**
Symptom: a freshly signed-up user can't log in ("email not confirmed"). Expected
— confirmations are ON. Use the SQL-seeded, pre-confirmed user (step 5) instead
of self-signup for demos.

**Roadmap fallback path.**
Symptom: roadmap looks like the standard template rather than tailored to the
tester's wording. Not a bug — the deterministic fallback ran (flash-lite drift or
a provider hiccup). Project is still *active* and fully usable. For higher
personalization, set a stronger `GEMINI_MODEL` in `.env` and restart.

**Gate provider/model issue.**
Symptom: a gate turn or evaluate returns a 502. The provider failed; nothing was
stored and the same step is retryable — just retry. Unlike roadmap, the gate has
no deterministic fallback (it needs real reasoning), so confirm `GEMINI_API_KEY`
is valid before a session (smoke checklist covers this).

**Report shows "missing" sections.**
Not a bug — the report honestly shows sections the tester didn't fill and labels
verification as self-reported. Fill the Prompt Builder / Review / Evidence /
Verification for the current phase to populate them.
