"""Abstract transcription provider — swappable via factory."""

from abc import ABC, abstractmethod

from app.models.meeting import SpeakerSegment, Transcript


class TranscriptionProvider(ABC):
    """Base class for transcription providers.

    Implementations: AssemblyAI, WhisperLocal.
    Selected via TRANSCRIPTION_PROVIDER env var or user_preferences.
    """

    @abstractmethod
    async def transcribe(self, audio_url: str) -> Transcript:
        """Transcribe audio and return a Transcript with speaker segments."""

    async def transcribe_text(self, text: str) -> Transcript:
        """Parse raw text/notes into a Transcript.

        Recognises speaker labels like "Phil:" or "[Henry] Some words".
        Shared default — providers override only when they need different behaviour.
        """
        lines = text.strip().split("\n")
        segments: list[SpeakerSegment] = []
        current_speaker = "Speaker 1"

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.endswith(":") and len(line) < 30:
                current_speaker = line.rstrip(":")
                continue
            if line.startswith("[") and "]" in line:
                current_speaker = line.split("]")[0].lstrip("[")
                line = line.split("]", 1)[1].strip()
                if not line:
                    continue

            segments.append(SpeakerSegment(speaker=current_speaker, text=line))

        if not segments:
            segments = [SpeakerSegment(speaker="Speaker 1", text=text)]

        raw_text = " ".join(s.text for s in segments)
        return Transcript(segments=segments, raw_text=raw_text)
