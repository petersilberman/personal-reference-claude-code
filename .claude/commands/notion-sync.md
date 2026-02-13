# Notion Sync Command

Bidirectional sync between Notion pages and local Markdown files.

**See `.claude/skills/sync-protocol.md` for shared sync patterns** (direction parsing, conflict detection, AI merge flow, watermark format, error handling).

## Usage

```
/notion-sync <source> <destination>
/notion-sync <file-with-watermark>
```

**Direction determined by argument order:**
- `notion-url file.md` → Notion → Markdown (download)
- `file.md notion-url` → Markdown → Notion (upload)
- Single arg: reads `notion_url` from frontmatter, syncs back to Notion

## Arguments

$ARGUMENTS

## Instructions

### 1. Parse Arguments & Determine Direction

Use the direction parsing pattern from `sync-protocol.md` with:
- Service domain: `notion.so`
- Watermark field: `notion_url`

### 2. Fetch Both Versions

**Fetch Notion content:**
```
notion_data = mcp__Notion__notion-fetch(id=notion_url)
notion_page_id = extract_page_id(notion_url)
notion_text = notion_data.text
notion_title = notion_data.title
```

**Fetch local content (if exists):**
```
if file_path exists:
    local_content = Read(file_path)
    local_frontmatter = parse_yaml_frontmatter(local_content)
    local_body = content after frontmatter
else:
    local_content = None
    local_frontmatter = {}
```

### 3. Detect Conflict

Use the conflict detection pattern from `sync-protocol.md` with watermark fields: `notion_content_hash`, `notion_last_sync`.

### 4. Handle Sync

**Case A: No Conflict → Direct Sync**

**If `notion_to_markdown`:**
1. Convert Notion content to Markdown (see Section 5)
2. Download images (see Section 6)
3. Create frontmatter watermark (see `sync-protocol.md` for format, use `notion_` prefix)
4. Write to file_path
5. Report success with title, image count, line count

**If `markdown_to_notion`:**
1. Convert Markdown to Notion format (see Section 7)
2. Upload images if local (see Section 8)
3. Update Notion page using `mcp__Notion__notion-update`
4. Update local frontmatter with new sync timestamp and hash
5. Report success with page URL, sections updated

**Case B: Conflict → AI Merge**

Follow the AI merge flow from `sync-protocol.md`.

### 5. Convert Notion → Markdown

Parse the Notion-flavored Markdown from `notion_data.text`:

**Block conversions:**
- `<page url="...">` tags → Extract content, ignore page structure
- `<synced_block_reference>` → Flatten children inline
- `<callout icon="..." color="...">` → Blockquote with icon
- `<image source="...">Caption</image>` → `![Caption](relative-path)` (download image)
- `<mention-page url="...">Title</mention-page>` → `<!-- notion-page: {page_id} -->`
- `<mention-user url="...">Name</mention-user>` → `@Name`
- `<mention-date start="...">` → Plain date text
- `<empty-block/>` → Remove (not needed in Markdown)

