"""Gmail OAuth2 authentication helpers."""

import json
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


def get_credentials(
    token_path: str | Path,
    credentials_path: str | Path,
) -> Credentials:
    """Load, refresh, or create OAuth2 credentials for the Gmail API.

    Parameters
    ----------
    token_path:
        Path to token.json (will be created/overwritten on new auth).
    credentials_path:
        Path to the OAuth client-secrets file (credentials.json).

    Returns
    -------
    google.oauth2.credentials.Credentials
    """
    token_path = Path(token_path)
    credentials_path = Path(credentials_path)

    # Fail early if the client-secrets file is missing.
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {credentials_path}"
        )

    creds: Credentials | None = None

    # 1. Try loading an existing token.
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            # Corrupted / unparseable token file -- fall through.
            creds = None

    # 2. Refresh if expired.
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Token revoked or otherwise unusable -- fall through.
                creds = None

    # 3. Run the interactive OAuth flow when we have no usable credentials.
    if creds is None or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

    # 4. Persist the token for future runs.
    _save_token(token_path, creds)

    return creds


def _save_token(token_path: Path, creds: Credentials) -> None:
    """Write token.json with owner-only permissions (0600)."""
    token_path.write_text(creds.to_json())
    os.chmod(token_path, 0o600)


def get_service(credentials: Credentials):
    """Build and return a Gmail API service object."""
    return build("gmail", "v1", credentials=credentials)


if __name__ == "__main__":
    token = Path("token.json")
    client_secrets = Path("credentials.json")
    credentials = get_credentials(token, client_secrets)
    service = get_service(credentials)
    profile = service.users().getProfile(userId="me").execute()
    print(f"Authenticated as {profile['emailAddress']}")
