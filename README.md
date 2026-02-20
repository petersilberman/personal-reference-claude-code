# Personal Reference for Claude Code

Reference implementation for bidirectional sync between a local markdown vault and cloud services (Google Docs, Notion, Google Tasks). Companion code for the blog series on my personal AI setup and use of Claude Code.

You can read those [blogs](https://petercto.substack.com/)

> **Note:** This repo is a reference companion to the [How I AI](https://petercto.substack.com/) blog series — not a supported framework. It's here to show what's possible and inspire your own setup. You will likely hit edge cases or bugs. That's expected. Take what's useful, adapt it to your workflow, and build something that works for you.

## What's Here

```
.claude/
├── commands/
│   ├── gdoc-sync.md            # /gdoc-sync command
│   ├── notion-sync.md          # /notion-sync command
│   └── sync-tasks.md           # /sync-tasks command
└── skills/
    └── sync-protocol.md        # Shared sync patterns

assets/
└── scripts/
    ├── google_docs_mcp.py      # Custom Google Docs MCP server
    └── google_calendar_mcp.py  # Custom Google Calendar & Tasks MCP server

capture/
└── google-tasks-inbox.md       # Landing zone for tasks pulled from Google

TASKS.md                        # Tasks dashboard with Obsidian query blocks
```

### Vault Files

This repo includes two files that mirror a real Obsidian vault layout:

- **`TASKS.md`** — A tasks dashboard at the vault root. Uses [Obsidian Tasks](https://publish.obsidian.md/tasks/Introduction) query blocks to aggregate tasks from across the vault, organized by person (`#alice`, `#bob`, etc.) and by type (`#output`, `#convo`). The person hashtags are the routing mechanism — tag a task `#alice` and it automatically shows up in Alice's section. No manual filing.

- **`capture/google-tasks-inbox.md`** — The landing zone where `/sync-tasks pull` drops new tasks from Google. Tasks sit here temporarily until you triage them into the right files (1-1 notes, project docs, etc.). Each task carries a `^gtask-{id}` block reference that links it back to Google Tasks for bidirectional sync.

## Commands

### `/gdoc-sync`

Bidirectional sync between Google Docs and local Markdown.

```bash
# Download: Google Docs → Markdown
/gdoc-sync https://docs.google.com/document/d/1abc123/edit docs/spec.md

# Upload: Markdown → Google Docs
/gdoc-sync docs/spec.md https://docs.google.com/document/d/1abc123/edit

# Re-sync (uses frontmatter URL)
/gdoc-sync docs/spec.md
```

### `/notion-sync`

Bidirectional sync between Notion and local Markdown.

```bash
# Download: Notion → Markdown
/notion-sync https://notion.so/Page-abc123 docs/spec.md

# Upload: Markdown → Notion
/notion-sync docs/spec.md https://notion.so/Page-abc123

# Re-sync
/notion-sync docs/spec.md
```

### `/sync-tasks`

Bidirectional sync between Obsidian tasks and Google Tasks.

```bash
# Pull new tasks from Google → capture/google-tasks-inbox.md
/sync-tasks pull

# Push completed tasks from Obsidian → Google
/sync-tasks push

# Full bidirectional sync (pull then push)
/sync-tasks sync

# Show sync status
/sync-tasks status
```

**Hashtag routing pattern:** Tasks captured from Google get routed via `#person` hashtags. A task tagged `#alice` shows up in Alice's section of `TASKS.md` via Obsidian Tasks query blocks. No manual filing needed — the tag IS the routing.

**Completion is sticky:** Once a task is marked complete on either side, sync propagates it but never reopens it. This prevents ping-pong conflicts.

## MCP Servers

### Google Docs MCP (`google_docs_mcp.py`)

Custom MCP server providing:

- `fetch_google_doc` - Fetch a Google Doc as Markdown with images
- `get_google_doc_metadata` - Get doc metadata without fetching content
- `update_google_doc` - Update a Google Doc from Markdown

**Setup:**

1. Enable Google Drive and Google Docs APIs in [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials (Desktop application)
3. Download `credentials.json` to `assets/scripts/`
4. Install dependencies: `pip install fastmcp google-api-python-client google-auth-oauthlib markdownify beautifulsoup4`
5. Run: `python assets/scripts/google_docs_mcp.py`

First run will prompt for OAuth authorization.

### Google Calendar & Tasks MCP (`google_calendar_mcp.py`)

Custom MCP server providing:

- `list_calendars` / `list_events` / `get_event` / `search_events` - Calendar read access
- `get_free_busy` - Check availability across calendars
- `list_tasks` / `get_task` / `create_task` / `update_task` - Task management
- `complete_task` / `uncomplete_task` / `delete_task` - Task status changes
- `get_sync_mapping` / `link_task` - Obsidian ↔ Google Tasks sync tracking

**Setup:**

1. Enable Google Calendar API and Google Tasks API in [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials (Desktop application)
3. Download `credentials.json` to `assets/scripts/`
4. Install dependencies: `pip install fastmcp google-api-python-client google-auth-oauthlib`
5. Run: `python assets/scripts/google_calendar_mcp.py`

First run will prompt for OAuth authorization. The server maintains a `task_sync_mapping.json` file (gitignored) to track which Obsidian block IDs correspond to which Google Task IDs.

### Notion MCP

Uses the [official Notion MCP server](https://github.com/notionhq/notion-mcp-server):

```bash
npx -y @notionhq/notion-mcp-server
```

## The Watermark Pattern

The gdoc-sync and notion-sync commands use "watermarked sync" — storing a content hash in the file's frontmatter:

```yaml
---
gdoc_url: https://docs.google.com/document/d/1abc/edit
gdoc_doc_id: 1abc
gdoc_last_sync: 2026-01-22T14:30:00Z
gdoc_content_hash: sha256:a3f5c8d9...
gdoc_last_modified: 2026-01-22T14:30:00Z
---
```

This enables conflict detection:

- Local changed, remote didn't → Push
- Remote changed, local didn't → Pull
- Both changed → Conflict (AI-assisted merge)

## Blog Series

This code accompanies the "How I AI" blog series:

- [Post 1: Foundation (directory structure)](https://petercto.substack.com/p/the-foundation-your-filesystem-and)
- [Post 2: Sync Gdoc / Notion](https://petercto.substack.com/p/sync-bringing-collaboration-to-your)
- [Post 3: Task Routing]() — Bidirectional Google Tasks ↔ Obsidian sync with hashtag routing
