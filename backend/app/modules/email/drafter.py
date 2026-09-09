"""Email draft generator with tone calibration via Claude."""

import logging

from app.claude import invoke_claude_json
from app.config import settings
from app.models.email import EmailDraft, EmailTone

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1024
_TEMPERATURE = 0.5


def _draft_prompt() -> str:
    return (
        f"You are an email drafting assistant for {settings.user_name},"
        f" who leads the AI Solutions team at {settings.user_company}.\n"
        "Generate a professional email draft based on the instructions.\n\n"
        "Tone guidelines:\n"
        "- formal: For external clients, senior stakeholders\n"
        "- casual: For internal team members\n"
        "- neutral: Default professional tone\n\n"
        f"{settings.user_name}'s communication style:\n"
        "- Professional but approachable\n"
        "- Clear and concise\n"
        "- Action-oriented\n\n"
        'Return JSON: {"to": ["recipient"], "subject": "...", "body": "..."}\n'
        "The body should be HTML-formatted. Respond with ONLY the JSON object."
    )


async def generate_reply(
    thread_subject: str,
    thread_snippet: str,
    from_address: str,
    instructions: str = "",
    tone: EmailTone = EmailTone.NEUTRAL,
) -> EmailDraft:
    """Generate a reply draft for an email thread."""
    user_msg = (
        f"Original email from: {from_address}\n"
        f"Subject: {thread_subject}\n\n"
        f"{thread_snippet}\n\n"
        f"Instructions for reply: {instructions or 'Write an appropriate reply'}\n"
        f"Tone: {tone.value}"
    )

    parsed = await invoke_claude_json(
        system_prompt=_draft_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )

    draft = EmailDraft(
        to=parsed.get("to", [from_address]),
        subject=parsed.get("subject", f"Re: {thread_subject}"),
        body=parsed.get("body", ""),
        tone=tone,
    )
    logger.info("Generated reply draft for: %s", thread_subject[:settings.email_subject_display_length])
    return draft


async def generate_new(
    instructions: str,
    tone: EmailTone = EmailTone.NEUTRAL,
) -> EmailDraft:
    """Generate a new email draft from natural language instructions."""
    user_msg = f"Instructions: {instructions}\nTone: {tone.value}"

    parsed = await invoke_claude_json(
        system_prompt=_draft_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )

    draft = EmailDraft(
        to=parsed.get("to", []),
        subject=parsed.get("subject", ""),
        body=parsed.get("body", ""),
        tone=tone,
    )
    logger.info("Generated new email draft: %s", draft.subject[:settings.email_subject_display_length])
    return draft
