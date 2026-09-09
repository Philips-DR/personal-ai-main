from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/process")
async def process_meeting(file: UploadFile | None = None, text: str | None = None) -> JSONResponse:
    # TODO (Phase 1D): Transcribe and process meeting audio or text
    raise NotImplementedError


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str) -> JSONResponse:
    # TODO (Phase 1D): Return meeting summary and action items
    raise NotImplementedError
