"""Morning brief scheduler using APScheduler."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.models.email import EmailDraft

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=settings.brief_timezone)
    return _scheduler


async def _get_brief_schedule() -> tuple[str, str]:
    """Return (cron_expression, timezone) from user preferences, falling back to settings."""
    try:
        from app.preferences.store import get_preferences
        prefs = await get_preferences()
        return prefs.brief_cron, prefs.brief_timezone
    except Exception:
        return settings.brief_cron_expression, settings.brief_timezone


async def start_scheduler() -> None:
    """Start the morning brief cron scheduler."""
    cron_expr, timezone = await _get_brief_schedule()

    scheduler = get_scheduler()
    scheduler.timezone = timezone

    async def generate_brief():
        try:
            from app.modules.morning_brief.aggregator import aggregate_brief_data
            from app.modules.morning_brief.formatter import format_brief

            try:
                from app.preferences.store import get_preferences
                prefs_obj = await get_preferences()
                prefs = prefs_obj.model_dump()
            except Exception:
                prefs = {}

            data = await aggregate_brief_data(prefs=prefs)
            brief_text = await format_brief(data)
            logger.info("Morning brief generated:\n%s", brief_text[:200])
            await _deliver_brief(brief_text, data.get("date", ""))
        except Exception as e:
            logger.error("Morning brief generation failed: %s", e)

    scheduler.add_job(
        generate_brief,
        "cron",
        **_parse_cron(cron_expr),
        id="morning_brief",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("Morning brief scheduler started: '%s' (%s)", cron_expr, timezone)


def _parse_cron(expression: str) -> dict:
    """Parse a standard 5-field cron expression into APScheduler kwargs."""
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Invalid cron expression: '{expression}' (expected 5 fields)")
    return {
        "minute": fields[0],
        "hour": fields[1],
        "day": fields[2],
        "month": fields[3],
        "day_of_week": fields[4],
    }


async def _deliver_brief(brief_text: str, date_label: str) -> None:
    """Send the morning brief as a self-email if delivery is configured."""
    if not settings.brief_delivery_email:
        return
    try:
        from app.modules.email.gmail_client import send_message
        from app.modules.email.oauth import get_credentials

        creds = await get_credentials()
        draft = EmailDraft(
            to=[settings.brief_delivery_email],
            subject=f"Morning Brief — {date_label}",
            body=brief_text.replace("\n", "<br>"),
        )
        await send_message(creds, draft, confirmed=True)
        logger.info("Morning brief delivered to %s", settings.brief_delivery_email)
    except Exception as e:
        logger.error("Morning brief email delivery failed: %s", e)


def get_next_run_time() -> str | None:
    scheduler = get_scheduler()
    job = scheduler.get_job("morning_brief")
    if job and job.next_run_time:
        return str(job.next_run_time)
    return None
