"""Unit tests for the Email module handler."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.email import EmailDraft
from app.models.orchestrator import Intent
from app.modules.email.handler import EmailModule
from tests.conftest import make_request


@pytest.fixture
def handler():
    return EmailModule()


def _sample_draft(**kwargs) -> EmailDraft:
    defaults = dict(to=["elton@ayadata.ai"], subject="Test Subject", body="Hello there.")
    defaults.update(kwargs)
    return EmailDraft(**defaults)


def _mock_session(rows: list[dict] | None = None, first_row: dict | None = None):
    """Return a get_session context manager that yields a mock session."""
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = rows or []
    mock_result.mappings.return_value.first.return_value = first_row

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


class TestEmailRead:
    async def test_returns_new_threads_from_poll(self, handler):
        threads = [{"subject": "Hello", "from_name": "Alice"}]
        with patch("app.modules.email.handler.poll_inbox", new=AsyncMock(return_value=threads)):
            req = make_request(Intent.EMAIL_READ, "check my email")
            response = await handler.handle(req)

        assert "Hello" in response.content
        assert "1 new email" in response.content

    async def test_falls_back_to_db_when_no_new_threads(self, handler):
        db_threads = [{"subject": "Old Thread", "from_name": "Bob", "last_synced_at": "2026-01-01", "category": None, "urgency_score": 0}]  # noqa: E501
        with (
            patch("app.modules.email.handler.poll_inbox", new=AsyncMock(return_value=[])),
            patch("app.modules.email.handler.get_session", _mock_session(rows=db_threads)),
        ):
            req = make_request(Intent.EMAIL_READ, "check my email")
            response = await handler.handle(req)

        assert "Old Thread" in response.content

    async def test_empty_inbox(self, handler):
        with (
            patch("app.modules.email.handler.poll_inbox", new=AsyncMock(return_value=[])),
            patch("app.modules.email.handler.get_session", _mock_session(rows=[])),
        ):
            req = make_request(Intent.EMAIL_READ, "check my email")
            response = await handler.handle(req)

        assert "empty" in response.content.lower() or "not connected" in response.content.lower()


class TestEmailTriage:
    async def test_triages_unclassified_threads(self, handler):
        unclassified = [
            {"id": "1", "subject": "Invoice", "snippet": "Please pay", "from_address": "vendor@co.com"}
        ]
        classification = {"category": "action_needed", "urgency_score": 4, "needs_reply": True}
        with (
            patch("app.modules.email.handler.get_session", _mock_session(rows=unclassified)),
            patch("app.modules.email.handler.classify_thread", new=AsyncMock(return_value=classification)),
        ):
            req = make_request(Intent.EMAIL_TRIAGE, "triage my inbox")
            response = await handler.handle(req)

        assert "Invoice" in response.content
        assert "action_needed" in response.content

    async def test_nothing_to_triage(self, handler):
        with patch("app.modules.email.handler.get_session", _mock_session(rows=[])):
            req = make_request(Intent.EMAIL_TRIAGE, "triage my inbox")
            response = await handler.handle(req)

        assert "triaged" in response.content.lower()


class TestEmailDraft:
    async def test_generates_reply_draft_for_thread(self, handler):
        thread = {"gmail_thread_id": "abc123", "subject": "Re: Project", "snippet": "...", "from_address": "alice@co.com"}  # noqa: E501
        draft = _sample_draft(subject="Re: Project")
        with (
            patch("app.modules.email.handler.get_session", _mock_session(first_row=thread)),
            patch("app.modules.email.handler.generate_reply", new=AsyncMock(return_value=draft)),
        ):
            req = make_request(Intent.EMAIL_DRAFT, "reply to Alice", params={"thread_id": "abc123"})
            response = await handler.handle(req)

        assert "Draft ready" in response.content
        assert len(response.pending_actions) == 1
        assert response.pending_actions[0].action_type == "email.send"

    async def test_generates_new_email(self, handler):
        draft = _sample_draft()
        with patch("app.modules.email.handler.generate_new", new=AsyncMock(return_value=draft)):
            req = make_request(Intent.EMAIL_DRAFT, "email Elton about the deployment")
            response = await handler.handle(req)

        assert "Draft ready" in response.content
        assert len(response.pending_actions) == 1

    async def test_thread_not_found(self, handler):
        with patch("app.modules.email.handler.get_session", _mock_session(first_row=None)):
            req = make_request(Intent.EMAIL_DRAFT, "reply to thread", params={"thread_id": "nonexistent"})
            response = await handler.handle(req)

        assert "couldn't find" in response.content.lower()

    async def test_pending_action_contains_draft_payload(self, handler):
        draft = _sample_draft(to=["henry@ayadata.ai"], subject="Hello Henry")
        with patch("app.modules.email.handler.generate_new", new=AsyncMock(return_value=draft)):
            req = make_request(Intent.EMAIL_DRAFT, "email Henry")
            response = await handler.handle(req)

        payload = response.pending_actions[0].payload
        assert payload["to"] == ["henry@ayadata.ai"]
        assert payload["subject"] == "Hello Henry"


class TestEmailSend:
    async def test_requires_draft_data(self, handler):
        req = make_request(Intent.EMAIL_SEND, "send it", params={})
        response = await handler.handle(req)

        assert "no draft" in response.content.lower() or "generate a draft" in response.content.lower()

    async def test_sends_approved_draft(self, handler):
        draft = _sample_draft()
        mock_creds = MagicMock()
        with (
            patch("app.modules.email.handler.get_credentials", new=AsyncMock(return_value=mock_creds)),
            patch("app.modules.email.gmail_client.send_message", new=AsyncMock(return_value={"id": "msg_001"})),
        ):
            req = make_request(
                Intent.EMAIL_SEND, "send", params={"draft": draft.model_dump()}
            )
            response = await handler.handle(req)

        assert "sent" in response.content.lower()
