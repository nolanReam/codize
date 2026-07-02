# Supabase project: legacy schema was wiped; Codize schema is live

Supabase project `tadkbymxkdncqahzshml` ("Codize", us-west-2, Postgres 17) originally contained an unrelated legacy product's schema (20 empty tables, migrations 001–010 dated 2026-06-16: cases/predictions/reviews for grade-3–6 students). With explicit owner approval on 2026-07-02 it was dropped (`drop_legacy_schema` migration) — including a legacy `on_auth_user_created` trigger on `auth.users` and an `ensure_rls` event trigger that would otherwise have caused surprises later.

Why it matters: `list_migrations` still shows the legacy 001–010 entries; they refer to dropped objects, not Codize. Codize's schema starts at version `20260702070937_codize_schema_with_rls`. Repo copies live in `supabase/migrations/`; schema doc in `docs/db/schema.md`.

M3 follow-up (2026-07-02): the wipe had left 8 orphaned legacy users (`@sparkagency.internal`) in `auth.users`; they were deleted during Milestone 3 under the same approval. `auth.users` now starts empty — any users found there are real or test users, not legacy.
