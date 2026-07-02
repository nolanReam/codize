-- Codize auth verification — SQL half. Run via Supabase MCP (execute_sql).
-- Creates two login-capable test users, then scripts/verify_auth.py runs the
-- HTTP tests against the real Auth + PostgREST APIs. ALWAYS run the cleanup
-- section afterwards.
--
-- Why SQL-created users instead of the /auth/v1/signup endpoint:
--   * GoTrue validates email deliverability (MX lookup) — fake domains are
--     rejected with email_address_invalid.
--   * Email confirmations are ON, and the built-in email sender has a very
--     low rate limit (429 over_email_send_rate_limit).
-- The signup trigger fires on INSERT into auth.users either way, so profile
-- auto-creation is still exercised.
--
-- GoTrue quirks these inserts must satisfy (learned 2026-07-02):
--   * The varchar token columns must be '' not NULL, or /token returns
--     500 "converting NULL to string is unsupported".
--   * Password login requires a matching auth.identities row (provider_id =
--     user id for the email provider).

-- ---------------------------------------------------------------------------
-- SETUP (expect final select: profiles_auto_created = 2)
-- ---------------------------------------------------------------------------
insert into auth.users (instance_id, id, aud, role, email, encrypted_password,
                        email_confirmed_at, created_at, updated_at,
                        raw_app_meta_data, raw_user_meta_data,
                        confirmation_token, recovery_token, email_change,
                        email_change_token_new, email_change_token_current,
                        phone_change, phone_change_token, reauthentication_token)
values
  ('00000000-0000-0000-0000-000000000000', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
   'authenticated', 'authenticated', 'rls-test-a@codize.local',
   extensions.crypt('C0dize!Test-A-9f2k', extensions.gen_salt('bf')),
   now(), now(), now(),
   '{"provider":"email","providers":["email"]}', '{}',
   '', '', '', '', '', '', '', ''),
  ('00000000-0000-0000-0000-000000000000', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
   'authenticated', 'authenticated', 'rls-test-b@codize.local',
   extensions.crypt('C0dize!Test-B-7x4m', extensions.gen_salt('bf')),
   now(), now(), now(),
   '{"provider":"email","providers":["email"]}', '{}',
   '', '', '', '', '', '', '', '');

insert into auth.identities (id, user_id, provider_id, provider, identity_data,
                             last_sign_in_at, created_at, updated_at)
values
  (gen_random_uuid(), 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
   'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'email',
   '{"sub":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","email":"rls-test-a@codize.local","email_verified":true}',
   now(), now(), now()),
  (gen_random_uuid(), 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
   'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'email',
   '{"sub":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","email":"rls-test-b@codize.local","email_verified":true}',
   now(), now(), now());

-- user B owns one project so user A has something to fail to reach
insert into public.projects (id, user_id, intake_purpose)
values ('bbbbbbbb-0000-4000-8000-000000000001',
        'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'user B purpose');

select count(*) as profiles_auto_created  -- expect 2 (signup trigger)
from public.profiles
where user_id in ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');

-- ---------------------------------------------------------------------------
-- CLEANUP (run after verify_auth.py; expect all zeros)
-- ---------------------------------------------------------------------------
-- delete from auth.users where email like 'rls-test-%@codize.local';
-- select
--   (select count(*) from public.profiles)      as profiles_left,
--   (select count(*) from public.projects)      as projects_left,
--   (select count(*) from public.gate_sessions) as gate_sessions_left,
--   (select count(*) from public.unlocks)       as unlocks_left,
--   (select count(*) from auth.users
--      where email like 'rls-test-%@codize.local') as test_users_left;
