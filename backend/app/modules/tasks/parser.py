import json
import logging
from datetime import datetime

from app.claude import invoke_claude_json
from app.config import settings
from app.models.task import TaskCreate, TaskPriority

logger = logging.getLogger(__name__)

_MAX_TOKENS = 512
_TEMPERATURE = 0.1


def _parse_prompt() -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return (
        f"You are a task extraction assistant. Given a natural language message from {settings.user_name},"
        " extract task details.\n\n"
        "Return a JSON object with these fields:\n"
        "- title: short task title (required)\n"
        "- description: optional longer description\n"
        f'- owner: who owns the task (default: "{settings.user_name}")\n'
        "- assignee: who is assigned (if different from owner)\n"
        f'- due_date: ISO date string if a deadline is mentioned (e.g. "Friday" → next Friday\'s date).'
        f" Use today as reference: {today}\n"
        '- priority: "urgent", "high", "medium", or "low" (default: "medium")\n'
        "- project_name: project name if mentioned\n"
        "- estimated_minutes: estimated effort in minutes if implied\n\n"
        'If the message doesn\'t describe a task, return {"title": null}.\n'
        "Respond with ONLY the JSON object, no other text."
    )


async def parse_task_from_nl(user_message: str) -> TaskCreate | None:
    """Parse a natural language message into a TaskCreate using Claude."""
    try:
        parsed = await invoke_claude_json(
            system_prompt=_parse_prompt(),
            messages=[{"role": "user", "content": user_message}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
    except json.JSONDecodeError:
        logger.error("Failed to parse task JSON from Claude")
        return None

    if not parsed.get("title"):
        return None

    return TaskCreate(
        title=parsed["title"],
        description=parsed.get("description"),
        owner=parsed.get("owner", settings.user_name),
        assignee=parsed.get("assignee"),
        due_date=parsed.get("due_date"),
        priority=TaskPriority(parsed.get("priority", "medium")),
        project_name=parsed.get("project_name"),
        estimated_minutes=parsed.get("estimated_minutes"),
        source_type="manual",
    )
