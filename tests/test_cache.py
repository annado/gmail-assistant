"""Tests for gmail_cache.py — email caching to local markdown files."""

import base64
from unittest.mock import MagicMock, patch

import pytest

import gmail_cache
from gmail_cache import find_cached, read_cached, save_email, ensure_cached


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode("ascii")


def _build_full_message(msg_id, subject="Test", sender="a@b.com", date="Mon, 7 Apr 2026 08:00:00 -0700", body_text="Hello"):
    return {
        "id": msg_id,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": date},
            ],
            "body": {"data": _b64(body_text)},
        },
    }


def _mock_service(*messages):
    service = MagicMock()
    msg_map = {m["id"]: m for m in messages}

    def get_side_effect(userId, id, format):
        return MagicMock(execute=MagicMock(return_value=msg_map[id]))

    service.users().messages().get = get_side_effect
    return service


@pytest.fixture(autouse=True)
def use_tmp_emails_dir(tmp_path, monkeypatch):
    """Redirect EMAILS_DIR to a tmp directory for all tests."""
    monkeypatch.setattr(gmail_cache, "EMAILS_DIR", tmp_path / "emails")


class TestFindCached:
    def test_returns_none_when_not_cached(self):
        assert find_cached("nonexistent") is None

    def test_finds_cached_file(self, tmp_path):
        emails_dir = tmp_path / "emails"
        (emails_dir / "2026" / "04").mkdir(parents=True)
        cached = emails_dir / "2026" / "04" / "msg123.md"
        cached.write_text("---\nid: msg123\n---\n\nHello")
        assert find_cached("msg123") == cached


class TestReadCached:
    def test_returns_none_when_not_cached(self):
        assert read_cached("nonexistent") is None

    def test_returns_body_without_frontmatter(self, tmp_path):
        emails_dir = tmp_path / "emails"
        (emails_dir / "2026" / "04").mkdir(parents=True)
        cached = emails_dir / "2026" / "04" / "msg123.md"
        cached.write_text("---\nid: msg123\nsubject: Test\n---\n\nThe email body.")
        result = read_cached("msg123")
        assert result == "The email body."
        assert "---" not in result


class TestSaveEmail:
    def test_saves_to_year_month_dir(self):
        msg = _build_full_message("msg1", date="Tue, 18 Mar 2026 10:00:00 -0700")
        service = _mock_service(msg)

        path = save_email(service, "msg1")

        assert "2026" in str(path)
        assert "03" in str(path)
        assert path.name == "msg1.md"
        assert path.exists()

    def test_file_has_frontmatter_and_body(self):
        msg = _build_full_message("msg1", subject="Field Trip", sender="office@school.edu", body_text="Permission slip due Friday.")
        service = _mock_service(msg)

        path = save_email(service, "msg1")
        content = path.read_text()

        assert content.startswith("---\n")
        assert "id: msg1" in content
        assert "subject: Field Trip" in content
        assert "from: office@school.edu" in content
        assert "Permission slip due Friday." in content

    def test_returns_cached_path_on_second_call(self):
        msg = _build_full_message("msg1")
        service = _mock_service(msg)

        path1 = save_email(service, "msg1")
        path2 = save_email(service, "msg1")

        assert path1 == path2
        # Gmail API should only be called once (first fetch)
        # Second call returns cached path

    def test_fallback_date_when_missing(self):
        msg = _build_full_message("msg1", date="")
        service = _mock_service(msg)

        path = save_email(service, "msg1")

        assert path.exists()
        assert path.name == "msg1.md"


class TestEnsureCached:
    def test_caches_multiple_emails(self):
        msg1 = _build_full_message("msg1", subject="Email 1", body_text="Body 1")
        msg2 = _build_full_message("msg2", subject="Email 2", body_text="Body 2")
        service = _mock_service(msg1, msg2)

        paths = ensure_cached(service, ["msg1", "msg2"])

        assert len(paths) == 2
        assert all(p.exists() for p in paths)
        assert "Body 1" in paths[0].read_text()
        assert "Body 2" in paths[1].read_text()

    def test_api_error_creates_placeholder(self):
        from googleapiclient.errors import HttpError

        service = MagicMock()
        resp = MagicMock()
        resp.status = 404
        service.users().messages().get().execute.side_effect = HttpError(resp, b"not found")

        paths = ensure_cached(service, ["bad_id"])

        assert len(paths) == 1
        assert paths[0].exists()
        content = paths[0].read_text()
        assert "fetch failed" in content
        assert "Error" in content

    def test_empty_list_returns_empty(self):
        service = MagicMock()
        assert ensure_cached(service, []) == []
