"""Gmail OAuth 2.0 flow — token exchange, refresh, and encrypted storage."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import text

from app.config import settings
from app.db.client import get_session

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    # Google Drive / Docs / Sheets (Phase 2)
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_URI = "https://oauth2.googleapis.com/token"


def _fernet() -> Fernet | None:
    """Return a Fernet instance if a key is configured, else None (no encryption)."""
    key = settings.oauth_token_encryption_key.strip()
    if not key:
        return None
    return Fernet(key.encode())


def _encrypt(value: str) -> str:
    f = _fernet()
    return f.encrypt(value.encode()).decode() if f else value


def _decrypt(value: str) -> str:
    f = _fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        # Token was stored unencrypted (pre-encryption migration path)
        return value


def get_auth_url() -> str:
    """Generate the Google OAuth consent screen URL."""
    client_config = {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "redirect_uris": [settings.gmail_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.gmail_redirect_uri
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url


async def exchange_code(code: str, authorization_response: str | None = None) -> None:
    """Exchange an authorization code for tokens and persist them."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URI,
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": settings.gmail_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    if "error" in token_data:
        raise RuntimeError(
            f"Token exchange failed: {token_data['error']} — {token_data.get('error_description', '')}"
        )

    expiry = None
    if "expires_in" in token_data:
        expiry = datetime.now(UTC) + timedelta(seconds=token_data["expires_in"])

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        expiry=expiry,
        scopes=SCOPES,
    )
    await _store_tokens(creds)
    logger.info("Gmail OAuth tokens stored successfully")


async def get_credentials() -> Credentials:
    """Load stored credentials, refreshing if expired."""
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM oauth_tokens WHERE provider = 'gmail' LIMIT 1")
        )
        row = result.mappings().first()

    if not row:
        raise RuntimeError("Gmail not connected. Run OAuth setup first.")

    row = dict(row)
    creds = Credentials(
        token=_decrypt(row["access_token"]),
        refresh_token=_decrypt(row["refresh_token"]),
        token_uri=TOKEN_URI,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        expiry=datetime.fromisoformat(str(row["token_expiry"])) if row["token_expiry"] else None,
        scopes=row.get("scopes", SCOPES),
    )

    if creds.expired or (creds.expiry and creds.expiry < datetime.now(UTC) + timedelta(minutes=5)):
        creds.refresh(Request())
        await _store_tokens(creds)
        logger.info("Refreshed Gmail OAuth token")

    return creds


async def _store_tokens(creds: Credentials) -> None:
    """Upsert encrypted tokens into the oauth_tokens table."""
    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO oauth_tokens (provider, access_token, refresh_token, token_expiry, scopes)
                VALUES ('gmail', :access_token, :refresh_token, :token_expiry, :scopes)
                ON CONFLICT (provider) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_expiry = EXCLUDED.token_expiry,
                    scopes = EXCLUDED.scopes,
                    updated_at = now()
            """),
            {
                "access_token": _encrypt(creds.token or ""),
                "refresh_token": _encrypt(creds.refresh_token or ""),
                "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
                "scopes": list(creds.scopes or SCOPES),
            },
        )
