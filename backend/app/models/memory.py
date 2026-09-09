from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class MemoryCategory(StrEnum):
    PERSON = "person"
    PROJECT = "project"
    PREFERENCE = "preference"
    FACT = "fact"
    CONVERSATION = "conversation"
    # Second-brain categories (Phase 2)
    SKILL_GOAL = "skill_goal"
    LEARNING_ROADMAP = "learning_roadmap"
    HABIT = "habit"
    INTEREST = "interest"
    RECURRING_NOTE = "recurring_note"


class MemoryEntry(BaseModel):
    id: UUID | None = None
    category: MemoryCategory
    subject: str  # e.g. "Henry", "AyaData Logistics", "email tone"
    content: str  # The memory content
    source_module: str | None = None
    source_id: str | None = None
    metadata: dict = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class Person(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    organization: str | None = None
    notes: str | None = None


class ProjectContext(BaseModel):
    name: str
    description: str | None = None
    members: list[str] = []
    status: str | None = None
