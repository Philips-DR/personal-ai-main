"""Unit tests for the Task module handler."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.orchestrator import Intent
from app.models.task import Task, TaskCreate, TaskPriority, TaskStatus
from app.modules.tasks.handler import TaskModule
from tests.conftest import make_request


@pytest.fixture
def handler():
    return TaskModule()


def _sample_task(**kwargs) -> Task:
    defaults = dict(
        id=uuid4(),
        title="Test Task",
        owner="Phil",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.TODO,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Task(**defaults)


def _sample_create() -> TaskCreate:
    return TaskCreate(title="Send report to Elton", owner="Phil", priority=TaskPriority.HIGH)


class TestTaskCreate:
    async def test_creates_task_from_nl(self, handler):
        task = _sample_task(title="Send report to Elton", priority=TaskPriority.HIGH)
        with (
            patch("app.modules.tasks.handler.parse_task_from_nl", new=AsyncMock(return_value=_sample_create())),
            patch("app.modules.tasks.handler.create_task", new=AsyncMock(return_value=task)),
        ):
            req = make_request(Intent.TASK_CREATE, "remind me to send the report to Elton")
            response = await handler.handle(req)

        assert "Send report to Elton" in response.content
        assert response.structured["task"]["title"] == "Send report to Elton"
        assert len(response.memory_updates) == 1

    async def test_returns_message_when_no_task_parsed(self, handler):
        with patch("app.modules.tasks.handler.parse_task_from_nl", new=AsyncMock(return_value=None)):
            req = make_request(Intent.TASK_CREATE, "hello there")
            response = await handler.handle(req)

        assert "specific" in response.content.lower() or "couldn't" in response.content.lower()

    async def test_includes_due_date_in_content(self, handler):
        due = datetime(2026, 5, 1)
        task = _sample_task(title="Report", due_date=due)
        create_data = TaskCreate(title="Report", owner="Phil", due_date=due, priority=TaskPriority.MEDIUM)
        with (
            patch("app.modules.tasks.handler.parse_task_from_nl", new=AsyncMock(return_value=create_data)),
            patch("app.modules.tasks.handler.create_task", new=AsyncMock(return_value=task)),
        ):
            req = make_request(Intent.TASK_CREATE, "write report by May 1")
            response = await handler.handle(req)

        assert "May 01" in response.content

    async def test_includes_assignee_when_present(self, handler):
        task = _sample_task(title="Deploy app", assignee="Henry")
        create_data = TaskCreate(title="Deploy app", owner="Phil", assignee="Henry", priority=TaskPriority.MEDIUM)
        with (
            patch("app.modules.tasks.handler.parse_task_from_nl", new=AsyncMock(return_value=create_data)),
            patch("app.modules.tasks.handler.create_task", new=AsyncMock(return_value=task)),
        ):
            req = make_request(Intent.TASK_CREATE, "ask Henry to deploy the app")
            response = await handler.handle(req)

        assert "Henry" in response.content


class TestTaskList:
    async def test_returns_task_list(self, handler):
        tasks = [_sample_task(title="Task A"), _sample_task(title="Task B")]
        with patch("app.modules.tasks.handler.list_tasks", new=AsyncMock(return_value=tasks)):
            req = make_request(Intent.TASK_LIST, "show my tasks")
            response = await handler.handle(req)

        assert "Task A" in response.content
        assert "Task B" in response.content
        assert len(response.structured["tasks"]) == 2

    async def test_empty_task_list(self, handler):
        with patch("app.modules.tasks.handler.list_tasks", new=AsyncMock(return_value=[])):
            req = make_request(Intent.TASK_LIST, "show my tasks")
            response = await handler.handle(req)

        assert "no open tasks" in response.content.lower() or "caught up" in response.content.lower()

    async def test_passes_owner_filter(self, handler):
        with patch("app.modules.tasks.handler.list_tasks", new=AsyncMock(return_value=[])) as mock_list:
            req = make_request(Intent.TASK_LIST, "show Henry's tasks", params={"owner": "Henry"})
            await handler.handle(req)

        mock_list.assert_awaited_once_with(owner="Henry")


class TestTaskUpdate:
    async def test_updates_task_status(self, handler):
        task_id = str(uuid4())
        task = _sample_task(title="Test Task", status=TaskStatus.DONE)
        with patch("app.modules.tasks.handler.update_task", new=AsyncMock(return_value=task)):
            req = make_request(
                Intent.TASK_UPDATE, "mark task done", params={"task_id": task_id, "status": "done"}
            )
            response = await handler.handle(req)

        assert "done" in response.content.lower()

    async def test_missing_task_id(self, handler):
        req = make_request(Intent.TASK_UPDATE, "mark task done", params={})
        response = await handler.handle(req)

        assert "which task" in response.content.lower() or "specify" in response.content.lower()

    async def test_task_not_found(self, handler):
        task_id = str(uuid4())
        with patch("app.modules.tasks.handler.update_task", new=AsyncMock(return_value=None)):
            req = make_request(Intent.TASK_UPDATE, "mark done", params={"task_id": task_id, "status": "done"})
            response = await handler.handle(req)

        assert "couldn't find" in response.content.lower() or "not found" in response.content.lower()


class TestTaskRemind:
    async def test_shows_overdue_and_due_today(self, handler):
        overdue = [_sample_task(title="Overdue Task", due_date=datetime(2026, 1, 1))]
        due_today = [_sample_task(title="Due Today Task")]
        reminders = {"overdue": overdue, "due_today": due_today, "total_open": 3}
        with patch("app.modules.tasks.reminders.get_reminders", new=AsyncMock(return_value=reminders)):
            req = make_request(Intent.TASK_REMIND, "remind me of my tasks")
            response = await handler.handle(req)

        assert "Overdue Task" in response.content
        assert "Due Today Task" in response.content

    async def test_all_caught_up(self, handler):
        reminders = {"overdue": [], "due_today": [], "total_open": 0}
        with patch("app.modules.tasks.reminders.get_reminders", new=AsyncMock(return_value=reminders)):
            req = make_request(Intent.TASK_REMIND, "any reminders?")
            response = await handler.handle(req)

        assert "caught up" in response.content.lower() or "no overdue" in response.content.lower()
