# Codize — Pre-Pilot Smoke Checklist

> [!NOTE]
> **Historical/current V1 pilot checklist.** Its product path is not V2 authority.

The final gate before inviting testers. Run it on the exact environment (local or
hosted) you'll use. If any **must-pass** item fails, fix it before the pilot.
Complements the pilot-facing `docs/pilot/demo_checklist.md` (this one is the
deploy/build-focused version).

**Never print secret values while doing this** — confirm presence, not contents.

---

## Repo & build

- [ ] **Clean working tree** — `git status` shows nothing unexpected staged/dirty.
- [ ] On the intended commit (note the hash: __________).
- [ ] Backend deps installed; **`pytest` green** (if backend code changed this cycle).
- [ ] Frontend: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`
      all pass (if frontend code changed this cycle).

## Environment & secrets

- [ ] Repo-root `.env` (local) **or** host env (deployed) has all backend names:
      `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
      `GEMINI_API_KEY`, `CORS_ORIGINS`. *(names present — values not printed)*
- [ ] Frontend env has `NEXT_PUBLIC_SUPABASE_URL`,
      `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL` (no trailing slash).
- [ ] `CORS_ORIGINS` matches the frontend origin actually in use (never `*`).
- [ ] **No secret in the frontend** — scan `frontend/` source + built bundle;
      no `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`,
      `sb_secret_*`, `sk-or-*`, or `AIza*` string appears. *(must-pass)*
- [ ] `.env` / `.env.local` are gitignored and not committed. *(must-pass)*

## Backend up

- [ ] Backend starts without error.
- [ ] `GET /health` → `{"status":"ok","service":"codize-backend","environment":...}`.

## Frontend up

- [ ] Frontend starts / deploy is live.
- [ ] **Landing page loads** (the 80% Trap page).

## Core flow (drive it once, end-to-end)

- [ ] **Login works** with a SQL-seeded, pre-confirmed test user.
- [ ] **Intake** completes (five questions; Q1 unskippable).
- [ ] **Roadmap reaches an active project without manual seeding** (personalized
      or template-fallback — both OK). *(must-pass)*
- [ ] **Artifacts save and reload** — save a Prompt Builder artifact, reload, it
      persists.
- [ ] **Gate runs with clean question text** — anchor → 3 turns → evaluate; the
      questions read as direct questions with no meta/preamble/"valid anchor"
      leakage. *(must-pass — this is the M13C.2B fix)*
- [ ] **Report exports Markdown** — copy/download works.
- [ ] Exported report has **no score / evaluator reasoning / threshold / key**.
      *(must-pass)*
- [ ] **Logout works.**

## Console / errors

- [ ] No console errors **except known-harmless ones** (see Known issues).
- [ ] No 500s during the walkthrough (a retryable **502** on a live LLM call is
      acceptable if a retry succeeds).

## Cleanup & record

- [ ] **Test data cleanup done** — SQL test users deleted after verification
      (`scripts/verify_auth.sql` CLEANUP), any name↔label map deleted.
- [ ] **Known issues recorded** for the session (below).

---

## Known issues to keep in mind (expected — not blockers)

- Roadmap may return the **template-fallback** version with a lighter model.
- Live LLM calls (roadmap, gate) can be **slow** or need a **one-tap retry**.
- A gate **fail → 30-minute cooldown** (intended, not a lockout).
- **Verification is self-reported**; Codize doesn't run tester code.
- **Scores/thresholds/evaluator reasoning are hidden** by design.
- Out of scope (don't demo/promise): browser IDE, GitHub OAuth, community, tool
  marketplace, analytics dashboard, hosted runtime, gamification.

## Verdict

- [ ] **All must-pass items green → ready for the pilot.**
- If any must-pass failed, note it, fix it, and re-run this section:
  ______________________________________________________________
