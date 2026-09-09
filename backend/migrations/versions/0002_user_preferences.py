"""Add user_preferences table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-25
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     TEXT NOT NULL UNIQUE DEFAULT 'phil',
            brief_cron              TEXT DEFAULT '0 7 * * *',
            brief_timezone          TEXT DEFAULT 'Africa/Lagos',
            brief_include_learning  BOOLEAN DEFAULT TRUE,
            brief_include_life      BOOLEAN DEFAULT TRUE,
            brief_tone              TEXT DEFAULT 'warm',
            learning_focus_areas    TEXT[] DEFAULT '{}',
            life_focus_areas        TEXT[] DEFAULT '{}',
            transcription_provider  TEXT DEFAULT 'assemblyai',
            drive_enabled           BOOLEAN DEFAULT FALSE,
            extra                   JSONB DEFAULT '{}',
            updated_at              TIMESTAMPTZ DEFAULT now()
        )
    """)
    # Seed default row for Phil
    op.execute("""
        INSERT INTO user_preferences (user_id)
        VALUES ('phil')
        ON CONFLICT (user_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_preferences")
