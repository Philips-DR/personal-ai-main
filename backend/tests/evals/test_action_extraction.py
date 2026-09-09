"""Eval: action item extraction from meeting transcripts.

Tests that the Claude prompt correctly extracts action items with
owner, description, and due date from known fixture transcripts.
"""


import pytest

from tests.evals.fixtures import (
    PLANNING_TRANSCRIPT,
    STANDUP_TRANSCRIPT,
)


@pytest.mark.eval
class TestActionExtraction:
    async def test_standup_finds_deployment_docs_action(
        self, mock_action_extractor_standup
    ):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items(STANDUP_TRANSCRIPT)
        descriptions = [i.description.lower() for i in items]

        doc_actions = [d for d in descriptions if any(
            kw in d for kw in ["deployment", "docs", "documentation", "document"]
        )]
        assert doc_actions, (
            f"Expected a deployment docs action item, got: {descriptions}"
        )

    async def test_standup_finds_demo_slides_action(
        self, mock_action_extractor_standup
    ):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items(STANDUP_TRANSCRIPT)
        descriptions = [i.description.lower() for i in items]

        slide_actions = [d for d in descriptions if any(
            kw in d for kw in ["slide", "demo", "presentation", "prepare"]
        )]
        assert slide_actions, (
            f"Expected a slides/demo action item, got: {descriptions}"
        )

    async def test_standup_action_has_owner(self, mock_action_extractor_standup):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items(STANDUP_TRANSCRIPT)
        owners = [i.owner for i in items if i.owner]
        assert owners, "Expected at least one action item with an assigned owner"

    async def test_action_items_have_source_quote(self, mock_action_extractor_standup):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items(STANDUP_TRANSCRIPT)
        assert all(
            item.source_quote for item in items
        ), "All action items should include a source_quote"

    async def test_planning_transcript_extracts_multiple_actions(
        self, mock_action_extractor_planning
    ):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items(PLANNING_TRANSCRIPT)
        assert len(items) >= 3, (
            f"Planning transcript should yield at least 3 action items, got {len(items)}"
        )

    async def test_empty_transcript_returns_no_actions(
        self, mock_action_extractor_empty
    ):
        from app.modules.meeting.action_extractor import extract_action_items

        items = await extract_action_items("Just a quick hello.")
        assert len(items) == 0


@pytest.mark.eval
class TestActionExtractionParsing:
    """Test the JSON parsing layer without touching Claude."""

    def test_action_extractor_handles_malformed_json_gracefully(self):
        from app.claude import _extract_json

        result = _extract_json('Sure! Here is the JSON:\n```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_action_extractor_handles_trailing_text(self):
        from app.claude import _extract_json

        result = _extract_json('{"key": "value"}\n\nHope that helps!')
        assert result == {"key": "value"}
