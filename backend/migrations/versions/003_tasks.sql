-- Task and project management
do $$ begin
  create type task_status as enum ('todo', 'in_progress', 'blocked', 'done', 'snoozed');
exception when duplicate_object then null; end $$;

do $$ begin
  create type task_priority as enum ('urgent', 'high', 'medium', 'low');
exception when duplicate_object then null; end $$;

create table if not exists projects (
  id uuid primary key default uuid_generate_v4(),
  name text not null unique,
  description text,
  created_at timestamptz default now()
);

create table if not exists tasks (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  description text,
  owner text not null default 'Phil',
  assignee text,
  due_date timestamptz,
  priority task_priority default 'medium',
  status task_status default 'todo',
  project_id uuid references projects(id) on delete set null,
  source_type text,
  source_id text,
  source_quote text,
  estimated_minutes int,
  reminder_at timestamptz,
  snoozed_until timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  completed_at timestamptz
);

create index if not exists idx_tasks_status on tasks (status);
create index if not exists idx_tasks_due on tasks (due_date);
create index if not exists idx_tasks_owner on tasks (owner);
create index if not exists idx_tasks_project on tasks (project_id);
