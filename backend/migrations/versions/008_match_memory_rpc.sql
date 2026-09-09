-- RPC function for pgvector similarity search used by the memory store.
-- Call via: supabase.rpc("match_memory_entries", {...})
create or replace function match_memory_entries(
  query_embedding vector(1536),
  match_limit int default 10,
  match_category text default null
)
returns table (
  id uuid,
  category text,
  subject text,
  content text,
  source_module text,
  source_id text,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz,
  expires_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    id, category, subject, content, source_module, source_id,
    metadata, created_at, updated_at, expires_at,
    1 - (embedding <=> query_embedding) as similarity
  from memory_entries
  where
    (match_category is null or category = match_category)
    and (expires_at is null or expires_at > now())
  order by embedding <=> query_embedding
  limit match_limit;
$$;
