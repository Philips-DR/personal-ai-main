"""Inbox polling — incremental sync using Gmail thread IDs."""

import logging
from datetime import datetime

from sqlalchemy import text

from app.config import settings
from app.db.client import get_session
from app.models.email import TriageCategory  # noqa: F401 (imported by callers)
from app.modules.email.gmail_client import (
    extract_body,
    extract_headers,
    get_thread,
    list_threads,
)
from app.modules.email.oauth import get_credentials

logger = logging.getLogger(__name__)


async def poll_inbox() -> list[dict]:
    """Poll inbox for new threads and insert into email_threads.

    Returns list of newly synced thread summaries.
    """
    creds = await get_credentials()
    threads = await list_threads(creds, max_results=settings.email_poll_max_results)
    new_threads = []

    for thread_summary in threads:
        thread_id = thread_summary["id"]

        # Skip already-synced threads
        async with get_session() as session:
            result = await session.execute(
                text("SELECT id FROM email_threads WHERE gmail_thread_id = :tid LIMIT 1"),
                {"tid": thread_id},
            )
            if result.mappings().first():
                continue

        try:
            thread_data = await get_thread(creds, thread_id)
            messages = thread_data.get("messages", [])
            if not messages:
                continue

            latest = messages[-1]
            headers = extract_headers(latest)
            body = extract_body(latest)

            row = {
                "gmail_thread_id": thread_id,
                "gmail_message_id": latest.get("id"),
                "subject": headers.get("subject", ""),
                "from_address": headers.get("from", ""),
                "from_name": _extract_name(headers.get("from", "")),
                "snippet": body[:settings.email_snippet_max_length] if body else "",
                "is_read": "UNREAD" not in latest.get("labelIds", []),
                "last_synced_at": datetime.utcnow().isoformat(),
            }

            async with get_session() as session:
                result = await session.execute(
                    text("""
                        INSERT INTO email_threads
                            (gmail_thread_id, gmail_message_id, subject,
                             from_address, from_name, snippet, is_read, last_synced_at)
                        VALUES
                            (:gmail_thread_id, :gmail_message_id, :subject,
                             :from_address, :from_name, :snippet, :is_read, :last_synced_at)
                        RETURNING *
                    """),
                    row,
                )
                new_threads.append(dict(result.mappings().first()))

            logger.info("Synced new email thread: %s", row["subject"])

        except Exception as e:
            logger.error("Failed to sync thread %s: %s", thread_id, e)

    logger.info("Poll complete: %d new threads synced", len(new_threads))
    return new_threads


def _extract_name(from_header: str) -> str:
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"')
    return from_header
