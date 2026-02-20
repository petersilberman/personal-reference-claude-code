#!/usr/bin/env python3
"""
Google Calendar & Tasks MCP Server

A FastMCP server providing read-only access to Google Calendar events and Tasks.
Supports searching, filtering, and listing capabilities over date/time ranges.

Requirements:
    pip install fastmcp google-api-python-client google-auth-oauthlib

Setup:
    1. Enable Google Calendar API and Google Tasks API in Google Cloud Console
    2. Create OAuth 2.0 credentials (Desktop application)
    3. Download credentials.json to the same directory as this script
    4. Run the server - it will prompt for OAuth authorization on first run

Usage:
    python google_calendar_mcp.py

    Or with FastMCP CLI:
    fastmcp run google_calendar_mcp.py:mcp
"""

import json
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

from fastmcp import FastMCP
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth2 scopes - read-only for Calendar, read-write for Tasks
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks",  # Full access for bidirectional sync
]

# Paths for credentials and token storage
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "google_calendar_token.json"

# Create the FastMCP server
mcp = FastMCP(
    name="Google Calendar MCP Server",
    instructions="""
    This server provides read-only access to Google Calendar and Google Tasks.

    Available capabilities:
    - List and search calendar events with date/time range filtering
    - Get detailed event information including attendees and locations
    - List Google Tasks with status filtering (pending/completed)

    All operations are read-only - no events or tasks will be modified.
    """,
)


# Mapping file for Obsidian <-> Google Task sync
SYNC_MAPPING_FILE = SCRIPT_DIR / "task_sync_mapping.json"


def load_sync_mapping() -> dict:
    """Load the Obsidian-Google task ID mapping."""
    if SYNC_MAPPING_FILE.exists():
        with open(SYNC_MAPPING_FILE, "r") as f:
            return json.load(f)
    return {"obsidian_to_google": {}, "google_to_obsidian": {}}


def save_sync_mapping(mapping: dict) -> None:
    """Save the Obsidian-Google task ID mapping."""
    with open(SYNC_MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)


def _link_sync_ids(obsidian_id: str, google_task_id: str) -> None:
    """Add a bidirectional mapping between an Obsidian ID and a Google Task ID."""
    mapping = load_sync_mapping()
    mapping["obsidian_to_google"][obsidian_id] = google_task_id
    mapping["google_to_obsidian"][google_task_id] = obsidian_id
    save_sync_mapping(mapping)


def _unlink_sync_id(google_task_id: str) -> None:
    """Remove a Google Task ID (and its Obsidian counterpart) from the mapping."""
    mapping = load_sync_mapping()
    obsidian_id = mapping["google_to_obsidian"].pop(google_task_id, None)
    if obsidian_id:
        mapping["obsidian_to_google"].pop(obsidian_id, None)
    save_sync_mapping(mapping)


def get_credentials() -> Credentials:
    """
    Get valid Google API credentials, refreshing or initiating OAuth flow as needed.

    Returns:
        Valid Credentials object for Google API access.

    Raises:
        FileNotFoundError: If credentials.json is not found.
    """
    creds = None

    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or get new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}. "
                    "Please download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


@lru_cache(maxsize=1)
def get_calendar_service():
    """Get Google Calendar API service (cached after first call)."""
    return build("calendar", "v3", credentials=get_credentials())


@lru_cache(maxsize=1)
def get_tasks_service():
    """Get Google Tasks API service (cached after first call)."""
    return build("tasks", "v1", credentials=get_credentials())


def parse_datetime(dt_str: Optional[str], default_offset_days: int = 0) -> Optional[str]:
    """
    Parse a datetime string and return RFC3339 format for Google API.

    Args:
        dt_str: DateTime string in various formats (ISO 8601, YYYY-MM-DD, etc.)
        default_offset_days: Days to offset from now if dt_str is None

    Returns:
        RFC3339 formatted datetime string or None.
    """
    if dt_str is None:
        if default_offset_days == 0:
            return None
        dt = datetime.now(timezone.utc) + timedelta(days=default_offset_days)
        return dt.isoformat()

    try:
        # Try parsing ISO format
        if "T" in dt_str:
            if dt_str.endswith("Z"):
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(dt_str)
        else:
            # Parse date only, assume start of day UTC
            dt = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        return dt.isoformat()
    except ValueError:
        return dt_str  # Return as-is, let Google API handle it


def _extract_time(time_obj: dict) -> Optional[str]:
    """Extract dateTime or date from a Calendar API time object."""
    return time_obj.get("dateTime", time_obj.get("date"))


