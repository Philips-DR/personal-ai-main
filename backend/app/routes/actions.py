from fastapi import APIRouter, HTTPException

from app.models.email import EmailDraft
from app.models.orchestrator import PendingAction
from app.modules.email.gmail_client import send_message
from app.modules.email.oauth import get_credentials

router = APIRouter()


@router.post("/execute")
async def execute_action(action: PendingAction) -> dict:
    """Execute a user-approved pending action."""
    if action.action_type == "email.send":
        try:
            draft = EmailDraft(**action.payload)
            creds = await get_credentials()
            result = await send_message(creds, draft, confirmed=True)
            return {"status": "ok", "message": f"Email sent. (ID: {result.get('id')})"}
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send email: {e}") from e

    raise HTTPException(status_code=400, detail=f"Unknown action type: {action.action_type}")


@router.post("/reject")
async def reject_action(action: PendingAction) -> dict:
    """Record that a pending action was rejected (no-op for now, returns acknowledgement)."""
    return {"status": "rejected", "message": f"Action rejected: {action.description}"}
