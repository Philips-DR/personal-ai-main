-- Memory store with pgvector for RAG
create table if not exists memory_entries (
  id uuid primary key default uuid_generate_v4(),
  category text not null check (category in ('person', 'project', 'preference', 'fact', 'conversation')),
  subject text not null,
  content text not null,
  embedding vector(1536),
  source_module text,
  source_id text,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  expires_at timestamptz
);

create index if not exists idx_memory_embedding
  on memory_entries using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create index if not exists idx_memory_category on memory_entries (category);
create index if not exists idx_memory_subject on memory_entries (subject);