def _format_person(person: dict) -> dict:
    """Extract email and display name from a Calendar API person object."""
    return {"email": person.get("email"), "name": person.get("displayName")}


def format_event(event: dict, include_details: bool = False) -> dict:
    """
    Format a calendar event into a clean dictionary.

    Args:
        event: Raw event from Google Calendar API
        include_details: Whether to include full details like attendees

    Returns:
        Formatted event dictionary.
    """
    result = {
        "id": event.get("id"),
        "summary": event.get("summary", "(No title)"),
        "start": _extract_time(event.get("start", {})),
        "end": _extract_time(event.get("end", {})),
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
    }

    if event.get("location"):
        result["location"] = event["location"]

    if event.get("description"):
        result["description"] = event["description"][:500]

    if not include_details:
        return result

    organizer = event.get("organizer", {})
    if organizer:
        result["organizer"] = {**_format_person(organizer), "self": organizer.get("self", False)}

    attendees = event.get("attendees", [])
    if attendees:
        result["attendees"] = [
            {
                **_format_person(att),
                "response_status": att.get("responseStatus"),
                "optional": att.get("optional", False),
                "organizer": att.get("organizer", False),
                "self": att.get("self", False),
            }
            for att in attendees
        ]

    conference = event.get("conferenceData", {})
    if conference:
        result["conference"] = {
            "type": conference.get("conferenceSolution", {}).get("name"),
            "entry_points": [
                {"type": ep.get("entryPointType"), "uri": ep.get("uri")}
                for ep in conference.get("entryPoints", [])
            ],
        }

    if event.get("recurrence"):
        result["recurrence"] = event["recurrence"]

    creator = event.get("creator", {})
    if creator:
        result["creator"] = _format_person(creator)

    return result


def format_task(task: dict) -> dict:
    """
    Format a task into a clean dictionary.

    Args:
        task: Raw task from Google Tasks API

    Returns:
        Formatted task dictionary.
    """
    return {
        "id": task.get("id"),
        "title": task.get("title", "(No title)"),
        "status": task.get("status"),  # "needsAction" or "completed"
        "due": task.get("due"),
        "notes": task.get("notes"),
        "completed": task.get("completed"),
        "updated": task.get("updated"),
        "parent": task.get("parent"),
        "position": task.get("position"),
        "html_link": task.get("selfLink"),
    }


# ============================================================================
# Calendar Tools
# ============================================================================

@mcp.tool(annotations={"readOnlyHint": True})
def list_calendars() -> list[dict]:
    """
    List all calendars accessible to the authenticated user.

    Returns a list of calendars with their IDs, names, and access roles.
    Use the calendar ID in other tools to access specific calendars.
    """
    try:
        service = get_calendar_service()
        items = service.calendarList().list().execute().get("items", [])

        return [
            {
                "id": cal.get("id"),
                "summary": cal.get("summary"),
                "description": cal.get("description"),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole"),
                "background_color": cal.get("backgroundColor"),
                "time_zone": cal.get("timeZone"),
            }
            for cal in items
        ]

    except HttpError as error:
        return [{"error": f"Failed to list calendars: {error}"}]


