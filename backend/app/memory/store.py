import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from app.db.client import get_session
from app.memory.embeddings import generate_embedding
from app.models.memory import MemoryCategory, MemoryEntry

logger = logging.getLogger(__name__)


def _vec(embedding: list[float]) -> str:
    """Format a float list as a pgvector literal string."""
    return f"[{','.join(str(x) for x in embedding)}]"


async def save_entry(
    category: MemoryCategory,
    subject: str,
    content: str,
    source_module: str | None = None,
    source_id: str | None = None,
    metadata: dict | None = None,
    expires_at: datetime | None = None,
) -> MemoryEntry:
    """Store a memory entry with its embedding in pgvector."""
    embedding = await generate_embedding(content)

    async with get_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO memory_entries
                    (category, subject, content, embedding, source_module, source_id, metadata, expires_at)
                VALUES
                    (:category, :subject, :content, CAST(:embedding AS vector(1536)),
                     :source_module, :source_id, CAST(:metadata AS jsonb), :expires_at)
                RETURNING id, category, subject, content, source_module, source_id,
                          metadata, created_at, updated_at, expires_at
            """),
            {
                "category": category.value,
                "subject": subject,
                "content": content,
                "embedding": _vec(embedding),
                "source_module": source_module,
                "source_id": source_id,
                "metadata": json.dumps(metadata or {}),
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        data = dict(result.mappings().first())

    logger.info("Saved memory entry: [%s] %s", category.value, subject)
    return MemoryEntry(**data)


async def search_similar(
    query: str,
    limit: int = 10,
    category: MemoryCategory | None = None,
) -> list[MemoryEntry]:
    """Search memory using pgvector cosine similarity via the match_memory_entries function."""
    query_embedding = await generate_embedding(query)

    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT * FROM match_memory_entries(
                    CAST(:query_embedding AS vector(1536)),
                    :match_limit,
                    :match_category
                )
            """),
            {
                "query_embedding": _vec(query_embedding),
                "match_limit": limit,
                "match_category": category.value if category else None,
            },
        )
        rows = result.mappings().all()

    entries = [MemoryEntry(**dict(r)) for r in rows]
    logger.info("Found %d similar memory entries for query", len(entries))
    return entries


async def get_by_category(category: MemoryCategory) -> list[MemoryEntry]:
    """Get all memory entries of a given category."""
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, category, subject, content, source_module, source_id,"
                " metadata, created_at, updated_at, expires_at"
                " FROM memory_entries WHERE category = :category"
            ),
            {"category": category.value},
        )
        rows = result.mappings().all()
    return [MemoryEntry(**dict(r)) for r in rows]


async def delete_entry(entry_id: UUID) -> None:
    """Delete a memory entry by ID."""
    async with get_session() as session:
        await session.execute(
            text("DELETE FROM memory_entries WHERE id = :id"),
            {"id": str(entry_id)},
        )
    logger.info("Deleted memory entry %s", entry_id)
