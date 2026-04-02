"""Gmail MCP server — exposes gmail_mark_as_read and gmail_fetch_body as tools."""

from fastmcp import FastMCP

from gmail_auth import get_credentials, get_service
from gmail_api import mark_as_read, fetch_body

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


if __name__ == "__main__":
    mcp.run()
