#!/usr/bin/env python3
"""
Google Docs MCP Server

A FastMCP server providing access to Google Docs as Markdown.
Fetches Google Docs via the Drive API, converts HTML to Markdown.

Requirements:
    pip install fastmcp google-api-python-client google-auth-oauthlib markdownify beautifulsoup4

Setup:
    1. Enable Google Drive API in Google Cloud Console
    2. Create OAuth 2.0 credentials (Desktop application)
    3. Download credentials.json to the same directory as this script
    4. Run the server - it will prompt for OAuth authorization on first run

Usage:
    python google_docs_mcp.py

    Or with FastMCP CLI:
    fastmcp run google_docs_mcp.py:mcp
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from fastmcp import FastMCP
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from markdownify import MarkdownConverter

# OAuth2 scopes - read/write for Docs and Drive
SCOPES = [
    "https://www.googleapis.com/auth/documents",  # Read/write Google Docs
    "https://www.googleapis.com/auth/drive.readonly",  # Read access to all Drive files
]

# Paths for credentials and token storage
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "google_docs_token.json"

# Create the FastMCP server
mcp = FastMCP(
    name="Google Docs MCP Server",
    instructions="""
    This server provides read/write access to Google Docs as Markdown.

    Available capabilities:
    - Fetch a Google Doc by URL or ID and return it as Markdown
    - Extract images from documents (as base64)
    - Update a Google Doc with markdown content
    - Preserve tables, headings, lists, bold/italic, and links
    - List all comments on a document with replies, quoted text, and author info

    Use this for bidirectional sync between Google Docs and local markdown files.
    """,
)


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


def get_drive_service():
    """Get Google Drive API service."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def get_docs_service():
    """Get Google Docs API service."""
    creds = get_credentials()
    return build("docs", "v1", credentials=creds)


def extract_doc_id(url_or_id: str) -> str:
    """
    Extract document ID from a Google Docs URL or return as-is if already an ID.

    Handles formats:
    - https://docs.google.com/document/d/{ID}/edit
    - https://docs.google.com/document/d/{ID}/edit?usp=sharing
    - https://docs.google.com/document/d/{ID}
    - Just the ID itself

    Args:
        url_or_id: Google Doc URL or document ID

    Returns:
        The document ID
    """
    # If it looks like a URL, parse it
    if url_or_id.startswith("http"):
        parsed = urlparse(url_or_id)
        # Path looks like /document/d/{ID}/edit or /document/d/{ID}
        path_parts = parsed.path.split("/")
        try:
            d_index = path_parts.index("d")
            return path_parts[d_index + 1]
        except (ValueError, IndexError):
            raise ValueError(f"Could not extract document ID from URL: {url_or_id}")

    # Otherwise assume it's already an ID
    return url_or_id


class FormatType(Enum):
    """Types of inline markdown formatting."""
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"
    LINK = "link"
    CODE = "code"


@dataclass
class FormattingSpan:
    """A span of formatted text with its position and type."""
    start: int              # Position in clean text
    end: int                # End position (exclusive)
    format_type: FormatType
    url: str = None         # Only for links


