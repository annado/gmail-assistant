"""Email caching — save fetched emails as local markdown files."""

import email.utils
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gmail_helpers import extract_body, body_to_markdown, handle_error, get_header

EMAILS_DIR = Path(__file__).parent / "emails"


def find_cached(message_id: str) -> Path | None:
    """Find a cached email file by message ID. Returns path if found, None if not."""
    matches = list(EMAILS_DIR.glob(f"**/{message_id}.md"))
    return matches[0] if matches else None


def read_cached(message_id: str) -> str | None:
    """Read a cached email's markdown content (body only, no frontmatter)."""
    path = find_cached(message_id)
    if path is None:
        return None
    try:
        text = path.read_text()
    except OSError:
        return None
    # Strip YAML frontmatter
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def _parse_year_month(date_str: str) -> tuple[str, str]:
    """Parse year and month from an email date header. Falls back to current date."""
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return f"{dt.year}", f"{dt.month:02d}"
    except (ValueError, TypeError):
        now = datetime.now(timezone.utc)
        return f"{now.year}", f"{now.month:02d}"


def save_email(service: Any, message_id: str) -> Path:
    """Fetch an email from Gmail and save as a markdown file. Returns the file path.

    If already cached, returns the existing path without re-fetching.
    """
    cached = find_cached(message_id)
    if cached is not None:
        return cached

    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    subject = get_header(msg, "subject") or "(no subject)"
    sender = get_header(msg, "from") or "(unknown sender)"
    date = get_header(msg, "date") or ""

    payload = msg.get("payload", {})
    plain, html = extract_body(payload)
    body = body_to_markdown(plain, html) or "(no body content)"

    year, month = _parse_year_month(date)
    path = EMAILS_DIR / year / month / f"{message_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = (
        f"---\n"
        f"id: {message_id}\n"
        f"subject: {subject}\n"
        f"from: {sender}\n"
        f"date: {date}\n"
        f"---\n\n"
    )
    path.write_text(frontmatter + body)

    return path


def ensure_cached(service: Any, message_ids: list[str]) -> list[Path]:
    """Ensure all given message IDs are cached locally. Returns list of file paths."""
    paths = []
    for msg_id in message_ids:
        try:
            paths.append(save_email(service, msg_id))
        except Exception as exc:
            # Log the error but continue with other messages
            error_msg = handle_error(exc, msg_id)
            # Create an error placeholder file so the caller gets a path
            year, month = _parse_year_month("")
            path = EMAILS_DIR / year / month / f"{msg_id}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"---\n"
                f"id: {msg_id}\n"
                f"subject: (fetch failed)\n"
                f"from: unknown\n"
                f"date: \n"
                f"---\n\n"
                f"{error_msg}\n"
            )
            paths.append(path)
    return paths
