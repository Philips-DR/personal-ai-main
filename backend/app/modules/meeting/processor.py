"""Transcript processor — cleanup and normalization."""

import logging
import re

from app.models.meeting import Transcript

logger = logging.getLogger(__name__)

FILLER_WORDS = re.compile(
    r"\b(um+|uh+|like|you know|sort of|kind of|basically|actually|literally|right\?|so,?\s*)\b",
    re.IGNORECASE,
)


async def clean_transcript(transcript: Transcript) -> Transcript:
    """Remove filler words and normalize speaker labels."""
    cleaned_segments = []
    speaker_map: dict[str, str] = {}
    speaker_counter = 1

    for segment in transcript.segments:
        text = segment.text
        # Remove filler words
        text = FILLER_WORDS.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        # Normalize speaker labels
        speaker = segment.speaker
        if speaker not in speaker_map:
            speaker_map[speaker] = f"Speaker {speaker_counter}"
            speaker_counter += 1

        cleaned_segments.append(segment.model_copy(update={
            "speaker": speaker_map[speaker],
            "text": text,
        }))

    raw_text = " ".join(s.text for s in cleaned_segments)
    logger.info("Cleaned transcript: %d segments", len(cleaned_segments))
    return Transcript(
        segments=cleaned_segments,
        raw_text=raw_text,
        duration_seconds=transcript.duration_seconds,
    )