def parse_inline_formatting(text: str) -> tuple[str, list[FormattingSpan]]:
    """
    Parse markdown inline formatting, return (clean_text, spans).

    Patterns (in priority order):
    1. Links: [text](url)
    2. Bold+Italic: ***text***
    3. Bold: **text**
    4. Italic: *text* (but not inside words like file*name)
    5. Inline code: `code`

    Args:
        text: Raw markdown text with formatting

    Returns:
        Tuple of (clean_text with formatting removed, list of FormattingSpans)
    """
    if not text:
        return text, []

    # Collect all matches with their positions and types
    # Each entry: (pattern, content_group, format_type, url_group_or_None)
    INLINE_PATTERNS = [
        (r'\[([^\]]+)\]\(([^)]+)\)',       1, FormatType.LINK,        2),
        (r'\*\*\*([^*]+)\*\*\*',           1, FormatType.BOLD_ITALIC, None),
        (r'\*\*([^*]+)\*\*',               1, FormatType.BOLD,        None),
        (r'(?<!\*)\*([^*]+)\*(?!\*)',       1, FormatType.ITALIC,      None),
        (r'`([^`]+)`',                      1, FormatType.CODE,        None),
    ]

    matches = []
    for pattern, content_group, format_type, url_group in INLINE_PATTERNS:
        for m in re.finditer(pattern, text):
            matches.append({
                'start': m.start(),
                'end': m.end(),
                'content': m.group(content_group),
                'format_type': format_type,
                'url': m.group(url_group) if url_group is not None else None
            })

    # Sort by start position and remove overlaps
    matches.sort(key=lambda x: x['start'])
    non_overlapping = []
    last_end = -1
    for match in matches:
        if match['start'] >= last_end:
            non_overlapping.append(match)
            last_end = match['end']

    # Build clean text and spans
    clean_text = []
    spans = []
    pos = 0
    clean_pos = 0

    for match in non_overlapping:
        # Add text before this match
        if match['start'] > pos:
            clean_text.append(text[pos:match['start']])
            clean_pos += match['start'] - pos

        # Add the content (without delimiters)
        content = match['content']
        clean_text.append(content)

        # Create span
        spans.append(FormattingSpan(
            start=clean_pos,
            end=clean_pos + len(content),
            format_type=match['format_type'],
            url=match['url']
        ))

        clean_pos += len(content)
        pos = match['end']

    # Add remaining text
    if pos < len(text):
        clean_text.append(text[pos:])

    return ''.join(clean_text), spans


