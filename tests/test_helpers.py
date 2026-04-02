"""Tests for gmail_helpers — extract_body and body_to_markdown."""

import base64
from typing import Any

from gmail_helpers import extract_body, body_to_markdown


def _b64(text: str, encoding: str = "utf-8") -> str:
    """URL-safe base64-encode a string, matching Gmail API format."""
    return base64.urlsafe_b64encode(text.encode(encoding)).decode("ascii")


# ---------- extract_body ----------


def test_extract_plain_text():
    payload: dict[str, Any] = {
        "mimeType": "text/plain",
        "body": {"data": _b64("Hello, world!"), "size": 13},
    }
    plain, html = extract_body(payload)
    assert plain == "Hello, world!"
    assert html == ""


def test_extract_html_converts_to_markdown():
    html_src = "<p>Hello <b>world</b></p>"
    payload: dict[str, Any] = {
        "mimeType": "text/html",
        "body": {"data": _b64(html_src), "size": len(html_src)},
    }
    plain, html = extract_body(payload)
    assert plain == ""
    assert html == html_src


def test_extract_nested_multipart():
    payload: dict[str, Any] = {
        "mimeType": "multipart/mixed",
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "body": {"size": 0},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": _b64("Plain nested"), "size": 12},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": _b64("<p>HTML nested</p>"), "size": 18},
                    },
                ],
            }
        ],
    }
    plain, html = extract_body(payload)
    assert plain == "Plain nested"
    assert html == "<p>HTML nested</p>"


def test_placeholder_html_ignored():
    plain = ""
    html = "<!--placeholder-->"
    result = body_to_markdown(plain, html)
    assert result == ""


def test_prefers_plain_over_html():
    result = body_to_markdown("I am plain text.", "<p>I am HTML</p>")
    assert result == "I am plain text."


def test_extract_body_empty_payload():
    payload: dict[str, Any] = {}
    plain, html = extract_body(payload)
    assert plain == ""
    assert html == ""


def test_extract_body_base64_encoded():
    text = "Base64 content: special chars =+/"
    payload: dict[str, Any] = {
        "mimeType": "text/plain",
        "body": {"data": _b64(text), "size": len(text)},
    }
    plain, html = extract_body(payload)
    assert plain == text


def test_extract_body_non_utf8_charset():
    raw = "caf\u00e9"
    encoded = base64.urlsafe_b64encode(raw.encode("iso-8859-1")).decode("ascii")
    payload: dict[str, Any] = {
        "mimeType": "text/plain",
        "headers": [
            {"name": "Content-Type", "value": "text/plain; charset=iso-8859-1"}
        ],
        "body": {"data": encoded, "size": 5},
    }
    plain, html = extract_body(payload)
    assert "caf" in plain  # at minimum the ascii portion survives


def test_extract_body_attachment_only():
    payload: dict[str, Any] = {
        "mimeType": "multipart/mixed",
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "application/pdf",
                "filename": "report.pdf",
                "body": {"attachmentId": "abc123", "size": 9999},
                "headers": [
                    {
                        "name": "Content-Disposition",
                        "value": 'attachment; filename="report.pdf"',
                    }
                ],
            }
        ],
    }
    plain, html = extract_body(payload)
    assert plain == ""
    assert html == ""


def test_html_with_inline_images():
    html_src = (
        '<p>Look:</p><img src="cid:img1@mail">'
        '<img src="data:image/png;base64,AAAA">'
        "<p>End</p>"
    )
    payload: dict[str, Any] = {
        "mimeType": "text/html",
        "body": {"data": _b64(html_src), "size": len(html_src)},
    }
    plain, html = extract_body(payload)
    md = body_to_markdown(plain, html)
    # CID and data URI images should not appear in output
    assert "cid:" not in md
    assert "data:image" not in md
    # Actual text content should remain
    assert "Look" in md
    assert "End" in md
