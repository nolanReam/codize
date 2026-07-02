# Auth milestone (M3) carry-over items from Milestone 2

1. Enable leaked-password protection in the Supabase Auth dashboard settings — flagged by the security advisor on 2026-07-02; it is an Auth config toggle, not SQL, so it could not be fixed in a migration.
2. The signup→profile trigger (`handle_new_user`) already exists and is verified; do not recreate it in auth work.
3. Live adversarial prompt testing is still pending an `ANTHROPIC_API_KEY` (none in the environment at M2 either) — required before Milestone 9.
