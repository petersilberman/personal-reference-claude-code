# Personal Reference for Claude Code

Reference implementation for bidirectional sync between local markdown files and cloud services (Google Docs, Notion). Companion code for the blog series on my personal AI setup and use of Claude Code. 

You can read those [blogs](https://petercto.substack.com/)

> **Note:** This repo is a reference companion to the [How I AI](https://petercto.substack.com/) blog series — not a supported framework. It's here to show what's possible and inspire your own setup. You will likely hit edge cases or bugs. That's expected. Take what's useful, adapt it to your workflow, and build something that works for you.

## What's Here

```
.claude/
├── commands/
│   ├── gdoc-sync.md      # /gdoc-sync command
│   └── notion-sync.md    # /notion-sync command
└── skills/
    └── sync-protocol.md  # Shared sync patterns

assets/
└── scripts/
    └── google_docs_mcp.py  # Custom Google Docs MCP server
```

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

### Notion MCP

Uses the [official Notion MCP server](https://github.com/notionhq/notion-mcp-server):

```bash
npx -y @notionhq/notion-mcp-server
```

## The Watermark Pattern

Both commands use "watermarked sync" — storing a content hash in the file's frontmatter:

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
- [Post 2: Sync Gdoc / Notion]()
- Post 3: Task Routing
