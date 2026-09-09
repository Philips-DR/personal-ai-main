from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Intent(StrEnum):
    # Email
    EMAIL_READ = "email.read"
    EMAIL_TRIAGE = "email.triage"
    EMAIL_DRAFT = "email.draft"
    EMAIL_SUMMARIZE = "email.summarize"
    EMAIL_SEND = "email.send"

    # Meeting
    MEETING_TRANSCRIBE = "meeting.transcribe"
    MEETING_SUMMARIZE = "meeting.summarize"
    MEETING_ACTIONS = "meeting.actions"

    # Tasks
    TASK_CREATE = "task.create"
    TASK_LIST = "task.list"
    TASK_UPDATE = "task.update"
    TASK_REMIND = "task.remind"

    # Morning Brief
    BRIEF_GENERATE = "brief.generate"
    BRIEF_CONFIGURE = "brief.configure"

    # GitHub Docs
    GITHUB_DOCUMENT = "github.document"

    # Google Drive / Docs / Sheets
    DRIVE_SEARCH = "drive.search"
    DRIVE_READ = "drive.read"
    DOC_CREATE = "doc.create"
    DOC_APPEND = "doc.append"
    SHEET_APPEND_ROW = "sheet.append_row"

    # Learning Coach
    LEARNING_PLAN = "learning.plan"
    LEARNING_REVIEW = "learning.review"
    LEARNING_PROMPT = "learning.prompt"
    LIFE_SUGGEST = "life.suggest"

    # General
    MEMORY_RECALL = "memory.recall"
    GENERAL_CHAT = "general.chat"


class IntentClassification(BaseModel):
    intent: Intent
    parameters: dict[str, Any] = {}
    confidence: float


class PendingAction(BaseModel):
    """An action requiring explicit user approval before execution."""

    action_type: str  # e.g. "email.send", "task.create"
    description: str  # Human-readable description for the review gate
    payload: dict[str, Any]  # Data needed to execute the action


class ContextBundle(BaseModel):
    memory_entries: list[dict[str, Any]] = []
    relevant_tasks: list[dict[str, Any]] = []
    relevant_emails: list[dict[str, Any]] = []


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ModuleRequest(BaseModel):
    intent: Intent
    user_message: str
    parameters: dict[str, Any] = {}
    context: ContextBundle = ContextBundle()
    conversation_history: list[Message] = []


class ModuleResponse(BaseModel):
    content: str
    structured: dict[str, Any] | None = None
    pending_actions: list[PendingAction] = []
    memory_updates: list[dict[str, Any]] = []
    follow_up_intents: list[Intent] = []


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[Message] = []


class ChatResponse(BaseModel):
    content: str
    structured: dict[str, Any] | None = None
    pending_actions: list[PendingAction] = []
