"""AssemblyAI transcription provider — diarization + filler word removal."""

import logging

import assemblyai as aai

from app.config import settings
from app.models.meeting import SpeakerSegment, Transcript
from app.modules.meeting.transcription.base import TranscriptionProvider

logger = logging.getLogger(__name__)


class AssemblyAIProvider(TranscriptionProvider):
    def __init__(self) -> None:
        aai.settings.api_key = settings.assemblyai_api_key

    async def transcribe(self, audio_url: str) -> Transcript:
        """Transcribe audio URL with speaker diarization."""
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            language_detection=True,
        )

        transcript = transcriber.transcribe(audio_url, config)

        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

        segments = []
        for utterance in transcript.utterances:
            segments.append(SpeakerSegment(
                speaker=f"Speaker {utterance.speaker}",
                text=utterance.text,
                start_ms=utterance.start,
                end_ms=utterance.end,
            ))

        raw_text = " ".join(s.text for s in segments)
        logger.info("Transcribed audio: %d segments, %d chars", len(segments), len(raw_text))

        return Transcript(
            segments=segments,
            raw_text=raw_text,
            duration_seconds=transcript.audio_duration,
        )
