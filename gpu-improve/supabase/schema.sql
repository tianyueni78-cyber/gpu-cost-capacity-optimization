create extension if not exists pgcrypto;

create table projects (
  project_id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id),
  name text not null,
  created_at timestamptz not null default now()
);

create table actions (
  action_id text primary key,
  project_id uuid not null references projects(project_id) on delete cascade,
  action_type text not null,
  resource_pool_id text not null,
  owner text not null,
  status text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (action_id, project_id)
);

create table action_events (
  event_id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(project_id) on delete cascade,
  action_id text not null,
  from_status text,
  to_status text not null,
  changed_at timestamptz not null default now(),
  note text,
  foreign key (action_id, project_id) references actions(action_id, project_id)
);

create table baselines (
  baseline_id uuid primary key,
  project_id uuid not null references projects(project_id) on delete cascade,
  action_id text not null,
  source_sha256 text not null,
  frozen_at timestamptz not null,
  payload jsonb not null,
  foreign key (action_id, project_id) references actions(action_id, project_id)
);

create table measurements (
  measurement_id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(project_id) on delete cascade,
  action_id text not null,
  period_start date not null,
  period_end date not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  foreign key (action_id, project_id) references actions(action_id, project_id)
);

create table benefit_results (
  result_id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(project_id) on delete cascade,
  action_id text not null,
  outcome text not null,
  evidence_grade text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  foreign key (action_id, project_id) references actions(action_id, project_id)
);

create or replace function project_owned(target_project uuid)
returns boolean language sql stable security definer set search_path = public
as $$ select exists(select 1 from projects p where p.project_id = target_project and p.owner_id = auth.uid()) $$;

alter table projects enable row level security;
alter table actions enable row level security;
alter table action_events enable row level security;
alter table baselines enable row level security;
alter table measurements enable row level security;
alter table benefit_results enable row level security;

create policy projects_owner on projects for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy actions_owner on actions for all using (project_owned(project_id)) with check (project_owned(project_id));
create policy action_events_owner on action_events for all using (project_owned(project_id)) with check (project_owned(project_id));
create policy baselines_owner on baselines for insert with check (project_owned(project_id));
create policy baselines_read on baselines for select using (project_owned(project_id));
create policy measurements_owner on measurements for all using (project_owned(project_id)) with check (project_owned(project_id));
create policy benefit_results_owner on benefit_results for all using (project_owned(project_id)) with check (project_owned(project_id));

create or replace function prevent_baseline_mutation()
returns trigger language plpgsql as $$ begin raise exception 'baseline is immutable'; end; $$;
create trigger baselines_no_update before update or delete on baselines
for each row execute function prevent_baseline_mutation();
