"""Thin Google Drive / Docs / Sheets service wrappers."""

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)


def _drive_service(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _docs_service(creds: Credentials):
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def _sheets_service(creds: Credentials):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


async def search_drive(creds: Credentials, query: str, max_results: int | None = None) -> list[dict]:
    """Search Drive files using a query string."""
    limit = max_results if max_results is not None else settings.drive_search_max_results
    service = _drive_service(creds)
    response = (
        service.files()
        .list(
            q=query,
            pageSize=limit,
            fields="files(id,name,mimeType,modifiedTime,webViewLink)",
        )
        .execute()
    )
    return response.get("files", [])


async def read_doc(creds: Credentials, doc_id: str) -> str:
    """Return plain-text content of a Google Doc."""
    service = _docs_service(creds)
    doc = service.documents().get(documentId=doc_id).execute()
    lines: list[str] = []
    for block in doc.get("body", {}).get("content", []):
        for el in block.get("paragraph", {}).get("elements", []):
            text = el.get("textRun", {}).get("content", "")
            lines.append(text)
    return "".join(lines)


async def create_doc(creds: Credentials, title: str, body: str) -> dict:
    """Create a Google Doc, return id + webViewLink."""
    docs = _docs_service(creds)
    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if body:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": body,
                        }
                    }
                ]
            },
        ).execute()

    drive = _drive_service(creds)
    file_meta = (
        drive.files()
        .get(fileId=doc_id, fields="id,name,webViewLink")
        .execute()
    )
    logger.info("Created Google Doc: %s (%s)", title, doc_id)
    return file_meta


async def append_to_doc(creds: Credentials, doc_id: str, text: str) -> None:
    """Append text at the end of an existing Google Doc."""
    docs = _docs_service(creds)
    doc = docs.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": end_index},
                        "text": f"\n{text}",
                    }
                }
            ]
        },
    ).execute()
    logger.info("Appended to Google Doc %s", doc_id)


async def append_sheet_row(
    creds: Credentials, spreadsheet_id: str, sheet_range: str, values: list
) -> None:
    """Append a row to a Google Sheet."""
    service = _sheets_service(creds)
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute()
    logger.info("Appended row to Sheet %s range %s", spreadsheet_id, sheet_range)
