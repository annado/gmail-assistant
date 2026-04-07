"""Tests for gmail_api.py — mark_as_read and fetch_body."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

import gmail_cache


def make_http_error(status, reason="error"):
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    return HttpError(resp, b"error detail")


def _build_message(
    msg_id="msg123",
    subject="Test Subject",
    plain_text="",
    html_text="",
    label_ids=None,
):
    """Build a fake Gmail API message dict."""
    parts = []
    if plain_text:
        parts.append(
            {
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(plain_text.encode()).decode()
                },
            }
        )
    if html_text:
        parts.append(
            {
                "mimeType": "text/html",
                "body": {
                    "data": base64.urlsafe_b64encode(html_text.encode()).decode()
                },
            }
        )
    payload = {
        "headers": [
            {"name": "Subject", "value": subject},
            {"name": "From", "value": "test@example.com"},
            {"name": "Date", "value": "Mon, 7 Apr 2026 08:00:00 -0700"},
        ],
    }
    if parts:
        payload["mimeType"] = "multipart/alternative"
        payload["parts"] = parts
    else:
        payload["mimeType"] = "text/plain"
        payload["body"] = {"data": ""}

    msg = {
        "id": msg_id,
        "labelIds": label_ids if label_ids is not None else ["INBOX", "UNREAD"],
        "payload": payload,
    }
    return msg


@pytest.fixture
def mock_service():
    """A MagicMock Gmail service with chainable methods."""
    return MagicMock()


@pytest.fixture(autouse=True)
def use_tmp_emails_dir(tmp_path, monkeypatch):
    """Redirect EMAILS_DIR to a tmp directory for all tests."""
    monkeypatch.setattr(gmail_cache, "EMAILS_DIR", tmp_path / "emails")


# ---------- mark_as_read ----------


class TestMarkAsRead:
    def test_mark_as_read_calls_modify(self, mock_service):
        """Verify messages().modify() called with removeLabelIds: ['UNREAD']."""
        from gmail_api import mark_as_read

        msg = _build_message()
        mock_service.users().messages().get().execute.return_value = msg
        mock_service.users().messages().modify().execute.return_value = msg

        mark_as_read(mock_service, "msg123")

        mock_service.users().messages().modify.assert_called_with(
            userId="me", id="msg123", body={"removeLabelIds": ["UNREAD"]}
        )

    def test_mark_as_read_returns_confirmation(self, mock_service):
        """Returns a success string containing the subject."""
        from gmail_api import mark_as_read

        msg = _build_message(subject="Meeting Tomorrow")
        mock_service.users().messages().get().execute.return_value = msg
        mock_service.users().messages().modify().execute.return_value = msg

        result = mark_as_read(mock_service, "msg123")

        assert "Meeting Tomorrow" in result
        assert "msg123" in result

    def test_mark_as_read_invalid_id(self, mock_service):
        """API returns 404 HttpError, tool returns error string (no exception)."""
        from gmail_api import mark_as_read

        mock_service.users().messages().modify().execute.side_effect = make_http_error(
            404
        )

        result = mark_as_read(mock_service, "bad_id")

        assert "bad_id" in result
        assert "not found" in result.lower()

    def test_mark_as_read_already_read(self, mock_service):
        """Message already lacks UNREAD label — returns confirmation (no-op is fine)."""
        from gmail_api import mark_as_read

        msg = _build_message(label_ids=["INBOX"])
        mock_service.users().messages().get().execute.return_value = msg
        mock_service.users().messages().modify().execute.return_value = msg

        result = mark_as_read(mock_service, "msg123")

        # Should still return a success-like string, not an error
        assert "msg123" in result
        assert "error" not in result.lower()


# ---------- fetch_body ----------


class TestFetchBody:
    def test_fetch_body_returns_markdown(self, mock_service):
        """Mock messages().get() with a sample payload, verify markdown output."""
        from gmail_api import fetch_body

        msg = _build_message(plain_text="Hello, world!")
        mock_service.users().messages().get().execute.return_value = msg

        result = fetch_body(mock_service, "msg123")

        assert "Hello, world!" in result

    def test_fetch_body_handles_placeholder(self, mock_service):
        """Mock payload with <!--placeholder--> HTML, verify fallback."""
        from gmail_api import fetch_body

        msg = _build_message(html_text="<!--placeholder-->")
        mock_service.users().messages().get().execute.return_value = msg

        result = fetch_body(mock_service, "msg123")

        # body_to_markdown treats comment-only HTML as empty, so result should
        # be empty or a "no content" message
        assert "<!--placeholder-->" not in result

    def test_fetch_body_api_error(self, mock_service):
        """API returns 500 HttpError, tool returns error string."""
        from gmail_api import fetch_body

        mock_service.users().messages().get().execute.side_effect = make_http_error(500)

        result = fetch_body(mock_service, "msg123")

        assert "500" in result
        assert "error" in result.lower()

    def test_fetch_body_empty_message(self, mock_service):
        """Message with no body parts returns graceful message."""
        from gmail_api import fetch_body

        msg = _build_message()  # no plain_text, no html_text
        mock_service.users().messages().get().execute.return_value = msg

        result = fetch_body(mock_service, "msg123")

        # Should not raise; should return something indicating no content
        assert isinstance(result, str)


# ---------- auth / rate-limit ----------


class TestEdgeCases:
    def test_expired_token_auto_refresh(self, mock_service):
        """Expired token triggers RefreshError, returns auth error string."""
        from gmail_api import mark_as_read

        mock_service.users().messages().modify().execute.side_effect = RefreshError(
            "Token has been expired or revoked."
        )

        result = mark_as_read(mock_service, "msg123")

        assert "expired" in result.lower() or "re-run" in result.lower()
        assert "gmail_auth" in result.lower() or "re-authorize" in result.lower()

    def test_rate_limit_returns_error(self, mock_service):
        """429 response returns descriptive error string."""
        from gmail_api import fetch_body

        mock_service.users().messages().get().execute.side_effect = make_http_error(429)

        result = fetch_body(mock_service, "msg123")

        assert "rate limit" in result.lower()
