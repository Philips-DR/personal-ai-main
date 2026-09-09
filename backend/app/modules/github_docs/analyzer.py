"""Repo analyzer — identify entry points, dependencies, APIs, config."""

import json
import logging

from app.claude import invoke_claude_json
from app.config import settings

logger = logging.getLogger(__name__)

_MAX_TOKENS = 2048
_TEMPERATURE = 0.2

_ANALYZE_PROMPT = """You are a repository analysis assistant. Given a repository's file tree and key file contents, analyze:

1. entry_points: Main entry files (main.py, index.ts, app.py, etc.)
2. dependencies: Key libraries and frameworks used
3. apis: API endpoints or routes defined (if any)
4. data_flows: How data moves through the system
5. config: Configuration files and their purposes
6. architecture_type: "monolith", "microservices", "serverless", "library", etc.

Return JSON with these fields. Respond with ONLY the JSON object."""


async def analyze_repo(tree: list[dict], file_contents: dict[str, str]) -> dict:
    """Analyze a repo's structure and key files via Claude."""
    file_list = "\n".join(f["path"] for f in tree[:settings.github_analyze_max_files])
    contents_text = ""
    for path, content in file_contents.items():
        contents_text += f"\n--- {path} ---\n{content[:settings.github_file_content_max_length]}\n"

    if len(contents_text) > settings.github_analyze_max_context:
        contents_text = contents_text[:settings.github_analyze_max_context] + "\n... (truncated)"

    user_msg = f"File tree:\n{file_list}\n\nKey file contents:{contents_text}"

    try:
        parsed = await invoke_claude_json(
            system_prompt=_ANALYZE_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        logger.info(
            "Analyzed repo: %s architecture, %d entry points",
            parsed.get("architecture_type"), len(parsed.get("entry_points", [])),
        )
        return parsed
    except json.JSONDecodeError:
        logger.error("Failed to parse repo analysis")
        return {
            "entry_points": [], "dependencies": [], "apis": [],
            "data_flows": [], "config": [], "architecture_type": "unknown",
        }
