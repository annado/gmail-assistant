"""Gmail API operations — mark_as_read and fetch_body.

Every public function returns a descriptive string and never raises exceptions.
"""

from typing import Any

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from gmail_helpers import extract_body, body_to_markdown


def _get_subject(message: dict[str, Any]) -> str:
    """Extract the Subject header from a Gmail API message dict."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "subject":
            return h.get("value", "(no subject)")
    return "(no subject)"


def _handle_error(err: Exception, message_id: str) -> str:
    """Convert known exceptions to user-friendly error strings."""
    if isinstance(err, HttpError):
        status = err.resp.status
        if status == 404:
            return f"Error: message {message_id} not found"
        if status == 429:
            return "Error: Gmail rate limit hit. Try again shortly."
        detail = err.content.decode("utf-8", errors="replace") if err.content else err.reason
        return f"Error: Gmail API returned {status}: {detail}"
    if isinstance(err, RefreshError):
        return "Authentication expired. Re-run gmail_auth.py to re-authorize."
    if isinstance(err, ConnectionError):
        return "Error: could not reach Gmail API. Check network."
    return f"Error: {err}"


def mark_as_read(service: Any, message_id: str) -> str:
    """Remove the UNREAD label from a message. Returns a descriptive string."""
    try:
        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        # Fetch subject for the confirmation message
        msg = service.users().messages().get(
            userId="me", id=message_id, format="metadata", metadataHeaders=["Subject"]
        ).execute()
        subject = _get_subject(msg)

        return f'\u2713 Marked as read: "{subject}" ({message_id})'
    except Exception as exc:
        return _handle_error(exc, message_id)


def fetch_body(service: Any, message_id: str) -> str:
    """Fetch a message and return its body as markdown."""
    try:
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        payload = msg.get("payload", {})
        plain, html = extract_body(payload)
        md = body_to_markdown(plain, html)

        if not md.strip():
            return "(no body content)"

        return md
    except Exception as exc:
        return _handle_error(exc, message_id)
