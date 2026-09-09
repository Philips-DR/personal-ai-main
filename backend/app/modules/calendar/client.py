"""Google Calendar read-only client — fetches today's events using shared OAuth credentials."""

import logging
from datetime import UTC, datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

CALENDAR_API_VERSION = "v3"


def _get_service(creds: Credentials):
    return build("calendar", CALENDAR_API_VERSION, credentials=creds)


async def get_today_events(creds: Credentials) -> list[dict]:
    """Return today's calendar events, sorted by start time."""
    service = _get_service(creds)

    now = datetime.now(tz=UTC)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = result.get("items", [])
    logger.info("Fetched %d calendar events for today", len(events))

    parsed = []
    for e in events:
        start = e.get("start", {})
        parsed.append({
            "title": e.get("summary", "No title"),
            "start": start.get("dateTime") or start.get("date", ""),
            "location": e.get("location", ""),
            "attendees": [a.get("email", "") for a in e.get("attendees", [])],
            "description": (e.get("description") or "")[:200],
        })

    return parsed
