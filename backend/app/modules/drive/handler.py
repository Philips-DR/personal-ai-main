"""Google Drive / Docs / Sheets module."""

import logging
import re

from app.config import settings
from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse, PendingAction
from app.modules.base import ModuleHandler

logger = logging.getLogger(__name__)

_DRIVE_FILE_RE = re.compile(r"docs\.google\.com/(?:document|spreadsheets)/d/([A-Za-z0-9_-]+)")


class DriveModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "drive"

    @property
    def supported_intents(self) -> list[Intent]:
        return [
            Intent.DRIVE_SEARCH,
            Intent.DRIVE_READ,
            Intent.DOC_CREATE,
            Intent.DOC_APPEND,
            Intent.SHEET_APPEND_ROW,
        ]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        intent = request.intent

        try:
            from app.modules.email.oauth import get_credentials
            creds = await get_credentials()
        except Exception as e:
            return ModuleResponse(content=f"Google account not connected: {e}")

        if intent == Intent.DRIVE_SEARCH:
            return await self._search(creds, request)
        if intent == Intent.DRIVE_READ:
            return await self._read(creds, request)
        if intent == Intent.DOC_CREATE:
            return await self._create_doc(creds, request)
        if intent == Intent.DOC_APPEND:
            return await self._append_doc(creds, request)
        if intent == Intent.SHEET_APPEND_ROW:
            return await self._append_sheet(creds, request)

        return ModuleResponse(content="Unsupported Drive intent.")

    async def _search(self, creds, request: ModuleRequest) -> ModuleResponse:
        from app.modules.drive.clients import search_drive

        query = request.parameters.get("query") or request.user_message
        drive_query = f"fullText contains '{query}' and trashed = false"
        files = await search_drive(creds, drive_query)

        if not files:
            return ModuleResponse(content=f"No files found matching '{query}'.")

        lines = [
            f"**{f['name']}** — [{f.get('mimeType','').split('.')[-1]}]({f.get('webViewLink','')})"
            for f in files
        ]
        return ModuleResponse(
            content="**Found in Drive:**\n\n" + "\n".join(lines),
            structured={"files": files},
        )

    async def _read(self, creds, request: ModuleRequest) -> ModuleResponse:
        from app.modules.drive.clients import read_doc

        doc_id = request.parameters.get("doc_id")
        if not doc_id:
            match = _DRIVE_FILE_RE.search(request.user_message)
            doc_id = match.group(1) if match else None

        if not doc_id:
            return ModuleResponse(content="Please provide a Google Doc URL or ID.")

        content = await read_doc(creds, doc_id)
        return ModuleResponse(content=f"**Document content:**\n\n{content[:4000]}")

    async def _create_doc(self, creds, request: ModuleRequest) -> ModuleResponse:
        title = request.parameters.get("title", settings.default_doc_title)
        body = request.parameters.get("body", "")
        confirmed = request.parameters.get("confirmed", False)

        if not confirmed:
            preview = body[:200] + ("..." if len(body) > 200 else "")
            return ModuleResponse(
                content=f"Ready to create a Google Doc titled **{title}**.",
                pending_actions=[
                    PendingAction(
                        action_type="doc.create",
                        description=f"Create Google Doc: \"{title}\"\nPreview: {preview}",
                        payload={"title": title, "body": body},
                    )
                ],
            )

        from app.modules.drive.clients import create_doc
        file_meta = await create_doc(creds, title, body)
        return ModuleResponse(
            content=(
                f"Google Doc created: **{file_meta['name']}**\n"
                f"{file_meta.get('webViewLink','')}"
            ),
            structured=file_meta,
        )

    async def _append_doc(self, creds, request: ModuleRequest) -> ModuleResponse:
        doc_id = request.parameters.get("doc_id")
        text = request.parameters.get("text", "")
        confirmed = request.parameters.get("confirmed", False)

        if not doc_id:
            return ModuleResponse(content="Please provide the Google Doc ID or URL.")

        if not confirmed:
            return ModuleResponse(
                content="Ready to append text to the Google Doc.",
                pending_actions=[
                    PendingAction(
                        action_type="doc.append",
                        description=f"Append to doc {doc_id}:\n{text[:200]}",
                        payload={"doc_id": doc_id, "text": text},
                    )
                ],
            )

        from app.modules.drive.clients import append_to_doc
        await append_to_doc(creds, doc_id, text)
        return ModuleResponse(content="Text appended to the Google Doc.")

    async def _append_sheet(self, creds, request: ModuleRequest) -> ModuleResponse:
        spreadsheet_id = request.parameters.get("spreadsheet_id")
        sheet_range = request.parameters.get("range", settings.default_sheet_range)
        values = request.parameters.get("values", [])
        confirmed = request.parameters.get("confirmed", False)

        if not spreadsheet_id:
            return ModuleResponse(content="Please provide the Google Sheet ID or URL.")

        if not confirmed:
            return ModuleResponse(
                content="Ready to append a row to the Google Sheet.",
                pending_actions=[
                    PendingAction(
                        action_type="sheet.append_row",
                        description=f"Append row to sheet {spreadsheet_id} [{sheet_range}]: {values}",  # noqa: E501
                        payload={
                            "spreadsheet_id": spreadsheet_id,
                            "range": sheet_range,
                            "values": values,
                        },
                    )
                ],
            )

        from app.modules.drive.clients import append_sheet_row
        await append_sheet_row(creds, spreadsheet_id, sheet_range, values)
        return ModuleResponse(content="Row appended to Google Sheet.")
