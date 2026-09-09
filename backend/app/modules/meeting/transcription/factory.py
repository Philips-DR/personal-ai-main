"""Factory for creating transcription providers — swappable via preferences or env var."""

from app.config import settings
from app.modules.meeting.transcription.base import TranscriptionProvider


def get_provider(name: str | None = None) -> TranscriptionProvider:
    """Create a transcription provider by name.

    Resolution order:
    1. Explicit ``name`` argument (from caller who already loaded preferences)
    2. ``TRANSCRIPTION_PROVIDER`` env var / config default ("assemblyai")
    """
    provider_name = name or settings.transcription_provider

    if provider_name == "assemblyai":
        from app.modules.meeting.transcription.assemblyai import AssemblyAIProvider
        return AssemblyAIProvider()

    if provider_name == "whisper":
        from app.modules.meeting.transcription.whisper_local import WhisperLocalProvider
        return WhisperLocalProvider()

    raise ValueError(
        f"Unknown transcription provider: '{provider_name}'. "
        "Available providers: assemblyai, whisper"
    )
