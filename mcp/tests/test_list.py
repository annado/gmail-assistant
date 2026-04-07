"""Tests for gmail_list.py — list_messages."""

from unittest.mock import MagicMock

import pytest

from gmail_list import list_messages


def _mock_service_with_messages(messages_meta):
    """Build a mock Gmail service that returns given message metadata.

    messages_meta: list of dicts with keys: id, subject, from, date
    """
    service = MagicMock()

    # messages().list() returns stubs with just IDs
    stubs = [{"id": m["id"]} for m in messages_meta]
    service.users().messages().list().execute.return_value = {
        "messages": stubs,
        "resultSizeEstimate": len(stubs),
    }

    # messages().get() returns full metadata per ID
    def get_side_effect(userId, id, format, metadataHeaders):
        for m in messages_meta:
            if m["id"] == id:
                return MagicMock(
                    execute=MagicMock(
                        return_value={
                            "id": id,
                            "payload": {
                                "headers": [
                                    {"name": "Subject", "value": m.get("subject", "")},
                                    {"name": "From", "value": m.get("from", "")},
                                    {"name": "Date", "value": m.get("date", "")},
                                ]
                            },
                        }
                    )
                )
        return MagicMock(execute=MagicMock(return_value={"id": id, "payload": {"headers": []}}))

    service.users().messages().get = get_side_effect
    return service


class TestListMessages:
    def test_returns_formatted_lines(self):
        service = _mock_service_with_messages(
            [
                {
                    "id": "msg1",
                    "subject": "Field Trip Friday",
                    "from": "office@school.edu",
                    "date": "Mon, 1 Apr 2026 08:00:00 -0700",
                },
                {
                    "id": "msg2",
                    "subject": "Math Homework",
                    "from": "teacher@school.edu",
                    "date": "Tue, 2 Apr 2026 09:00:00 -0700",
                },
            ]
        )
        result = list_messages(service, "from:school.edu")
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "msg1" in lines[0]
        assert "Field Trip Friday" in lines[0]
        assert "office@school.edu" in lines[0]
        assert "Apr 2026" in lines[0]

    def test_no_messages_found(self):
        service = MagicMock()
        service.users().messages().list().execute.return_value = {
            "messages": [],
            "resultSizeEstimate": 0,
        }
        result = list_messages(service, "from:nobody")
        assert "No messages found" in result

    def test_no_messages_key(self):
        service = MagicMock()
        service.users().messages().list().execute.return_value = {
            "resultSizeEstimate": 0,
        }
        result = list_messages(service, "from:nobody")
        assert "No messages found" in result

    def test_api_error_returns_string(self):
        from googleapiclient.errors import HttpError

        service = MagicMock()
        resp = MagicMock()
        resp.status = 500
        resp.reason = "Internal Server Error"
        service.users().messages().list().execute.side_effect = HttpError(
            resp, b"server error"
        )
        result = list_messages(service, "is:unread")
        assert "Error" in result
        assert "500" in result

    def test_passes_query_and_max_results(self):
        service = MagicMock()
        service.users().messages().list().execute.return_value = {"messages": []}
        list_messages(service, "from:test@example.com", max_results=5)
        service.users().messages().list.assert_called_with(
            userId="me", q="from:test@example.com", maxResults=5
        )