**Rich text conversions:**
- `**bold**` → keep as-is
- `*italic*` → keep as-is
- `~~strikethrough~~` → keep as-is
- `<span underline="true">text</span>` → `<u>text</u>`
- `<span color="...">text</span>` → Plain text (Markdown doesn't support colors)
- `` `code` `` → keep as-is
- `[text](url)` → keep as-is
- `$equation$` → keep as-is

**URL cleanup:**
- `{{URL}}` → `URL` (unwrap compressed URL syntax)
- `{{https://example.com}}` → `https://example.com`

### 6. Download Images (Notion → Markdown)

For each `<image source="...">` tag:

1. **Extract image URL:**
   ```
   url = image.source attribute
   caption = image inner text
   ```

2. **Create images directory:**
   ```
   base_name = file_path without extension
   images_dir = "{base_name}.images/"
   mkdir -p images_dir
   ```

3. **Generate filename:**
   - Try to extract meaningful name from URL
   - Fall back to `image-{sequence}.{ext}`
   - Preserve extension from URL or Content-Type

4. **Download using curl:**
   ```bash
   curl -sL -o "{images_dir}/{filename}" "{url}"
   ```

5. **Verify download:**
   - Check file exists and size > 0
   - If failed: log warning, continue with other images

6. **Rewrite markdown:**
   ```markdown
   ![{caption}]({base_name}.images/{filename})
   ```

### 7. Convert Markdown → Notion (Future Enhancement)

**Note:** Initial implementation focuses on Notion → Markdown. Markdown → Notion conversion is a future enhancement.

For now, when `markdown_to_notion` is requested:
- Use `mcp__Notion__notion-update` with the markdown content
- Notion API will handle basic markdown → blocks conversion
- Images: warn if local paths detected (not yet supported)

**Future:** Implement full conversion:
- Parse frontmatter and remove before sending
- Convert standard Markdown to Notion blocks
- Upload local images to Notion
- Handle special Obsidian syntax (tags, links, embeds)

### 8. Handle Local Images (Markdown → Notion)

**Current behavior:**
- Detect `![caption](local-path)` references
- Warn: "⚠️  Local images detected. Upload to Notion manually or use hosted URLs."
- Continue sync without images

**Future enhancement:**
- Upload images to Notion using API
- Replace local paths with Notion CDN URLs
- Update local markdown with new URLs

### 9. Insert Conflict Marker

Use conflict marker format from `sync-protocol.md` with service label: `NOTION`.

### 10. Error Handling

Use error handling pattern from `sync-protocol.md`.

### 11. Success Output

Use success output pattern from `sync-protocol.md`.

## Example Sessions

### Session 1: Initial Download

```
User: /notion-sync https://notion.so/Onboarding-a1b2c3d4 tmp/onboarding.md

Claude: Fetching Notion page...
Found page: "Team Onboarding Guide"
Downloading 3 images...

✅ Synced from Notion → tmp/onboarding.md

Downloaded 3 images to tmp/onboarding.images/
125 lines written
```

### Session 2: Update After Local Edits

```
User: /notion-sync tmp/onboarding.md

Claude: Reading tmp/onboarding.md...
Notion page: https://notion.so/Onboarding-a1b2c3d4

Checking for conflicts...
No conflicts detected (Notion unchanged since last sync)

✅ Synced from tmp/onboarding.md → Notion

Updated: https://notion.so/Onboarding-a1b2c3d4
```

### Session 3: Conflict Resolution

```
User: /notion-sync tmp/spec.md

Claude: Reading tmp/spec.md...
Notion page: https://notion.so/Product-Spec-abc123

⚠️  Conflict detected - both versions changed since last sync

Analyzing differences...

📝 Merge Preview:

SECTION: Overview
  ├─ Notion added: "Updated Q2 timeline"
  └─ Local added: "Added security requirements"
  → Merged: Both additions included

SECTION: Architecture
  └─ Local only: Refactored diagram description
  → Keeping local version

Accept this merge? [User selects: Yes, apply merge]

✅ Merge approved and applied

Synced from tmp/spec.md → Notion
```

## Limitations

1. **Images:**
   - Notion → MD: ✅ Downloads and converts
   - MD → Notion: ⚠️ Local images not yet uploaded (future)

2. **Notion blocks:**
   - Only converts common block types
   - Advanced blocks (databases, embeds) converted to placeholders

3. **Bidirectional links:**
   - Notion page mentions converted to comments
   - No automatic resolution of Obsidian [[wikilinks]]

4. **Formatting:**
   - Some Notion colors/styling lost in conversion
   - Markdown is plain text priority

5. **Concurrent edits:**
   - No locking mechanism
   - Last sync wins (with conflict detection)

## Future Enhancements

1. **Image upload** (MD → Notion)
2. **Bulk sync** (sync entire folder of pages)
3. **Watch mode** (auto-sync on file changes)
4. **Conflict visualization** (side-by-side diff view)
5. **Partial sync** (sync only changed sections)
6. **Database sync** (Notion database ↔ folder of MD files)
