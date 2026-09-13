insert into auth.users (id, email)
values
  ('33333333-3333-3333-3333-333333333333', 'student@example.com'),
  ('66666666-6666-6666-6666-666666666666', 'other@example.com')
on conflict do nothing;

insert into organizations (organization_id, name)
values
  ('11111111-1111-1111-1111-111111111111', 'Student Lab'),
  ('44444444-4444-4444-4444-444444444444', 'Other Lab')
on conflict do nothing;

insert into projects (organization_id, project_id, name)
values
  ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'GPU Pilot'),
  ('44444444-4444-4444-4444-444444444444', '55555555-5555-5555-5555-555555555555', 'Private Project')
on conflict do nothing;

insert into memberships (organization_id, user_id, role)
values
  ('11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', 'ORG_ADMIN'),
  ('44444444-4444-4444-4444-444444444444', '66666666-6666-6666-6666-666666666666', 'ORG_ADMIN')
on conflict do nothing;

insert into product_entitlements (organization_id, product, active)
select '11111111-1111-1111-1111-111111111111', product, true
from unnest(array['gpu-data','gpu-optimize','gpu-improve','gpu-forecast']) product
on conflict do nothing;

grant usage on schema public, auth to authenticated;
grant select on organizations, memberships, projects, product_entitlements, subscriptions, connectors, jobs, audit_events to authenticated;
grant insert, update on jobs to authenticated;
