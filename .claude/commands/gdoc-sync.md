# Google Docs Sync Command

Bidirectional sync between Google Docs and local Markdown files.

**See `.claude/skills/sync-protocol.md` for shared sync patterns** (direction parsing, conflict detection, AI merge flow, watermark format, error handling).

## Usage

```
/gdoc-sync <source> <destination>
/gdoc-sync <file-with-watermark>
```

**Direction determined by argument order:**
- `gdoc-url file.md` → Google Docs → Markdown (download)
- `file.md gdoc-url` → Markdown → Google Docs (upload)
- Single arg: reads `gdoc_url` from frontmatter, syncs back to Google Docs

## Arguments

$ARGUMENTS

## Instructions

### 1. Parse Arguments & Determine Direction

Use the direction parsing pattern from `sync-protocol.md` with:
- Service domain: `docs.google.com`
- Watermark field: `gdoc_url`

### 2. Fetch Both Versions

**Fetch Google Doc content:**
```
gdoc_data = mcp__google-docs__fetch_google_doc(url=gdoc_url, include_images=True)
gdoc_doc_id = gdoc_data.metadata.doc_id
gdoc_markdown = gdoc_data.markdown
gdoc_title = gdoc_data.title
gdoc_last_modified = gdoc_data.metadata.last_modified
gdoc_images = gdoc_data.images  # Array of {name, data (base64), format}
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

Use the conflict detection pattern from `sync-protocol.md` with watermark fields: `gdoc_content_hash`, `gdoc_last_sync`.

### 4. Handle Sync

**Case A: No Conflict → Direct Sync**

**If `gdoc_to_markdown`:**
1. Use markdown from `gdoc_data.markdown` (already clean)
2. Download images from base64 (see Section 5)
3. Create frontmatter watermark (see `sync-protocol.md` for format, use `gdoc_` prefix)
4. Write to file_path
5. Report success with doc title, image count, line count

**If `markdown_to_gdoc`:**
1. Extract markdown body (remove frontmatter)
2. Check for local image paths and warn (see Section 6)
3. Update Google Doc:
   ```
   result = mcp__google-docs__update_google_doc(
       url=gdoc_url,
       markdown=local_body,
       title=None  # Keep existing title unless specified
   )
   ```
4. Update local frontmatter with new sync timestamp and hash
5. Report success with doc URL, sections updated

**Case B: Conflict → AI Merge**

Follow the AI merge flow from `sync-protocol.md`.

### 5. Download Images (Google Docs → Markdown)

For each image in `gdoc_data.images`:

1. **Extract image data:**
   ```
   name = image.name          # e.g., "image-1.png"
   base64_data = image.data   # base64 encoded string
   format = image.format      # e.g., "png"
   ```

2. **Create images directory:**
   ```
   base_name = file_path without extension
   images_dir = "{base_name}.images/"
   mkdir -p images_dir
   ```

3. **Decode and save:**
   ```python
   import base64
   image_bytes = base64.b64decode(base64_data)
   with open(f"{images_dir}/{name}", "wb") as f:
       f.write(image_bytes)
   ```

4. **Verify save:**
   - Check file exists and size > 0
   - If failed: log warning, continue with other images

5. **Rewrite markdown image paths:**
   ```markdown
   # Original from MCP: ![image](image-1.png)
   # Rewrite to: ![image]({base_name}.images/image-1.png)
   ```

6. **Report images downloaded:**
   ```
   Downloaded {N} images:
     • {base_name}.images/image-1.png (512KB)
     • {base_name}.images/image-2.png (1.2MB)
   ```

### 6. Handle Local Images (Markdown → Google Docs)

**Current behavior:**
- Detect `![caption](local-path)` references in markdown body
- Check if path is local (not http:// or https://)
- Warn: "⚠️  Local images detected. Image upload not yet supported. Upload to Google Doc manually or use hosted URLs."
- Continue sync without images (Google Docs will show broken image markers or plain text)

**Future enhancement:**
- Upload images to Google Drive
- Insert into Google Doc using inline object references
- Update local markdown with Drive URLs

### 7. Insert Conflict Marker

Use conflict marker format from `sync-protocol.md` with service label: `GOOGLE_DOCS`.

### 8. Error Handling

Use error handling pattern from `sync-protocol.md`. Google Docs-specific:
- OAuth expired: "Delete `assets/scripts/google_docs_token.json` and restart Claude Desktop."

### 9. Success Output

Use success output pattern from `sync-protocol.md`.

### 10. Watermark Format Reference

Use watermark format from `sync-protocol.md` with `gdoc_` prefix. Fields:
- `gdoc_url`, `gdoc_doc_id`, `gdoc_last_sync`, `gdoc_content_hash`, `gdoc_last_modified`

### 11. Implementation Notes

**Supported Markdown formatting (Google Docs → Markdown):**
- Headings (# ## ### ...)
- Bold (**text**)
- Italic (*text*)
- Lists (bullets and numbered)
- Links ([text](url))
- Tables
- Images (downloaded as base64)

**Supported Markdown formatting (Markdown → Google Docs):**
- Headings (# ## ### ...)
- Paragraphs
- Lists (bullets with `-`, numbered with `1.`)
- Bold (**text**)
- Italic (*text*)
- Bold+Italic (***text***)
- Links ([text](url)) — rendered as clickable hyperlinks
- Inline code (`code`) — rendered with monospace font and light gray background
- Code blocks (```...```) — rendered with monospace font and light gray background
- Tables (`| col1 | col2 |` with separator row) — supports inline formatting in cells

**Image handling:**
- Download: Fully supported (base64 → local files)
- Upload: Not yet implemented (future enhancement)

**Future enhancements:**
- Image upload (local files → Google Drive → Google Doc)
- Selective section sync
- Watch mode (auto-sync on changes)

### 12. Examples

**Example 1: Initial download from Google Docs**
```bash
$ /gdoc-sync https://docs.google.com/document/d/1ABC123/edit docs/product-spec.md

