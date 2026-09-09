"""Action item extractor via Claude — structured with source quotes."""

import json
import logging

from app.claude import invoke_claude_json
from app.config import settings
from app.models.meeting import ActionItem
from app.models.task import TaskPriority

logger = logging.getLogger(__name__)

_MAX_TOKENS = 2048
_TEMPERATURE = 0.1


def _extract_prompt() -> str:
    return (
        "You are an action item extraction assistant. Given a meeting transcript, extract all action items.\n\n"
        "For each item, provide:\n"
        "- description: What needs to be done (required)\n"
        f"- owner: Who is responsible — default to \"{settings.user_name}\" if unclear (string)\n"
        "- due_date: ISO date string if mentioned, else null\n"
        '- priority: "urgent", "high", "medium", or "low" — default "medium"\n'
        "- source_quote: The EXACT quote from the transcript that led to this action item (required)\n\n"
        'Self-check: After extracting, re-read the transcript and ask: "Did I miss any action items?"\n\n'
        'Return JSON: {"action_items": [...]}\n'
        "Respond with ONLY the JSON object."
    )


async def extract_action_items(transcript_text: str) -> list[ActionItem]:
    """Extract action items from a meeting transcript."""
    text = transcript_text[:settings.transcript_max_length]

    try:
        parsed = await invoke_claude_json(
            system_prompt=_extract_prompt(),
            messages=[{"role": "user", "content": text}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
    except json.JSONDecodeError:
        logger.error("Failed to parse action items JSON")
        return []

    items = []
    for raw in parsed.get("action_items", []):
        try:
            items.append(ActionItem(
                description=raw["description"],
                owner=raw.get("owner", settings.user_name),
                due_date=raw.get("due_date"),
                priority=TaskPriority(raw.get("priority", "medium")),
                source_quote=raw.get("source_quote", ""),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed action item: %s", e)

    logger.info("Extracted %d action items", len(items))
    return items
