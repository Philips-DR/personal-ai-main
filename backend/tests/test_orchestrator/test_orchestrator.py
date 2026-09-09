"""Integration tests for the Orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.orchestrator import (
    ChatRequest,
    ContextBundle,
    Intent,
    IntentClassification,
    ModuleResponse,
)
from app.orchestrator.module_router import ModuleRouter
from app.orchestrator.orchestrator import Orchestrator


def _make_orchestrator(handler_response: ModuleResponse | None = None) -> Orchestrator:
    """Build an Orchestrator with a single stub handler."""
    mock_handler = MagicMock()
    mock_handler.name = "stub"
    mock_handler.supported_intents = [Intent.GENERAL_CHAT]
    mock_handler.handle = AsyncMock(
        return_value=handler_response or ModuleResponse(content="Hello from stub.")
    )

    router = ModuleRouter()
    router.register(mock_handler)
    return Orchestrator(router)


@pytest.fixture
def mock_context():
    return ContextBundle()


class TestOrchestratorProcess:
    async def test_routes_message_to_handler(self):
        orchestrator = _make_orchestrator(ModuleResponse(content="All good."))
        classification = IntentClassification(intent=Intent.GENERAL_CHAT, confidence=0.95)

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(return_value=ContextBundle())),
            patch("app.orchestrator.orchestrator.classify_intent", new=AsyncMock(return_value=classification)),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()),
        ):
            response = await orchestrator.process(ChatRequest(message="hello"))

        assert response.content == "All good."

    async def test_returns_error_response_on_exception(self):
        orchestrator = _make_orchestrator()

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(side_effect=Exception("DB down"))),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()),
        ):
            response = await orchestrator.process(ChatRequest(message="hello"))

        assert "error" in response.content.lower()
        assert response.pending_actions == []

    async def test_logs_audit_on_success(self):
        orchestrator = _make_orchestrator(ModuleResponse(content="Done."))
        classification = IntentClassification(intent=Intent.GENERAL_CHAT, confidence=0.9)

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(return_value=ContextBundle())),
            patch("app.orchestrator.orchestrator.classify_intent", new=AsyncMock(return_value=classification)),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()) as mock_log,
        ):
            await orchestrator.process(ChatRequest(message="test"))

        mock_log.assert_awaited_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["action"] == "orchestrator.process"
        assert call_kwargs["intent"] == Intent.GENERAL_CHAT.value

    async def test_logs_audit_on_error(self):
        orchestrator = _make_orchestrator()

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(side_effect=RuntimeError("fail"))),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()) as mock_log,
        ):
            await orchestrator.process(ChatRequest(message="test"))

        mock_log.assert_awaited_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["action"] == "orchestrator.error"

    async def test_passes_pending_actions_through(self):
        from app.models.orchestrator import PendingAction

        pending = PendingAction(
            action_type="email.send",
            description="Send email to Alice",
            payload={"to": ["alice@co.com"], "subject": "Hi", "body": "Hello"},
        )
        orchestrator = _make_orchestrator(
            ModuleResponse(content="Draft ready.", pending_actions=[pending])
        )
        classification = IntentClassification(intent=Intent.GENERAL_CHAT, confidence=0.9)

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(return_value=ContextBundle())),
            patch("app.orchestrator.orchestrator.classify_intent", new=AsyncMock(return_value=classification)),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()),
        ):
            response = await orchestrator.process(ChatRequest(message="draft email"))

        assert len(response.pending_actions) == 1
        assert response.pending_actions[0].action_type == "email.send"

    async def test_chains_follow_up_intents(self):
        follow_up_handler = MagicMock()
        follow_up_handler.name = "tasks"
        follow_up_handler.supported_intents = [Intent.TASK_CREATE]
        follow_up_handler.handle = AsyncMock(return_value=ModuleResponse(content="Task created."))

        primary_handler = MagicMock()
        primary_handler.name = "meeting"
        primary_handler.supported_intents = [Intent.MEETING_TRANSCRIBE]
        primary_handler.handle = AsyncMock(
            return_value=ModuleResponse(
                content="Meeting processed.",
                follow_up_intents=[Intent.TASK_CREATE],
            )
        )

        router = ModuleRouter()
        router.register(primary_handler)
        router.register(follow_up_handler)
        orchestrator = Orchestrator(router)

        classification = IntentClassification(intent=Intent.MEETING_TRANSCRIBE, confidence=0.9)

        with (
            patch("app.orchestrator.orchestrator.build_context", new=AsyncMock(return_value=ContextBundle())),
            patch("app.orchestrator.orchestrator.classify_intent", new=AsyncMock(return_value=classification)),
            patch("app.orchestrator.orchestrator.save_entry", new=AsyncMock()),
            patch("app.orchestrator.orchestrator.log_action", new=AsyncMock()),
        ):
            response = await orchestrator.process(ChatRequest(message="process meeting notes"))

        assert "Meeting processed" in response.content
        assert "Task created" in response.content
        follow_up_handler.handle.assert_awaited_once()


class TestModuleRouter:
    def test_registers_and_routes_handler(self):
        handler = MagicMock()
        handler.supported_intents = [Intent.TASK_CREATE]
        router = ModuleRouter()
        router.register(handler)

        result = router.route(Intent.TASK_CREATE)
        assert result is handler

    def test_raises_on_unknown_intent(self):
        router = ModuleRouter()
        with pytest.raises(KeyError):
            router.route(Intent.TASK_CREATE)
