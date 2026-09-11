create extension if not exists pgcrypto;

create table if not exists organizations (
  organization_id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists memberships (
  organization_id uuid not null references organizations(organization_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('ORG_ADMIN','ANALYST','APPROVER','VIEWER')),
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create table if not exists projects (
  organization_id uuid not null references organizations(organization_id) on delete cascade,
  project_id uuid not null default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now(),
  primary key (project_id),
  unique (organization_id, project_id)
);

create table if not exists product_entitlements (
  organization_id uuid not null references organizations(organization_id) on delete cascade,
  product text not null check (product in ('gpu-data','gpu-optimize','gpu-improve','gpu-forecast')),
  active boolean not null default false,
  primary key (organization_id, product)
);

create table if not exists subscriptions (
  organization_id uuid primary key references organizations(organization_id) on delete cascade,
  plan_id text not null,
  status text not null check (status in ('TRIAL','ACTIVE','PAST_DUE','EXPIRED','CANCELLED')),
  current_period_end timestamptz not null,
  provider_reference text unique
);

create table if not exists connectors (
  organization_id uuid not null,
  project_id uuid not null,
  connector_id uuid not null default gen_random_uuid(),
  kind text not null check (kind in ('AWS','KUBERNETES','PROMETHEUS')),
  secret_reference text not null,
  sync_cursor text,
  last_success_at timestamptz,
  created_at timestamptz not null default now(),
  primary key (connector_id),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

create table if not exists jobs (
  organization_id uuid not null,
  project_id uuid not null,
  job_id uuid not null default gen_random_uuid(),
  product text not null,
  operation text not null,
  idempotency_key text not null,
  status text not null check (status in ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
  progress smallint not null default 0 check (progress between 0 and 100),
  public_error_code text,
  created_at timestamptz not null default now(),
  primary key (job_id),
  unique (organization_id, idempotency_key),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

create table if not exists audit_events (
  organization_id uuid not null,
  project_id uuid not null,
  event_id uuid not null default gen_random_uuid(),
  actor_user_id uuid references auth.users(id),
  action text not null,
  resource_type text not null,
  resource_id text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (event_id),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

create or replace function is_organization_member(target_organization uuid)
returns boolean language sql stable security definer set search_path = public
as $$ select exists(select 1 from memberships m where m.organization_id = target_organization and m.user_id = auth.uid()) $$;

create or replace function prevent_audit_mutation() returns trigger language plpgsql
as $$ begin raise exception 'audit events are append only'; end $$;
drop trigger if exists audit_events_immutable on audit_events;
create trigger audit_events_immutable before update or delete on audit_events
for each row execute function prevent_audit_mutation();

alter table organizations enable row level security;
alter table memberships enable row level security;
alter table projects enable row level security;
alter table product_entitlements enable row level security;
alter table subscriptions enable row level security;
alter table connectors enable row level security;
alter table jobs enable row level security;
alter table audit_events enable row level security;

create policy organizations_members on organizations for select using (is_organization_member(organization_id));
create policy memberships_members on memberships for select using (is_organization_member(organization_id));
create policy projects_members on projects for select using (is_organization_member(organization_id));
create policy entitlements_members on product_entitlements for select using (is_organization_member(organization_id));
create policy subscriptions_members on subscriptions for select using (is_organization_member(organization_id));
create policy connectors_members on connectors for select using (is_organization_member(organization_id));
create policy jobs_members on jobs for select using (is_organization_member(organization_id));
create policy audit_members on audit_events for select using (is_organization_member(organization_id));
