"""Email triage — classify threads by category and urgency via Claude."""

import json
import logging

from app.claude import invoke_claude_json
from app.config import settings
from app.models.email import TriageCategory

logger = logging.getLogger(__name__)

_MAX_TOKENS = 256
_TEMPERATURE = 0.1


def _triage_prompt() -> str:
    return (
        f"You are an email triage assistant for {settings.user_name}."
        " Classify this email into exactly one category:\n\n"
        "- action_needed: Requires action (reply, review, approve, etc.)\n"
        "- follow_up: Needs follow-up but not immediately urgent\n"
        "- fyi: Informational, no action needed\n"
        "- newsletter: Marketing, newsletters, automated updates\n"
        "- spam: Unwanted or irrelevant\n\n"
        "Also assign an urgency score from 1-5 (5 = most urgent).\n\n"
        f"Context: {settings.user_name} leads an AI Solutions team at {settings.user_company}.\n\n"
        'Return JSON: {"category": "<category>", "urgency_score": <1-5>, "reason": "<brief explanation>"}\n'
        "Respond with ONLY the JSON object."
    )


async def classify_thread(subject: str, snippet: str, from_address: str) -> dict:
    """Classify an email thread using Claude."""
    email_text = f"From: {from_address}\nSubject: {subject}\n\n{snippet}"

    try:
        parsed = await invoke_claude_json(
            system_prompt=_triage_prompt(),
            messages=[{"role": "user", "content": email_text}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        category = parsed.get("category", "fyi")
        try:
            TriageCategory(category)
        except ValueError:
            category = "fyi"

        return {
            "category": category,
            "urgency_score": min(max(int(parsed.get("urgency_score", 3)), 1), 5),
            "reason": parsed.get("reason", ""),
            "needs_reply": category in ("action_needed", "follow_up"),
        }
    except json.JSONDecodeError:
        logger.error("Failed to parse triage response")
        return {"category": "fyi", "urgency_score": 3, "reason": "", "needs_reply": False}
