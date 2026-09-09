"""Eval: prompt version comparisons.

Snapshot-style tests that capture what Claude produces for a known input.
Run with ``pytest -m eval`` to execute.

Useful workflow:
1. Record a baseline with --snapshot-update
2. Change a prompt in the codebase
3. Run evals — any degradation shows up as a diff
"""

import pytest

from tests.evals.fixtures import STANDUP_TRANSCRIPT


@pytest.mark.eval
class TestBriefFormatting:
    async def test_brief_contains_all_required_sections(
        self, mock_brief_formatter
    ):
        from app.modules.morning_brief.formatter import format_brief

        data = {
            "date": "Monday, May 25, 2026",
            "overdue_tasks": [{"title": "Submit Q2 report", "due_date": "2026-05-20"}],
            "due_today_tasks": [{"title": "Review PR #42"}],
            "total_open_tasks": 5,
            "priority_emails": [
                {"subject": "Production outage", "from_name": "Elton", "urgency_score": 9}
            ],
            "pending_meeting_actions": [],
            "today_events": [{"title": "Standup", "start": "09:00", "location": None}],
            "learning_nudge": None,
            "life_nudge": None,
            "prefs": {},
        }
        brief = await format_brief(data)

        assert len(brief) > 100, "Brief should be substantive"
        assert "Phil" in brief or "morning" in brief.lower(), (
            "Brief should address Phil or say good morning"
        )

    async def test_brief_with_learning_nudge_includes_study_section(
        self, mock_brief_formatter_with_learning
    ):
        from app.modules.morning_brief.formatter import format_brief

        data = {
            "date": "Monday, May 25, 2026",
            "overdue_tasks": [],
            "due_today_tasks": [],
            "total_open_tasks": 0,
            "priority_emails": [],
            "pending_meeting_actions": [],
            "today_events": [],
            "learning_nudge": {
                "roadmaps": [{"subject": "Roadmap: Rust", "content": "Week 1: Ownership"}],
                "habits": [],
            },
            "life_nudge": None,
            "prefs": {"brief_include_learning": True},
        }
        brief = await format_brief(data)
        assert len(brief) > 50


@pytest.mark.eval
class TestMeetingSummarizer:
    async def test_summary_has_executive_summary(self, mock_summarizer):
        from app.modules.meeting.summarizer import summarize_meeting

        summary = await summarize_meeting(STANDUP_TRANSCRIPT)
        assert summary.executive_summary, "Summary must have an executive_summary"
        assert len(summary.executive_summary) > 20

    async def test_summary_has_topics(self, mock_summarizer):
        from app.modules.meeting.summarizer import summarize_meeting

        summary = await summarize_meeting(STANDUP_TRANSCRIPT)
        assert summary.topics, "Summary should identify at least one topic"
