-- Beta-critical resumable Project setup. Partial answers remain bounded,
-- structured Project state; command provenance is backend-only.

alter table public.v2_projects
  add column setup_draft_command_id uuid;

create unique index v2_projects_setup_draft_command_key
  on public.v2_projects (owner_user_id, setup_draft_command_id)
  where setup_draft_command_id is not null;

create function codize_v2_internal.save_v2_setup_draft(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid,
  p_project_context text,
  p_initial_change_label text,
  p_done_condition text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_draft jsonb;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_command_id is null
     or p_project_context is null or pg_catalog.octet_length(p_project_context) > 8192
     or p_initial_change_label is null or pg_catalog.octet_length(p_initial_change_label) > 200
     or p_done_condition is null or pg_catalog.octet_length(p_done_condition) > 4096 then
    raise exception using errcode = '22023', message = 'invalid Project setup draft command';
  end if;

  v_draft := pg_catalog.jsonb_build_object(
    'project_context', pg_catalog.btrim(p_project_context),
    'initial_change_label', pg_catalog.btrim(p_initial_change_label),
    'done_condition', pg_catalog.btrim(p_done_condition),
    'source', 'student_setup_draft'
  );

  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  if v_project.setup_draft_command_id = p_command_id then
    if v_project.setup_draft <> v_draft then
      raise exception using errcode = '23505', message = 'setup draft command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'project', pg_catalog.to_jsonb(v_project), 'replayed', true
    );
  end if;

  if v_project.version <> p_expected_project_version
     or v_project.lifecycle_state <> 'draft'
     or v_project.setup_resume_step not in ('idea_capture', 'existing_project_context') then
    raise exception using errcode = '40001', message = 'stale or ineligible Project setup draft';
  end if;

  update public.v2_projects as p
  set setup_draft = v_draft,
      setup_draft_command_id = p_command_id,
      version = p.version + 1
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  returning * into v_project;

  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project), 'replayed', false
  );
end;
$$;

-- Draft saves advance Project version before establishment. Preserve the
-- existing atomic setup behavior while allowing its semantic response-loss
-- replay at any valid post-draft Project version.
create or replace function codize_v2_internal.establish_v2_manual_project(
  p_owner_user_id uuid,
  p_project_id uuid,
  p_expected_project_version bigint,
  p_command_id uuid,
  p_project_context text,
  p_plan_item_id uuid,
  p_change_label text,
  p_done_condition text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project public.v2_projects%rowtype;
  v_item public.v2_plan_items%rowtype;
begin
  if p_owner_user_id is null or p_project_id is null
     or p_expected_project_version is null or p_command_id is null
     or p_plan_item_id is null
     or p_project_context is null or pg_catalog.btrim(p_project_context) = ''
     or pg_catalog.octet_length(p_project_context) > 8192
     or p_change_label is null or pg_catalog.btrim(p_change_label) = ''
     or pg_catalog.octet_length(p_change_label) > 200
     or p_done_condition is null or pg_catalog.btrim(p_done_condition) = ''
     or pg_catalog.octet_length(p_done_condition) > 4096 then
    raise exception using errcode = '22023', message = 'invalid manual Project setup command';
  end if;

  select * into v_project from public.v2_projects as p
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  for update;
  if not found then
    raise exception using errcode = 'P0002', message = 'v2 project not found';
  end if;

  if v_project.last_plan_command_id = p_command_id then
    select * into v_item from public.v2_plan_items as pi
    where pi.id = p_plan_item_id and pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id;
    if not found
       or v_project.setup_draft ->> 'project_context' <> pg_catalog.btrim(p_project_context)
       or v_item.label <> pg_catalog.btrim(p_change_label)
       or v_item.intended_outcome <> pg_catalog.btrim(p_done_condition) then
      raise exception using errcode = '23505', message = 'manual setup command id already used';
    end if;
    return pg_catalog.jsonb_build_object(
      'project', pg_catalog.to_jsonb(v_project),
      'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', true
    );
  end if;

  if v_project.lifecycle_state = 'active'
     and v_project.setup_resume_step = 'ready'
     and v_project.version >= 2
     and v_project.plan_version = 2
     and v_project.setup_draft = pg_catalog.jsonb_build_object(
       'project_context', pg_catalog.btrim(p_project_context),
       'source', 'student_setup'
     ) then
    select * into v_item from public.v2_plan_items as pi
    where pi.project_id = p_project_id
      and pi.owner_user_id = p_owner_user_id
      and pi.scope_band = 'first_version'
      and pi.status = 'ready'
      and pi.label = pg_catalog.btrim(p_change_label)
      and pi.intended_outcome = pg_catalog.btrim(p_done_condition);
    if found and (
      select pg_catalog.count(*) from public.v2_plan_items as pi
      where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id
    ) = 1 then
      return pg_catalog.jsonb_build_object(
        'project', pg_catalog.to_jsonb(v_project),
        'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', true
      );
    end if;
  end if;

  if v_project.version <> p_expected_project_version
     or v_project.lifecycle_state <> 'draft'
     or v_project.setup_resume_step not in ('idea_capture', 'existing_project_context') then
    raise exception using errcode = '40001', message = 'stale or ineligible manual Project setup';
  end if;
  if exists (select 1 from public.v2_plan_items as pi
             where pi.project_id = p_project_id and pi.owner_user_id = p_owner_user_id) then
    raise exception using errcode = '23514', message = 'manual setup requires an empty plan';
  end if;

  insert into public.v2_plan_items (
    id, project_id, owner_user_id, label, intended_outcome,
    scope_band, status, order_key
  ) values (
    p_plan_item_id, p_project_id, p_owner_user_id,
    pg_catalog.btrim(p_change_label), pg_catalog.btrim(p_done_condition),
    'first_version', 'ready', 1024
  ) returning * into v_item;

  update public.v2_projects as p
  set lifecycle_state = 'active', setup_resume_step = 'ready',
      setup_draft = pg_catalog.jsonb_build_object(
        'project_context', pg_catalog.btrim(p_project_context),
        'source', 'student_setup'
      ),
      setup_draft_command_id = null,
      last_plan_command_id = p_command_id,
      plan_version = p.plan_version + 1,
      version = p.version + 1
  where p.id = p_project_id and p.owner_user_id = p_owner_user_id
  returning * into v_project;

  return pg_catalog.jsonb_build_object(
    'project', pg_catalog.to_jsonb(v_project),
    'plan_item', pg_catalog.to_jsonb(v_item), 'replayed', false
  );
end;
$$;

create function public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
returns jsonb language sql security invoker set search_path=''
as $$ select codize_v2_internal.save_v2_setup_draft($1,$2,$3,$4,$5,$6,$7) $$;

alter function codize_v2_internal.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
  owner to codize_v2_executor;
alter function codize_v2_internal.establish_v2_manual_project(uuid,uuid,bigint,uuid,text,uuid,text,text)
  owner to codize_v2_executor;

revoke execute on function
  public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
from public, anon, authenticated;
revoke execute on function
  codize_v2_internal.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
from public, anon, authenticated, service_role;
grant execute on function
  codize_v2_internal.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
to service_role;
grant execute on function
  public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
to service_role;

comment on function public.save_v2_setup_draft(uuid,uuid,bigint,uuid,text,text,text)
  is 'Backend-only partial V2 Project setup persistence with optimistic concurrency and replay identity.';
