-- Immutable audit log for all agent actions
create table if not exists audit_log (
  id uuid primary key default uuid_generate_v4(),
  action text not null,
  module text not null,
  intent text,
  input_summary text,
  output_summary text,
  metadata jsonb default '{}',
  error text,
  duration_ms int,
  created_at timestamptz default now()
);

-- Append-only: no updates or deletes allowed
create index if not exists idx_audit_action on audit_log (action);
create index if not exists idx_audit_module on audit_log (module);
create index if not exists idx_audit_created on audit_log (created_at desc);
