import json
import os
import stat
from unittest.mock import MagicMock, patch, mock_open

import pytest
from google.oauth2.credentials import Credentials

from gmail_auth import get_credentials, get_service, SCOPES


# ---- test_loads_existing_valid_token ----

def test_loads_existing_valid_token(
    valid_token_file, token_path, fake_credentials_file, credentials_path
):
    """When a valid, non-expired token.json exists, return credentials directly."""
    with patch(
        "gmail_auth.Credentials.from_authorized_user_file"
    ) as mock_from_file:
        creds = MagicMock(spec=Credentials)
        creds.valid = True
        creds.expired = False
        creds.to_json.return_value = '{"token": "valid"}'
        mock_from_file.return_value = creds

        result = get_credentials(token_path, credentials_path)

        mock_from_file.assert_called_once_with(str(token_path), SCOPES)
        assert result is creds


# ---- test_refreshes_expired_token ----

def test_refreshes_expired_token(
    valid_token_file, token_path, fake_credentials_file, credentials_path
):
    """When the token is expired but has a refresh_token, it should be refreshed."""
    with patch(
        "gmail_auth.Credentials.from_authorized_user_file"
    ) as mock_from_file, patch("gmail_auth.Request") as mock_request_cls:
        creds = MagicMock(spec=Credentials)
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "1//refresh"
        creds.to_json.return_value = '{"token": "refreshed"}'
        # After refresh(), valid should become True
        def do_refresh(_req):
            creds.valid = True
        creds.refresh.side_effect = do_refresh
        mock_from_file.return_value = creds

        result = get_credentials(token_path, credentials_path)

        creds.refresh.assert_called_once_with(mock_request_cls.return_value)
        assert result is creds


# ---- test_triggers_flow_when_no_token ----

def test_triggers_flow_when_no_token(
    token_path, fake_credentials_file, credentials_path
):
    """When no token.json exists, InstalledAppFlow should be triggered."""
    assert not token_path.exists()

    with patch("gmail_auth.InstalledAppFlow") as mock_flow_cls:
        mock_flow = MagicMock()
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.to_json.return_value = '{"token": "new"}'
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = get_credentials(token_path, credentials_path)

        mock_flow_cls.from_client_secrets_file.assert_called_once_with(
            str(credentials_path), SCOPES
        )
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is mock_creds


# ---- test_saves_token_after_auth ----

def test_saves_token_after_auth(
    token_path, fake_credentials_file, credentials_path
):
    """After a new OAuth flow, the token should be written to disk."""
    with patch("gmail_auth.InstalledAppFlow") as mock_flow_cls:
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.to_json.return_value = '{"token": "brand-new"}'
        mock_flow_cls.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_creds
        )

        get_credentials(token_path, credentials_path)

        assert token_path.exists()
        assert json.loads(token_path.read_text()) == {"token": "brand-new"}


# ---- test_corrupted_token_file ----

def test_corrupted_token_file(
    token_path, fake_credentials_file, credentials_path
):
    """A malformed token.json should not crash; it should fall through to OAuth flow."""
    token_path.write_text("NOT VALID JSON {{{{")

    with patch("gmail_auth.InstalledAppFlow") as mock_flow_cls:
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.to_json.return_value = '{"token": "recovered"}'
        mock_flow_cls.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_creds
        )

        result = get_credentials(token_path, credentials_path)

        # Should have fallen through to the OAuth flow
        mock_flow_cls.from_client_secrets_file.assert_called_once()
        assert result is mock_creds


# ---- test_revoked_token ----

def test_revoked_token(
    valid_token_file, token_path, fake_credentials_file, credentials_path
):
    """If token refresh raises RefreshError (revoked), fall through to OAuth flow."""
    from google.auth.exceptions import RefreshError

    with patch(
        "gmail_auth.Credentials.from_authorized_user_file"
    ) as mock_from_file, patch("gmail_auth.Request"), patch(
        "gmail_auth.InstalledAppFlow"
    ) as mock_flow_cls:
        creds = MagicMock(spec=Credentials)
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "1//revoked"
        creds.refresh.side_effect = RefreshError("Token has been revoked")
        mock_from_file.return_value = creds

        mock_new_creds = MagicMock(spec=Credentials)
        mock_new_creds.to_json.return_value = '{"token": "new-after-revoke"}'
        mock_flow_cls.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_new_creds
        )

        result = get_credentials(token_path, credentials_path)

        mock_flow_cls.from_client_secrets_file.assert_called_once()
        assert result is mock_new_creds


# ---- test_missing_credentials_file ----

def test_missing_credentials_file(token_path, tmp_auth_dir):
    """If credentials.json is missing, raise a clear FileNotFoundError."""
    missing_creds = tmp_auth_dir / "nonexistent_credentials.json"

    with pytest.raises(FileNotFoundError, match="credentials"):
        get_credentials(token_path, missing_creds)


# ---- test_token_written_with_0600 ----

def test_token_written_with_0600(
    token_path, fake_credentials_file, credentials_path
):
    """token.json must be created with owner-only read/write permissions (0600)."""
    with patch("gmail_auth.InstalledAppFlow") as mock_flow_cls:
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.to_json.return_value = '{"token": "secure"}'
        mock_flow_cls.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_creds
        )

        get_credentials(token_path, credentials_path)

        file_stat = os.stat(token_path)
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"
