import logging

from app.config import settings
from app.memory.store import search_similar
from app.models.memory import MemoryCategory
from app.models.orchestrator import ContextBundle

logger = logging.getLogger(__name__)


async def retrieve_context(
    user_message: str,
    limit: int | None = None,
) -> ContextBundle:
    """Retrieve relevant context from the memory store for a user message.

    Uses RAG (semantic similarity) to find the most relevant memory entries.
    Enforces the configured token budget by limiting results.
    """
    limit = limit or settings.max_memory_entries_per_query

    # Primary search: find semantically similar entries
    memory_entries = await search_similar(user_message, limit=limit)

    # Separate into typed lists for convenience
    relevant_tasks = [
        e.model_dump()
        for e in memory_entries
        if e.category in (MemoryCategory.FACT, MemoryCategory.CONVERSATION)
        and "task" in e.content.lower()
    ]

    relevant_emails = [
        e.model_dump()
        for e in memory_entries
        if e.category == MemoryCategory.CONVERSATION
        and "email" in e.content.lower()
    ]

    logger.info(
        "Retrieved context: %d memory entries, %d task-related, %d email-related",
        len(memory_entries),
        len(relevant_tasks),
        len(relevant_emails),
    )

    return ContextBundle(
        memory_entries=[e.model_dump() for e in memory_entries],
        relevant_tasks=relevant_emails,
        relevant_emails=relevant_emails,
    )
