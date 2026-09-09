import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.modules.email.oauth import exchange_code, get_auth_url

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/gmail")
async def gmail_auth_start() -> RedirectResponse:
    """Redirect the user to the Google OAuth consent screen."""
    auth_url = get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/gmail/callback")
async def gmail_auth_callback(request: Request, code: str, state: str | None = None) -> JSONResponse:
    """Exchange the authorization code for tokens and store them."""
    try:
        authorization_response = str(request.url)
        await exchange_code(code=code, authorization_response=authorization_response)
        return JSONResponse({"status": "ok", "message": "Gmail connected successfully."})
    except Exception as e:
        logger.exception("OAuth exchange failed")
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}") from e
