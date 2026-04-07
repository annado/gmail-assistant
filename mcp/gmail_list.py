"""Gmail API operation — list messages by search query."""

from typing import Any

from gmail_helpers import handle_error, get_header


def list_messages(service: Any, query: str, max_results: int = 10) -> str:
    """Search Gmail and return matching messages as formatted lines.

    Each line: "{message_id} | {subject} | {sender} | {date}"
    Returns a descriptive string on error (never raises).
    """
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            return "No messages found."

        lines = []
        for msg_stub in messages:
            msg_id = msg_stub["id"]
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
            subject = get_header(msg, "subject") or "(no subject)"
            sender = get_header(msg, "from") or "(unknown sender)"
            date = get_header(msg, "date") or "(no date)"
            lines.append(f"{msg_id} | {subject} | {sender} | {date}")

        return "\n".join(lines)
    except Exception as exc:
        return handle_error(exc, "list")
