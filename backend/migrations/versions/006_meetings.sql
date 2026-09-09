-- Meeting records and action items
create table if not exists meetings (
  id uuid primary key default uuid_generate_v4(),
  title text,
  date timestamptz,
  participants text[],
  raw_input_type text check (raw_input_type in ('audio', 'text', 'transcript')),
  raw_input_url text,
  raw_transcript text,
  enriched_transcript text,
  summary text,
  key_decisions text[],
  open_questions text[],
  topics text[],
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists meeting_action_items (
  id uuid primary key default uuid_generate_v4(),
  meeting_id uuid not null references meetings(id) on delete cascade,
  task_id uuid references tasks(id) on delete set null,
  description text not null,
  owner text,
  due_date timestamptz,
  priority task_priority default 'medium',
  source_quote text not null,
  created_at timestamptz default now()
);

create index if not exists idx_meeting_action_meeting on meeting_action_items (meeting_id);
