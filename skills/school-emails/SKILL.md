---
name: school-emails
description: Summarize recent school emails with personal context about your children
allowed-tools: "mcp__gmail-assistant__gmail_list_messages mcp__gmail-assistant__gmail_fetch_body mcp__gmail-assistant__gmail_mark_as_read Read Write Glob"
---

# School Email Summary

Summarize recent school emails using personal context about the user's children.

## Steps

1. **Load personal context** — Read `context.toml` from this skill's directory for children's names, grades, schools, teachers, and activities.

2. **Find school emails** — Use `gmail_list_messages` to search for recent unread school emails. Build a single query per school by OR-ing the `school_from` addresses in context.toml using Gmail's `{...}` OR syntax:
   - `{from:synapseschool.org from:synapseschoolorg.myenotice.com} is:unread newer_than:7d`
   - Deduplicate message IDs across schools if addresses overlap.

3. **Fetch email bodies** — Call `gmail_fetch_body` for each message ID returned. This caches emails as local markdown files automatically.

4. **Read cached emails** — Use the Read tool to read each cached email file. Files are stored under `emails/` in the project root as `emails/YYYY/MM/{message_id}.md`.

5. **Read summary instructions** — Read `prompt.md` from this skill's directory for formatting guidance.

6. **Write summary** — Summarize all emails into a single file: `school-summary-YYYY-MM-DD.md` in the project root. Use today's date. Apply the personal context so the summary references the right child, grade, teacher, or activity when relevant.

7. **Mark as read** (optional) — If the user asks, call `gmail_mark_as_read` for each summarized message.
