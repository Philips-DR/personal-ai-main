"""Eval: intent routing — verify the classifier prompt maps known inputs correctly.

These tests mock Claude's response so they run fast without hitting Bedrock.
Use the ``--eval-live`` flag (see conftest.py) to run against the real model.
"""

import pytest

from app.models.orchestrator import Intent


@pytest.mark.eval
class TestIntentRoutingMocked:
    """Fast evals using pre-determined Claude outputs."""

    @pytest.mark.parametrize("message,expected_intent", [
        ("show me my tasks for today", "task.list"),
        ("remind me to send the report to Elton by Friday", "task.create"),
        ("mark the API task as done", "task.update"),
        ("what's in my inbox?", "email.read"),
        ("triage my email", "email.triage"),
        ("draft a reply to Sarah's meeting request", "email.draft"),
        ("generate my morning brief", "brief.generate"),
        ("change my brief to 8am", "brief.configure"),
        ("help me build a Rust learning roadmap", "learning.plan"),
        ("what should I study today?", "learning.prompt"),
        ("suggest something I can do this weekend", "life.suggest"),
        ("find my notes from last week", "drive.search"),
        ("what did we decide in the last board meeting?", "memory.recall"),
        ("hello, how are you?", "general.chat"),
    ])
    async def test_intent_maps_to_correct_module(
        self, message: str, expected_intent: str, mock_classifier
    ):
        from app.orchestrator.intent_classifier import classify_intent

        result = await classify_intent(message)
        assert result.intent == Intent(expected_intent), (
            f"Message '{message}' → got '{result.intent}', expected '{expected_intent}'"
        )

    async def test_low_confidence_falls_back_to_general(self, mock_classifier_low_confidence):
        from app.orchestrator.intent_classifier import classify_intent

        result = await classify_intent("qwerty asdf zxcv")
        assert result.intent == Intent.GENERAL_CHAT

    async def test_unknown_intent_string_falls_back(self, mock_classifier_unknown_intent):
        from app.orchestrator.intent_classifier import classify_intent

        result = await classify_intent("something obscure")
        assert result.intent == Intent.GENERAL_CHAT


@pytest.mark.eval
class TestIntentEnumCoverage:
    """Verify the classifier prompt lists every Intent value."""

    def test_all_intents_in_classifier_prompt(self):
        from app.orchestrator.intent_classifier import _SYSTEM_PROMPT

        for intent in Intent:
            assert intent.value in _SYSTEM_PROMPT, (
                f"Intent '{intent.value}' is missing from the classifier system prompt"
            )
