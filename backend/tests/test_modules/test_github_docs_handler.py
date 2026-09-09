"""Unit tests for the GitHub Docs module handler."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.orchestrator import Intent
from app.modules.github_docs.handler import GitHubDocsModule
from tests.conftest import make_request


@pytest.fixture
def handler():
    return GitHubDocsModule()


def _sample_tree_data() -> dict:
    return {
        "owner": "ayadata-ai",
        "repo": "my-project",
        "files": ["README.md", "src/main.py", "src/utils.py"],
    }


def _sample_analysis() -> dict:
    return {
        "entry_points": ["src/main.py"],
        "key_modules": ["utils"],
        "dependencies": ["fastapi"],
    }


class TestGitHubDocsHandle:
    async def test_generates_all_6_doc_types(self, handler):
        docs = {k: f"# {k} content" for k in ["readme", "architecture", "module_docs", "workflow", "api_reference", "setup_guide"]}  # noqa: E501

        with (
            patch("app.modules.github_docs.handler.fetch_repo_tree", new=AsyncMock(return_value=_sample_tree_data())),
            patch("app.modules.github_docs.handler.select_key_files", return_value=["src/main.py"]),
            patch("app.modules.github_docs.handler.fetch_file_contents", new=AsyncMock(return_value={"src/main.py": "code"})),  # noqa: E501
            patch("app.modules.github_docs.handler.analyze_repo", new=AsyncMock(return_value=_sample_analysis())),
            patch("app.modules.github_docs.handler.generate_readme", new=AsyncMock(return_value=docs["readme"])),
            patch("app.modules.github_docs.handler.generate_architecture", new=AsyncMock(return_value=docs["architecture"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_module_docs", new=AsyncMock(return_value=docs["module_docs"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_workflow", new=AsyncMock(return_value=docs["workflow"])),
            patch("app.modules.github_docs.handler.generate_api_reference", new=AsyncMock(return_value=docs["api_reference"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_setup_guide", new=AsyncMock(return_value=docs["setup_guide"])),  # noqa: E501
            patch("app.modules.github_docs.handler.bundle_markdown", return_value="full bundle content"),
        ):
            req = make_request(
                Intent.GITHUB_DOCUMENT, "document this repo",
                params={"repo_url": "https://github.com/ayadata-ai/my-project"}
            )
            response = await handler.handle(req)

        assert "ayadata-ai/my-project" in response.content
        assert "6/6" in response.content
        assert response.structured["repo"] == "ayadata-ai/my-project"
        assert len(response.structured["docs"]) == 6

    async def test_missing_repo_url(self, handler):
        req = make_request(Intent.GITHUB_DOCUMENT, "document something", params={})
        response = await handler.handle(req)

        assert "provide a github" in response.content.lower() or "url" in response.content.lower()

    async def test_partial_generation_on_doc_failure(self, handler):
        with (
            patch("app.modules.github_docs.handler.fetch_repo_tree", new=AsyncMock(return_value=_sample_tree_data())),
            patch("app.modules.github_docs.handler.select_key_files", return_value=[]),
            patch("app.modules.github_docs.handler.fetch_file_contents", new=AsyncMock(return_value={})),
            patch("app.modules.github_docs.handler.analyze_repo", new=AsyncMock(return_value=_sample_analysis())),
            patch("app.modules.github_docs.handler.generate_readme", new=AsyncMock(return_value="# README")),
            patch("app.modules.github_docs.handler.generate_architecture", new=AsyncMock(side_effect=Exception("AI error"))),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_module_docs", new=AsyncMock(return_value="# Modules")),
            patch("app.modules.github_docs.handler.generate_workflow", new=AsyncMock(return_value="# Workflow")),
            patch("app.modules.github_docs.handler.generate_api_reference", new=AsyncMock(return_value="# API")),
            patch("app.modules.github_docs.handler.generate_setup_guide", new=AsyncMock(return_value="# Setup")),
            patch("app.modules.github_docs.handler.bundle_markdown", return_value="bundle"),
        ):
            req = make_request(
                Intent.GITHUB_DOCUMENT, "document repo",
                params={"repo_url": "https://github.com/ayadata-ai/my-project"}
            )
            response = await handler.handle(req)

        # Should succeed with 5/6 types
        assert "5/6" in response.content
        assert "Generation failed" in response.structured["docs"]["architecture"]

    async def test_repo_fetch_failure_returns_error(self, handler):
        with patch(
            "app.modules.github_docs.handler.fetch_repo_tree",
            new=AsyncMock(side_effect=Exception("Network error"))
        ):
            req = make_request(
                Intent.GITHUB_DOCUMENT, "document repo",
                params={"repo_url": "https://github.com/ayadata-ai/my-project"}
            )
            response = await handler.handle(req)

        assert "failed" in response.content.lower()

    async def test_creates_memory_update(self, handler):
        docs = {k: "# content" for k in ["readme", "architecture", "module_docs", "workflow", "api_reference", "setup_guide"]}  # noqa: E501
        with (
            patch("app.modules.github_docs.handler.fetch_repo_tree", new=AsyncMock(return_value=_sample_tree_data())),
            patch("app.modules.github_docs.handler.select_key_files", return_value=[]),
            patch("app.modules.github_docs.handler.fetch_file_contents", new=AsyncMock(return_value={})),
            patch("app.modules.github_docs.handler.analyze_repo", new=AsyncMock(return_value=_sample_analysis())),
            patch("app.modules.github_docs.handler.generate_readme", new=AsyncMock(return_value=docs["readme"])),
            patch("app.modules.github_docs.handler.generate_architecture", new=AsyncMock(return_value=docs["architecture"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_module_docs", new=AsyncMock(return_value=docs["module_docs"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_workflow", new=AsyncMock(return_value=docs["workflow"])),
            patch("app.modules.github_docs.handler.generate_api_reference", new=AsyncMock(return_value=docs["api_reference"])),  # noqa: E501
            patch("app.modules.github_docs.handler.generate_setup_guide", new=AsyncMock(return_value=docs["setup_guide"])),  # noqa: E501
            patch("app.modules.github_docs.handler.bundle_markdown", return_value="bundle"),
        ):
            req = make_request(
                Intent.GITHUB_DOCUMENT, "doc",
                params={"repo_url": "https://github.com/ayadata-ai/my-project"}
            )
            response = await handler.handle(req)

        assert len(response.memory_updates) == 1
        assert "ayadata-ai/my-project" in response.memory_updates[0]["subject"]
