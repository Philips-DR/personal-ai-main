"""Initial schema — all tables, extensions, and the match_memory_entries RPC.

Revision ID: 0001
Revises:
Create Date: 2026-05-25
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- Memory store (pgvector RAG) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            category text NOT NULL CHECK (category IN ('person', 'project', 'preference', 'fact', 'conversation', 'skill_goal', 'learning_roadmap', 'habit', 'interest', 'recurring_note')),
            subject text NOT NULL,
            content text NOT NULL,
            embedding vector(1536),
            source_module text,
            source_id text,
            metadata jsonb DEFAULT '{}',
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now(),
            expires_at timestamptz
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries (category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_subject ON memory_entries (subject)")

    # --- Enums ---
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'blocked', 'done', 'snoozed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_priority AS ENUM ('urgent', 'high', 'medium', 'low');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE triage_category AS ENUM ('action_needed', 'follow_up', 'fyi', 'newsletter', 'spam');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE draft_status AS ENUM ('none', 'pending_review', 'approved', 'sent');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)

    # --- Projects ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            name text NOT NULL UNIQUE,
            description text,
            created_at timestamptz DEFAULT now()
        )
    """)

    # --- Tasks ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            title text NOT NULL,
            description text,
            owner text NOT NULL DEFAULT 'Phil',
            assignee text,
            due_date timestamptz,
            priority task_priority DEFAULT 'medium',
            status task_status DEFAULT 'todo',
            project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
            source_type text,
            source_id text,
            source_quote text,
            estimated_minutes int,
            reminder_at timestamptz,
            snoozed_until timestamptz,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now(),
            completed_at timestamptz
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks (due_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks (owner)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks (project_id)")

    # --- Email threads ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS email_threads (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            gmail_thread_id text UNIQUE NOT NULL,
            gmail_message_id text,
            subject text,
            from_address text,
            from_name text,
            snippet text,
            category triage_category,
            urgency_score int CHECK (urgency_score BETWEEN 1 AND 5),
            summary text,
            is_read boolean DEFAULT false,
            needs_reply boolean DEFAULT false,
            draft_id text,
            draft_content text,
            draft_status draft_status DEFAULT 'none',
            last_synced_at timestamptz,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_thread_id ON email_threads (gmail_thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_category ON email_threads (category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_needs_reply ON email_threads (needs_reply) WHERE needs_reply = true")

    # --- Audit log ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            action text NOT NULL,
            module text NOT NULL,
            intent text,
            input_summary text,
            output_summary text,
            metadata jsonb DEFAULT '{}',
            error text,
            duration_ms int,
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_log (module)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at DESC)")

    # --- Meetings ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            title text,
            date timestamptz,
            participants text[],
            raw_input_type text CHECK (raw_input_type IN ('audio', 'text', 'transcript')),
            raw_input_url text,
            raw_transcript text,
            enriched_transcript text,
            summary text,
            key_decisions text[],
            open_questions text[],
            topics text[],
            metadata jsonb DEFAULT '{}',
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS meeting_action_items (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            task_id uuid REFERENCES tasks(id) ON DELETE SET NULL,
            description text NOT NULL,
            owner text,
            due_date timestamptz,
            priority task_priority DEFAULT 'medium',
            source_quote text NOT NULL,
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_meeting_action_meeting ON meeting_action_items (meeting_id)")

    # --- OAuth tokens ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            provider text NOT NULL UNIQUE,
            access_token text NOT NULL,
            refresh_token text NOT NULL,
            token_expiry timestamptz NOT NULL,
            scopes text[],
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
    """)

    # --- pgvector similarity search function ---
    op.execute("""
        CREATE OR REPLACE FUNCTION match_memory_entries(
            query_embedding vector(1536),
            match_limit int DEFAULT 10,
            match_category text DEFAULT NULL
        )
        RETURNS TABLE (
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
        LANGUAGE sql STABLE
        AS $$
            SELECT
                id, category, subject, content, source_module, source_id,
                metadata, created_at, updated_at, expires_at,
                1 - (embedding <=> query_embedding) AS similarity
            FROM memory_entries
            WHERE
                (match_category IS NULL OR category = match_category)
                AND (expires_at IS NULL OR expires_at > now())
            ORDER BY embedding <=> query_embedding
            LIMIT match_limit;
        $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS match_memory_entries")
    op.execute("DROP TABLE IF EXISTS oauth_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS meeting_action_items CASCADE")
    op.execute("DROP TABLE IF EXISTS meetings CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS email_threads CASCADE")
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_entries CASCADE")
    op.execute("DROP TYPE IF EXISTS draft_status")
    op.execute("DROP TYPE IF EXISTS triage_category")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
