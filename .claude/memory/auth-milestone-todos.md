# Auth carry-over items after Milestone 3 (2026-07-02)

1. **Leaked-password protection: advisor-clean as of end of M3 (2026-07-02).** The WARN was present at session start and gone on two advisor re-runs at session end — it is a Dashboard-only toggle (Authentication → Sign In / Providers → Passwords), so it was evidently enabled in the dashboard mid-session. Re-check `get_advisors` each milestone; if the WARN returns, that toggle is the fix.
2. **Email confirmations are ON** — new signups get no session until the confirmation link is clicked. The frontend milestone (M13) must handle the "check your email" state, or confirmations must be deliberately disabled then. Also: the built-in email sender rate-limits after ~2 sends/hour and GoTrue MX-validates signup email domains (fake domains → `email_address_invalid`).
3. The signup→profile trigger (`handle_new_user`) exists and is verified end-to-end; never recreate it.
4. Backend JWT verification design for M4 is written in `docs/auth.md`: verify against JWKS (ES256) with PyJWT, `aud == "authenticated"`, user id = `sub`; backend uses service role so every query must filter by `user_id == sub` itself.
5. Live adversarial prompt testing is still pending an `ANTHROPIC_API_KEY` (absent at M1, M2 and M3) — required before Milestone 9. Never ask the user to paste the key into chat.
