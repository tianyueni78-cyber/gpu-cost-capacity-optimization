create table projects (id text primary key, owner_id uuid not null default auth.uid(), name text not null);
create table forecast_jobs (id text, project_id text references projects(id), primary key(id, project_id));
create table data_snapshots (id text, project_id text references projects(id), summary jsonb not null, primary key(id, project_id));
create table backtest_runs (id text, project_id text references projects(id), metrics jsonb not null, primary key(id, project_id));
create table forecast_versions (version_id text, project_id text references projects(id), owner_id uuid not null default auth.uid(), payload jsonb not null default '{}'::jsonb, primary key(version_id, project_id));
create table forecast_adjustments (id text, project_id text references projects(id), version_id text, payload jsonb not null, primary key(id, project_id), foreign key(version_id, project_id) references forecast_versions(version_id, project_id));
create table capacity_scenarios (id text, project_id text references projects(id), version_id text, payload jsonb not null, primary key(id, project_id), foreign key(version_id, project_id) references forecast_versions(version_id, project_id));
create table purchase_plans (id text, project_id text references projects(id), version_id text, payload jsonb not null, primary key(id, project_id), foreign key(version_id, project_id) references forecast_versions(version_id, project_id));
create table forecast_actuals (id text, project_id text references projects(id), version_id text, payload jsonb not null, primary key(id, project_id), foreign key(version_id, project_id) references forecast_versions(version_id, project_id));

alter table projects enable row level security;
alter table forecast_jobs enable row level security;
alter table data_snapshots enable row level security;
alter table backtest_runs enable row level security;
alter table forecast_versions enable row level security;
alter table forecast_adjustments enable row level security;
alter table capacity_scenarios enable row level security;
alter table purchase_plans enable row level security;
alter table forecast_actuals enable row level security;

create policy project_ownership on projects using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy job_project_ownership on forecast_jobs using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy snapshot_project_ownership on data_snapshots using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy backtest_project_ownership on backtest_runs using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy version_project_ownership on forecast_versions using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy adjustment_project_ownership on forecast_adjustments using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy capacity_project_ownership on capacity_scenarios using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy purchase_project_ownership on purchase_plans using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));
create policy actual_project_ownership on forecast_actuals using (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid())) with check (exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()));

create function prevent_forecast_version_mutation() returns trigger language plpgsql as $$ begin raise exception 'published forecast versions are immutable'; end $$;
create trigger forecast_versions_immutable before update or delete on forecast_versions for each row execute function prevent_forecast_version_mutation();
