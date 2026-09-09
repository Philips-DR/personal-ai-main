"""Task reminder logic — used by morning brief and on-demand."""

import logging
from datetime import datetime

from app.models.task import TaskStatus

logger = logging.getLogger(__name__)


async def get_reminders() -> dict:
    """Get categorized task reminders."""
    from app.modules.tasks.store import get_due_tasks, list_tasks

    now = datetime.utcnow()
    overdue = await get_due_tasks(before=now)
    all_open = await list_tasks(status=TaskStatus.TODO)

    # Tasks due today
    today_end = now.replace(hour=23, minute=59, second=59)
    due_today = [t for t in all_open if t.due_date and t.due_date <= today_end]

    return {
        "overdue": overdue,
        "due_today": due_today,
        "total_open": len(all_open),
    }
