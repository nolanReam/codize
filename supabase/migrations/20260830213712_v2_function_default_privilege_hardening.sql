-- Bring an already-provisioned hosted Supabase database to the same
-- future-function default as a fresh V2 foundation install. Supabase's hosted
-- defaults for postgres/public are schema-specific, while PostgreSQL's ordinary
-- PUBLIC EXECUTE default is global, so both scopes must be hardened.
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated, service_role;

alter default privileges for role postgres
  revoke execute on functions from public;
