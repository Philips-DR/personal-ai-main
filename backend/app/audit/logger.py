import asyncio
import json
import logging
import time

from sqlalchemy import text

from app.db.client import get_session
from app.models.audit import AuditEntry

logger = logging.getLogger(__name__)


async def log_action(
    action: str,
    module: str,
    intent: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    metadata: dict | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
) -> AuditEntry:
    """Log an action to the immutable audit log (append-only)."""
    if input_summary and len(input_summary) > 500:
        input_summary = input_summary[:497] + "..."
    if output_summary and len(output_summary) > 500:
        output_summary = output_summary[:497] + "..."

    async with get_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO audit_log
                    (action, module, intent, input_summary, output_summary,
                     metadata, error, duration_ms)
                VALUES
                    (:action, :module, :intent, :input_summary, :output_summary,
                     CAST(:metadata AS jsonb), :error, :duration_ms)
                RETURNING *
            """),
            {
                "action": action,
                "module": module,
                "intent": intent,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "metadata": json.dumps(metadata or {}),
                "error": error,
                "duration_ms": duration_ms,
            },
        )
        data = dict(result.mappings().first())

    logger.info("Audit: [%s] %s (module=%s)", action, intent or "N/A", module)
    return AuditEntry(**data)


class AuditTimer:
    """Context manager that measures duration and fires log_action() on exit."""

    def __init__(self, action: str, module: str, **kwargs):
        self.action = action
        self.module = module
        self.kwargs = kwargs
        self.start: float = 0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.monotonic() - self.start) * 1000)
        error = str(exc_val) if exc_val else None
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                log_action(
                    action=self.action,
                    module=self.module,
                    duration_ms=duration_ms,
                    error=error,
                    **self.kwargs,
                )
            )
        except RuntimeError:
            asyncio.run(
                log_action(
                    action=self.action,
                    module=self.module,
                    duration_ms=duration_ms,
                    error=error,
                    **self.kwargs,
                )
            )
        return False
