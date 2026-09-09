from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
async def get_brief() -> JSONResponse:
    # TODO (Phase 1E): Generate and return today's morning brief
    raise NotImplementedError


@router.post("/configure")
async def configure_brief(cron_expression: str, timezone: str) -> JSONResponse:
    # TODO (Phase 1E): Update brief schedule
    raise NotImplementedError
