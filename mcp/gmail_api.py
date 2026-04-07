"""Gmail API operations — mark_as_read and fetch_body.

Every public function returns a descriptive string and never raises exceptions.
"""

from typing import Any

from gmail_helpers import extract_body, body_to_markdown, handle_error, get_header
from gmail_cache import find_cached, read_cached, save_email


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
        subject = get_header(msg, "subject") or "(no subject)"

        return f'\u2713 Marked as read: "{subject}" ({message_id})'
    except Exception as exc:
        return handle_error(exc, message_id)


def fetch_body(service: Any, message_id: str) -> str:
    """Fetch a message and return its body as markdown. Uses local cache if available."""
    try:
        cached = read_cached(message_id)
        if cached is not None:
            return cached

        save_email(service, message_id)
        cached = read_cached(message_id)
        if cached is not None:
            return cached

        return "(no body content)"
    except Exception as exc:
        return handle_error(exc, message_id)
