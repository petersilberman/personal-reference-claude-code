# Bidirectional Sync Protocol

Shared patterns for bidirectional sync between cloud services and local Markdown files. Used by `/gdoc-sync`, `/notion-sync`, and future sync commands.

## Direction Parsing

```
if args.length == 1:
    file_path = args[0]
    read frontmatter from file_path
    if no {service}_url in frontmatter:
        ERROR: "No {service}_url in frontmatter. Use two-arg form."
    service_url = frontmatter.{service}_url
    direction = "markdown_to_{service}"

elif args.length == 2:
    if args[0] is URL (starts with "http" or contains service domain):
        direction = "{service}_to_markdown"
        service_url = args[0]
        file_path = args[1]
    elif args[0] ends with ".md" or is local path:
        direction = "markdown_to_{service}"
        file_path = args[0]
        service_url = args[1]
    else:
        ERROR: "Could not determine direction."
else:
    ERROR: "Usage: /{service}-sync <source> <destination> or /{service}-sync <file>"
```

## Watermark Format

```yaml
---
{service}_url: {full_url}
{service}_id: {document_id}
{service}_last_sync: {ISO8601_timestamp}
{service}_content_hash: sha256:{hash_of_content}
{service}_last_modified: {service_last_modified_time}
---
```

**Field purposes:**
- `{service}_url` - Human-readable URL for reference
- `{service}_id` - API identifier for programmatic access
- `{service}_last_sync` - When this sync occurred (for conflict detection)
- `{service}_content_hash` - Hash of service content at sync time (for detecting service-side changes)
- `{service}_last_modified` - Service's reported modification time

## Conflict Detection

Only check when syncing FROM local TO service AND file has watermark:

```
if direction == "markdown_to_{service}" AND frontmatter.{service}_url exists:
    # Check if service changed since last sync
    current_hash = sha256(service_content)
    stored_hash = frontmatter.{service}_content_hash
    service_changed = (current_hash != stored_hash)

    # Check if local changed since last sync
    file_mtime = os.stat(file_path).st_mtime
    last_sync = parse_iso8601(frontmatter.{service}_last_sync)
    local_changed = (file_mtime > last_sync)

    CONFLICT = service_changed AND local_changed
else:
    CONFLICT = False
```

## AI Merge Flow

**Step 1: Present Conflict**
```
⚠️  Conflict Detected

Both {service} and local file changed since last sync:
- {Service} last modified: {time}
- Local file modified: {time}
- Last sync: {time}

Attempting intelligent merge...
```

**Step 2: Synthesize Merge**
- Identify sections changed only in service → keep service
- Identify sections changed only in local → keep local
- Identify sections changed in both → intelligently merge

**Step 3: Present Preview**
```
📝 Merge Preview

SECTION: {section_name}
  ├─ {Service}: {change_description}
  └─ Local: {change_description}
  → Merged: {merge_strategy}

[... repeat for each section ...]
```

**Step 4: Ask Approval (AskUserQuestion)**
```
Question: "Accept this merge?"
Options:
- "Yes, apply merge"
- "No, insert conflict marker"
```

**Step 5: Handle Response**
- Approved: Apply merged content, update watermark, report success
- Rejected: Insert conflict marker, report manual resolution needed

## Conflict Marker Format

**In Markdown file:**
```markdown
<!-- SYNC-CONFLICT: {timestamp} -->
<!-- Unable to auto-merge. Resolve manually and remove this block. -->

<<<<<<< {SERVICE_NAME}
{content from service version}
=======
{content from local version}
>>>>>>> LOCAL

<!-- /SYNC-CONFLICT -->
```

**In service document (if destination):**
- Insert warning at top:
  ```
  ⚠️ SYNC CONFLICT ({timestamp})

  Unable to auto-merge with local file.
  See local file for full diff.
  ```

**Next sync behavior:**
- Before any sync, check for conflict markers
- If found: ERROR: "Unresolved conflict marker found. Resolve manually first."

## Image Handling

**Download (Service → Markdown):**
1. Create images directory: `{file_base_name}.images/`
2. Download each image to that directory
3. Rewrite markdown paths: `![caption]({base_name}.images/{filename})`
4. Report: "Downloaded N images to {path}"

**Upload (Markdown → Service):**
- Current: Warn about local images, continue without them
- Future: Upload to service, update references

## Error Handling Pattern

| Error | Behavior |
|-------|----------|
| Document not found | "❌ Document not found. Check URL and permissions." |
| Auth error | "❌ Authentication failed. Check credentials/re-authorize." |
| Permission denied | "❌ No write access. Check permissions." |
| Local file not found | "❌ File not found: {path}" |
| No watermark (single-arg) | "❌ No {service}_url in frontmatter. Use two-arg form." |
| Conflict marker present | "❌ Unresolved conflict marker found. Resolve manually first." |
| Image download fails | "⚠️ Failed to download image: {name}. Continuing..." |
| Parse error | "❌ Parse error at line {N}: {error}" |
| Rate limit | "❌ API rate limit exceeded. Wait and retry." |
| Network error | "❌ Network error: {error}. Check connection." |

## Success Output Pattern

**Service → Markdown:**
```
✅ Synced from {Service} → {file_path}

Document: "{title}"
Last modified: {time}

Downloaded N images:
  • {path}/image-1.png (size)
  • {path}/image-2.png (size)

{line_count} lines written
```

**Markdown → Service:**
```
✅ Synced from {file_path} → {Service}

Updated: {url}

⚠️ Note: Local images not uploaded (not yet supported)

{N} sections updated
```

**No changes:**
```
ℹ️ No changes detected. Files are in sync.
```
