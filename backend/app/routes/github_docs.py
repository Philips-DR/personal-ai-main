from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class DocRequest(BaseModel):
    repo_url: str
    private_token: str | None = None  # For private repos


@router.post("/generate")
async def generate_docs(request: DocRequest) -> JSONResponse:
    # TODO (Phase 1F): Analyse repo and generate all 6 doc types
    raise NotImplementedError
