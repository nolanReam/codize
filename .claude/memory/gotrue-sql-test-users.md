# Creating login-capable Supabase test users via SQL (GoTrue quirks)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

Learned 2026-07-02 while verifying auth (Milestone 3). The real `/auth/v1/signup` endpoint is impractical for automated tests on this project (MX-validated email domains + ~2/hour built-in email rate limit + confirmations ON), so tests insert users directly — the signup trigger fires on `insert into auth.users` either way. Two non-obvious requirements or login breaks:

1. GoTrue's varchar token columns (`confirmation_token`, `recovery_token`, `email_change*`, `phone_change*`, `reauthentication_token`) must be `''`, **not NULL** — otherwise `/token?grant_type=password` returns 500 "converting NULL to string is unsupported".
2. Password login requires a matching `auth.identities` row (`provider='email'`, `provider_id` = the user's id, `identity_data` with sub/email).

Canonical working version: `scripts/verify_auth.sql` SETUP section. Password hashing: `extensions.crypt('pw', extensions.gen_salt('bf'))`; set `email_confirmed_at` so login works with confirmations ON.
