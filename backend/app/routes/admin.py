"""Admin endpoints — audit log and prompt metrics."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.db.client import get_session

router = APIRouter()


class AuditRow(BaseModel):
    id: str
    action: str
    module: str
    intent: str | None
    input_summary: str | None
    output_summary: str | None
    metadata: dict
    error: str | None
    duration_ms: int | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditRow]
    total: int
    limit: int
    offset: int


class ModuleMetric(BaseModel):
    module: str
    total_calls: int
    error_calls: int
    avg_duration_ms: float
    total_input_tokens: int
    total_output_tokens: int


class IntentCount(BaseModel):
    intent: str
    count: int


class Metrics(BaseModel):
    by_module: list[ModuleMetric]
    by_intent: list[IntentCount]
    total_calls: int
    total_errors: int
    total_input_tokens: int
    total_output_tokens: int
    avg_duration_ms: float


@router.get("/audit", response_model=AuditPage)
async def get_audit_log(
    module: str | None = Query(None),
    intent: str | None = Query(None),
    has_error: bool | None = Query(None),
    from_date: datetime | None = Query(None),  # noqa: B008
    to_date: datetime | None = Query(None),  # noqa: B008
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> AuditPage:
    filters = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if module:
        filters.append("module = :module")
        params["module"] = module
    if intent:
        filters.append("intent = :intent")
        params["intent"] = intent
    if has_error is True:
        filters.append("error IS NOT NULL")
    elif has_error is False:
        filters.append("error IS NULL")
    if from_date:
        filters.append("created_at >= :from_date")
        params["from_date"] = from_date.isoformat()
    if to_date:
        filters.append("created_at <= :to_date")
        params["to_date"] = to_date.isoformat()

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    async with get_session() as session:
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM audit_log {where}"),  # noqa: S608
            params,
        )
        total = count_result.scalar() or 0

        rows_result = await session.execute(
            text(
                f"SELECT id, action, module, intent, input_summary, output_summary,"  # noqa: S608
                f" metadata, error, duration_ms, created_at"
                f" FROM audit_log {where}"
                f" ORDER BY created_at DESC"
                f" LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        rows = rows_result.mappings().all()

    items = [
        AuditRow(
            id=str(r["id"]),
            action=r["action"],
            module=r["module"],
            intent=r["intent"],
            input_summary=r["input_summary"],
            output_summary=r["output_summary"],
            metadata=r["metadata"] or {},
            error=r["error"],
            duration_ms=r["duration_ms"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return AuditPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/metrics", response_model=Metrics)
async def get_metrics() -> Metrics:
    async with get_session() as session:
        # Per-module aggregates — extract tokens from metadata jsonb
        mod_result = await session.execute(text("""
            SELECT
                module,
                COUNT(*) AS total_calls,
                COUNT(error) AS error_calls,
                ROUND(AVG(duration_ms)::numeric, 1) AS avg_duration_ms,
                COALESCE(SUM(
                    (metadata->'tokens'->>'input_tokens')::int
                ), 0) AS total_input_tokens,
                COALESCE(SUM(
                    (metadata->'tokens'->>'output_tokens')::int
                ), 0) AS total_output_tokens
            FROM audit_log
            GROUP BY module
            ORDER BY total_calls DESC
        """))
        module_rows = mod_result.mappings().all()

        # Per-intent distribution
        intent_result = await session.execute(text("""
            SELECT intent, COUNT(*) AS count
            FROM audit_log
            WHERE intent IS NOT NULL
            GROUP BY intent
            ORDER BY count DESC
        """))
        intent_rows = intent_result.mappings().all()

        # Totals
        total_result = await session.execute(text("""
            SELECT
                COUNT(*) AS total_calls,
                COUNT(error) AS total_errors,
                ROUND(AVG(duration_ms)::numeric, 1) AS avg_duration_ms,
                COALESCE(SUM(
                    (metadata->'tokens'->>'input_tokens')::int
                ), 0) AS total_input_tokens,
                COALESCE(SUM(
                    (metadata->'tokens'->>'output_tokens')::int
                ), 0) AS total_output_tokens
            FROM audit_log
        """))
        totals = dict(total_result.mappings().first() or {})

    return Metrics(
        by_module=[
            ModuleMetric(
                module=r["module"],
                total_calls=r["total_calls"],
                error_calls=r["error_calls"],
                avg_duration_ms=float(r["avg_duration_ms"] or 0),
                total_input_tokens=int(r["total_input_tokens"] or 0),
                total_output_tokens=int(r["total_output_tokens"] or 0),
            )
            for r in module_rows
        ],
        by_intent=[
            IntentCount(intent=r["intent"], count=r["count"])
            for r in intent_rows
        ],
        total_calls=int(totals.get("total_calls", 0)),
        total_errors=int(totals.get("total_errors", 0)),
        total_input_tokens=int(totals.get("total_input_tokens", 0)),
        total_output_tokens=int(totals.get("total_output_tokens", 0)),
        avg_duration_ms=float(totals.get("avg_duration_ms") or 0),
    )
