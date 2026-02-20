# Sync Tasks Command

Bidirectional sync between Obsidian tasks and Google Tasks.

## Usage

```
/sync-tasks [direction]
```

**Directions:**
- `pull` — Pull new tasks from Google Tasks into Obsidian (creates capture file)
- `push` — Push Obsidian tasks to Google Tasks
- `sync` (default) — Full bidirectional sync
- `status` — Show sync status without making changes

## How It Works

### Task Identity
Tasks are linked via block IDs in Obsidian:
```markdown
- [ ] Review roadmap #task 📅 2026-01-20 ^gtask-abc123
```

The `^gtask-{id}` block reference links the Obsidian task to Google Task ID.

### Sync Logic

**Completion is Sticky**: Once a task is marked complete on EITHER side, it stays complete everywhere. Sync never reopens tasks.

**Push (Obsidian → Google):**
1. Scan task files for `#task` items that have a `^gtask-*` block ID
2. For completed tasks (`[x]}`): mark complete in Google Tasks
3. For open tasks: check if title/due date changed and update Google
4. Tasks without `^gtask-*` ID are ignored (use `pull` to create links)

**Pull (Google → Obsidian):**
1. Fetch ALL Google Tasks (including completed: `show_completed=True`)
2. Build a map of all Google Task IDs → status
3. For each linked task in Obsidian (has `^gtask-*` ID):
   - If Google is complete AND Obsidian is open → mark Obsidian `[x]` with completion date
   - If Google task NOT FOUND (deleted) AND Obsidian is open → mark Obsidian `[x]` (deleted = was completed)
   - If Obsidian is already `[x]` → leave it alone (never reopen)
4. For unlinked pending Google tasks: append to capture file for triage
5. Skip unlinked completed Google tasks (already done, don't need to track)

### Files Scanned
- `journal/1-1s/**/*.md` — 1-1 notes
- `projects/**/*.md` — Project tasks
- `capture/**/*.md` — Captured tasks

## Instructions

When user runs `/sync-tasks`:

1. **Determine direction** from argument (default: `sync`)

2. **For `status`:**
   - Call `mcp__google-calendar__get_sync_mapping` to show current links
   - Call `mcp__google-calendar__list_tasks` to show Google Tasks count
   - Count Obsidian tasks with `#task` tag
   - Report: X linked, Y Google-only, Z Obsidian-only

3. **For `pull`:**
   - Call `mcp__google-calendar__list_tasks(show_completed=True)` — fetch ALL tasks including completed
   - Build a set of all Google Task IDs (for existence checking)
   - Grep for existing linked tasks in Obsidian (tasks with `^gtask-*` block IDs that are still open `[ ]`)
   - For each open linked Obsidian task:
     - Extract the Google ID from `^gtask-{id}`
     - Look up status in Google:
       - **If Google complete**: Update Obsidian to `[x]` with ✅ and completion date
       - **If Google NOT FOUND (deleted)**: Update Obsidian to `[x]` with ✅ today (deleted = was completed)
       - **If Google pending**: No action needed
   - For each Google task not linked in Obsidian:
     - **If pending**: Append to `capture/google-tasks-inbox.md`
     - **If completed**: Skip (already done, don't need to import)
   - Report: X tasks synced to complete locally (Y from Google complete, Z from deleted), W new tasks pulled

4. **For `push`:**
   - Grep for tasks with `^gtask-` block IDs across vault (excludes tmp/, node_modules/, .claude/)
   - Parse each linked task: status (`[ ]` vs `[x]`), title, due date (📅), google_id
   - For each linked task:
     - If completed in Obsidian (`[x]`): call `complete_task(task_id)`
     - If open: optionally update title/due if changed (future enhancement)
   - Report what was synced
   - Note: Unlinked Obsidian tasks are NOT pushed. Use `pull` to import from Google first.

5. **For `sync`:**
   - Do pull first
   - Then do push
   - Report combined results

## Task Parsing

Parse Obsidian task lines:
```
- [ ] Task title #task 📅 2026-01-20 ^gtask-abc123
- [x] Completed task #task ✅ 2026-01-15 ^gtask-def456
```

Extract:
- `status`: `open` if `[ ]`, `done` if `[x]` or `[X]`
- `title`: text before first emoji or `#task`
- `due`: date after 📅
- `google_id`: ID after `^gtask-`
- `file_path`: which file it came from
- `line_number`: for updating

## Example Session

```
User: /sync-tasks status

Claude: Checking sync status...

📊 Sync Status:
- Google Tasks: 8 pending
- Obsidian tasks with #task: 23
- Linked (synced): 5
- Google-only (need pull): 3
- Obsidian-only (not pushed): 18

Run `/sync-tasks pull` to import Google-only tasks.
Run `/sync-tasks push` to push Obsidian tasks to Google.
```

```
User: /sync-tasks pull

Claude: Pulling from Google Tasks...

Checking 85 Google Tasks (52 pending, 33 completed)...

**Completion sync (Google → Obsidian):**
✅ "some task" → marked complete locally (was done in Google)
✅ "Call with vendor" → marked complete locally

**New tasks to triage:**
1. "Review Q1 budget" (due 2026-01-15)
2. "Update roadmap doc" (no due date)

✅ 2 tasks marked complete in Obsidian
✅ 2 new tasks appended to capture/google-tasks-inbox.md
```

```
User: /sync-tasks push

Claude: Scanning for linked tasks (^gtask-*)...

Found 12 linked tasks:
- 3 completed in Obsidian → marking complete in Google
- 9 still open (no changes to sync)

Syncing completions...
✅ "Q1 roadmap review" → completed
✅ "Skip level with Bob" → completed
✅ "Email vendor about renewal" → completed

Done. 3 tasks marked complete in Google Tasks.
```

## Capture File Format

New tasks from Google are appended to `capture/google-tasks-inbox.md`:

```markdown
# Google Tasks Inbox

Tasks pulled from Google Tasks. Move to appropriate files and link.

---

## 2026-01-10

- [ ] Review Q1 budget #task 📅 2026-01-15 ^gtask-abc123
- [ ] Call with vendor #task 📅 2026-01-12 ^gtask-def456
- [ ] Update roadmap doc #task ^gtask-ghi789
```

## Error Handling

- **Auth expired**: Prompt to re-run auth flow
- **Task not found**: Remove from sync mapping, warn user
- **File not found**: Skip, warn user
- **Parse error**: Skip task, continue with others

## Updating Local Tasks (Pull Completion Sync)

When a Google task is complete but the local Obsidian task is open, update the line:

**Before:**
```markdown
- [ ] some work #task 📅 2026-01-20 ^gtask-1124b3ZwM3VLY2dYWXExYQ
```

**After:**
```markdown
- [x] some work #task 📅 2026-01-20 ✅ 2026-01-25 ^gtask-1124b3ZwM3VLY2dYWXExYQ
```

Changes:
1. `[ ]` → `[x]`
2. Add `✅ YYYY-MM-DD` (completion date from Google's `completed` field, or today if not available)

Use the Edit tool to make these changes in the actual files. The `^gtask-*` block ID tells you which file/line to update (from the Grep results).

## Limitations

- Only syncs tasks with `#task` tag
- Due dates only (no scheduled/start dates in Google Tasks)
- No recurring task sync (Google Tasks doesn't support recurrence well)
- Completion status is binary (no in-progress in Google Tasks)
- **Completion is sticky**: Once marked complete, sync will never reopen a task
