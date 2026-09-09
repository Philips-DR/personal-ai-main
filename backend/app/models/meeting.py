from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.task import TaskPriority


class SpeakerSegment(BaseModel):
    speaker: str
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


class Transcript(BaseModel):
    segments: list[SpeakerSegment]
    raw_text: str
    duration_seconds: int | None = None


class ActionItem(BaseModel):
    description: str
    owner: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    source_quote: str  # Original text from transcript


class MeetingSummary(BaseModel):
    executive_summary: str  # 3 sentences max
    key_decisions: list[str]
    open_questions: list[str]
    topics: list[str]


class Meeting(BaseModel):
    id: UUID | None = None
    title: str | None = None
    date: datetime | None = None
    participants: list[str] = []
    raw_input_type: str | None = None  # "audio", "text", "transcript"
    raw_input_url: str | None = None
    raw_transcript: str | None = None
    enriched_transcript: str | None = None
    summary: MeetingSummary | None = None
    action_items: list[ActionItem] = []
    created_at: datetime | None = None


class MeetingActionItem(BaseModel):
    id: UUID | None = None
    meeting_id: UUID
    task_id: UUID | None = None
    description: str
    owner: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    source_quote: str
    created_at: datetime | None = None
