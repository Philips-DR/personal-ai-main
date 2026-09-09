import logging

from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler
from app.modules.tasks.parser import parse_task_from_nl
from app.modules.tasks.store import (
    create_task,
    list_tasks,
    update_task,
)

logger = logging.getLogger(__name__)


class TaskModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "tasks"

    @property
    def supported_intents(self) -> list[Intent]:
        return [Intent.TASK_CREATE, Intent.TASK_LIST, Intent.TASK_UPDATE, Intent.TASK_REMIND]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        intent = request.intent

        if intent == Intent.TASK_CREATE:
            return await self._handle_create(request)
        elif intent == Intent.TASK_LIST:
            return await self._handle_list(request)
        elif intent == Intent.TASK_UPDATE:
            return await self._handle_update(request)
        elif intent == Intent.TASK_REMIND:
            return await self._handle_remind(request)

        return ModuleResponse(content="I'm not sure how to handle that task request.")

    async def _handle_create(self, request: ModuleRequest) -> ModuleResponse:
        task_data = await parse_task_from_nl(request.user_message)
        if not task_data:
            return ModuleResponse(content="I couldn't extract a task from that message. Could you be more specific?")

        task = await create_task(task_data)
        due = f" (due {task.due_date.strftime('%b %d')})" if task.due_date else ""
        content = f"Created task: **{task.title}**{due} — priority {task.priority.value}"
        if task.assignee:
            content += f", assigned to {task.assignee}"

        return ModuleResponse(
            content=content,
            structured={"task": task.model_dump()},
            memory_updates=[{
                "category": "fact",
                "subject": f"Task: {task.title}",
                "content": (
                    f"Phil created a task: {task.title}. Status: {task.status.value}."
                    f" Due: {task.due_date or 'no deadline'}"
                ),
            }],
        )

    async def _handle_list(self, request: ModuleRequest) -> ModuleResponse:
        owner = request.parameters.get("owner")
        tasks = await list_tasks(owner=owner)
        if not tasks:
            return ModuleResponse(content="You have no open tasks. Nice work!")

        lines = ["Here are your tasks:\n"]
        for t in tasks:
            due = f" · Due {t.due_date.strftime('%b %d')}" if t.due_date else ""
            status = f" [{t.status.value}]" if t.status.value != "todo" else ""
            lines.append(f"- **{t.title}**{due}{status} ({t.priority.value})")
        return ModuleResponse(content="\n".join(lines), structured={"tasks": [t.model_dump() for t in tasks]})

    async def _handle_update(self, request: ModuleRequest) -> ModuleResponse:
        from uuid import UUID

        from app.models.task import TaskStatus, TaskUpdate

        task_id = request.parameters.get("task_id")
        if not task_id:
            return ModuleResponse(content="Which task would you like to update? Please specify a task title or ID.")

        status = request.parameters.get("status")
        update = TaskUpdate()
        if status:
            import contextlib
            with contextlib.suppress(ValueError):
                update.status = TaskStatus(status)

        task = await update_task(UUID(task_id), update)
        if not task:
            return ModuleResponse(content=f"Couldn't find task {task_id}.")

        return ModuleResponse(content=f"Updated task **{task.title}** — status: {task.status.value}")

    async def _handle_remind(self, request: ModuleRequest) -> ModuleResponse:
        from app.modules.tasks.reminders import get_reminders

        reminders = await get_reminders()
        lines = []

        if reminders["overdue"]:
            lines.append("**Overdue:**")
            for t in reminders["overdue"]:
                lines.append(f"  - {t.title} (was due {t.due_date.strftime('%b %d')})")

        if reminders["due_today"]:
            lines.append("**Due today:**")
            for t in reminders["due_today"]:
                lines.append(f"  - {t.title}")

        if not lines:
            return ModuleResponse(content="No overdue or due-today tasks. You're all caught up!")

        lines.insert(0, f"You have {reminders['total_open']} open tasks.\n")
        return ModuleResponse(content="\n".join(lines))
