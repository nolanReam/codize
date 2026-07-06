# Codize — Hosted Smoke Checklist (M13F.1)

Run this against the **deployed URLs** immediately after every deploy and
before inviting any tester. Companion to `friend_pilot_deployment.md`.
Local-run equivalent: `pre_pilot_smoke_checklist.md`.

Use a disposable account (a real email you control — confirmations are ON —
or a SQL-seeded test user via `scripts/verify_auth.sql`).

---

## The 12 checks

1. [ ] **Frontend loads on Vercel** — `https://<app>.vercel.app` renders the
   landing page (hero terminal, scenes scroll).
2. [ ] **Login/signup works** — sign up with a fresh email → "check your
   email" notice appears; sign in with a confirmed user succeeds.
3. [ ] **Auth redirect returns to the Vercel URL** — the confirmation email's
   link opens `https://<app>.vercel.app/login` (not localhost). If it opens
   localhost, fix Supabase Site URL / Redirect URLs
   (friend_pilot_deployment.md §5).
4. [ ] **`/app` loads after login** — the protected shell renders; a first
   login shows the tutorial; a brand-new user lands on intake question 1.
5. [ ] **Intake works** — answer all five questions (helper text + chips
   render), edit one answer, Finish intake → archetype classified.
6. [ ] **Roadmap generation works** — "Generate my roadmap" reaches an
   **active** 7-phase roadmap (personalized or fallback — both pass) in
   under ~60 s.
7. [ ] **Prompt Builder saves** — build a prompt, save, hard-reload the
   page, confirm it loads back (save *and* load through the hosted
   backend).
8. [ ] **Gate starts** — Project Defense: start → anchor accepted → Turn 1
   question appears and is clean (no prompt/template leakage). Completing
   all 3 turns + verdict is optional here but do it once per pilot.
9. [ ] **Report loads** — the Project Defense Report page assembles;
   Markdown copy/download works; the export contains **no score, no
   evaluator reasoning, no keys/JWT**.
10. [ ] **Backend `/health` works** —
    `GET https://<backend>/health` →
    `{"status":"ok","service":"codize-backend","environment":"production"}`
    — and `https://<backend>/docs` returns 404 (production hides it).
11. [ ] **No CORS errors** — with DevTools console open, do steps 4–7:
    zero CORS / blocked-request errors. If any appear, backend
    `CORS_ORIGINS` is missing the exact frontend origin.
12. [ ] **No secrets in the frontend bundle/env** — DevTools → Sources (or
    `view-source` on the built JS chunks): search for `sb_secret_`,
    `sk-or-`, `AIza`, `SERVICE_ROLE` → zero hits. Also check
    Vercel → Settings → Environment Variables lists **only** the three
    `NEXT_PUBLIC_*` values.

## After the smoke

- Log out; confirm the landing page is reachable logged-out.
- Note the deployed commit hash + both URLs somewhere outside the repo (for
  rollback).
- Delete the disposable smoke account (SQL CLEANUP in
  `scripts/verify_auth.sql`) if you seeded one.

**If any step fails, fix it before sending anyone the link** — the two most
likely culprits are the CORS ↔ API-base-URL pair
(friend_pilot_deployment.md §4) and Supabase redirect config (§5).
