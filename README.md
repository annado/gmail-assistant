# gmail-assistant

An MCP server that provides Gmail utility tools for Claude Code, plus Claude Code skills for email management workflows.

## What it does

### MCP server (`mcp/`)

Gmail actions Claude can't do natively. Complements the built-in Claude.ai Gmail integration (which handles drafts, labels, and basic search/read).

- **`gmail_mark_as_read`** — Mark a message as read by message ID.
- **`gmail_fetch_body`** — Fetch a message's full body as markdown. Caches results to `emails/YYYY/MM/{id}.md` to avoid re-fetching and to bypass MCP result size limits.
- **`gmail_list_messages`** — Search Gmail with standard query syntax (`from:`, `is:unread`, `newer_than:`, etc.) and return `id | subject | sender | date` lines.

### Skills (`skills/`)

Claude Code skills that orchestrate the MCP tools into higher-level workflows.

- **`/school-emails`** — Summarize recent school emails into a dated markdown file, using personal context (children, grades, teachers) from a local `context.toml`.

## Setup

1. Install dependencies:

   ```
   uv sync
   ```

2. Place Gmail OAuth credentials at `mcp/credentials.json` (download from Google Cloud Console — Desktop App OAuth client). On first run, the server will open a browser for authentication and write `mcp/token.json`.

3. Configure the MCP server in your project's `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "gmail-assistant": {
         "command": "uv",
         "args": ["run", "--directory", "/path/to/gmail-assistant/mcp", "python", "server.py"]
       }
     }
   }
   ```

## Installing skills

Skills live in `skills/` as a source directory. Symlink any skill into Claude Code's discovery path:

```bash
ln -s /path/to/gmail-assistant/skills/school-emails ~/.claude/skills/school-emails
```

For `/school-emails`, copy the example context and fill in your details:

```bash
cp skills/school-emails/context.example.toml skills/school-emails/context.toml
$EDITOR skills/school-emails/context.toml
```

Run `/reload-plugins` if Claude Code is already running. Invoke with `/school-emails`.

## Development

Run tests:

```
uv run python -m pytest mcp/tests/ -v
```

## Layout

```
gmail-assistant/
├── mcp/                    # MCP server + Gmail API modules + tests
├── skills/                 # Claude Code skills
│   └── school-emails/
├── emails/                 # (git-ignored) cached email markdown
└── docs/                   # Plans, TODOs, version notes
```
