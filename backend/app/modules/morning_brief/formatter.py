"""Morning brief formatter via Claude."""

import json
import logging

from app.claude import invoke_claude
from app.config import settings

logger = logging.getLogger(__name__)

_MAX_TOKENS = 2048
_TEMPERATURE = 0.5


def _brief_system() -> str:
    return (
        f"You are {settings.user_name}'s personal AI assistant — warm, direct, and genuinely helpful.\n"
        f"{settings.user_name} is a {settings.user_job_title} at {settings.user_company}."
        " Generate their morning brief.\n\n"
        "Write in a conversational but professional tone. The brief should feel like a smart colleague\n"
        "giving a quick rundown, not a robot reciting a report.\n\n"
        "Structure the brief as:\n\n"
        f"# Good morning, {settings.user_name}! ☀️ — {{date}}\n\n"
        "## Your Top 3 Today\n"
        "(Pick the 3 most important/urgent items across ALL sources — tasks, emails, meetings)\n\n"
        "## Calendar\n"
        '(Today\'s meetings with times; "Clear day!" if none)\n\n'
        "## Emails Needing Your Attention\n"
        "(List with sender and subject; skip section if none)\n\n"
        "## Tasks\n"
        "(Overdue first in bold, then due today; skip if none)\n\n"
        "## Meeting Follow-ups\n"
        "(Pending action items from recent meetings; skip if none)\n\n"
        "## Learning Today\n"
        "(Only include if learning data provided — reference their roadmap and suggest one small study action)\n\n"
        "## Life Nudge\n"
        "(Only include if life data provided — one practical, personal suggestion)\n\n"
        "## Quick Stats\n"
        "- X open tasks | Y emails need reply | Z meetings today\n\n"
        "Keep it scannable. Use bold for urgency. Be encouraging but honest about overdue items."
    )


async def format_brief(brief_data: dict) -> str:
    """Format aggregated data into a morning brief via Claude."""
    prefs = brief_data.get("prefs", {})
    tone = prefs.get("brief_tone", "warm")

    data_summary = {
        "date": brief_data["date"],
        "tone": tone,
        "overdue_tasks": [
            {"title": t.get("title"), "due": str(t.get("due_date", ""))[:10]}
            for t in brief_data["overdue_tasks"]
        ],
        "due_today_tasks": [{"title": t.get("title")} for t in brief_data["due_today_tasks"]],
        "total_open_tasks": brief_data["total_open_tasks"],
        "priority_emails": [
            {"subject": e.get("subject"), "from": e.get("from_name"), "urgency": e.get("urgency_score")}
            for e in brief_data["priority_emails"]
        ],
        "pending_meeting_actions": [
            {
                "description": a.get("description"),
                "owner": a.get("owner"),
                "meeting": a.get("meeting_title", ""),
            }
            for a in brief_data["pending_meeting_actions"]
        ],
        "today_events": [
            {"title": e.get("title"), "start": e.get("start"), "location": e.get("location")}
            for e in brief_data.get("today_events", [])
        ],
    }

    if brief_data.get("learning_nudge"):
        data_summary["learning_nudge"] = brief_data["learning_nudge"]

    if brief_data.get("life_nudge"):
        data_summary["life_nudge"] = brief_data["life_nudge"]

    result = await invoke_claude(
        system_prompt=_brief_system(),
        messages=[{"role": "user", "content": json.dumps(data_summary, indent=2)}],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )

    logger.info("Generated morning brief")
    return result.strip()
