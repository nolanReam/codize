# Codize Authentication (Milestone 3)

Supabase project `tadkbymxkdncqahzshml` (GoTrue v2.192.0). Environment contract
in `.env.example`. Verification scripts: `scripts/verify_auth.sql` (test-user
setup/cleanup, run via Supabase MCP) + `scripts/verify_auth.py` (HTTP tests
against the real Auth and PostgREST APIs).

## Auth configuration audit (verified 2026-07-02)

| Item | Status | Evidence |
|---|---|---|
| Email/password auth enabled | ✅ | `/auth/v1/signup` accepts email/password; `/auth/v1/token?grant_type=password` issues sessions |
| Signup flow available | ✅ | signup attempt reached `user_confirmation_requested` (auth logs); blocked only by the email send rate limit, not by config |
| Email confirmations | **ON** | signup triggers a confirmation email; unconfirmed users get no session. Frontend (M13) must handle the "check your email" state, or confirmations get disabled deliberately later — decide then, not now |
| Email deliverability validation | ON | GoTrue MX-checks the signup email domain (`email_address_invalid` for fake domains) |
| Built-in email sender | very low rate limit | `429 over_email_send_rate_limit` after a couple of sends. Fine for MVP dev; production needs custom SMTP (out of MVP scope) |
| Profile auto-creation trigger | ✅ works | `on_auth_user_created` → `handle_new_user()` (SECURITY DEFINER, EXECUTE revoked from client roles); created `profiles` rows for every test insert into `auth.users` |
| `profiles.user_id` → `auth.users.id` | ✅ | FK with `on delete cascade`; verified by cascade leaving zero rows on user delete |
| RLS on `profiles` (and all tables) | ✅ | 11/11 checks in `verify_auth.py`, run with real user JWTs — see verification record |
| Leaked-password protection | ✅ enabled (advisor-verified) | WARN present at session start on 2026-07-02, gone on re-run at session end (advisor returned zero findings twice). Not toggled by tooling — MCP/CLI cannot change it — so it was evidently enabled in the dashboard mid-session |
| JWT signing | ES256 via JWKS | `/auth/v1/.well-known/jwks.json` serves an ES256 P-256 key (the legacy HS256 anon key remains valid for PostgREST `apikey`) |

### Leaked-password protection

A Dashboard-only toggle (**Authentication → Sign In / Providers → Passwords →
"Leaked password protection"**, HaveIBeenPwned check) that MCP/CLI cannot
change. The security advisor flagged it disabled at the start of the M3
session and reported **zero findings** on two re-runs at the end of the same
session (2026-07-02) — enabled in the dashboard mid-session. If the WARN ever
reappears, that dashboard toggle is the fix.

## Backend auth enforcement design (implemented in Milestone 4)

Implemented in `backend/app/core/security.py` + `backend/app/deps/auth.py`
(M4); tests sign locally generated ES256 tokens and stub only the JWKS fetch,
so live verification of a real Supabase JWT is still pending backend env vars.
The rule from the spec: UI hiding is never security; every protected endpoint
enforces auth **server-side**.

1. **Token flow.** The frontend authenticates against Supabase Auth directly
   (the one permitted frontend→external call) and holds the session JWT. Every
   FastAPI request carries it as `Authorization: Bearer <access_token>`.
2. **Verification.** FastAPI verifies the JWT signature and claims itself — it
   never trusts a user id sent in a request body. Verify against the project
   JWKS (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, ES256; PyJWT's
   `PyJWKClient` caches keys), checking `exp` and `aud == "authenticated"`.
   The authenticated user id is `sub`.
3. **401 vs 403/404.** Missing/expired/invalid token → **401**. Valid token
   but the resource belongs to another user → **403** (or **404** where
   revealing existence is itself a leak — decide per-endpoint in M4; default
   404 for `/projects/{id}`-style lookups).
4. **Ownership checks in the service layer.** The backend uses the
   service-role key (bypasses RLS), so **every** query it makes on behalf of a
   user must filter/verify `user_id == sub`. RLS remains defense-in-depth
   against the anon key, not a substitute for backend checks.
