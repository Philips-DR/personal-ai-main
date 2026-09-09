"""Email thread summarizer via Claude."""

import logging

from app.claude import invoke_claude

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """You are an email summarization assistant. Given an email thread, produce a concise 2-3 sentence summary that captures:
1. What is being discussed
2. What action (if any) is needed
3. Key deadlines or dates mentioned

Be concise and actionable."""


async def summarize_thread(subject: str, snippet: str, from_address: str) -> str:
    """Summarize an email thread into 2-3 sentences."""
    email_text = f"From: {from_address}\nSubject: {subject}\n\n{snippet}"

    result = await invoke_claude(
        system_prompt=_SUMMARIZE_PROMPT,
        messages=[{"role": "user", "content": email_text}],
        max_tokens=256,
        temperature=0.3,
    )

    logger.info("Summarized email thread: %s", subject[:50])
    return result.strip()
