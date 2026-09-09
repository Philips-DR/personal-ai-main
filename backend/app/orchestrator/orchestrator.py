import logging
import time

from app.audit.logger import log_action
from app.claude import get_request_tokens, reset_request_tokens
from app.memory.store import save_entry
from app.models.memory import MemoryCategory
from app.models.orchestrator import (
    ChatRequest,
    ChatResponse,
    ModuleRequest,
)
from app.orchestrator.context_builder import build_context
from app.orchestrator.intent_classifier import classify_intent
from app.orchestrator.module_router import ModuleRouter

logger = logging.getLogger(__name__)

MAX_FOLLOW_UP_DEPTH = 3


class Orchestrator:
    """Central brain: classify intent, route to module, chain follow-ups, log audit."""

    def __init__(self, router: ModuleRouter) -> None:
        self.router = router

    async def process(self, request: ChatRequest) -> ChatResponse:
        """Full orchestration flow for a user message."""
        reset_request_tokens()
        start = time.monotonic()
        intent_result = None
        module_response = None
        error = None

        try:
            # 1. Build context from memory
            context = await build_context(request.message, request.conversation_history)

            # 2. Classify intent
            intent_result = await classify_intent(
                request.message,
                [m.model_dump() for m in request.conversation_history],
            )
            logger.info("Intent: %s (%.2f)", intent_result.intent, intent_result.confidence)

            # 3. Route to module
            handler = self.router.route(intent_result.intent)

            # 4. Build module request
            module_request = ModuleRequest(
                intent=intent_result.intent,
                user_message=request.message,
                parameters=intent_result.parameters,
                context=context,
                conversation_history=request.conversation_history,
            )

            # 5. Execute module
            module_response = await handler.handle(module_request)

            # 6. Process follow-up intents (chained modules)
            follow_ups = module_response.follow_up_intents[:MAX_FOLLOW_UP_DEPTH]
            for follow_up_intent in follow_ups:
                try:
                    follow_up_handler = self.router.route(follow_up_intent)
                    follow_up_request = ModuleRequest(
                        intent=follow_up_intent,
                        user_message=request.message,
                        parameters=module_response.structured or {},
                        context=context,
                        conversation_history=request.conversation_history,
                    )
                    follow_up_response = await follow_up_handler.handle(follow_up_request)
                    # Merge follow-up content
                    module_response.content += f"\n\n{follow_up_response.content}"
                    if follow_up_response.structured:
                        module_response.structured = {
                            **(module_response.structured or {}),
                            **follow_up_response.structured,
                        }
                except Exception as e:
                    logger.error("Follow-up intent '%s' failed: %s", follow_up_intent, e)

            # 7. Store memory updates
            for mem_update in module_response.memory_updates:
                try:
                    await save_entry(
                        category=MemoryCategory(mem_update.get("category", "fact")),
                        subject=mem_update.get("subject", ""),
                        content=mem_update.get("content", ""),
                        source_module=handler.name,
                    )
                except Exception as e:
                    logger.error("Failed to save memory update: %s", e)

            # 8. Log to audit (non-fatal — never crash the response)
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                tokens = get_request_tokens()
                await log_action(
                    action="orchestrator.process",
                    module=handler.name,
                    intent=intent_result.intent.value,
                    input_summary=request.message,
                    output_summary=module_response.content[:200],
                    duration_ms=duration_ms,
                    metadata={
                        "confidence": intent_result.confidence,
                        "tokens": tokens,
                    },
                )
            except Exception as audit_err:
                logger.warning("Audit log unavailable: %s", audit_err)

            return ChatResponse(
                content=module_response.content,
                structured=module_response.structured,
                pending_actions=module_response.pending_actions,
            )

        except Exception as e:
            error = str(e)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("Orchestrator error: %s", error)

            try:
                await log_action(
                    action="orchestrator.error",
                    module="orchestrator",
                    intent=intent_result.intent.value if intent_result else None,
                    input_summary=request.message,
                    error=error,
                    duration_ms=duration_ms,
                )
            except Exception as audit_err:
                logger.warning("Audit log unavailable: %s", audit_err)

            return ChatResponse(
                content=f"I encountered an error processing your request: {error}",
                structured=None,
                pending_actions=[],
            )