5. **Service-role key is server-only.** Lives only in backend env
   (`SUPABASE_SERVICE_ROLE_KEY`); never in frontend files, never returned by
   any endpoint, never logged.
6. **FastAPI shape.** A single auth dependency (e.g. `CurrentUser`) applied to
   every protected route; route handlers stay thin and ownership logic lives
   in `services/` per the architecture rules.

## Project Data API write boundary (M16S.1)

RLS answers "which rows?"; object grants independently answer "which
operations?". Before M16S.1, owner RLS correctly blocked cross-user access,
but the inherited `authenticated` table-level `UPDATE` and `INSERT` grants on
`projects` still allowed an owner to bypass FastAPI and forge the owner's own
`workflow_artifacts`. That preserved confidentiality but violated integrity.

The M16S.1 forward migration makes `projects` read-only to authenticated Data
API clients: revoke all table privileges from `authenticated`, then grant back
only `SELECT`. Owner reads continue through `projects_select_own`; anonymous
access remains denied; the trusted backend role remains unchanged. Project
creation is not a browser insert: the first authenticated intake answer calls
FastAPI, which creates the row through the owner-filtered repository. No
frontend code uses `.from("projects")`, table writes, RPCs, or product-data
Supabase calls.

The retained owner insert/update/delete RLS policies are inert without matching
object privileges and remain defense in depth. A future direct browser write
must first justify the data ownership model, then add a forward migration for
only the necessary column privilege or a narrowly reviewed RPC. Broad project
mutation must not be restored.

Post-deployment verification is mandatory:

1. Run `scripts/verify_workflow_artifact_write_boundary.sql` as one
   transactional batch.
2. Run `scripts/verify_workflow_artifact_write_boundary.py` against the same
   environment with its FastAPI base URL.
3. Re-run `scripts/verify_auth.py` and Supabase security advisors.

The shared hosted pilot database was inspected read-only during implementation;
the forward migration was not applied there because it was not identified as a
safe development/test target.

### Linked Evidence handoff (M16B.3A)

Both `GET` and `POST /workflow/{phase}/evidence/from-verification`, plus linked
updates through `PUT /workflow/{phase}/evidence`, use `require_user`. They accept
no user id, project id, or workspace id: the owned project is loaded only with
the verified JWT subject, and the requested phase must exist in that project's
stored roadmap. The repository's trusted write is still filtered by both
project id and JWT-derived user id.

The GET is pure and returns only student-safe handoff context. It does not
create Evidence. The POST requires explicit server-issued target selection and
copies provenance only from the current owned linked Verification artifact.
Normal Evidence PUTs cannot submit source linkage, snapshots, fingerprints,
timestamps, completion, or stale state. In linked mode they accept target
updates only; legacy top-level entries/summary cannot bypass the selected
target provenance. Detected credential-shaped Evidence is rejected without
echoing or logging it. No route calls a provider, fetches a
submitted URL, or exposes the backend credential. The M16S.1 database grants
remain the second integrity boundary: authenticated browser clients can read
their project row through RLS but cannot mutate `workflow_artifacts` directly.

## Verification record (2026-07-02)

Test users are created by `scripts/verify_auth.sql` SETUP (SQL inserts, because
GoTrue MX-validates signup emails and the built-in sender is rate-limited; the
signup trigger fires on insert regardless). Two GoTrue quirks the SQL handles:
token varchar columns must be `''` not NULL (else `/token` 500s), and password
login requires an `auth.identities` row.

`python scripts/verify_auth.py` — **11/11 PASS** with real JWTs from
`grant_type=password` logins:

- password login issues JWTs for both test users
- A sees exactly their own profile; B's profile/project invisible to A, even
  when queried directly by id
- `gate_sessions.score` denied to authenticated users (42501)
- A's UPDATE of B's project touches 0 rows; unlock forgery INSERT denied (42501)
- anon denied on profiles and projects (42501)
- A can update their own profile; B's data unmodified after A's tamper attempt

Cleanup verified: deleting the test users cascaded away all rows — profiles,
projects, gate_sessions, unlocks and auth.users all at 0.

Also removed during this milestone: 8 orphaned `@sparkagency.internal` users in
`auth.users` left over from the wiped legacy product (covered by the approved
2026-07-02 legacy wipe).
