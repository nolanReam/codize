-- M16S.1 effective database verification.
--
-- Run this whole file as one batch through Supabase execute_sql or the SQL
-- editor AFTER the migration is deployed. It creates two rows only inside a
-- transaction, exercises effective role behavior, and rolls everything back.
-- Any failed expectation raises and aborts the batch. The final row must show
-- every boolean true and both cleanup counts zero.

begin;

insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_app_meta_data, raw_user_meta_data
) values
  (
    '00000000-0000-0000-0000-000000000000',
    'c1610000-0000-4000-8000-000000000001',
    'authenticated', 'authenticated', 'm16s1-a@codize.local', '',
    now(), now(), now(),
    '{"provider":"email","providers":["email"]}', '{}'
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    'c1610000-0000-4000-8000-000000000002',
    'authenticated', 'authenticated', 'm16s1-b@codize.local', '',
    now(), now(), now(),
    '{"provider":"email","providers":["email"]}', '{}'
  );

insert into public.projects (
  id, user_id, intake_purpose, task_progress, workflow_artifacts
) values
  (
    'c1610000-0000-4000-8000-000000000011',
    'c1610000-0000-4000-8000-000000000001',
    'M16S.1 owner A',
    '{"1":["ai-1"]}',
    '{"1":{"prompt_builder":{"saved_at":"baseline"}}}'
  ),
  (
    'c1610000-0000-4000-8000-000000000012',
    'c1610000-0000-4000-8000-000000000002',
    'M16S.1 owner B',
    '{}',
    '{}'
  );

-- Owner A: reads work, every direct project mutation fails at the privilege
-- layer. These cover whole-value replacement, jsonb_set, concatenation,
-- mixed-column smuggling, upsert, forged insert, and delete.
set local role authenticated;
select set_config(
  'request.jwt.claims',
  '{"sub":"c1610000-0000-4000-8000-000000000001","role":"authenticated"}',
  true
);

do $$
begin
  if (
    select count(*) from public.projects
    where id = 'c1610000-0000-4000-8000-000000000011'
      and workflow_artifacts ? '1'
  ) <> 1 then
    raise exception 'owner could not read own workflow artifact';
  end if;

  begin
    update public.projects
    set workflow_artifacts = '{"forged":true}'
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'owner full workflow_artifacts replacement unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    update public.projects
    set workflow_artifacts = jsonb_set(
      workflow_artifacts, '{1,prompt_builder,forged}', 'true'::jsonb, true
    )
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'owner partial workflow_artifacts mutation unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    update public.projects
    set workflow_artifacts = workflow_artifacts || '{"forged":true}'::jsonb
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'owner jsonb concatenation unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    update public.projects
    set intake_purpose = 'smuggled', workflow_artifacts = '{"forged":true}'
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'owner mixed protected update unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    insert into public.projects (id, user_id, intake_purpose, workflow_artifacts)
    values (
      'c1610000-0000-4000-8000-000000000011',
      'c1610000-0000-4000-8000-000000000001',
      'upsert', '{"forged":true}'
    )
    on conflict (id) do update
      set workflow_artifacts = excluded.workflow_artifacts;
    raise exception 'owner protected upsert unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    insert into public.projects (id, user_id, intake_purpose, workflow_artifacts)
    values (
      'c1610000-0000-4000-8000-000000000013',
      'c1610000-0000-4000-8000-000000000001',
      'forged insert', '{"1":{"change_map":{"status":"confirmed"}}}'
    );
    raise exception 'owner forged project insert unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    delete from public.projects
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'owner direct project delete unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$$;

-- Another authenticated user can neither see nor mutate owner A's row.
select set_config(
  'request.jwt.claims',
  '{"sub":"c1610000-0000-4000-8000-000000000002","role":"authenticated"}',
  true
);

do $$
begin
  if (
    select count(*) from public.projects
    where id = 'c1610000-0000-4000-8000-000000000011'
  ) <> 0 then
    raise exception 'cross-user project read unexpectedly succeeded';
  end if;

  begin
    update public.projects
    set workflow_artifacts = '{"forged":true}'
    where id = 'c1610000-0000-4000-8000-000000000011';
    raise exception 'cross-user project update unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$$;

