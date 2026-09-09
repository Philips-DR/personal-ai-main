-- Gmail thread cache and triage state
do $$ begin
  create type triage_category as enum ('action_needed', 'follow_up', 'fyi', 'newsletter', 'spam');
exception when duplicate_object then null; end $$;

do $$ begin
  create type draft_status as enum ('none', 'pending_review', 'approved', 'sent');
exception when duplicate_object then null; end $$;

create table if not exists email_threads (
  id uuid primary key default uuid_generate_v4(),
  gmail_thread_id text unique not null,
  gmail_message_id text,
  subject text,
  from_address text,
  from_name text,
  snippet text,
  category triage_category,
  urgency_score int check (urgency_score between 1 and 5),
  summary text,
  is_read boolean default false,
  needs_reply boolean default false,
  draft_id text,
  draft_content text,
  draft_status draft_status default 'none',
  last_synced_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_email_thread_id on email_threads (gmail_thread_id);
create index if not exists idx_email_category on email_threads (category);
create index if not exists idx_email_needs_reply on email_threads (needs_reply) where needs_reply = true;
