"""Meeting summarizer via Claude — executive summary, decisions, questions, topics."""

import logging

from app.claude import invoke_claude_json
from app.config import settings
from app.models.meeting import MeetingSummary

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """You are a meeting summarization assistant. Given a meeting transcript, produce:

1. executive_summary: A concise 3-sentence summary
2. key_decisions: List of decisions made (strings)
3. open_questions: List of unresolved questions or items needing follow-up (strings)
4. topics: List of main topics discussed (strings)

Return JSON: {"executive_summary": "...", "key_decisions": [...], "open_questions": [...], "topics": [...]}
Respond with ONLY the JSON object."""


async def summarize_meeting(transcript_text: str) -> MeetingSummary:
    """Generate a structured meeting summary from transcript text."""
    text = transcript_text[:settings.transcript_max_length]

    parsed = await invoke_claude_json(
        system_prompt=_SUMMARIZE_PROMPT,
        messages=[{"role": "user", "content": text}],
        max_tokens=1024,
        temperature=0.3,
    )

    summary = MeetingSummary(**parsed)
    logger.info(
        "Generated meeting summary: %d decisions, %d questions",
        len(summary.key_decisions), len(summary.open_questions),
    )
    return summary
