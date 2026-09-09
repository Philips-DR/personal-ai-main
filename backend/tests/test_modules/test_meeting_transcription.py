"""Tests for the transcription provider layer."""

import pytest

from app.modules.meeting.transcription.base import TranscriptionProvider
from app.modules.meeting.transcription.factory import get_provider
from app.modules.meeting.transcription.whisper_local import WhisperLocalProvider


class TestTranscribeText:
    """Base class transcribe_text — shared by all providers via inheritance."""

    async def test_plain_text_becomes_single_segment(self):
        provider = WhisperLocalProvider()
        transcript = await provider.transcribe_text("Hello world, this is a test.")
        assert len(transcript.segments) == 1
        assert transcript.segments[0].speaker == "Speaker 1"
        assert "Hello world" in transcript.segments[0].text
        assert "Hello world" in transcript.raw_text

    async def test_colon_speaker_labels_parsed(self):
        provider = WhisperLocalProvider()
        text = "Phil:\nHello everyone.\nHenry:\nThanks for joining."
        transcript = await provider.transcribe_text(text)
        assert len(transcript.segments) == 2
        assert transcript.segments[0].speaker == "Phil"
        assert transcript.segments[1].speaker == "Henry"

    async def test_bracket_speaker_labels_parsed(self):
        provider = WhisperLocalProvider()
        text = "[Alice] Good morning.\n[Bob] Morning, let's start."
        transcript = await provider.transcribe_text(text)
        assert transcript.segments[0].speaker == "Alice"
        assert transcript.segments[1].speaker == "Bob"

    async def test_empty_lines_skipped(self):
        provider = WhisperLocalProvider()
        text = "Phil:\n\nHello.\n\nHenry:\n\nWorld."
        transcript = await provider.transcribe_text(text)
        assert len(transcript.segments) == 2

    async def test_empty_input_returns_single_segment(self):
        provider = WhisperLocalProvider()
        transcript = await provider.transcribe_text("")
        assert len(transcript.segments) == 1


class TestFactory:
    def test_assemblyai_provider_returned(self):
        provider = get_provider("assemblyai")
        assert provider.__class__.__name__ == "AssemblyAIProvider"

    def test_whisper_provider_returned(self):
        provider = get_provider("whisper")
        assert isinstance(provider, WhisperLocalProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown transcription provider"):
            get_provider("deepgram")

    def test_whisper_inherits_base(self):
        assert issubclass(WhisperLocalProvider, TranscriptionProvider)


class TestWhisperLocalProvider:
    def test_lazy_model_load(self):
        provider = WhisperLocalProvider(model_size="base")
        assert provider._model is None  # not loaded until first transcribe()

    def test_model_size_from_config(self):
        from app.config import settings
        provider = WhisperLocalProvider()
        assert provider._model_size == settings.whisper_model_size

    def test_model_size_override(self):
        provider = WhisperLocalProvider(model_size="tiny")
        assert provider._model_size == "tiny"

    async def test_invalid_path_raises(self):
        provider = WhisperLocalProvider()
        with pytest.raises(ValueError, match="Cannot resolve audio source"):
            await provider._resolve_audio("/nonexistent/path/audio.mp3")
