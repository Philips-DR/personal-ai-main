import logging
from uuid import uuid4

from sqlalchemy import text

from app.config import settings
from app.db.client import get_session
from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler
from app.modules.meeting.action_extractor import extract_action_items
from app.modules.meeting.processor import clean_transcript
from app.modules.meeting.summarizer import summarize_meeting
from app.modules.meeting.transcription.factory import get_provider

logger = logging.getLogger(__name__)

_QUOTE_DISPLAY_MAX = 100  # chars of source_quote shown in chat response


class MeetingModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "meeting"

    @property
    def supported_intents(self) -> list[Intent]:
        return [
            Intent.MEETING_TRANSCRIBE,
            Intent.MEETING_SUMMARIZE,
            Intent.MEETING_ACTIONS,
        ]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        """Full meeting pipeline: transcribe → clean → summarize → extract actions → persist."""
        provider_name: str | None = None
        try:
            from app.preferences.store import get_preferences
            prefs = await get_preferences()
            provider_name = prefs.transcription_provider
        except Exception:
            pass
        provider = get_provider(provider_name)

        audio_url = request.parameters.get("audio_url")
        text_input = request.parameters.get("text")
        input_type = "audio" if audio_url else "text"

        # Step 1: Transcribe
        if audio_url:
            transcript = await provider.transcribe(audio_url)
        elif text_input:
            transcript = await provider.transcribe_text(text_input)
        else:
            transcript = await provider.transcribe_text(request.user_message)

        # Step 2: Clean
        cleaned = await clean_transcript(transcript)

        # Step 3: Summarize
        summary = await summarize_meeting(cleaned.raw_text)

        # Step 4: Extract action items
        action_items = await extract_action_items(cleaned.raw_text)

        # Step 5: Persist to Postgres
        meeting_id = str(uuid4())
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO meetings
                            (id, raw_input_type, raw_transcript, summary,
                             key_decisions, open_questions, topics)
                        VALUES
                            (:id, :raw_input_type, :raw_transcript, :summary,
                             :key_decisions, :open_questions, :topics)
                    """),
                    {
                        "id": meeting_id,
                        "raw_input_type": input_type,
                        "raw_transcript": cleaned.raw_text[:settings.transcript_db_max_length],
                        "summary": summary.executive_summary,
                        "key_decisions": summary.key_decisions,
                        "open_questions": summary.open_questions,
                        "topics": summary.topics,
                    },
                )

                for item in action_items:
                    await session.execute(
                        text("""
                            INSERT INTO meeting_action_items
                                (meeting_id, description, owner,
                                 due_date, priority, source_quote)
                            VALUES
                                (:meeting_id, :description, :owner,
                                 :due_date, :priority, :source_quote)
                        """),
                        {
                            "meeting_id": meeting_id,
                            "description": item.description,
                            "owner": item.owner,
                            "due_date": item.due_date.isoformat() if item.due_date else None,
                            "priority": item.priority.value,
                            "source_quote": item.source_quote,
                        },
                    )
        except Exception as e:
            logger.warning("Failed to save meeting to DB: %s", e)

        # Build response
        lines = [f"**Meeting Summary:**\n{summary.executive_summary}\n"]
        if summary.key_decisions:
            lines.append("**Key Decisions:**")
            for d in summary.key_decisions:
                lines.append(f"  - {d}")
        if summary.open_questions:
            lines.append("**Open Questions:**")
            for q in summary.open_questions:
                lines.append(f"  - {q}")
        if action_items:
            lines.append(f"\n**Action Items ({len(action_items)}):**")
            for i, item in enumerate(action_items, 1):
                owner = f" ({item.owner})" if item.owner else ""
                lines.append(f"  {i}. {item.description}{owner}")
                if item.source_quote:
                    lines.append(f"     > _{item.source_quote[:_QUOTE_DISPLAY_MAX]}_")

        return ModuleResponse(
            content="\n".join(lines),
            structured={
                "meeting_id": meeting_id,
                "summary": summary.model_dump(),
                "action_items": [a.model_dump() for a in action_items],
            },
            follow_up_intents=[Intent.TASK_CREATE] if action_items else [],
            memory_updates=[{
                "category": "fact",
                "subject": f"Meeting: {summary.topics[0] if summary.topics else 'Notes'}",
                "content": f"Meeting processed. {len(action_items)} action items extracted.",
            }],
        )
