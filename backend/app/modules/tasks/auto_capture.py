"""Auto-capture tasks from meeting action items and email triage."""

import logging

from app.models.task import TaskCreate, TaskPriority

logger = logging.getLogger(__name__)


async def extract_from_meeting_actions(action_items: list[dict]) -> list[TaskCreate]:
    """Convert meeting action items into TaskCreate objects."""
    tasks = []
    for item in action_items:
        task = TaskCreate(
            title=item["description"],
            owner=item.get("owner", "Phil"),
            due_date=item.get("due_date"),
            priority=TaskPriority(item.get("priority", "medium")),
            source_type="meeting",
            source_id=item.get("meeting_id"),
            source_quote=item.get("source_quote"),
        )
        tasks.append(task)
    logger.info("Extracted %d tasks from meeting action items", len(tasks))
    return tasks


async def extract_from_email(email_data: dict) -> list[TaskCreate]:
    """Extract tasks from an action-needed email."""
    tasks = []
    summary = email_data.get("summary", "")
    subject = email_data.get("subject", "")

    if email_data.get("category") == "action_needed" and summary:
        task = TaskCreate(
            title=f"Follow up: {subject}",
            description=summary,
            source_type="email",
            source_id=email_data.get("gmail_thread_id"),
            source_quote=summary,
        )
        tasks.append(task)
    logger.info("Extracted %d tasks from email", len(tasks))
    return tasks
