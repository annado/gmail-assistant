# TODOs

Deferred work and improvements not yet scheduled into a versioned plan.

## Add `gmail_cache_email` tool returning file path

**Why:** `gmail_fetch_body` currently returns the email body string over MCP. For the school-emails skill, this means ~50KB per email rides through the MCP result channel on every run, even though the body already lives on disk in `emails/YYYY/MM/{id}.md`. The original v0.4 design said skills should use the cached file paths and read them directly via the Read tool.

**Proposed change:**
- Add a new MCP tool `gmail_cache_email(message_id) -> str` that ensures the email is cached and returns the absolute file path (does not return the body).
- Keep `gmail_fetch_body` for ad-hoc / one-shot uses that want the body inline.
- Update `skills/school-emails/SKILL.md` to call `gmail_cache_email` and then use the Read tool on the returned paths.

**Files to touch:**
- `mcp/server.py` — add new tool
- `mcp/gmail_api.py` — add `cache_email(service, message_id) -> str` (path)
- `mcp/tests/test_api.py` — tests for new function
- `mcp/tests/test_server.py` — tool registration test
- `skills/school-emails/SKILL.md` — switch from `gmail_fetch_body` to `gmail_cache_email` + Read

**Trade-offs:** Adds one new tool to the MCP surface area but no breaking change. Skill workflow becomes two-step (cache then Read) instead of one MCP call.