-- Anonymous clients have neither read nor write privileges.
reset role;
set local role anon;

do $$
begin
  begin
    perform count(*) from public.projects;
    raise exception 'anonymous project read unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    insert into public.projects (user_id, workflow_artifacts)
    values ('c1610000-0000-4000-8000-000000000001', '{"forged":true}');
    raise exception 'anonymous project insert unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$$;

-- The trusted backend role still writes the protected column, while sibling
-- project state remains unchanged.
reset role;
set local role service_role;

update public.projects
set workflow_artifacts = '{"1":{"prompt_builder":{"saved_at":"trusted"}}}'
where id = 'c1610000-0000-4000-8000-000000000011';

do $$
begin
  if not exists (
    select 1 from public.projects
    where id = 'c1610000-0000-4000-8000-000000000011'
      and workflow_artifacts #>> '{1,prompt_builder,saved_at}' = 'trusted'
      and intake_purpose = 'M16S.1 owner A'
      and task_progress = '{"1":["ai-1"]}'::jsonb
      and user_id = 'c1610000-0000-4000-8000-000000000001'
  ) then
    raise exception 'trusted backend write or neighboring-field preservation failed';
  end if;
end
$$;

reset role;

-- Alternate-path inventory: there must be no public/api view or executable
-- authenticated function that references projects, and no executable
-- authenticated SECURITY DEFINER function in an exposed schema.
do $$
begin
  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname in ('public', 'api')
      and c.relkind in ('v', 'm')
      and pg_get_viewdef(c.oid, true) ilike '%projects%'
  ) then
    raise exception 'exposed view references projects';
  end if;

  if exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'api')
      and has_function_privilege('authenticated', p.oid, 'execute')
      and case
        when p.prokind in ('f', 'p')
          then pg_get_functiondef(p.oid) ilike '%projects%'
        else false
      end
  ) then
    raise exception 'authenticated executable function references projects';
  end if;

  if exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'api')
      and p.prosecdef
      and has_function_privilege('authenticated', p.oid, 'execute')
  ) then
    raise exception 'authenticated executable SECURITY DEFINER function exists';
  end if;
end
$$;

rollback;

select
  c.relrowsecurity as projects_rls_enabled,
  has_table_privilege('authenticated', c.oid, 'select') as owner_select_granted,
  not has_table_privilege('authenticated', c.oid, 'insert') as owner_insert_denied,
  not has_table_privilege('authenticated', c.oid, 'update') as owner_update_denied,
  not has_table_privilege('authenticated', c.oid, 'delete') as owner_delete_denied,
  not has_column_privilege(
    'authenticated', c.oid, 'workflow_artifacts', 'insert'
  ) as workflow_insert_denied,
  not has_column_privilege(
    'authenticated', c.oid, 'workflow_artifacts', 'update'
  ) as workflow_update_denied,
  (
    has_table_privilege('service_role', c.oid, 'select')
    and has_table_privilege('service_role', c.oid, 'insert')
    and has_table_privilege('service_role', c.oid, 'update')
    and has_table_privilege('service_role', c.oid, 'delete')
  ) as trusted_backend_crud_granted,
  (
    not has_table_privilege('anon', c.oid, 'select')
    and not has_table_privilege('anon', c.oid, 'insert')
    and not has_table_privilege('anon', c.oid, 'update')
    and not has_table_privilege('anon', c.oid, 'delete')
  ) as anonymous_crud_denied,
  (select count(*) from auth.users where email like 'm16s1-%@codize.local')
    as temporary_users_left,
  (select count(*) from public.projects
    where id in (
      'c1610000-0000-4000-8000-000000000011',
      'c1610000-0000-4000-8000-000000000012',
      'c1610000-0000-4000-8000-000000000013'
    )) as temporary_projects_left
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'projects';
