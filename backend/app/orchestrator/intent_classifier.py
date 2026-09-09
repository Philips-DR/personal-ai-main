import json
import logging

from app.claude import invoke_claude_json
from app.config import settings
from app.models.orchestrator import Intent, IntentClassification

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the intent classifier for a personal AI assistant.
Classify the user's message into exactly one of these intents:

- email.read: User wants to check or read emails
- email.triage: User wants inbox triaged or classified
- email.draft: User wants to compose or reply to an email
- email.summarize: User wants an email thread summarized
- email.send: User confirms sending a drafted email
- meeting.transcribe: User is providing meeting audio/text for transcription
- meeting.summarize: User wants a meeting summary
- meeting.actions: User wants action items from a meeting
- task.create: User wants to create a new task or reminder
- task.list: User wants to see their tasks
- task.update: User wants to update, complete, or snooze a task
- task.remind: User asks about upcoming deadlines or reminders
- brief.generate: User wants to see their morning brief
- brief.configure: User wants to change brief schedule, timezone, tone, or toggles
- github.document: User wants documentation generated from a repo
- drive.search: User wants to find files in Google Drive
- drive.read: User wants to read a Google Doc's content
- doc.create: User wants to create a new Google Doc
- doc.append: User wants to add text to an existing Google Doc
- sheet.append_row: User wants to add a row to a Google Sheet
- learning.plan: User wants a learning roadmap or study plan for a skill
- learning.review: User wants a review of their learning progress
- learning.prompt: User has a study question, wants coaching, or wants to be quizzed
- life.suggest: User wants suggestions for life outside work (books, habits, hobbies)
- memory.recall: User asks about past conversations or remembered facts
- general.chat: General conversation that doesn't fit other intents

Respond with a JSON object: {"intent": "<intent>", "parameters": {}, "confidence": 0.0-1.0}

Extract relevant parameters:
- For email: thread_id, to, subject, tone (formal/casual)
- For tasks: title, owner, due_date, priority, project_name, assignee
- For meeting: input_type (audio/text/transcript), audio_url
- For github: repo_url
- For drive/docs: doc_id, title, body, text, range, spreadsheet_id
- For learning: goal, experience_level, daily_minutes, duration_weeks

Confidence threshold: if below 0.6, default to general.chat."""


async def classify_intent(
    user_message: str, conversation_history: list[dict] | None = None
) -> IntentClassification:
    """Classify the user's message into an intent using Claude via Bedrock."""
    messages = []
    if conversation_history:
        for msg in conversation_history[-settings.conversation_history_limit:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    messages.append({"role": "user", "content": user_message})

    try:
        parsed = await invoke_claude_json(
            system_prompt=_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=512,
            temperature=0.1,
        )
        intent_str = parsed.get("intent", "general.chat")
        confidence = parsed.get("confidence", 0.0)

        # Validate intent exists
        try:
            intent = Intent(intent_str)
        except ValueError:
            logger.warning("Unknown intent '%s', defaulting to general.chat", intent_str)
            intent = Intent.GENERAL_CHAT
            confidence = 0.3

        # Low confidence fallback
        if confidence < settings.intent_confidence_threshold:
            logger.info(
                "Low confidence (%.2f < %.2f) for '%s', defaulting to general.chat",
                confidence, settings.intent_confidence_threshold, intent,
            )
            intent = Intent.GENERAL_CHAT

        logger.info("Classified intent: %s (confidence: %.2f)", intent, confidence)
        return IntentClassification(
            intent=intent,
            parameters=parsed.get("parameters", {}),
            confidence=confidence,
        )

    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse intent classification response: %s", e)
        return IntentClassification(intent=Intent.GENERAL_CHAT, confidence=0.0)
