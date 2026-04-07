"""Tests for gmail_school.py — prepare_school_summary."""

import base64
from unittest.mock import MagicMock, patch

import pytest

import gmail_cache
from context_config import PersonalContext, ChildContext
from gmail_school import prepare_school_summary


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode("ascii")


def _build_full_message(msg_id, subject="Test", sender="a@b.com", date="Mon, 1 Apr 2026 08:00:00 -0700", body_text="Hello"):
    """Build a fake Gmail API full-format message."""
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
    """Build a mock service that returns messages in order by ID."""
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


@pytest.fixture
def sample_context():
    return PersonalContext(
        children=(
            ChildContext(
                name="Alex",
                grade=7,
                school="Lincoln Middle School",
                sports=("soccer",),
                activities=("robotics club",),
                teachers=("Ms. Johnson (Math)",),
            ),
        )
    )


@pytest.fixture
def empty_context():
    return PersonalContext()


class TestPrepareSchoolSummary:
    def test_no_message_ids(self, sample_context):
        service = MagicMock()
        result = prepare_school_summary(service, [], sample_context)
        assert "No message IDs" in result

    def test_returns_context_and_file_paths(self, sample_context):
        msg = _build_full_message("msg1", subject="Field Trip", sender="office@school.edu", body_text="Permission slip due Friday.")
        service = _mock_service(msg)

        result = prepare_school_summary(service, ["msg1"], sample_context)

        assert "PERSONAL CONTEXT" in result
        assert "Alex" in result
        assert "Grade: 7" in result
        assert "Lincoln Middle School" in result
        assert "soccer" in result
        assert "Ms. Johnson" in result
        assert "EMAIL FILES (1 emails)" in result
        assert "msg1.md" in result
        # Body should NOT be in the result (it's in the file)
        assert "Permission slip due Friday." not in result

    def test_multiple_emails_returns_multiple_paths(self, sample_context):
        msg1 = _build_full_message("msg1", subject="Email One", body_text="Body one")
        msg2 = _build_full_message("msg2", subject="Email Two", body_text="Body two")
        service = _mock_service(msg1, msg2)

        result = prepare_school_summary(service, ["msg1", "msg2"], sample_context)

        assert "EMAIL FILES (2 emails)" in result
        assert "msg1.md" in result
        assert "msg2.md" in result
        # Bodies should NOT be in the result
        assert "Body one" not in result
        assert "Body two" not in result

    def test_empty_context(self, empty_context):
        msg = _build_full_message("msg1")
        service = _mock_service(msg)

        result = prepare_school_summary(service, ["msg1"], empty_context)

        assert "No personal context configured" in result
        assert "msg1.md" in result

    def test_api_error_still_returns_path(self, sample_context):
        from googleapiclient.errors import HttpError

        service = MagicMock()
        resp = MagicMock()
        resp.status = 404
        service.users().messages().get().execute.side_effect = HttpError(resp, b"not found")

        result = prepare_school_summary(service, ["bad_id"], sample_context)

        # Should still have a file path (error placeholder)
        assert "bad_id.md" in result

    def test_includes_summary_instructions(self, sample_context):
        msg = _build_full_message("msg1")
        service = _mock_service(msg)

        result = prepare_school_summary(service, ["msg1"], sample_context)

        assert "SUMMARY INSTRUCTIONS" in result
        assert "action items" in result

    @patch("gmail_school._load_summary_instructions", return_value=None)
    def test_missing_prompt_file_omits_instructions(self, _mock, sample_context):
        msg = _build_full_message("msg1")
        service = _mock_service(msg)

        result = prepare_school_summary(service, ["msg1"], sample_context)

        assert "SUMMARY INSTRUCTIONS" not in result

    def test_cached_files_contain_email_body(self, sample_context, tmp_path):
        msg = _build_full_message("msg1", body_text="Important school info")
        service = _mock_service(msg)

        prepare_school_summary(service, ["msg1"], sample_context)

        # Verify the cached file has the body
        cached_files = list((tmp_path / "emails").rglob("msg1.md"))
        assert len(cached_files) == 1
        content = cached_files[0].read_text()
        assert "Important school info" in content