def _query_events(
    calendar_id: str,
    time_min: Optional[str],
    time_max: Optional[str],
    max_results: int,
    show_deleted: bool = False,
    query: Optional[str] = None,
) -> list[dict]:
    """Shared event query logic for list_events and search_events."""
    service = get_calendar_service()

    if time_min is None:
        time_min = datetime.now(timezone.utc).isoformat()
    else:
        time_min = parse_datetime(time_min)

    time_max = parse_datetime(time_max) if time_max else None
    max_results = max(1, min(2500, max_results))

    params = {
        "calendarId": calendar_id,
        "timeMin": time_min,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max
    if show_deleted:
        params["showDeleted"] = True
    if query:
        params["q"] = query

    events = service.events().list(**params).execute().get("items", [])
    return [format_event(event) for event in events]


@mcp.tool(annotations={"readOnlyHint": True})
def list_events(
    calendar_id: Annotated[str, "Calendar ID (use 'primary' for main calendar)"] = "primary",
    time_min: Annotated[Optional[str], "Start of time range (ISO 8601 or YYYY-MM-DD). Defaults to now."] = None,
    time_max: Annotated[Optional[str], "End of time range (ISO 8601 or YYYY-MM-DD). Optional."] = None,
    max_results: Annotated[int, "Maximum number of events to return (1-2500)"] = 50,
    show_deleted: Annotated[bool, "Whether to include deleted events"] = False,
) -> list[dict]:
    """
    List calendar events within a specified time range.

    Returns events sorted by start time. Each event includes summary, start/end times,
    location (if any), and a link to view the event.

    Examples:
    - List next 10 events: list_events(max_results=10)
    - Events this week: list_events(time_min="2024-01-01", time_max="2024-01-07")
    - Events from specific calendar: list_events(calendar_id="work@group.calendar.google.com")
    """
    try:
        return _query_events(calendar_id, time_min, time_max, max_results, show_deleted)
    except HttpError as error:
        return [{"error": f"Failed to list events: {error}"}]


@mcp.tool(annotations={"readOnlyHint": True})
def get_event(
    event_id: Annotated[str, "The event ID to retrieve"],
    calendar_id: Annotated[str, "Calendar ID containing the event"] = "primary",
) -> dict:
    """
    Get detailed information about a specific calendar event.

    Returns full event details including:
    - Summary, description, location
    - Start and end times
    - Organizer and all attendees with their response status
    - Conference/meeting links
    - Recurrence information

    Use list_events or search_events first to find the event ID.
    """
    try:
        service = get_calendar_service()
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
        ).execute()

        return format_event(event, include_details=True)

    except HttpError as error:
        return {"error": f"Failed to get event: {error}"}


@mcp.tool(annotations={"readOnlyHint": True})
def search_events(
    query: Annotated[str, "Search query to match against event text (summary, description, location, attendees)"],
    calendar_id: Annotated[str, "Calendar ID to search in"] = "primary",
    time_min: Annotated[Optional[str], "Start of time range (ISO 8601 or YYYY-MM-DD). Defaults to now."] = None,
    time_max: Annotated[Optional[str], "End of time range (ISO 8601 or YYYY-MM-DD). Optional."] = None,
    max_results: Annotated[int, "Maximum number of events to return"] = 50,
) -> list[dict]:
    """
    Search for calendar events matching a query string.

    The query is matched against event summary, description, location,
    attendee names, and attendee emails (Google's built-in search).

    Examples:
    - Find meetings with John: search_events(query="John")
    - Find project standups: search_events(query="standup")
    - Find events at a location: search_events(query="Conference Room A")
    """
    try:
        return _query_events(calendar_id, time_min, time_max, max_results, query=query)
    except HttpError as error:
        return [{"error": f"Failed to search events: {error}"}]


@mcp.tool(annotations={"readOnlyHint": True})
def get_free_busy(
    calendar_ids: Annotated[list[str], "List of calendar IDs to check"],
    time_min: Annotated[str, "Start of time range (ISO 8601 or YYYY-MM-DD)"],
    time_max: Annotated[str, "End of time range (ISO 8601 or YYYY-MM-DD)"],
) -> dict:
    """
    Get free/busy information for one or more calendars.

    Returns busy time blocks for each calendar within the specified range.
    Useful for finding available meeting times.

    Example:
    - Check availability: get_free_busy(
        calendar_ids=["primary", "colleague@example.com"],
        time_min="2024-01-15",
        time_max="2024-01-16"
      )
    """
    try:
        service = get_calendar_service()

        time_min = parse_datetime(time_min) or datetime.now(timezone.utc).isoformat()
        time_max = parse_datetime(time_max) or (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids],
        }

        result = service.freebusy().query(body=body).execute()

        # Format the response
        calendars = result.get("calendars", {})
        formatted = {}

        for cal_id, data in calendars.items():
            if data.get("errors"):
                formatted[cal_id] = {"errors": data["errors"]}
            else:
                formatted[cal_id] = {
                    "busy_periods": [
                        {"start": period["start"], "end": period["end"]}
                        for period in data.get("busy", [])
                    ]
                }

        return {
            "time_min": time_min,
            "time_max": time_max,
            "calendars": formatted,
        }

    except HttpError as error:
        return {"error": f"Failed to get free/busy info: {error}"}


# ============================================================================
# Tasks Tools
# ============================================================================

@mcp.tool(annotations={"readOnlyHint": True})
def list_task_lists() -> list[dict]:
    """
    List all task lists for the authenticated user.

    Returns task list IDs and names. Use the task list ID in list_tasks
    to get tasks from a specific list.
    """
    try:
        service = get_tasks_service()
        items = service.tasklists().list(maxResults=100).execute().get("items", [])

        return [
            {
                "id": tl.get("id"),
                "title": tl.get("title"),
                "updated": tl.get("updated"),
            }
            for tl in items
        ]

    except HttpError as error:
        return [{"error": f"Failed to list task lists: {error}"}]


