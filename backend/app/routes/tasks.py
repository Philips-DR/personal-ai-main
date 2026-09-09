from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.task import TaskCreate, TaskUpdate

router = APIRouter()


@router.get("/")
async def list_tasks(status: str | None = None, owner: str | None = None) -> JSONResponse:
    # TODO (Phase 1B): Return filtered task list
    raise NotImplementedError


@router.post("/")
async def create_task(task: TaskCreate) -> JSONResponse:
    # TODO (Phase 1B): Create a new task
    raise NotImplementedError


@router.patch("/{task_id}")
async def update_task(task_id: str, update: TaskUpdate) -> JSONResponse:
    # TODO (Phase 1B): Update an existing task
    raise NotImplementedError


@router.post("/{task_id}/complete")
async def complete_task(task_id: str) -> JSONResponse:
    # TODO (Phase 1B): Mark a task as done
    raise NotImplementedError
