# gmail-assistant

An MCP server that provides Gmail utility tools for Claude Code, complementing the built-in Claude.ai Gmail integration.

## What it does

The built-in Claude.ai Gmail MCP handles search, listing, reading message snippets, drafts, and labels. This server fills the gaps:

- **`gmail_mark_as_read`** — Mark a message as read by message ID.
- **`gmail_fetch_body`** — Fetch a message's full body as markdown, handling HTML newsletters and multipart MIME.

## Setup

1. Install dependencies:

   ```
   uv sync
   ```

2. Authenticate with Gmail (creates `token.json`):

   ```
   uv run gmail_auth.py
   ```

3. Run the server:

   ```
   uv run server.py
   ```

## Development

Run tests:

```
uv run pytest
```
