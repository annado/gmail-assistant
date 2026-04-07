import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def tmp_auth_dir(tmp_path):
    """Provides a temporary directory for token and credentials files."""
    return tmp_path


@pytest.fixture
def token_path(tmp_auth_dir):
    """Path to token.json inside the temp directory."""
    return tmp_auth_dir / "token.json"


@pytest.fixture
def credentials_path(tmp_auth_dir):
    """Path to credentials.json inside the temp directory."""
    return tmp_auth_dir / "credentials.json"


@pytest.fixture
def fake_credentials_file(credentials_path):
    """Write a minimal OAuth client-secrets file for InstalledAppFlow."""
    data = {
        "installed": {
            "client_id": "fake-client-id.apps.googleusercontent.com",
            "client_secret": "fake-client-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    credentials_path.write_text(json.dumps(data))
    return credentials_path


@pytest.fixture
def valid_token_data():
    """Return a dict representing a valid serialised token."""
    return {
        "token": "ya29.valid-access-token",
        "refresh_token": "1//valid-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "fake-client-id.apps.googleusercontent.com",
        "client_secret": "fake-client-secret",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.labels",
        ],
    }


@pytest.fixture
def valid_token_file(token_path, valid_token_data):
    """Write a valid token.json and return its path."""
    token_path.write_text(json.dumps(valid_token_data))
    return token_path


@pytest.fixture
def mock_gmail_service():
    """A MagicMock that mimics the Gmail API service object."""
    service = MagicMock()
    service.users.return_value.getProfile.return_value.execute.return_value = {
        "emailAddress": "test@example.com"
    }
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [],
        "resultSizeEstimate": 0,
    }
    return service
