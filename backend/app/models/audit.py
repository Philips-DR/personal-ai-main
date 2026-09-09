from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: UUID | None = None
    action: str  # e.g. "email.triaged", "task.created", "draft.sent"
    module: str  # e.g. "orchestrator", "email", "meeting"
    intent: str | None = None
    input_summary: str | None = None   # Truncated user input
    output_summary: str | None = None  # Truncated response
    metadata: dict = {}                # Token counts, latency, etc.
    error: str | None = None
    duration_ms: int | None = None
    created_at: datetime | None = None
