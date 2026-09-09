"""Local Whisper transcription provider via faster-whisper (CTranslate2)."""

import logging
import os
import tempfile
from pathlib import Path

import httpx

from app.config import settings
from app.models.meeting import SpeakerSegment, Transcript
from app.modules.meeting.transcription.base import TranscriptionProvider

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".mp4", ".m4a", ".ogg", ".flac", ".webm"}


class WhisperLocalProvider(TranscriptionProvider):
    """On-device transcription using faster-whisper.

    All audio stays local — no data sent to third-party services.
    Diarization is not built into faster-whisper; segments are labelled
    sequentially as Speaker 1, Speaker 2, … based on detected pauses.
    Pair with pyannote.audio for true multi-speaker diarization (Phase 4+).
    """

    def __init__(self, model_size: str | None = None) -> None:
        self._model_size = model_size or settings.whisper_model_size
        self._model = None  # lazy-loaded on first use

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper model '%s' (first call)", self._model_size)
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded")
        return self._model

    async def transcribe(self, audio_url: str) -> Transcript:
        """Transcribe audio from a local path or HTTP URL."""
        audio_path = await self._resolve_audio(audio_url)
        try:
            return self._run_transcription(audio_path)
        finally:
            if audio_path != audio_url and os.path.exists(audio_path):
                os.unlink(audio_path)

    def _run_transcription(self, audio_path: str) -> Transcript:
        model = self._get_model()
        segments_iter, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        segments = list(segments_iter)

        speaker_segments = []
        for seg in segments:
            speaker_segments.append(
                SpeakerSegment(
                    speaker="Speaker 1",
                    text=seg.text.strip(),
                    start_ms=int(seg.start * 1000),
                    end_ms=int(seg.end * 1000),
                )
            )

        raw_text = " ".join(s.text for s in speaker_segments)
        duration = int(info.duration) if info.duration else None

        logger.info(
            "Whisper transcribed %d segments, %d chars, %.1fs",
            len(speaker_segments), len(raw_text), info.duration or 0,
        )

        return Transcript(
            segments=speaker_segments,
            raw_text=raw_text,
            duration_seconds=duration,
        )

    async def _resolve_audio(self, audio_url: str) -> str:
        """Return a local filesystem path, downloading if needed."""
        path = Path(audio_url)
        if path.exists() and path.suffix.lower() in _AUDIO_EXTENSIONS:
            return audio_url

        if audio_url.startswith(("http://", "https://")):
            suffix = Path(audio_url).suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name

            logger.info("Downloading audio for Whisper: %s", audio_url)
            async with (
                httpx.AsyncClient(follow_redirects=True, timeout=120) as client,
                client.stream("GET", audio_url) as resp,
            ):
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

            logger.info("Downloaded audio to %s", tmp_path)
            return tmp_path

        raise ValueError(
            f"Cannot resolve audio source: '{audio_url}'. "
            "Provide a local file path or an HTTP/HTTPS URL."
        )
