"""Morning brief aggregator — pulls data from all modules."""

import logging
from datetime import datetime

from sqlalchemy import text

from app.config import settings
from app.db.client import get_session
from app.memory.store import get_by_category
from app.models.memory import MemoryCategory
from app.modules.tasks.reminders import get_reminders

logger = logging.getLogger(__name__)


async def aggregate_brief_data(prefs: dict | None = None) -> dict:
    """Pull all data sources for the morning brief."""

    # 1. Tasks: overdue + due today + open count
    reminders = await get_reminders()

    # 2. Emails: unread threads needing a reply, sorted by urgency
    async with get_session() as session:
        result = await session.execute(
            text(  # noqa: S608
                "SELECT * FROM email_threads WHERE needs_reply = true"
                " ORDER BY urgency_score DESC NULLS LAST"
                f" LIMIT {settings.brief_priority_emails_limit}"
            )
        )
        priority_emails = [dict(r) for r in result.mappings().all()]

    # 3. Recent meetings with unresolved action items (task_id IS NULL)
    async with get_session() as session:
        result = await session.execute(
            text(  # noqa: S608
                "SELECT mai.id, mai.meeting_id, mai.description, mai.owner,"
                " mai.due_date, mai.priority, mai.source_quote, mai.created_at,"
                " m.title AS meeting_title, m.date AS meeting_date"
                " FROM meeting_action_items mai"
                " JOIN meetings m ON m.id = mai.meeting_id"
                " WHERE mai.task_id IS NULL"
                f" ORDER BY mai.created_at DESC LIMIT {settings.brief_action_items_limit}"
            )
        )
        pending_actions = [dict(r) for r in result.mappings().all()]

    # 4. Today's calendar events (non-fatal if Gmail not connected)
    today_events: list[dict] = []
    try:
        from app.modules.calendar.client import get_today_events
        from app.modules.email.oauth import get_credentials

        creds = await get_credentials()
        today_events = await get_today_events(creds)
    except Exception as e:
        logger.warning("Could not fetch calendar events: %s", e)

    # 5. Learning nudge — from stored roadmaps and habits (if enabled)
    learning_nudge: dict | None = None
    if not prefs or prefs.get("brief_include_learning", True):
        try:
            roadmaps = await get_by_category(MemoryCategory.LEARNING_ROADMAP)
            habits = await get_by_category(MemoryCategory.HABIT)
            if roadmaps or habits:
                learning_nudge = {
                    "roadmaps": [
                        {"subject": r.subject, "content": r.content[:300]}
                        for r in roadmaps[:settings.brief_roadmaps_limit]
                    ],
                    "habits": [
                        {"subject": h.subject, "content": h.content}
                        for h in habits[:settings.brief_habits_limit]
                    ],
                }
        except Exception as e:
            logger.warning("Could not fetch learning data: %s", e)

    # 6. Life nudge — interests and life goals (if enabled)
    life_nudge: dict | None = None
    if not prefs or prefs.get("brief_include_life", True):
        try:
            interests = await get_by_category(MemoryCategory.INTEREST)
            skill_goals = await get_by_category(MemoryCategory.SKILL_GOAL)
            if interests or skill_goals:
                life_nudge = {
                    "interests": [
                        {"subject": i.subject, "content": i.content[:200]}
                        for i in interests[:settings.brief_interests_limit]
                    ],
                    "skill_goals": [
                        {"subject": g.subject, "content": g.content}
                        for g in skill_goals[:settings.brief_skill_goals_limit]
                    ],
                }
        except Exception as e:
            logger.warning("Could not fetch life data: %s", e)

    return {
        "date": datetime.utcnow().strftime("%A, %B %d, %Y"),
        "overdue_tasks": reminders["overdue"],
        "due_today_tasks": reminders["due_today"],
        "total_open_tasks": reminders["total_open"],
        "priority_emails": priority_emails,
        "pending_meeting_actions": pending_actions,
        "today_events": today_events,
        "learning_nudge": learning_nudge,
        "life_nudge": life_nudge,
        "prefs": prefs or {},
    }
