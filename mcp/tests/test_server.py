"""Tests for the Gmail MCP server (server.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import Client

from server import mcp


@pytest.mark.asyncio
async def test_tools_are_registered():
    """MCP server lists both tools with descriptions."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        assert "gmail_mark_as_read" in tool_names
        assert "gmail_fetch_body" in tool_names
        # Check descriptions exist
        for t in tools:
            assert t.description, f"Tool {t.name} has no description"


@pytest.mark.asyncio
@patch("server.get_service")
@patch("server.get_credentials")
@patch("server.mark_as_read")
async def test_mark_as_read_tool(mock_mark, mock_creds, mock_svc):
    """Calling gmail_mark_as_read invokes the right function and returns result."""
    mock_creds.return_value = MagicMock()
    mock_svc.return_value = MagicMock()
    mock_mark.return_value = '✓ Marked as read: "Test Subject" (msg123)'

    async with Client(mcp) as client:
        result = await client.call_tool("gmail_mark_as_read", {"message_id": "msg123"})
        assert result.content[0].text == '✓ Marked as read: "Test Subject" (msg123)'
        mock_mark.assert_called_once_with(mock_svc.return_value, "msg123")


@pytest.mark.asyncio
@patch("server.get_service")
@patch("server.get_credentials")
@patch("server.fetch_body")
async def test_fetch_body_tool(mock_fetch, mock_creds, mock_svc):
    """Calling gmail_fetch_body returns markdown content."""
    mock_creds.return_value = MagicMock()
    mock_svc.return_value = MagicMock()
    mock_fetch.return_value = "# Hello\n\nThis is a test email."

    async with Client(mcp) as client:
        result = await client.call_tool("gmail_fetch_body", {"message_id": "msg456"})
        assert result.content[0].text == "# Hello\n\nThis is a test email."
        mock_fetch.assert_called_once_with(mock_svc.return_value, "msg456")


@pytest.mark.asyncio
@patch("server.get_service")
@patch("server.get_credentials")
@patch("server.mark_as_read")
async def test_tool_invalid_message_id(mock_mark, mock_creds, mock_svc):
    """Invalid message ID returns error string, not exception."""
    mock_creds.return_value = MagicMock()
    mock_svc.return_value = MagicMock()
    mock_mark.return_value = "Error: message bad_id not found"

    async with Client(mcp) as client:
        result = await client.call_tool("gmail_mark_as_read", {"message_id": "bad_id"})
        assert "Error" in result.content[0].text
        assert "bad_id" in result.content[0].text


@pytest.mark.asyncio
@patch("server.get_service")
@patch("server.get_credentials")
@patch("server.fetch_body")
async def test_tool_api_failure(mock_fetch, mock_creds, mock_svc):
    """Underlying API error surfaces as error string through MCP."""
    mock_creds.return_value = MagicMock()
    mock_svc.return_value = MagicMock()
    mock_fetch.return_value = "Error: Gmail API returned 500: Internal Server Error"

    async with Client(mcp) as client:
        result = await client.call_tool("gmail_fetch_body", {"message_id": "msg789"})
        assert "Error" in result.content[0].text
        assert "500" in result.content[0].text


# ---------- new v0.2 tools ----------


@pytest.mark.asyncio
async def test_new_tools_are_registered():
    """MCP server lists the v0.2 tools."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        assert "gmail_list_messages" in tool_names


@pytest.mark.asyncio
@patch("server.get_service")
@patch("server.get_credentials")
@patch("server.list_messages")
async def test_list_messages_tool(mock_list, mock_creds, mock_svc):
    """Calling gmail_list_messages invokes list_messages and returns result."""
    mock_creds.return_value = MagicMock()
    mock_svc.return_value = MagicMock()
    mock_list.return_value = "msg1 | Test Subject | sender@test.com | Mon, 1 Apr 2026"

    async with Client(mcp) as client:
        result = await client.call_tool(
            "gmail_list_messages", {"query": "from:school.edu", "max_results": 5}
        )
        assert "msg1" in result.content[0].text
        mock_list.assert_called_once_with(mock_svc.return_value, "from:school.edu", 5)


