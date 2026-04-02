"""Gmail API payload helpers — extract body text and convert to markdown."""

import base64
import re
from typing import Any

import markdownify


def _get_charset(part: dict[str, Any]) -> str:
    """Extract charset from Content-Type header in a Gmail API part, default utf-8."""
    headers = part.get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "content-type":
            value = h.get("value", "")
            match = re.search(r"charset=([^\s;]+)", value, re.IGNORECASE)
            if match:
                return match.group(1).strip('"').strip("'")
    return "utf-8"


def _is_attachment(part: dict[str, Any]) -> bool:
    """Check whether a MIME part is an attachment (not inline body text)."""
    if part.get("filename"):
        return True
    headers = part.get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "content-disposition":
            if "attachment" in h.get("value", "").lower():
                return True
    return False


def _decode_body(part: dict[str, Any]) -> str:
    """Decode the base64url body data of a Gmail API part to a string."""
    body = part.get("body", {})
    data = body.get("data")
    if not data:
        return ""
    raw_bytes = base64.urlsafe_b64decode(data)
    charset = _get_charset(part)
    try:
        return raw_bytes.decode(charset)
    except (UnicodeDecodeError, LookupError):
        return raw_bytes.decode("utf-8", errors="replace")


def extract_body(payload: dict[str, Any]) -> tuple[str, str]:
    """Recursively walk a Gmail API message payload and return (plain_text, html).

    Skips attachment parts. Collects the first text/plain and text/html found.
    """
    plain = ""
    html = ""

    def _walk(part: dict[str, Any]) -> None:
        nonlocal plain, html

        mime_type = part.get("mimeType", "")

        # Recurse into multipart containers
        if mime_type.startswith("multipart/"):
            for sub in part.get("parts", []):
                _walk(sub)
            return

        # Skip attachments
        if _is_attachment(part):
            return

        if mime_type == "text/plain" and not plain:
            plain = _decode_body(part)
        elif mime_type == "text/html" and not html:
            html = _decode_body(part)

    if payload:
        _walk(payload)

    return plain, html


def _strip_cid_and_data_images(html: str) -> str:
    """Remove <img> tags whose src is a cid: reference or data: URI."""
    return re.sub(
        r'<img\s[^>]*src=["\'](?:cid:|data:)[^"\']*["\'][^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )


def _is_only_comments(html: str) -> bool:
    """Return True if the HTML string contains only HTML comments and whitespace."""
    stripped = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL).strip()
    return stripped == ""


def body_to_markdown(plain: str, html: str) -> str:
    """Pick plain text if available; otherwise convert HTML to markdown.

    Treats HTML that is only comments (e.g. ``<!--placeholder-->``) as empty.
    """
    if plain:
        return plain

    if not html or _is_only_comments(html):
        return ""

    cleaned = _strip_cid_and_data_images(html)
    return markdownify.markdownify(cleaned).strip()
