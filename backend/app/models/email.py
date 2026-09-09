from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class TriageCategory(StrEnum):
    ACTION_NEEDED = "action_needed"
    FOLLOW_UP = "follow_up"
    FYI = "fyi"
    NEWSLETTER = "newsletter"
    SPAM = "spam"


class DraftStatus(StrEnum):
    NONE = "none"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"


class EmailTone(StrEnum):
    FORMAL = "formal"
    CASUAL = "casual"
    NEUTRAL = "neutral"


class EmailThread(BaseModel):
    id: UUID | None = None
    gmail_thread_id: str
    gmail_message_id: str | None = None
    subject: str | None = None
    from_address: str | None = None
    from_name: str | None = None
    snippet: str | None = None
    category: TriageCategory | None = None
    urgency_score: int | None = None  # 1-5
    summary: str | None = None
    is_read: bool = False
    needs_reply: bool = False
    draft_id: str | None = None
    draft_content: str | None = None
    draft_status: DraftStatus = DraftStatus.NONE
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmailDraft(BaseModel):
    to: list[str]
    subject: str
    body: str
    tone: EmailTone = EmailTone.NEUTRAL
    in_reply_to_thread_id: str | None = None
    gmail_draft_id: str | None = None  # Set after saving to Gmail
