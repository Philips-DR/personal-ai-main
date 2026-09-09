"""Shared Claude invocation helpers — single place for all Bedrock/Claude calls."""

import json
import logging
from contextvars import ContextVar

from app.bedrock import get_bedrock_client
from app.config import settings

logger = logging.getLogger(__name__)

# Accumulates token usage for all Claude calls within a single async request.
# Reset at the start of each orchestrator.process() call via reset_request_tokens().
_request_tokens: ContextVar[dict | None] = ContextVar("_request_tokens", default=None)

_ZERO_TOKENS: dict = {"input_tokens": 0, "output_tokens": 0, "calls": 0}


def reset_request_tokens() -> None:
    """Call at the start of each request to clear accumulated token counts."""
    _request_tokens.set({"input_tokens": 0, "output_tokens": 0, "calls": 0})


def get_request_tokens() -> dict:
    """Return token usage accumulated since the last reset_request_tokens() call."""
    return dict(_request_tokens.get() or _ZERO_TOKENS)


def _accumulate(usage: dict) -> None:
    current = _request_tokens.get() or dict(_ZERO_TOKENS)
    _request_tokens.set({
        "input_tokens": current["input_tokens"] + usage.get("input_tokens", 0),
        "output_tokens": current["output_tokens"] + usage.get("output_tokens", 0),
        "calls": current["calls"] + 1,
    })


async def invoke_claude(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """Invoke Claude via Bedrock and return the text response."""
    client = get_bedrock_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
        "temperature": temperature,
    })

    response = client.invoke_model(
        modelId=settings.claude_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())

    _accumulate(result.get("usage", {}))

    text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    return text


async def invoke_claude_json(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> dict:
    """Invoke Claude and parse the response as JSON."""
    text = await invoke_claude(system_prompt, messages, max_tokens, temperature)
    return _extract_json(text)


def _extract_json(text: str) -> dict:
    """Extract the first JSON object or array from a string."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = "\n".join(line for line in lines[1:] if line.strip() != "```")
        stripped = inner.strip()

    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = stripped.find(start_char)
        if start == -1:
            continue
        end = stripped.rfind(end_char)
        if end != -1 and end >= start:
            return json.loads(stripped[start:end + 1])

    return json.loads(stripped)