@mcp.tool(annotations={"readOnlyHint": True})
def list_tasks(
    task_list_id: Annotated[str, "Task list ID (use '@default' for default list)"] = "@default",
    show_completed: Annotated[bool, "Whether to include completed tasks"] = True,
    show_hidden: Annotated[bool, "Whether to include hidden tasks"] = False,
    due_min: Annotated[Optional[str], "Minimum due date (ISO 8601 or YYYY-MM-DD)"] = None,
    due_max: Annotated[Optional[str], "Maximum due date (ISO 8601 or YYYY-MM-DD)"] = None,
    max_results: Annotated[int, "Maximum number of tasks to return"] = 100,
    completed_min: Annotated[Optional[str], "Minimum completion date (ISO 8601)"] = None,
    completed_max: Annotated[Optional[str], "Maximum completion date (ISO 8601)"] = None,
) -> list[dict]:
    """
    List tasks from a task list with optional filtering.

    Filter options:
    - show_completed: Set to False to only see pending tasks
    - due_min/due_max: Filter by due date range
    - completed_min/completed_max: Filter by completion date (requires show_completed=True)

    Task status values:
    - "needsAction": Task is pending/incomplete
    - "completed": Task is completed

    Examples:
    - All pending tasks: list_tasks(show_completed=False)
    - Tasks due this week: list_tasks(due_min="2024-01-01", due_max="2024-01-07")
    - Recently completed: list_tasks(completed_min="2024-01-01")
    """
    try:
        service = get_tasks_service()

        request_params = {
            "tasklist": task_list_id,
            "showCompleted": show_completed,
            "showHidden": show_hidden,
            "maxResults": min(100, max(1, max_results)),
        }

        date_filters = {
            "dueMin": due_min, "dueMax": due_max,
            "completedMin": completed_min, "completedMax": completed_max,
        }
        for key, value in date_filters.items():
            if value:
                request_params[key] = parse_datetime(value)

        result = service.tasks().list(**request_params).execute()
        tasks = result.get("items", [])

        return [format_task(task) for task in tasks]

    except HttpError as error:
        return [{"error": f"Failed to list tasks: {error}"}]


@mcp.tool(annotations={"readOnlyHint": True})
def get_task(
    task_id: Annotated[str, "The task ID to retrieve"],
    task_list_id: Annotated[str, "Task list ID containing the task"] = "@default",
) -> dict:
    """
    Get detailed information about a specific task.

    Returns full task details including title, notes, status, due date,
    and completion information.

    Use list_tasks first to find the task ID.
    """
    try:
        service = get_tasks_service()
        task = service.tasks().get(
            tasklist=task_list_id,
            task=task_id,
        ).execute()

        return format_task(task)

    except HttpError as error:
        return {"error": f"Failed to get task: {error}"}


# ============================================================================
# Tasks Write Tools (for bidirectional sync)
# ============================================================================

@mcp.tool()
def create_task(
    title: Annotated[str, "The task title"],
    task_list_id: Annotated[str, "Task list ID (use '@default' for default list)"] = "@default",
    notes: Annotated[Optional[str], "Optional notes/description for the task"] = None,
    due: Annotated[Optional[str], "Due date (ISO 8601 or YYYY-MM-DD)"] = None,
    obsidian_id: Annotated[Optional[str], "Obsidian block ID for sync tracking (e.g., 'vp-product/2026-Q1.md:42')"] = None,
) -> dict:
    """
    Create a new Google Task.

    Used for syncing tasks from Obsidian to Google Tasks.
    Optionally provide an obsidian_id to track the mapping for bidirectional sync.

    Examples:
    - Simple task: create_task(title="Review roadmap")
    - With due date: create_task(title="Submit report", due="2026-01-20")
    - With sync tracking: create_task(title="Review roadmap", obsidian_id="vp-product/2026-Q1.md:42")
    """
    try:
        service = get_tasks_service()

        task_body = {"title": title}
        if notes:
            task_body["notes"] = notes
        if due:
            due_parsed = parse_datetime(due)
            if due_parsed:
                task_body["due"] = due_parsed

        result = service.tasks().insert(tasklist=task_list_id, body=task_body).execute()

        if obsidian_id:
            _link_sync_ids(obsidian_id, result["id"])

        return format_task(result)

    except HttpError as error:
        return {"error": f"Failed to create task: {error}"}


