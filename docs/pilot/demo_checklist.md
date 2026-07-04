# Codize Pilot — Demo & Pre-Flight Checklist

> For full setup/run/deploy detail see `docs/deployment/` —
> `local_demo_runbook.md` (step-by-step local run + troubleshooting),
> `pre_pilot_smoke_checklist.md` (the deploy/build smoke gate), and
> `hosted_deployment_plan.md` (Vercel + FastAPI host). This file is the quick
> per-session pre-flight.

Run this on the **exact machine** you'll use, **before** the first tester (and a
quick re-check before each session). It prevents the two most common pilot
killers: a cold environment and a live demo that hits an avoidable error.

**Never expose secrets during a demo:** don't screen-share the repo-root `.env`,
the SQL editor with keys, or any terminal line containing a service-role/provider
key. Keep those windows closed.

---

## T-minus (once, before the pilot)

- [ ] **Clean git working tree** (`git status` — nothing unexpected staged/dirty).
- [ ] **Known issues reviewed** — read the "Known issues & limits" list in
      `tester_script.md` so nothing on it surprises you mid-session.
- [ ] Repo-root `.env` exists and has Supabase + Gemini/OpenRouter values.
- [ ] Backend deps installed (`backend/.venv` present, `requirements.txt`
      installed).
- [ ] Frontend deps installed (`frontend/` `npm install` done).
- [ ] `frontend/.env.local` set with **public** values only
      (`NEXT_PUBLIC_SUPABASE_URL`, anon key, `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`).
- [ ] One disposable, confirmed test user created via `scripts/verify_auth.sql`
      SETUP, with a **placeholder** email. Password noted somewhere non-repo.
- [ ] Backend test suite green: from `backend/`, `.venv\Scripts\python -m pytest`.

## T-5 min (before each session)

- [ ] Backend running: from `backend/`,
      `.venv\Scripts\uvicorn app.main:app --env-file ../.env`.
- [ ] `http://localhost:8000/health` returns OK.
- [ ] Frontend running: from `frontend/`, `npm run dev` → `http://localhost:3000`.
- [ ] Logged **out** and starting clean (or a fresh test user for a first-run
      experience).
- [ ] Secret-bearing windows (`.env`, SQL editor, key-laden terminals) closed or
      off-screen.
- [ ] `observation_notes_template.md` copy open; `pre_survey.md` ready.
- [ ] Network is up (roadmap + gate make live LLM calls).

## Happy-path smoke (do it yourself once before testers arrive)

Walk the whole loop to confirm it's live end-to-end:

1. [ ] Landing page loads.
2. [ ] Sign in with the test user.
3. [ ] Intake: answer all five questions (Q1 first, unskippable).
4. [ ] Roadmap generates → project goes **active** (personalized **or** fallback
       roadmap — both fine).
5. [ ] Cockpit + phase board render.
6. [ ] Save one Build Loop artifact (e.g. Prompt Builder), reload the page, and
       confirm it **loads back** (save *and* load work).
7. [ ] Project Defense: anchor → 3 turns → evaluate returns a verdict.
8. [ ] Report page assembles; Markdown copy/download works.
9. [ ] Exported Markdown is clean — **no score, no evaluator reasoning, no keys/
       JWT, no service-role value** in the text.
10. [ ] Log out.

If any step fails, fix or note it **before** running testers — don't debug live in
front of a tester.

## Talking points for a live group demo (optional, ≤5 min)

- Lead with the **80% trap**: "AI gets your project to *runs*, not to
  *you-can-defend-it*."
- Show intake → roadmap fast; don't dwell.
- Spend the time on the **Project Defense** — that's the product.
- Close on the **exported Report** as the artifact a student shows a teacher/judge.
- Do **not** promise out-of-scope features (browser IDE, GitHub OAuth, community,
  marketplace, analytics, gamification) — say "not in this version" if asked.

## Reset between testers

- [ ] Log out; clear the previous tester's session.
- [ ] If reusing one test user, reset its project state via SQL, **or** use the
      next test user for a true first-run experience.
- [ ] New `observation_notes_template.md` copy; blank `pre_survey.md`.

## Teardown (after the pilot)

- [ ] Delete all disposable test users (`scripts/verify_auth.sql` CLEANUP).
- [ ] Delete any name↔P# mapping you kept (should live outside this repo).
- [ ] Stop backend/frontend dev servers.
