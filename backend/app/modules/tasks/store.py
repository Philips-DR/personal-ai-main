import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from app.db.client import get_session
from app.models.task import Project, Task, TaskCreate, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)


async def create_task(task_data: TaskCreate) -> Task:
    row = task_data.model_dump(exclude_none=True, exclude={"project_name", "id"})

    async with get_session() as session:
        # Resolve project_id from project_name
        if task_data.project_name:
            result = await session.execute(
                text("SELECT id FROM projects WHERE name = :name LIMIT 1"),
                {"name": task_data.project_name},
            )
            proj = result.mappings().first()
            if proj:
                row["project_id"] = str(proj["id"])

        # Serialise enum values to strings
        for field in ("status", "priority"):
            if field in row and hasattr(row[field], "value"):
                row[field] = row[field].value

        cols = ", ".join(row)
        params = ", ".join(f":{k}" for k in row)
        result = await session.execute(
            text(f"INSERT INTO tasks ({cols}) VALUES ({params}) RETURNING *"),  # noqa: S608
            row,
        )
        data = dict(result.mappings().first())

    logger.info("Created task: %s", task_data.title)
    return Task(**data)


async def get_task(task_id: UUID) -> Task | None:
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM tasks WHERE id = :id"),
            {"id": str(task_id)},
        )
        row = result.mappings().first()
    return Task(**dict(row)) if row else None


async def list_tasks(
    status: TaskStatus | None = None,
    owner: str | None = None,
    project_id: UUID | None = None,
) -> list[Task]:
    filters = []
    params: dict = {}
    if status:
        filters.append("status = :status")
        params["status"] = status.value
    if owner:
        filters.append("owner = :owner")
        params["owner"] = owner
    if project_id:
        filters.append("project_id = :project_id")
        params["project_id"] = str(project_id)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    async with get_session() as session:
        result = await session.execute(
            text(f"SELECT * FROM tasks {where} ORDER BY created_at DESC"),  # noqa: S608
            params,
        )
        rows = result.mappings().all()
    return [Task(**dict(r)) for r in rows]


async def update_task(task_id: UUID, update_data: TaskUpdate) -> Task | None:
    row = update_data.model_dump(exclude_none=True)
    if not row:
        return await get_task(task_id)

    row["updated_at"] = datetime.utcnow().isoformat()
    for field in ("status", "priority"):
        if field in row and hasattr(row[field], "value"):
            row[field] = row[field].value

    assignments = ", ".join(f"{k} = :{k}" for k in row)
    row["_id"] = str(task_id)
    async with get_session() as session:
        result = await session.execute(
            text(f"UPDATE tasks SET {assignments} WHERE id = :_id RETURNING *"),  # noqa: S608
            row,
        )
        data = result.mappings().first()

    logger.info("Updated task %s", task_id)
    return Task(**dict(data)) if data else None


async def complete_task(task_id: UUID) -> Task | None:
    now = datetime.utcnow().isoformat()
    async with get_session() as session:
        result = await session.execute(
            text("""
                UPDATE tasks
                SET status = 'done', completed_at = :now, updated_at = :now
                WHERE id = :id
                RETURNING *
            """),
            {"now": now, "id": str(task_id)},
        )
        data = result.mappings().first()

    logger.info("Completed task %s", task_id)
    return Task(**dict(data)) if data else None


async def get_due_tasks(before: datetime | None = None) -> list[Task]:
    params: dict = {"statuses": ["todo", "in_progress"]}
    extra = ""
    if before:
        extra = " AND due_date <= :before"
        params["before"] = before.isoformat()

    async with get_session() as session:
        result = await session.execute(
            text(f"""
                SELECT * FROM tasks
                WHERE status = ANY(:statuses)
                AND due_date IS NOT NULL
                {extra}
                ORDER BY due_date
            """),  # noqa: S608
            params,
        )
        rows = result.mappings().all()
    return [Task(**dict(r)) for r in rows]


async def get_projects() -> list[Project]:
    async with get_session() as session:
        result = await session.execute(text("SELECT * FROM projects ORDER BY name"))
        rows = result.mappings().all()
    return [Project(**dict(r)) for r in rows]


async def create_project(name: str, description: str | None = None) -> Project:
    async with get_session() as session:
        result = await session.execute(
            text("INSERT INTO projects (name, description) VALUES (:name, :description) RETURNING *"),
            {"name": name, "description": description},
        )
        data = dict(result.mappings().first())
    return Project(**data)
