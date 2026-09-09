"""Fixtures shared across eval tests.

All mocks here return realistic Claude outputs so evals run fast without
hitting Bedrock. To run against the real model, set EVAL_LIVE=1:

    EVAL_LIVE=1 pytest -m eval --tb=short
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_classifier():
    """Routes each input to the intent embedded in the test parametrize args."""
    def _side_effect(system_prompt, messages, **kwargs):
        msg = messages[-1]["content"] if messages else ""
        mapping = {
            "show me my tasks for today": "task.list",
            "remind me to send the report to Elton by Friday": "task.create",
            "mark the api task as done": "task.update",
            "mark the API task as done": "task.update",
            "what's in my inbox?": "email.read",
            "triage my email": "email.triage",
            "draft a reply to sarah's meeting request": "email.draft",
            "draft a reply to Sarah's meeting request": "email.draft",
            "generate my morning brief": "brief.generate",
            "change my brief to 8am": "brief.configure",
            "help me build a rust learning roadmap": "learning.plan",
            "help me build a Rust learning roadmap": "learning.plan",
            "what should i study today?": "learning.prompt",
            "what should I study today?": "learning.prompt",
            "suggest something i can do this weekend": "life.suggest",
            "suggest something I can do this weekend": "life.suggest",
            "find my notes from last week": "drive.search",
            "what did we decide in the last board meeting?": "memory.recall",
            "hello, how are you?": "general.chat",
        }
        intent = mapping.get(msg, "general.chat")
        return {"intent": intent, "confidence": 0.9, "parameters": {}}

    with patch(
        "app.orchestrator.intent_classifier.invoke_claude_json",
        new=AsyncMock(side_effect=_side_effect),
    ):
        yield


@pytest.fixture
def mock_classifier_low_confidence():
    with patch(
        "app.orchestrator.intent_classifier.invoke_claude_json",
        new=AsyncMock(return_value={"intent": "task.list", "confidence": 0.3, "parameters": {}}),
    ):
        yield


@pytest.fixture
def mock_classifier_unknown_intent():
    with patch(
        "app.orchestrator.intent_classifier.invoke_claude_json",
        new=AsyncMock(return_value={
            "intent": "nonexistent.thing", "confidence": 0.95, "parameters": {}
        }),
    ):
        yield


# ---------------------------------------------------------------------------
# Action extractor mocks
# ---------------------------------------------------------------------------

_STANDUP_ACTIONS = {
    "action_items": [
        {
            "description": "Update deployment documentation",
            "owner": "Henry",
            "due_date": None,
            "priority": "medium",
            "source_quote": "can you also update the deployment docs by Thursday?",
        },
        {
            "description": "Prepare demo slides for AyaData team (non-technical audience)",
            "owner": "Elton",
            "due_date": None,
            "priority": "medium",
            "source_quote": "Elton, can you prepare the slides for the demo?",
        },
        {
            "description": "Check availability for demo on Wednesday and confirm",
            "owner": "Phil",
            "due_date": None,
            "priority": "low",
            "source_quote": "let me know by tomorrow if Wednesday works",
        },
    ]
}

_PLANNING_ACTIONS = {
    "action_items": [
        {
            "description": "Complete database migration",
            "owner": "Bob",
            "due_date": "2026-06-01",
            "priority": "high",
            "source_quote": "we need to complete the database migration by June 1st",
        },
        {
            "description": "Provide weekly Monday status update on infra",
            "owner": "Bob",
            "due_date": None,
            "priority": "medium",
            "source_quote": "give us a status update every Monday",
        },
        {
            "description": "Support Bob on networking side (20% time, 3 weeks)",
            "owner": "Dave",
            "due_date": None,
            "priority": "medium",
            "source_quote": "I can carve out 20% of my time for the next three weeks",
        },
        {
            "description": "Send Bob a calendar invite",
            "owner": "Dave",
            "due_date": None,
            "priority": "low",
            "source_quote": "I'll send Bob a calendar invite today",
        },
        {
            "description": "Ship API rate limiting feature",
            "owner": "Carol",
            "due_date": "2026-06-15",
            "priority": "high",
            "source_quote": "we need the API rate limiting feature shipped by June 15th",
        },
        {
            "description": "Prepare design doc for rate limiting for review",
            "owner": "Carol",
            "due_date": None,
            "priority": "medium",
            "source_quote": "I'll have a design doc ready for review by next Friday",
        },
        {
            "description": "Schedule Acme Corp onboarding kickoff call",
            "owner": "Alice",
            "due_date": None,
            "priority": "high",
            "source_quote": "I'll handle the kickoff call scheduling this week",
        },
    ]
}

_EMPTY_ACTIONS = {"action_items": []}


@pytest.fixture
def mock_action_extractor_standup():
    with patch(
        "app.modules.meeting.action_extractor.invoke_claude_json",
        new=AsyncMock(return_value=_STANDUP_ACTIONS),
    ):
        yield


@pytest.fixture
def mock_action_extractor_planning():
    with patch(
        "app.modules.meeting.action_extractor.invoke_claude_json",
        new=AsyncMock(return_value=_PLANNING_ACTIONS),
    ):
        yield


@pytest.fixture
def mock_action_extractor_empty():
    with patch(
        "app.modules.meeting.action_extractor.invoke_claude_json",
        new=AsyncMock(return_value=_EMPTY_ACTIONS),
    ):
        yield


# ---------------------------------------------------------------------------
# Summarizer mock
# ---------------------------------------------------------------------------

_STANDUP_SUMMARY = {
    "executive_summary": (
        "The team held a standup covering progress on the Postgres migration "
        "and authentication refactor. Key follow-ups include updating deployment "
        "docs and preparing slides for a client demo next week."
    ),
    "key_decisions": [
        "Demo to be held on Wednesday next week.",
        "Henry owns deployment documentation update by Thursday.",
    ],
    "open_questions": [
        "Does Wednesday work for everyone for the demo?",
    ],
    "topics": ["Postgres migration", "Auth refactor", "Demo preparation", "Deployment docs"],
}


@pytest.fixture
def mock_summarizer():
    with patch(
        "app.modules.meeting.summarizer.invoke_claude_json",
        new=AsyncMock(return_value=_STANDUP_SUMMARY),
    ):
        yield


# ---------------------------------------------------------------------------
# Morning brief formatter mock
# ---------------------------------------------------------------------------

_BRIEF_TEXT = """# Good morning, Phil! — Monday, May 25, 2026

## Your Top 3 Today
1. **OVERDUE:** Submit Q2 report (was due May 20)
2. Review PR #42
3. Standup at 09:00

## Calendar
- 09:00 Standup

## Emails Needing Your Attention
- **Production outage** from Elton (urgency: 9/10)

## Tasks
- **OVERDUE:** Submit Q2 report

## Quick Stats
- 5 open tasks | 1 email needs reply | 1 meeting today"""

_BRIEF_TEXT_WITH_LEARNING = _BRIEF_TEXT + "\n\n## Learning Today\nContinue Rust Week 1: Ownership"


@pytest.fixture
def mock_brief_formatter():
    with patch(
        "app.modules.morning_brief.formatter.invoke_claude",
        new=AsyncMock(return_value=_BRIEF_TEXT),
    ):
        yield


@pytest.fixture
def mock_brief_formatter_with_learning():
    with patch(
        "app.modules.morning_brief.formatter.invoke_claude",
        new=AsyncMock(return_value=_BRIEF_TEXT_WITH_LEARNING),
    ):
        yield
