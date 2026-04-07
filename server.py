"""Gmail MCP server — exposes Gmail tools for Claude."""

from fastmcp import FastMCP

from gmail_auth import get_credentials, get_service
from gmail_api import mark_as_read, fetch_body
from gmail_list import list_messages
from gmail_school import prepare_school_summary
from context_config import load_context

mcp = FastMCP(name="gmail-assistant")


@mcp.tool
async def gmail_mark_as_read(message_id: str) -> str:
    """Mark a Gmail message as read given its message ID. Returns confirmation with the email subject."""
    creds = get_credentials("token.json", "credentials.json")
    service = get_service(creds)
    return mark_as_read(service, message_id)


@mcp.tool
async def gmail_fetch_body(message_id: str) -> str:
    """Fetch a Gmail message body as markdown given its message ID. Handles HTML newsletters and multipart MIME."""
    creds = get_credentials("token.json", "credentials.json")
    service = get_service(creds)
    return fetch_body(service, message_id)


@mcp.tool
async def gmail_list_messages(query: str, max_results: int = 10) -> str:
    """Search Gmail and return matching messages as 'id | subject | sender | date' lines.
    Accepts standard Gmail search syntax (e.g. 'from:school.edu is:unread')."""
    creds = get_credentials("token.json", "credentials.json")
    service = get_service(creds)
    return list_messages(service, query, max_results)


@mcp.tool
async def gmail_summarize_school_emails(message_ids: list[str]) -> str:
    """Fetch multiple school emails with personal context (child grade, teachers, activities).
    Pass all related school emails together so Claude can write one holistic parent summary."""
    creds = get_credentials("token.json", "credentials.json")
    service = get_service(creds)
    context = load_context()
    return prepare_school_summary(service, message_ids, context)


if __name__ == "__main__":
    mcp.run()
