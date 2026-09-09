"""Shared fixtures for all tests."""


import pytest

from app.models.orchestrator import ContextBundle, Intent, ModuleRequest


@pytest.fixture
def context():
    return ContextBundle()


def make_request(intent: Intent, message: str = "test", params: dict | None = None) -> ModuleRequest:
    return ModuleRequest(
        intent=intent,
        user_message=message,
        parameters=params or {},
        context=ContextBundle(),
    )
