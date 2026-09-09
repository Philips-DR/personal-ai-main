import logging

from sqlalchemy import text

from app.config import settings
from app.db.client import get_session
from app.models.email import TriageCategory  # noqa: F401
from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse, PendingAction
from app.modules.base import ModuleHandler
from app.modules.email.drafter import generate_new, generate_reply
from app.modules.email.oauth import get_credentials
from app.modules.email.poller import poll_inbox
from app.modules.email.summarizer import summarize_thread
from app.modules.email.triage import classify_thread

logger = logging.getLogger(__name__)


class EmailModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "email"

    @property
    def supported_intents(self) -> list[Intent]:
        return [
            Intent.EMAIL_READ,
            Intent.EMAIL_TRIAGE,
            Intent.EMAIL_DRAFT,
            Intent.EMAIL_SUMMARIZE,
            Intent.EMAIL_SEND,
        ]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        try:
            return await self._dispatch(request)
        except RuntimeError as e:
            if "Gmail not connected" in str(e):
                return ModuleResponse(
                    content=(
                        "Gmail isn't connected yet. To set it up, visit:\n\n"
                        "`/api/auth/gmail`\n\n"
                        "This will redirect you to Google to authorise access."
                    )
                )
            raise

    async def _dispatch(self, request: ModuleRequest) -> ModuleResponse:
        intent = request.intent
        if intent == Intent.EMAIL_READ:
            return await self._handle_read(request)
        elif intent == Intent.EMAIL_TRIAGE:
            return await self._handle_triage(request)
        elif intent == Intent.EMAIL_DRAFT:
            return await self._handle_draft(request)
        elif intent == Intent.EMAIL_SUMMARIZE:
            return await self._handle_summarize(request)
        elif intent == Intent.EMAIL_SEND:
            return await self._handle_send(request)
        return ModuleResponse(content="I couldn't handle that email request.")

    async def _handle_read(self, request: ModuleRequest) -> ModuleResponse:
        new_threads = await poll_inbox()
        if not new_threads:
            async with get_session() as session:
                result = await session.execute(
                    text(  # noqa: S608
                        "SELECT * FROM email_threads ORDER BY last_synced_at DESC NULLS LAST"
                        f" LIMIT {settings.email_threads_limit}"
                    )
                )
                threads = [dict(r) for r in result.mappings().all()]
            if not threads:
                return ModuleResponse(content="Your inbox is empty or Gmail is not connected yet.")

            lines = ["Here are your recent emails:\n"]
            for t in threads:
                cat = f" [{t.get('category', 'unclassified')}]" if t.get("category") else ""
                urgent = " ⚡" if (t.get("urgency_score") or 0) >= 4 else ""
                subject = t.get("subject", "No subject")
                sender = t.get("from_name", "Unknown")
                lines.append(f"- **{subject}** from {sender}{cat}{urgent}")
            return ModuleResponse(content="\n".join(lines), structured={"threads": threads})

        lines = [f"Found {len(new_threads)} new email(s):\n"]
        for t in new_threads:
            lines.append(f"- **{t.get('subject', 'No subject')}** from {t.get('from_name', 'Unknown')}")
        return ModuleResponse(content="\n".join(lines), structured={"new_threads": new_threads})

    async def _handle_triage(self, request: ModuleRequest) -> ModuleResponse:
        async with get_session() as session:
            result = await session.execute(
                text(  # noqa: S608
                    "SELECT * FROM email_threads WHERE category IS NULL"
                    f" LIMIT {settings.email_triage_limit}"
                )
            )
            unclassified = [dict(r) for r in result.mappings().all()]

        if not unclassified:
            return ModuleResponse(content="All emails have been triaged. Use 'read my emails' to see them.")

        triaged = []
        for thread in unclassified:
            classification = await classify_thread(
                subject=thread.get("subject", ""),
                snippet=thread.get("snippet", ""),
                from_address=thread.get("from_address", ""),
            )
            async with get_session() as session:
                await session.execute(
                    text("""
                        UPDATE email_threads
                        SET category = :category, urgency_score = :urgency_score, needs_reply = :needs_reply
                        WHERE id = :id
                    """),
                    {
                        "category": classification["category"],
                        "urgency_score": classification["urgency_score"],
                        "needs_reply": classification["needs_reply"],
                        "id": str(thread["id"]),
                    },
                )
            triaged.append({**thread, **classification})

        lines = [f"Triage complete for {len(triaged)} email(s):\n"]
        for t in triaged:
            subj = str(t["subject"])[:settings.email_subject_display_length]
            lines.append(f"- **{subj}** → {t['category']} (urgency: {t['urgency_score']}/5)")
        return ModuleResponse(content="\n".join(lines), structured={"triaged": triaged})

    async def _handle_draft(self, request: ModuleRequest) -> ModuleResponse:
        thread_id = request.parameters.get("thread_id")
        instructions = request.parameters.get("instructions", "")
        tone = request.parameters.get("tone", "neutral")

        if thread_id:
            async with get_session() as session:
                result = await session.execute(
                    text("SELECT * FROM email_threads WHERE gmail_thread_id = :tid LIMIT 1"),
                    {"tid": thread_id},
                )
                row = result.mappings().first()
            if not row:
                return ModuleResponse(content="I couldn't find that email thread.")

            thread = dict(row)
            draft = await generate_reply(
                thread_subject=thread.get("subject", ""),
                thread_snippet=thread.get("snippet", ""),
                from_address=thread.get("from_address", ""),
                instructions=instructions,
                tone=tone,
            )
            draft.in_reply_to_thread_id = thread_id
        else:
            draft = await generate_new(instructions=request.user_message, tone=tone)

        return ModuleResponse(
            content=f"**Draft ready:**\n\n**To:** {', '.join(draft.to)}\n**Subject:** {draft.subject}\n\n{draft.body}",
            structured={"draft": draft.model_dump()},
            pending_actions=[PendingAction(
                action_type="email.send",
                description=f"Send email to {', '.join(draft.to)}: {draft.subject}",
                payload=draft.model_dump(),
            )],
        )

    async def _handle_summarize(self, request: ModuleRequest) -> ModuleResponse:
        async with get_session() as session:
            result = await session.execute(
                text(  # noqa: S608
                    "SELECT * FROM email_threads ORDER BY last_synced_at DESC NULLS LAST"
                    f" LIMIT {settings.email_summarize_limit}"
                )
            )
            threads = [dict(r) for r in result.mappings().all()]

        if not threads:
            return ModuleResponse(content="No email threads to summarize.")

        summaries = []
        for t in threads[:settings.email_summarize_limit]:
            summary = await summarize_thread(
                subject=t.get("subject", ""),
                snippet=t.get("snippet", ""),
                from_address=t.get("from_address", ""),
            )
            summaries.append(f"**{t.get('subject', 'No subject')}**\n{summary}")

        return ModuleResponse(content="\n\n---\n\n".join(summaries))

    async def _handle_send(self, request: ModuleRequest) -> ModuleResponse:
        from app.modules.email.gmail_client import send_message

        draft_data = request.parameters.get("draft", {})
        if not draft_data:
            return ModuleResponse(content="No draft data provided. Please generate a draft first.")

        from app.models.email import EmailDraft
        draft = EmailDraft(**draft_data)

        try:
            creds = await get_credentials()
            result = await send_message(creds, draft, confirmed=True)
            return ModuleResponse(content=f"Email sent successfully! (Message ID: {result.get('id')})")
        except PermissionError:
            return ModuleResponse(
                content="I need your explicit approval to send this email.",
                pending_actions=[PendingAction(
                    action_type="email.send",
                    description=f"Send email to {', '.join(draft.to)}: {draft.subject}",
                    payload=draft.model_dump(),
                )],
            )
