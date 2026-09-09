-- OAuth 2.0 token storage
-- Note: access_token and refresh_token should be encrypted at the application layer
create table if not exists oauth_tokens (
  id uuid primary key default uuid_generate_v4(),
  provider text not null unique,  -- e.g. 'gmail'
  access_token text not null,
  refresh_token text not null,
  token_expiry timestamptz not null,
  scopes text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
