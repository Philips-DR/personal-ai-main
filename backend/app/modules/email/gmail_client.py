"""Gmail API wrapper — read threads, create drafts, send.

The send method enforces the review gate: it requires confirmed=True.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models.email import EmailDraft

logger = logging.getLogger(__name__)

GMAIL_API_VERSION = "v1"


def _get_service(creds: Credentials):
    return build("gmail", GMAIL_API_VERSION, credentials=creds)


async def list_threads(creds: Credentials, max_results: int = 20, query: str = "in:inbox") -> list[dict]:
    """List Gmail threads matching a query."""
    service = _get_service(creds)
    result = service.users().threads().list(userId="me", maxResults=max_results, q=query).execute()
    threads = result.get("threads", [])
    logger.info("Listed %d Gmail threads", len(threads))
    return threads


async def get_thread(creds: Credentials, thread_id: str) -> dict:
    """Get full details of a Gmail thread."""
    service = _get_service(creds)
    result = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    return result


async def get_message(creds: Credentials, msg_id: str) -> dict:
    """Get a single Gmail message."""
    service = _get_service(creds)
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


async def create_draft(creds: Credentials, draft: EmailDraft) -> str:
    """Create a Gmail draft. Returns the draft ID."""
    service = _get_service(creds)
    message = _build_message(draft)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw, "threadId": draft.in_reply_to_thread_id}},
    ).execute()
    draft_id = result["id"]
    logger.info("Created Gmail draft %s", draft_id)
    return draft_id


async def send_draft(creds: Credentials, draft_id: str, *, confirmed: bool = False) -> dict:
    """Send a Gmail draft.

    REVIEW GATE: confirmed must be True. This is enforced at the code level.
    """
    if not confirmed:
        raise PermissionError("Email send requires explicit user approval (confirmed=True)")

    service = _get_service(creds)
    result = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    logger.info("Sent Gmail draft %s (messageId: %s)", draft_id, result.get("id"))
    return result


async def send_message(creds: Credentials, draft: EmailDraft, *, confirmed: bool = False) -> dict:
    """Send an email directly (no draft step).

    REVIEW GATE: confirmed must be True.
    """
    if not confirmed:
        raise PermissionError("Email send requires explicit user approval (confirmed=True)")

    service = _get_service(creds)
    message = _build_message(draft)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}
    if draft.in_reply_to_thread_id:
        body["threadId"] = draft.in_reply_to_thread_id

    result = service.users().messages().send(userId="me", body=body).execute()
    logger.info("Sent email (messageId: %s)", result.get("id"))
    return result


async def mark_read(creds: Credentials, msg_id: str) -> None:
    """Mark a message as read."""
    service = _get_service(creds)
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def _build_message(draft: EmailDraft) -> MIMEMultipart:
    """Build a MIME message from an EmailDraft."""
    msg = MIMEMultipart()
    msg["to"] = ", ".join(draft.to)
    msg["subject"] = draft.subject
    msg.attach(MIMEText(draft.body, "html"))
    return msg


def extract_headers(msg_data: dict) -> dict:
    """Extract common headers from a Gmail message payload."""
    headers = msg_data.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}
    return {
        "from": header_map.get("from", ""),
        "to": header_map.get("to", ""),
        "subject": header_map.get("subject", ""),
        "date": header_map.get("date", ""),
    }


def extract_body(msg_data: dict) -> str:
    """Extract plain text body from a Gmail message."""
    payload = msg_data.get("payload", {})

    # Try plain text part first
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Fallback to full body
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""
