#!/usr/bin/env python3
"""Interactive Gmail OAuth 2.0 setup — command-line alternative to the web flow.

Authorizes Google access and stores the resulting tokens encrypted in the
`oauth_tokens` table, using the same code path as the web callback.

Requires an OAuth client of type **Desktop app** (this flow listens on an
ephemeral localhost port). If your credentials are a **Web application** client,
use the browser flow instead: start the backend and visit /api/auth/gmail.

Usage: python scripts/setup_oauth.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402


async def main() -> None:
    # Imported here so the sys.path insert above is in effect.
    from app.config import settings
    from app.modules.email.oauth import SCOPES, store_credentials

    if not settings.gmail_client_id or not settings.gmail_client_secret:
        sys.exit(
            "GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in backend/.env.local.\n"
            "Create credentials at https://console.cloud.google.com/apis/credentials"
        )

    client_config = {
        "installed": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        sys.exit(
            "Google did not return a refresh token — the assistant could not stay "
            "authorized. Revoke this app at https://myaccount.google.com/permissions "
            "and run this script again."
        )

    await store_credentials(creds)
    print(f"Gmail OAuth tokens stored (encrypted) for {len(SCOPES)} scopes.")


if __name__ == "__main__":
    asyncio.run(main())
