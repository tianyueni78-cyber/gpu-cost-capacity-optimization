alter table datasets drop constraint if exists datasets_source_type_check;
alter table datasets add constraint datasets_source_type_check check (source_type in ('SAMPLE','UPLOAD','PUBLIC'));

create table if not exists optimization_recommendations (
  organization_id uuid not null,
  project_id uuid not null,
  recommendation_id uuid primary key default gen_random_uuid(),
  result_id uuid not null references analysis_results(result_id) on delete cascade,
  dataset_id uuid not null references datasets(dataset_id) on delete cascade,
  recommendation_key text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  unique (result_id, recommendation_key),
  foreign key (organization_id, project_id) references projects(organization_id, project_id) on delete cascade
);

alter table optimization_recommendations enable row level security;
drop policy if exists optimization_recommendations_members on optimization_recommendations;
create policy optimization_recommendations_members on optimization_recommendations
using (is_organization_member(organization_id))
with check (is_organization_member(organization_id));
grant select, insert, update on optimization_recommendations to authenticated;
