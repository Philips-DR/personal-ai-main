from fastapi import APIRouter

from app.models.orchestrator import ChatRequest, ChatResponse
from app.modules.drive.handler import DriveModule
from app.modules.email.handler import EmailModule
from app.modules.general_chat.handler import GeneralChatHandler
from app.modules.github_docs.handler import GitHubDocsModule
from app.modules.learning_coach.handler import LearningCoachModule
from app.modules.meeting.handler import MeetingModule
from app.modules.morning_brief.handler import MorningBriefModule
from app.modules.tasks.handler import TaskModule
from app.orchestrator.module_router import ModuleRouter
from app.orchestrator.orchestrator import Orchestrator

router = APIRouter()

# Initialize module registry and orchestrator at module level (singleton)
_module_router = ModuleRouter()
_module_router.register(GeneralChatHandler())
_module_router.register(TaskModule())
_module_router.register(EmailModule())
_module_router.register(MeetingModule())
_module_router.register(MorningBriefModule())
_module_router.register(GitHubDocsModule())
_module_router.register(DriveModule())
_module_router.register(LearningCoachModule())
_orchestrator = Orchestrator(_module_router)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Main entry point — route user messages through the orchestrator."""
    return await _orchestrator.process(request)
