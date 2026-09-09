"""Unit tests for the Morning Brief module handler."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.orchestrator import Intent
from app.models.preferences import UserPreferences
from app.modules.morning_brief.handler import MorningBriefModule
from tests.conftest import make_request


@pytest.fixture
def handler():
    return MorningBriefModule()


def _sample_brief_data() -> dict:
    return {
        "date": "Monday, April 28, 2026",
        "overdue_tasks": [],
        "due_today_tasks": [],
        "total_open_tasks": 2,
        "priority_emails": [],
        "pending_meeting_actions": [],
        "today_events": [],
    }


class TestBriefGenerate:
    async def test_generates_brief(self, handler):
        prefs = _mock_prefs()
        with (
            patch("app.preferences.store.get_preferences", new=AsyncMock(return_value=prefs)),
            patch("app.modules.morning_brief.handler.aggregate_brief_data", new=AsyncMock(return_value=_sample_brief_data())),  # noqa: E501
            patch("app.modules.morning_brief.handler.format_brief", new=AsyncMock(return_value="# Morning Brief\n\nAll clear today.")),  # noqa: E501
            patch("app.modules.morning_brief.handler.get_next_run_time", return_value="2026-04-29 07:00:00+01:00"),
        ):
            req = make_request(Intent.BRIEF_GENERATE, "give me my morning brief")
            response = await handler.handle(req)

        assert "Morning Brief" in response.content
        assert "2026-04-29" in response.content  # next run time in footer
        assert response.structured is not None

    async def test_brief_includes_next_run_footer(self, handler):
        prefs = _mock_prefs()
        with (
            patch("app.preferences.store.get_preferences", new=AsyncMock(return_value=prefs)),
            patch("app.modules.morning_brief.handler.aggregate_brief_data", new=AsyncMock(return_value=_sample_brief_data())),  # noqa: E501
            patch("app.modules.morning_brief.handler.format_brief", new=AsyncMock(return_value="Brief content")),
            patch("app.modules.morning_brief.handler.get_next_run_time", return_value="Tomorrow 07:00"),
        ):
            req = make_request(Intent.BRIEF_GENERATE, "morning brief")
            response = await handler.handle(req)

        assert "Next scheduled brief" in response.content

    async def test_brief_without_next_run_time(self, handler):
        prefs = _mock_prefs()
        with (
            patch("app.preferences.store.get_preferences", new=AsyncMock(return_value=prefs)),
            patch("app.modules.morning_brief.handler.aggregate_brief_data", new=AsyncMock(return_value=_sample_brief_data())),  # noqa: E501
            patch("app.modules.morning_brief.handler.format_brief", new=AsyncMock(return_value="Brief content")),
            patch("app.modules.morning_brief.handler.get_next_run_time", return_value=None),
        ):
            req = make_request(Intent.BRIEF_GENERATE, "morning brief")
            response = await handler.handle(req)

        assert "Next scheduled brief" not in response.content


def _mock_prefs(**overrides) -> UserPreferences:
    import uuid
    from datetime import UTC, datetime
    defaults = dict(
        id=uuid.uuid4(),
        user_id="phil",
        brief_cron="0 8 * * *",
        brief_timezone="UTC",
        brief_include_learning=True,
        brief_include_life=True,
        brief_tone="warm",
        learning_focus_areas=[],
        life_focus_areas=[],
        transcription_provider="assemblyai",
        drive_enabled=False,
        extra={},
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return UserPreferences(**defaults)


class TestBriefConfigure:
    async def test_updates_cron_schedule(self, handler):
        prefs = _mock_prefs(brief_cron="0 8 * * *")
        with (
            patch("app.modules.morning_brief.handler.start_scheduler", new=AsyncMock()),
            patch("app.preferences.store.update_preferences", new=AsyncMock(return_value=prefs)),
            patch("app.preferences.store.get_preferences", new=AsyncMock(return_value=prefs)),
        ):
            req = make_request(
                Intent.BRIEF_CONFIGURE, "change brief to 8am",
                params={"cron": "0 8 * * *"}
            )
            response = await handler.handle(req)

        assert "0 8 * * *" in response.content

    async def test_updates_timezone(self, handler):
        prefs = _mock_prefs(brief_timezone="UTC")
        with (
            patch("app.modules.morning_brief.handler.start_scheduler", new=AsyncMock()),
            patch("app.preferences.store.update_preferences", new=AsyncMock(return_value=prefs)),
            patch("app.preferences.store.get_preferences", new=AsyncMock(return_value=prefs)),
        ):
            req = make_request(
                Intent.BRIEF_CONFIGURE, "change timezone to UTC",
                params={"timezone": "UTC"}
            )
            response = await handler.handle(req)

        assert "UTC" in response.content
