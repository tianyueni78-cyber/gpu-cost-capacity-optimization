create table if not exists datasets (
  organization_id uuid not null,
  project_id uuid not null,
  dataset_id uuid primary key default gen_random_uuid(),
  source_type text not null check (source_type in ('SAMPLE','UPLOAD')),
  status text not null default 'READY' check (status in ('READY','ANALYZING','SUCCEEDED','BLOCKED','FAILED')),
  row_counts jsonb not null default '{}'::jsonb,
  period_start timestamptz,
  period_end timestamptz,
  created_at timestamptz not null default now(),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

create table if not exists dataset_files (
  organization_id uuid not null,
  project_id uuid not null,
  file_id uuid primary key default gen_random_uuid(),
  dataset_id uuid not null references datasets(dataset_id) on delete cascade,
  role text not null check (role in ('inventory','usage','billing','sla')),
  file_name text not null,
  storage_path text not null,
  row_count integer not null check (row_count >= 0),
  created_at timestamptz not null default now(),
  unique (dataset_id, role),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

alter table jobs add column if not exists dataset_id uuid references datasets(dataset_id) on delete cascade;

create table if not exists analysis_results (
  organization_id uuid not null,
  project_id uuid not null,
  result_id uuid primary key default gen_random_uuid(),
  dataset_id uuid not null references datasets(dataset_id) on delete cascade,
  job_id uuid not null unique references jobs(job_id) on delete cascade,
  status text not null check (status in ('SUCCEEDED','BLOCKED','FAILED')),
  summary jsonb not null default '{}'::jsonb,
  audit jsonb not null default '[]'::jsonb,
  signals jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

create table if not exists report_artifacts (
  organization_id uuid not null,
  project_id uuid not null,
  artifact_id uuid primary key default gen_random_uuid(),
  result_id uuid not null references analysis_results(result_id) on delete cascade,
  kind text not null,
  file_name text not null,
  storage_path text not null,
  mime_type text not null,
  created_at timestamptz not null default now(),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

alter table datasets enable row level security;
alter table dataset_files enable row level security;
alter table analysis_results enable row level security;
alter table report_artifacts enable row level security;

drop policy if exists datasets_members on datasets;
drop policy if exists dataset_files_members on dataset_files;
drop policy if exists analysis_results_members on analysis_results;
drop policy if exists report_artifacts_members on report_artifacts;
create policy datasets_members on datasets using (is_organization_member(organization_id)) with check (is_organization_member(organization_id));
create policy dataset_files_members on dataset_files using (is_organization_member(organization_id)) with check (is_organization_member(organization_id));
create policy analysis_results_members on analysis_results using (is_organization_member(organization_id)) with check (is_organization_member(organization_id));
create policy report_artifacts_members on report_artifacts using (is_organization_member(organization_id)) with check (is_organization_member(organization_id));

grant select, insert, update on datasets, dataset_files, analysis_results, report_artifacts to authenticated;