@mcp.tool()
def update_task(
    task_id: Annotated[str, "The Google Task ID to update"],
    task_list_id: Annotated[str, "Task list ID containing the task"] = "@default",
    title: Annotated[Optional[str], "New title (optional)"] = None,
    notes: Annotated[Optional[str], "New notes (optional)"] = None,
    due: Annotated[Optional[str], "New due date (optional, ISO 8601 or YYYY-MM-DD)"] = None,
) -> dict:
    """
    Update an existing Google Task.

    Only the fields provided will be updated; others remain unchanged.

    Examples:
    - Update title: update_task(task_id="abc123", title="New title")
    - Update due date: update_task(task_id="abc123", due="2026-01-25")
    """
    try:
        service = get_tasks_service()
        existing = service.tasks().get(tasklist=task_list_id, task=task_id).execute()

        if title is not None:
            existing["title"] = title
        if notes is not None:
            existing["notes"] = notes
        if due is not None:
            due_parsed = parse_datetime(due)
            if due_parsed:
                existing["due"] = due_parsed

        result = service.tasks().update(tasklist=task_list_id, task=task_id, body=existing).execute()
        return format_task(result)

    except HttpError as error:
        return {"error": f"Failed to update task: {error}"}


def _update_task_status(task_id: str, task_list_id: str, status: str, clear_completed: bool = False) -> dict:
    """Fetch a task, update its status, and return the formatted result."""
    service = get_tasks_service()
    existing = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
    existing["status"] = status
    if clear_completed:
        existing.pop("completed", None)
    result = service.tasks().update(tasklist=task_list_id, task=task_id, body=existing).execute()
    return format_task(result)


@mcp.tool()
def complete_task(
    task_id: Annotated[str, "The Google Task ID to mark as complete"],
    task_list_id: Annotated[str, "Task list ID containing the task"] = "@default",
) -> dict:
    """
    Mark a Google Task as completed.

    Used when a task is completed in Obsidian and needs to sync to Google.

    Example:
    - complete_task(task_id="abc123")
    """
    try:
        return _update_task_status(task_id, task_list_id, "completed")
    except HttpError as error:
        return {"error": f"Failed to complete task: {error}"}


@mcp.tool()
def uncomplete_task(
    task_id: Annotated[str, "The Google Task ID to mark as incomplete"],
    task_list_id: Annotated[str, "Task list ID containing the task"] = "@default",
) -> dict:
    """
    Mark a Google Task as incomplete (needs action).

    Used when a completed task is reopened in Obsidian.

    Example:
    - uncomplete_task(task_id="abc123")
    """
    try:
        return _update_task_status(task_id, task_list_id, "needsAction", clear_completed=True)
    except HttpError as error:
        return {"error": f"Failed to uncomplete task: {error}"}


@mcp.tool()
def delete_task(
    task_id: Annotated[str, "The Google Task ID to delete"],
    task_list_id: Annotated[str, "Task list ID containing the task"] = "@default",
) -> dict:
    """
    Delete a Google Task.

    Warning: This permanently deletes the task. Use complete_task for normal completion.

    Example:
    - delete_task(task_id="abc123")
    """
    try:
        service = get_tasks_service()
        service.tasks().delete(tasklist=task_list_id, task=task_id).execute()
        _unlink_sync_id(task_id)
        return {"success": True, "deleted_task_id": task_id}

    except HttpError as error:
        return {"error": f"Failed to delete task: {error}"}


@mcp.tool(annotations={"readOnlyHint": True})
def get_sync_mapping() -> dict:
    """
    Get the current Obsidian <-> Google Task ID mapping.

    Returns the bidirectional mapping used to track which Obsidian tasks
    correspond to which Google Tasks.
    """
    return load_sync_mapping()


@mcp.tool()
def link_task(
    obsidian_id: Annotated[str, "Obsidian identifier (e.g., 'vp-product/2026-Q1.md:42' or block ID)"],
    google_task_id: Annotated[str, "Google Task ID to link"],
) -> dict:
    """
    Manually link an existing Obsidian task to an existing Google Task.

    Use this to establish sync relationship between tasks that weren't
    created through the sync process.

    Example:
    - link_task(obsidian_id="vp-product/2026-Q1.md:42", google_task_id="abc123")
    """
    _link_sync_ids(obsidian_id, google_task_id)
    return {
        "success": True,
        "obsidian_id": obsidian_id,
        "google_task_id": google_task_id,
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
