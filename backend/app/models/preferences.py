from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserPreferences(BaseModel):
    id: UUID
    user_id: str
    brief_cron: str
    brief_timezone: str
    brief_include_learning: bool
    brief_include_life: bool
    brief_tone: str
    learning_focus_areas: list[str]
    life_focus_areas: list[str]
    transcription_provider: str
    drive_enabled: bool
    extra: dict
    updated_at: datetime


class PreferencesUpdate(BaseModel):
    brief_cron: str | None = None
    brief_timezone: str | None = None
    brief_include_learning: bool | None = None
    brief_include_life: bool | None = None
    brief_tone: str | None = None
    learning_focus_areas: list[str] | None = None
    life_focus_areas: list[str] | None = None
    transcription_provider: str | None = None
    drive_enabled: bool | None = None
    extra: dict | None = None