✅ Synced from Google Docs → docs/product-spec.md

Document: "Product Specification v2"
Last modified: 2026-01-22 10:15:00

Downloaded 3 images:
  • product-spec.images/architecture-1.png (1.2MB)
  • product-spec.images/mockup-2.png (856KB)
  • product-spec.images/flowchart-3.png (654KB)

142 lines written
```

**Example 2: Edit local file and sync back**
```bash
# User edits docs/product-spec.md locally
$ /gdoc-sync docs/product-spec.md

✅ Synced from docs/product-spec.md → Google Docs

Updated: https://docs.google.com/document/d/1ABC123/edit

3 sections updated
```

**Example 3: Conflict detected and resolved**
```bash
# Both Google Doc and local file were edited
$ /gdoc-sync docs/product-spec.md

⚠️  Conflict Detected

Both Google Doc and local file changed since last sync:
- Google Doc last modified: 2026-01-22 14:30:00
- Local file modified: 2026-01-22 14:25:00
- Last sync: 2026-01-22 10:00:00

Attempting intelligent merge...

📝 Merge Preview

SECTION: Introduction
  ├─ Google Doc: No changes
  └─ Local: Added background context paragraph
  → Merged: Keep local version

SECTION: Requirements
  ├─ Google Doc: Added requirement #7
  └─ Local: Updated requirement #3 wording
  → Merged: Combined both changes

SECTION: Timeline
  ├─ Google Doc: Changed Q2 to Q3
  └─ Local: Added milestone details
  → Merged: Q3 with milestone details

[AskUserQuestion prompt appears]
Question: "Accept this merge?"
Options: ["Yes, apply merge", "No, insert conflict marker"]

# User selects "Yes, apply merge"

✅ Merge applied successfully

Synced to Google Docs: https://docs.google.com/document/d/1ABC123/edit
```

**Example 4: Error - no watermark**
```bash
$ /gdoc-sync docs/new-file.md

❌ No gdoc_url in frontmatter. Use: /gdoc-sync <url> <file>
```

### 13. Comparison to Notion Sync

| Feature | notion-sync | gdoc-sync |
|---------|-------------|-----------|
| Bidirectional sync | ✅ | ✅ |
| Watermark tracking | ✅ | ✅ |
| Conflict detection | ✅ | ✅ |
| AI merge | ✅ | ✅ |
| Image download | ✅ (URL) | ✅ (base64) |
| Image upload | 🚧 Future | 🚧 Future |
| Rich formatting | ✅ (Notion blocks) | ✅ (Bold, italic, links, code) |
| Inline styles | ✅ | ✅ |
| Tables | ✅ | ✅ |
| Comments/suggestions | ❌ | ❌ |

**Key differences:**
- Google Docs uses base64 image encoding (simpler download)
- Notion has richer block structure, Google Docs is more document-centric
- Google Docs requires OAuth with specific scopes
