import logging

from app.claude import invoke_claude
from app.config import settings
from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler

logger = logging.getLogger(__name__)

_MAX_TOKENS = 2048
_TEMPERATURE = 0.7


def _system_prompt() -> str:
    return (
        f"You are {settings.user_name}'s personal AI assistant,"
        f" built by the {settings.user_company} AI Solutions team.\n"
        "You help with email management, meeting processing, task tracking,"
        " morning briefings, and GitHub documentation.\n\n"
        "Be concise, helpful, and professional. If you're not sure about something, ask for clarification.\n"
        f"You have access to memory about {settings.user_name}'s contacts, projects,"
        " and preferences — use that context naturally.\n\n"
        f"When {settings.user_name} asks you to do something you can't do yet,"
        " explain what module would handle it and that it's coming in a future phase."
    )


class GeneralChatHandler(ModuleHandler):
    @property
    def name(self) -> str:
        return "general_chat"

    @property
    def supported_intents(self) -> list[Intent]:
        return [Intent.GENERAL_CHAT, Intent.MEMORY_RECALL]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        context_text = ""
        if request.context.memory_entries:
            context_text = "\n\nRelevant context from memory:\n"
            for entry in request.context.memory_entries[:settings.context_memory_limit]:
                cat = entry.get("category", "")
                subj = entry.get("subject", "")
                body = entry.get("content", "")
                context_text += f"- [{cat}] {subj}: {body}\n"

        system_prompt = _system_prompt()
        if context_text:
            system_prompt += context_text

        messages = []
        for msg in request.conversation_history[-settings.conversation_history_limit:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.user_message})

        content = await invoke_claude(
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )

        return ModuleResponse(content=content)