# Mapping from FormatType to (textStyle dict, fields string).
# FormatType.LINK is handled specially since it needs the span's URL.
FORMAT_STYLE_MAP = {
    FormatType.BOLD: (
        {'bold': True},
        'bold'
    ),
    FormatType.ITALIC: (
        {'italic': True},
        'italic'
    ),
    FormatType.BOLD_ITALIC: (
        {'bold': True, 'italic': True},
        'bold,italic'
    ),
    FormatType.CODE: (
        {
            'weightedFontFamily': {'fontFamily': 'Courier New'},
            'backgroundColor': {'color': {'rgbColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}}}
        },
        'weightedFontFamily,backgroundColor'
    ),
}


def generate_style_requests(spans: list[FormattingSpan], base_index: int) -> list:
    """
    Generate updateTextStyle requests for each formatting span.

    Args:
        spans: List of FormattingSpan objects
        base_index: The starting index in the document for this text

    Returns:
        List of updateTextStyle request dicts for Google Docs API
    """
    requests = []

    for span in spans:
        start_idx = base_index + span.start
        end_idx = base_index + span.end
        range_dict = {'startIndex': start_idx, 'endIndex': end_idx}

        if span.format_type == FormatType.LINK:
            text_style = {'link': {'url': span.url}}
            fields = 'link'
        elif span.format_type in FORMAT_STYLE_MAP:
            text_style, fields = FORMAT_STYLE_MAP[span.format_type]
        else:
            continue

        requests.append({
            'updateTextStyle': {
                'range': range_dict,
                'textStyle': text_style,
                'fields': fields
            }
        })

    return requests


def collect_code_block(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """
    Collect lines of a code block starting from a ``` line.

    Args:
        lines: All lines of the document
        start_idx: Index of the opening ``` line

    Returns:
        Tuple of (code_lines without delimiters, index of line after closing ```)
    """
    code_lines = []
    i = start_idx + 1  # Skip opening ```

    while i < len(lines):
        if lines[i].strip().startswith('```'):
            return code_lines, i + 1
        code_lines.append(lines[i])
        i += 1

    # No closing ``` found, return what we have
    return code_lines, i


def is_table_separator(line: str) -> bool:
    """
    Check if line is a markdown table separator (|---|---|).

    Args:
        line: Line to check

    Returns:
        True if line is a table separator row
    """
    stripped = line.strip()
    if not stripped.startswith('|') or not stripped.endswith('|'):
        return False
    # Check for pattern like |---|---| or |:---:|:---|
    cells = stripped[1:-1].split('|')
    return all(re.match(r'^[\s:-]+$', cell) and '-' in cell for cell in cells)


def parse_table_row(line: str) -> list[str]:
    """
    Parse a markdown table row into cell values.

    Args:
        line: Table row line (e.g., "| a | b | c |")

    Returns:
        List of cell content strings
    """
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split('|')]


def collect_table(lines: list[str], start_idx: int) -> tuple[list[list[str]], int]:
    """
    Collect markdown table rows starting from start_idx.

    Expects:
    - Line at start_idx is the header row
    - Line at start_idx + 1 is the separator row
    - Lines after that are data rows until non-table line

    Args:
        lines: All document lines
        start_idx: Index of the header row

    Returns:
        Tuple of (table_data, next_line_index)
        table_data is list of rows, each row is list of cell strings
    """
    table_data = []
    i = start_idx

    # Parse header row
    header_row = parse_table_row(lines[i])
    table_data.append(header_row)
    num_cols = len(header_row)
    i += 1

    # Skip separator row
    if i < len(lines) and is_table_separator(lines[i]):
        i += 1
    else:
        # Not a valid table
        return [], start_idx + 1

    # Parse data rows
    while i < len(lines):
        line = lines[i].strip()
        # Check if this looks like a table row
        if not line.startswith('|'):
            break
        # Don't treat another separator as a data row
        if is_table_separator(line):
            break

        row = parse_table_row(line)
        # Pad or truncate to match column count
        if len(row) < num_cols:
            row.extend([''] * (num_cols - len(row)))
        elif len(row) > num_cols:
            row = row[:num_cols]

        table_data.append(row)
        i += 1

    return table_data, i


@dataclass
class TableInfo:
    """Information about a table to be created."""
    data: list[list[str]]  # 2D list of cell content
    insert_index: int      # Where to insert the table


def generate_table_requests(
    table_data: list[list[str]],
    current_index: int
) -> tuple[list[dict], int, TableInfo]:
    """
    Generate request to create an empty table (population happens in second phase).

    This function now only creates the empty table structure. Cell population
    happens in a separate batch after fetching the document to get actual indices.

    Args:
        table_data: 2D list of cell content strings
        current_index: Document index where table starts

    Returns:
        Tuple of (list with insertTable request, new current_index, TableInfo for population)
    """
    if not table_data or not table_data[0]:
        return [], current_index, None

    num_rows = len(table_data)
    num_cols = len(table_data[0])

    requests = []

    # Only create the empty table - cell content will be added in second phase
    requests.append({
        'insertTable': {
            'rows': num_rows,
            'columns': num_cols,
            'location': {'index': current_index}
        }
    })

    # Store table info for later population
    table_info = TableInfo(data=table_data, insert_index=current_index)

    # Estimate new index after table
    # Empty table structure: approximately 2 + rows * (1 + cols * 2) indices
    # Plus 1 newline per cell (num_rows * num_cols)
    estimated_size = 2 + num_rows * (1 + num_cols * 2) + (num_rows * num_cols)
    new_index = current_index + estimated_size

    return requests, new_index, table_info


def extract_table_cell_indices(doc_content: list, table_insert_index: int) -> list[list[int]]:
    """
    Extract actual cell indices from a Google Docs document structure.

    Finds the table that was inserted near table_insert_index and extracts
    the paragraph start indices for each cell.

    Args:
        doc_content: The 'body.content' list from a Google Docs document
        table_insert_index: The approximate index where the table was inserted

    Returns:
        2D list of cell indices [row][col] -> paragraph start index
    """
    cell_indices = []

    # Find the table element closest to our insert index
    for element in doc_content:
        if 'table' not in element:
            continue

        start_index = element.get('startIndex', 0)
        # Allow some tolerance in finding the right table
        if abs(start_index - table_insert_index) > 50:
            continue

        table = element['table']
        table_rows = table.get('tableRows', [])

        for row in table_rows:
            row_indices = []
            cells = row.get('tableCells', [])

            for cell in cells:
                # Each cell contains content elements; find the paragraph
                cell_content = cell.get('content', [])
                for cell_element in cell_content:
                    if 'paragraph' in cell_element:
                        # The paragraph start index is where we insert text
                        para_start = cell_element.get('startIndex', 0)
                        row_indices.append(para_start)
                        break
                else:
                    # Fallback: use start index from first content element
                    if cell_content:
                        row_indices.append(cell_content[0].get('startIndex', 0))

            cell_indices.append(row_indices)

        # Found our table, stop searching
        break

    return cell_indices


def generate_table_population_requests(
    table_info: TableInfo,
    cell_indices: list[list[int]]
) -> list[dict]:
    """
    Generate requests to populate table cells with content.

    Uses actual cell indices extracted from the document structure.
    Processes cells in reverse order to avoid index shifting.

    Args:
        table_info: TableInfo with cell content data
        cell_indices: 2D list of actual cell indices from document

    Returns:
        List of insertText and updateTextStyle requests
    """
    requests = []
    table_data = table_info.data
    num_rows = len(table_data)
    num_cols = len(table_data[0]) if table_data else 0

    # Verify dimensions match
    if len(cell_indices) != num_rows:
        return []  # Structure mismatch, skip population

    # Collect all cell insertions with their actual indices
    cell_insertions = []

    for row_idx in range(num_rows):
        if len(cell_indices[row_idx]) != num_cols:
            continue  # Row dimension mismatch

        for col_idx in range(num_cols):
            cell_content = table_data[row_idx][col_idx]
            if cell_content:  # Only insert non-empty content
                cell_index = cell_indices[row_idx][col_idx]
                cell_insertions.append({
                    'row': row_idx,
                    'col': col_idx,
                    'index': cell_index,
                    'content': cell_content
                })

    # Sort by index in REVERSE order (highest first) to avoid shifting
    cell_insertions.sort(key=lambda x: x['index'], reverse=True)

    # Generate insert and style requests for each cell
    for cell in cell_insertions:
        # Parse inline formatting
        clean_text, spans = parse_inline_formatting(cell['content'])

        # Insert the clean text
        requests.append({
            'insertText': {
                'location': {'index': cell['index']},
                'text': clean_text
            }
        })

        # Apply inline formatting
        style_requests = generate_style_requests(spans, cell['index'])
        requests.extend(style_requests)

    return requests


def get_document_end_index(doc: dict) -> int:
    """
    Extract the end index from a Google Docs document structure.

    Args:
        doc: The document dict returned by docs_service.documents().get()

    Returns:
        The document end index (position after last content)
    """
    content = doc.get('body', {}).get('content', [])
    end_index = 1
    for element in content:
        if 'endIndex' in element:
            end_index = max(end_index, element['endIndex'])
    # Return position for insertion (one before the final newline)
    return end_index - 1 if end_index > 1 else 1


def split_markdown_at_tables(markdown: str) -> list[dict]:
    """
    Split markdown into segments at table boundaries.

    Returns a list of segments where each is either:
    - {'type': 'content', 'content': '# Heading\n\nParagraph...'}
    - {'type': 'table', 'data': [['col1', 'col2'], ['a', 'b']]}

    This enables incremental processing with document fetches between tables
    to eliminate index estimation drift.

    Args:
        markdown: Full markdown content

    Returns:
        List of segment dicts
    """
    segments = []
    lines = markdown.split('\n')
    i = 0
    current_content_lines = []

    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()

        # Check if this is the start of a table (line with | followed by separator)
        if '|' in line_stripped and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            # Flush any accumulated content before this table
            if current_content_lines:
                content = '\n'.join(current_content_lines)
                if content.strip():  # Only add non-empty content
                    segments.append({'type': 'content', 'content': content})
                current_content_lines = []

            # Collect the table
            table_data, next_i = collect_table(lines, i)
            if table_data:
                segments.append({'type': 'table', 'data': table_data})
            i = next_i
        else:
            current_content_lines.append(line)
            i += 1

    # Flush remaining content
    if current_content_lines:
        content = '\n'.join(current_content_lines)
        if content.strip():
            segments.append({'type': 'content', 'content': content})

    return segments


def convert_markdown_segment_to_requests(
    markdown: str,
    start_index: int
) -> tuple[list[dict], int]:
    """
    Convert a markdown segment (without tables) to Google Docs API requests.

    Handles headings, paragraphs, bullet/numbered lists, code blocks, and
    inline formatting (bold, italic, links, inline code). Tables are handled
    separately via split_markdown_at_tables + generate_table_requests.

    Args:
        markdown: Markdown content (should not contain tables)
        start_index: Document index where content starts

    Returns:
        Tuple of (list of request dicts, new current_index after content)
    """
    requests = []
    current_index = start_index

    # Each entry: (pattern, text_group_index, bullet_preset)
    list_patterns = [
        (r'^(\t*)[-*]\s+(.+)$',       2, 'BULLET_DISC_CIRCLE_SQUARE'),
        (r'^(\t*)(\d+)\.\s+(.+)$',    3, 'NUMBERED_DECIMAL_ALPHA_ROMAN'),
    ]

    lines = markdown.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()

        # Skip empty lines (but add a paragraph break)
        if not line_stripped:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            current_index += 1
            i += 1
            continue

        # Detect code block
        if line_stripped.startswith('```'):
            code_lines, next_i = collect_code_block(lines, i)
            if code_lines:
                code_text = '\n'.join(code_lines) + '\n'

                # Insert code text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': code_text
                    }
                })

                # Apply monospace font to code block
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + len(code_text)
                        },
                        'textStyle': {
                            'weightedFontFamily': {'fontFamily': 'Courier New'},
                            'backgroundColor': {'color': {'rgbColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}}}
                        },
                        'fields': 'weightedFontFamily,backgroundColor'
                    }
                })

                current_index += len(code_text)
            i = next_i
            continue

        # Detect heading level
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line_stripped)
        if heading_match:
            level = len(heading_match.group(1))
            raw_text = heading_match.group(2)

            # Parse inline formatting
            clean_text, spans = parse_inline_formatting(raw_text)

            # Insert clean text
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text + '\n'
                }
            })

            # Apply heading style
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(clean_text) + 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': f'HEADING_{level}'
                    },
                    'fields': 'namedStyleType'
                }
            })

            # Apply inline formatting
            style_requests = generate_style_requests(spans, current_index)
            requests.extend(style_requests)

            current_index += len(clean_text) + 1
            i += 1
            continue

        # Detect unordered or ordered list (with optional tab indentation for nesting)
        list_matched = False
        for list_pattern, text_group, bullet_preset in list_patterns:
            list_match = re.match(list_pattern, line)
            if list_match:
                indent_level = len(list_match.group(1))
                raw_text = list_match.group(text_group)
                clean_text, spans = parse_inline_formatting(raw_text)

                # Insert clean text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': clean_text + '\n'
                    }
                })

                # Apply bullet/numbered list
                end_idx = current_index + len(clean_text) + 1
                requests.append({
                    'createParagraphBullets': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': end_idx
                        },
                        'bulletPreset': bullet_preset
                    }
                })

                # Apply nesting indentation for sub-items
                if indent_level > 0:
                    requests.append(generate_nesting_request(
                        current_index, end_idx, indent_level
                    ))

                # Apply inline formatting
                style_requests = generate_style_requests(spans, current_index)
                requests.extend(style_requests)

                current_index = end_idx
                i += 1
                list_matched = True
                break

        if list_matched:
            continue

        # Regular paragraph
        raw_text = line_stripped

        # Parse inline formatting
        clean_text, spans = parse_inline_formatting(raw_text)

        # Insert the clean text
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': clean_text + '\n'
            }
        })

        # Apply inline formatting
        style_requests = generate_style_requests(spans, current_index)
        requests.extend(style_requests)

        current_index += len(clean_text) + 1
        i += 1

    return requests, current_index


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Lowercase, hyphenated slug
    """
    # Lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r"[^a-z0-9-]", "", text)
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    return text or "untitled"


def generate_nesting_request(start_index: int, end_index: int, indent_level: int) -> dict:
    """
    Generate updateParagraphStyle request to nest a bullet.

    Args:
        start_index: Start of paragraph
        end_index: End of paragraph
        indent_level: Nesting depth (1 = first sub-level)

    Returns:
        updateParagraphStyle request dict
    """
    return {
        'updateParagraphStyle': {
            'range': {
                'startIndex': start_index,
                'endIndex': end_index
            },
            'paragraphStyle': {
                'indentFirstLine': {
                    'magnitude': 18 + 36 * indent_level,
                    'unit': 'PT'
                },
                'indentStart': {
                    'magnitude': 36 * (indent_level + 1),
                    'unit': 'PT'
                }
            },
            'fields': 'indentFirstLine,indentStart'
        }
    }


class GoogleDocsMarkdownConverter(MarkdownConverter):
    """Custom markdown converter that preserves Google Docs list nesting.

    Google Docs exports nested lists as flat <ul>/<ol> elements with CSS classes
    like 'lst-kix_abc123-N' where N is the nesting level. The standard markdownify
    converter treats these as top-level lists. This subclass reads the class to
    restore tab indentation in the markdown output.
    """

    def convert_li(self, el, text, convert_as_inline, **kwargs):
        parent = el.parent
        level = 0
        if parent:
            for cls in parent.get('class', []):
                m = re.match(r'lst-\w+-(\d+)', cls)
                if m:
                    level = int(m.group(1))
                    break

        result = super().convert_li(el, text, convert_as_inline, **kwargs)

        if level > 0:
            indent = '\t' * level
            lines = result.split('\n')
            result = '\n'.join(
                indent + line if line.strip() else line
                for line in lines
            )

        return result


def convert_html_to_markdown(html: str) -> str:
    """
    Convert HTML to Markdown with settings optimized for Google Docs export.

    Args:
        html: HTML content from Google Docs

    Returns:
        Tuple of (markdown_string, list of extracted base64 images)
    """
    # Parse HTML and clean it before conversion
    soup = BeautifulSoup(html, "html.parser")

    # Remove style, script, meta, link tags completely (including content)
    for tag in soup.find_all(["style", "script", "meta", "link"]):
        tag.decompose()

    # Extract and replace base64 images with placeholders
    extracted_images = []
    for i, img in enumerate(soup.find_all("img")):
        src = img.get("src", "")
        if src.startswith("data:image"):
            # Extract the base64 data
            # Format: data:image/png;base64,<data>
            match = re.match(r"data:image/(\w+);base64,(.+)", src)
            if match:
                img_format = match.group(1)
                img_data = match.group(2)
                img_name = f"image-{i + 1}.{img_format}"
                extracted_images.append({
                    "name": img_name,
                    "data": img_data,
                    "format": img_format,
                })
                # Replace src with placeholder
                img["src"] = f"{{{{IMAGE:{img_name}}}}}"

    # Extract just the body content if present
    body = soup.find("body")
    if body:
        clean_html = str(body)
    else:
        clean_html = str(soup)

    # markdownify with custom converter to preserve list nesting
    markdown = GoogleDocsMarkdownConverter(
        heading_style="ATX",  # Use # for headings
        bullets="-",  # Use - for unordered lists
        strip=["script", "style", "meta", "link", "head"],  # Remove these tags
    ).convert(clean_html)

    # Convert image placeholders to markdown format
    markdown = re.sub(
        r"!\[\]\(\{\{IMAGE:([^}]+)\}\}\)",
        r"![image](\1)",
        markdown
    )

    # Clean up excessive whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    return markdown.strip(), extracted_images


@mcp.tool()
def fetch_google_doc(
    url: Annotated[str, "Google Doc URL or document ID"],
    include_images: Annotated[bool, "Whether to extract and return images"] = True,
) -> dict:
    """
    Fetch a Google Doc and return it as Markdown.

    Handles:
    - Headings, bold, italic, links, lists
    - Tables
    - Images (optionally extracted as base64)

    Args:
        url: Google Doc URL (e.g., https://docs.google.com/document/d/{ID}/edit) or just the document ID
        include_images: Whether to extract images from the document

    Returns:
        {
            "title": "Document Title",
            "markdown": "# Heading\\n\\nContent...",
            "images": [{"name": "image-1.png", "data": "base64..."}],  # if include_images
            "metadata": {
                "doc_id": "...",
                "last_modified": "...",
                "slug": "document-title"
            }
        }
    """
    try:
        doc_id = extract_doc_id(url)
        service = get_drive_service()

        # Get document metadata
        file_metadata = service.files().get(
            fileId=doc_id,
            fields="id,name,modifiedTime,owners"
        ).execute()

        title = file_metadata.get("name", "Untitled")
        slug = slugify(title)

        # Export as HTML
        html_content = service.files().export(
            fileId=doc_id,
            mimeType="text/html"
        ).execute()

        # Handle bytes response
        if isinstance(html_content, bytes):
            html_content = html_content.decode("utf-8")

        # Convert to Markdown (also extracts embedded base64 images)
        markdown, extracted_images = convert_html_to_markdown(html_content)

        # Build response
        result = {
            "title": title,
            "markdown": markdown,
            "metadata": {
                "doc_id": doc_id,
                "last_modified": file_metadata.get("modifiedTime"),
                "slug": slug,
            }
        }

        # Include images if requested
        if include_images:
            result["images"] = extracted_images
        else:
            result["images"] = []

        return result

    except HttpError as error:
        return {"error": f"Failed to fetch document: {error}"}
    except ValueError as error:
        return {"error": str(error)}


@mcp.tool()
def get_google_doc_metadata(
    url: Annotated[str, "Google Doc URL or document ID"],
) -> dict:
    """
    Get metadata about a Google Doc without fetching full content.

    Useful for checking document existence and basic info before fetching.

    Args:
        url: Google Doc URL or document ID

    Returns:
        {
            "title": "Document Title",
            "doc_id": "...",
            "last_modified": "...",
            "owner": "...",
            "slug": "document-title"
        }
    """
    try:
        doc_id = extract_doc_id(url)
        service = get_drive_service()

        file_metadata = service.files().get(
            fileId=doc_id,
            fields="id,name,modifiedTime,owners"
        ).execute()

        owners = file_metadata.get("owners", [])
        owner_email = owners[0].get("emailAddress") if owners else None

        return {
            "title": file_metadata.get("name", "Untitled"),
            "doc_id": doc_id,
            "last_modified": file_metadata.get("modifiedTime"),
            "owner": owner_email,
            "slug": slugify(file_metadata.get("name", "untitled")),
        }

    except HttpError as error:
        return {"error": f"Failed to get document metadata: {error}"}
    except ValueError as error:
        return {"error": str(error)}


@mcp.tool()
def list_google_doc_comments(
    url: Annotated[str, "Google Doc URL or document ID"],
    include_resolved: Annotated[bool, "Whether to include resolved comments"] = True,
    include_deleted: Annotated[bool, "Whether to include deleted comments"] = False,
) -> dict:
    """
    List all comments on a Google Doc with full details.

    Returns comments with:
    - Comment text and HTML content
    - Quoted/highlighted text from the document
    - Author name and photo
    - Creation and modification times
    - Resolved status
    - All replies with their details

    Args:
        url: Google Doc URL or document ID
        include_resolved: Include resolved comment threads (default True)
        include_deleted: Include deleted comments (default False)

    Returns:
        {
            "doc_id": "...",
            "comment_count": 3,
            "comments": [
                {
                    "id": "...",
                    "content": "Comment text",
                    "html_content": "<p>Comment text</p>",
                    "quoted_text": "highlighted text from doc",
                    "author": {"name": "...", "photo_url": "..."},
                    "created_time": "...",
                    "modified_time": "...",
                    "resolved": False,
                    "replies": [...]
                }
            ]
        }
    """
    try:
        doc_id = extract_doc_id(url)
        service = get_drive_service()

        # Fields to request - must be explicit for comments API
        comment_fields = (
            "comments(id,content,htmlContent,author,createdTime,modifiedTime,"
            "resolved,deleted,quotedFileContent,replies(id,content,htmlContent,"
            "author,createdTime,modifiedTime,deleted)),nextPageToken"
        )

        all_comments = []
        page_token = None

        # Paginate through all comments
        while True:
            response = service.comments().list(
                fileId=doc_id,
                fields=comment_fields,
                includeDeleted=include_deleted,
                pageSize=100,
                pageToken=page_token,
            ).execute()

            comments = response.get("comments", [])
            all_comments.extend(comments)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        # Transform comments to cleaner structure
        result_comments = []
        for comment in all_comments:
            # Skip resolved if not requested
            if not include_resolved and comment.get("resolved", False):
                continue

            # Extract author info
            author = comment.get("author", {})
            author_info = {
                "name": author.get("displayName", "Unknown"),
                "photo_url": author.get("photoLink"),
            }

            # Extract quoted text
            quoted_content = comment.get("quotedFileContent", {})
            quoted_text = quoted_content.get("value") if quoted_content else None

            # Transform replies
            replies = []
            for reply in comment.get("replies", []):
                reply_author = reply.get("author", {})
                replies.append({
                    "id": reply.get("id"),
                    "content": reply.get("content"),
                    "html_content": reply.get("htmlContent"),
                    "author": {
                        "name": reply_author.get("displayName", "Unknown"),
                        "photo_url": reply_author.get("photoLink"),
                    },
                    "created_time": reply.get("createdTime"),
                    "modified_time": reply.get("modifiedTime"),
                    "deleted": reply.get("deleted", False),
                })

            result_comments.append({
                "id": comment.get("id"),
                "content": comment.get("content"),
                "html_content": comment.get("htmlContent"),
                "quoted_text": quoted_text,
                "author": author_info,
                "created_time": comment.get("createdTime"),
                "modified_time": comment.get("modifiedTime"),
                "resolved": comment.get("resolved", False),
                "deleted": comment.get("deleted", False),
                "replies": replies,
            })

        return {
            "doc_id": doc_id,
            "comment_count": len(result_comments),
            "comments": result_comments,
        }

    except HttpError as error:
        return {"error": f"Failed to list comments: {error}"}
    except ValueError as error:
        return {"error": str(error)}


@mcp.tool()
def update_google_doc(
    url: Annotated[str, "Google Doc URL or document ID"],
    markdown: Annotated[str, "Markdown content to write to the document"],
    title: Annotated[str, "Optional new title for the document"] = None,
) -> dict:
    """
    Update a Google Doc with markdown content.

    This will REPLACE all existing content in the document with the provided markdown.

    Supports:
    - Headings (# ## ### etc.)
    - Paragraphs
    - Bullet lists (-)
    - Numbered lists (1.)
    - Bold (**text**)
    - Italic (*text*)
    - Bold+Italic (***text***)
    - Links ([text](url))
    - Inline code (`code`)
    - Code blocks (```...```)
    - Tables (| col1 | col2 | with separator row)

    Note: Images are not supported yet.

    Args:
        url: Google Doc URL or document ID
        markdown: Markdown content to write
        title: Optional new title for the document

    Returns:
        {
            "success": bool,
            "doc_id": str,
            "url": str,
            "last_modified": str,
            "error": str (if failed)
        }
    """
    try:
        doc_id = extract_doc_id(url)
        docs_service = get_docs_service()
        drive_service = get_drive_service()

        # First, get the current document to find its end index
        doc = docs_service.documents().get(documentId=doc_id).execute()
        doc_title = doc.get('title')
        end_index = get_document_end_index(doc)

        # Step 1: Delete all existing content (except the first character which is required)
        # Only delete if there's actually content to delete (range must be non-empty: end > start)
        if end_index > 1:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': end_index
                        }
                    }
                }]}
            ).execute()

        # Step 2: Process markdown incrementally, fetching after each table
        # to get actual indices and avoid estimation drift
        segments = split_markdown_at_tables(markdown)
        current_index = 1

        for segment in segments:
            if segment['type'] == 'content':
                # Convert and insert text content
                requests, _ = convert_markdown_segment_to_requests(
                    segment['content'], current_index
                )
                if requests:
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()
                    # Fetch actual position after content insertion
                    doc = docs_service.documents().get(documentId=doc_id).execute()
                    current_index = get_document_end_index(doc)

            elif segment['type'] == 'table':
                # Insert empty table at current (known correct) position
                table_data = segment['data']
                table_requests, _, table_info = generate_table_requests(
                    table_data, current_index
                )
                if table_requests:
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': table_requests}
                    ).execute()

                    # Immediately populate this table while we know exactly where it is
                    # Fetch fresh document state
                    doc = docs_service.documents().get(documentId=doc_id).execute()
                    doc_content = doc.get('body', {}).get('content', [])

                    # Find and populate the table we just inserted (at current_index)
                    if table_info:
                        cell_indices = extract_table_cell_indices(doc_content, current_index)
                        if cell_indices:
                            population_requests = generate_table_population_requests(
                                table_info, cell_indices
                            )
                            if population_requests:
                                docs_service.documents().batchUpdate(
                                    documentId=doc_id,
                                    body={'requests': population_requests}
                                ).execute()

                    # Fetch actual position after table insertion and population
                    doc = docs_service.documents().get(documentId=doc_id).execute()
                    current_index = get_document_end_index(doc)

        # Update title if provided
        if title and title != doc_title:
            drive_service.files().update(
                fileId=doc_id,
                body={'name': title}
            ).execute()

        # Get updated metadata
        file_metadata = drive_service.files().get(
            fileId=doc_id,
            fields="id,name,modifiedTime,webViewLink"
        ).execute()

        return {
            "success": True,
            "version": "v2-immediate-table-population",
            "doc_id": doc_id,
            "url": file_metadata.get("webViewLink"),
            "title": file_metadata.get("name"),
            "last_modified": file_metadata.get("modifiedTime"),
        }

    except HttpError as error:
        return {
            "success": False,
            "error": f"Failed to update document: {error}"
        }
    except ValueError as error:
        return {
            "success": False,
            "error": str(error)
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Unexpected error: {error}"
        }


if __name__ == "__main__":
    mcp.run()
