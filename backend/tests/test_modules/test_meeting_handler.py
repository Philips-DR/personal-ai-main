"""Unit tests for the Meeting module handler."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.meeting import ActionItem, MeetingSummary, SpeakerSegment, Transcript
from app.models.orchestrator import Intent
from app.models.task import TaskPriority
from app.modules.meeting.handler import MeetingModule
from tests.conftest import make_request


@pytest.fixture
def handler():
    return MeetingModule()


def _sample_transcript(text: str = "Alice: Let's ship by Friday. Bob: I'll update the docs.") -> Transcript:
    return Transcript(
        segments=[SpeakerSegment(speaker="Alice", text=text)],
        raw_text=text,
    )


def _sample_summary() -> MeetingSummary:
    return MeetingSummary(
        executive_summary="Team discussed shipping schedule and documentation.",
        key_decisions=["Ship by Friday"],
        open_questions=["Who reviews the PR?"],
        topics=["Deployment", "Documentation"],
    )


def _sample_action_items() -> list[ActionItem]:
    return [
        ActionItem(
            description="Update the docs",
            owner="Bob",
            priority=TaskPriority.HIGH,
            source_quote="I'll update the docs",
        )
    ]


def _mock_session():
    """Return a get_session context manager that silently accepts all writes."""
    mock_result = MagicMock()
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


def _mock_failing_session():
    """Return a get_session context manager whose execute() raises."""
    @asynccontextmanager
    async def _mock_get_session():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        yield mock_session

    return _mock_get_session


class TestMeetingHandle:
    async def test_full_pipeline_with_text_input(self, handler):
        transcript = _sample_transcript()
        summary = _sample_summary()
        actions = _sample_action_items()
        provider = MagicMock()
        provider.transcribe_text = AsyncMock(return_value=transcript)

        with (
            patch("app.modules.meeting.handler.get_provider", return_value=provider),
            patch("app.modules.meeting.handler.clean_transcript", new=AsyncMock(return_value=transcript)),
            patch("app.modules.meeting.handler.summarize_meeting", new=AsyncMock(return_value=summary)),
            patch("app.modules.meeting.handler.extract_action_items", new=AsyncMock(return_value=actions)),
            patch("app.modules.meeting.handler.get_session", _mock_session()),
        ):
            req = make_request(Intent.MEETING_TRANSCRIBE, "Team discussed shipping and docs")
            response = await handler.handle(req)

        assert "Team discussed shipping" in response.content
        assert "Ship by Friday" in response.content
        assert "Update the docs" in response.content
        assert response.structured["meeting_id"] is not None

    async def test_chains_to_task_creation_when_actions_exist(self, handler):
        transcript = _sample_transcript()
        summary = _sample_summary()
        actions = _sample_action_items()
        provider = MagicMock()
        provider.transcribe_text = AsyncMock(return_value=transcript)

        with (
            patch("app.modules.meeting.handler.get_provider", return_value=provider),
            patch("app.modules.meeting.handler.clean_transcript", new=AsyncMock(return_value=transcript)),
            patch("app.modules.meeting.handler.summarize_meeting", new=AsyncMock(return_value=summary)),
            patch("app.modules.meeting.handler.extract_action_items", new=AsyncMock(return_value=actions)),
            patch("app.modules.meeting.handler.get_session", _mock_session()),
        ):
            req = make_request(Intent.MEETING_SUMMARIZE, "meeting notes here")
            response = await handler.handle(req)

        assert Intent.TASK_CREATE in response.follow_up_intents

    async def test_no_follow_up_when_no_actions(self, handler):
        transcript = _sample_transcript()
        summary = _sample_summary()
        provider = MagicMock()
        provider.transcribe_text = AsyncMock(return_value=transcript)

        with (
            patch("app.modules.meeting.handler.get_provider", return_value=provider),
            patch("app.modules.meeting.handler.clean_transcript", new=AsyncMock(return_value=transcript)),
            patch("app.modules.meeting.handler.summarize_meeting", new=AsyncMock(return_value=summary)),
            patch("app.modules.meeting.handler.extract_action_items", new=AsyncMock(return_value=[])),
            patch("app.modules.meeting.handler.get_session", _mock_session()),
        ):
            req = make_request(Intent.MEETING_ACTIONS, "short meeting, no actions")
            response = await handler.handle(req)

        assert response.follow_up_intents == []

    async def test_includes_source_quotes_in_response(self, handler):
        transcript = _sample_transcript()
        summary = _sample_summary()
        actions = _sample_action_items()
        provider = MagicMock()
        provider.transcribe_text = AsyncMock(return_value=transcript)

        with (
            patch("app.modules.meeting.handler.get_provider", return_value=provider),
            patch("app.modules.meeting.handler.clean_transcript", new=AsyncMock(return_value=transcript)),
            patch("app.modules.meeting.handler.summarize_meeting", new=AsyncMock(return_value=summary)),
            patch("app.modules.meeting.handler.extract_action_items", new=AsyncMock(return_value=actions)),
            patch("app.modules.meeting.handler.get_session", _mock_session()),
        ):
            req = make_request(Intent.MEETING_TRANSCRIBE, "notes")
            response = await handler.handle(req)

        assert "I'll update the docs" in response.content

    async def test_db_failure_does_not_crash_response(self, handler):
        transcript = _sample_transcript()
        summary = _sample_summary()
        actions = _sample_action_items()
        provider = MagicMock()
        provider.transcribe_text = AsyncMock(return_value=transcript)

        with (
            patch("app.modules.meeting.handler.get_provider", return_value=provider),
            patch("app.modules.meeting.handler.clean_transcript", new=AsyncMock(return_value=transcript)),
            patch("app.modules.meeting.handler.summarize_meeting", new=AsyncMock(return_value=summary)),
            patch("app.modules.meeting.handler.extract_action_items", new=AsyncMock(return_value=actions)),
            patch("app.modules.meeting.handler.get_session", _mock_failing_session()),
        ):
            req = make_request(Intent.MEETING_TRANSCRIBE, "notes")
            response = await handler.handle(req)

        assert "Meeting Summary" in response.content
