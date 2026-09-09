from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    SNOOZED = "snoozed"


class TaskPriority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Project(BaseModel):
    id: UUID | None = None
    name: str
    description: str | None = None
    created_at: datetime | None = None


class Task(BaseModel):
    id: UUID | None = None
    title: str
    description: str | None = None
    owner: str = "Phil"
    assignee: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    project_id: UUID | None = None
    project_name: str | None = None  # Convenience field, not stored
    source_type: str | None = None  # "meeting", "email", "manual"
    source_id: str | None = None
    source_quote: str | None = None
    estimated_minutes: int | None = None
    reminder_at: datetime | None = None
    snoozed_until: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    owner: str = "Phil"
    assignee: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    project_name: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    source_quote: str | None = None
    estimated_minutes: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee: str | None = None
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    reminder_at: datetime | None = None
    snoozed_until: datetime | None = None
