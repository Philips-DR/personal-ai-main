from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.modules.morning_brief.scheduler import start_scheduler
from app.routes import (
    actions,
    admin,
    auth,
    brief,
    chat,
    email,
    github_docs,
    meeting,
    preferences,
    tasks,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_scheduler()
    logger.info("Morning brief scheduler started")
    yield


app = FastAPI(
    title="Personal AI Assistant",
    description="Agentic AI assistant for AyaData",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(email.router, prefix="/api/email", tags=["email"])
app.include_router(meeting.router, prefix="/api/meeting", tags=["meeting"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(brief.router, prefix="/api/brief", tags=["brief"])
app.include_router(github_docs.router, prefix="/api/github-docs", tags=["github-docs"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "env": settings.app_env}
