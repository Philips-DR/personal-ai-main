#!/usr/bin/env python3
"""Interactive Gmail OAuth 2.0 setup script.

Run once to authorize Gmail access and store tokens in Supabase.
Usage: python scripts/setup_oauth.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from google_auth_oauthlib.flow import InstalledAppFlow
from supabase import create_client

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def main() -> None:
    from app.config import settings

    client_config = {
        "installed": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    supabase.table("oauth_tokens").upsert(
        {
            "provider": "gmail",
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_expiry": creds.expiry.isoformat(),
            "scopes": list(creds.scopes or SCOPES),
        },
        on_conflict="provider",
    ).execute()

    print("Gmail OAuth tokens stored successfully.")


if __name__ == "__main__":
    main()
