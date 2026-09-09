"""Async PostgreSQL engine and session factory (SQLAlchemy 2.0 + asyncpg)."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _json_serializer(obj):
    return json.dumps(obj)


def _get_database_url() -> str:
    url = settings.database_url
    # Normalise: ensure asyncpg dialect is specified
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _get_database_url(),
    pool_size=10,
    max_overflow=5,
    echo=False,
    json_serializer=_json_serializer,
)

_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session with automatic commit/rollback."""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
