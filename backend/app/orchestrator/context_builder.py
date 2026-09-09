import logging

from app.memory.retriever import retrieve_context
from app.models.orchestrator import ContextBundle, Message

logger = logging.getLogger(__name__)


async def build_context(
    user_message: str,
    conversation_history: list[Message] | None = None,
) -> ContextBundle:
    """Assemble context from the memory store for a user message.

    Uses RAG retrieval to pull the most relevant memory entries.
    Returns an empty bundle if the memory store is unavailable.
    """
    try:
        context = await retrieve_context(user_message)
        logger.info("Built context with %d memory entries", len(context.memory_entries))
        return context
    except Exception as e:
        logger.warning("Memory retrieval unavailable, proceeding without context: %s", e)
        return ContextBundle()
