from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/threads")
async def list_threads() -> JSONResponse:
    # TODO (Phase 1C): Return triaged email threads
    raise NotImplementedError


@router.post("/triage")
async def triage_inbox() -> JSONResponse:
    # TODO (Phase 1C): Trigger inbox triage
    raise NotImplementedError


@router.post("/draft/{thread_id}/approve")
async def approve_draft(thread_id: str) -> JSONResponse:
    # TODO (Phase 1C): Approve and send a pending draft
    raise NotImplementedError


@router.post("/draft/{thread_id}/reject")
async def reject_draft(thread_id: str) -> JSONResponse:
    # TODO (Phase 1C): Reject a pending draft
    raise NotImplementedError
