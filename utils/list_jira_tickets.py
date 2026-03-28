#!/usr/bin/env python3
"""
list_jira_tickets.py — Fetch and display Jira issues assigned to the current user.

By default, lists ALL tickets assigned to the current user (regardless of status).
Use --open-only to restrict results to open/unresolved issues only.

Flow name: ListJiraTicketsFlow

Contract:
  Inputs:
    - JIRA_URL (env var): Base URL for the Jira instance (e.g., https://kavia-team.atlassian.net)
    - JIRA_USER_EMAIL (env var): Atlassian account email for authentication
    - JIRA_API_TOKEN (env var): Atlassian API token for authentication
    - --all flag (CLI): List all tickets assigned to the user (default behavior)
    - --open-only flag (CLI): List only open/unresolved tickets
  Outputs:
    - Formatted table of Jira issues printed to stdout
    - Exit code 0 on success, 1 on configuration/auth/network errors
  Errors:
    - Missing configuration → clear message listing which vars are missing
    - Authentication failure → actionable message with link to generate API token
    - Network/API errors → error message with HTTP status and response body excerpt
  Side effects:
    - HTTP GET requests to the Jira REST API (read-only)

Usage:
    # List ALL tickets assigned to you (default)
    python3 utils/list_jira_tickets.py

    # Explicitly list all tickets
    python3 utils/list_jira_tickets.py --all

    # List only open/unresolved tickets
    python3 utils/list_jira_tickets.py --open-only
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging setup — structured, consistent, flow-named
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ListJiraTicketsFlow")

# ---------------------------------------------------------------------------
# Configuration (Boundary Layer)
# ---------------------------------------------------------------------------

# JQL queries for different modes
ALL_TICKETS_JQL = (
    'assignee = currentUser() ORDER BY updated DESC'
)

OPEN_TICKETS_JQL = (
    'assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC'
)

# Fields to request from the Jira API
JIRA_FIELDS = "key,summary,status,priority,issuetype,updated,project"

# Maximum results per request
MAX_RESULTS = 50


@dataclass
class JiraConfig:
    """
    Validated configuration for connecting to a Jira instance.

    Invariants:
        - All three fields are non-empty strings after construction via load_config().
    """
    url: str
    user_email: str
    api_token: str


@dataclass
class JiraIssue:
    """Structured representation of a single Jira issue."""
    key: str
    summary: str
    status: str
    priority: str
    issue_type: str
    project: str
    updated: str


@dataclass
class ListTicketsResult:
    """Result object from the ListJiraTicketsFlow."""
    success: bool
    issues: List[JiraIssue] = field(default_factory=list)
    total: int = 0
    error_message: Optional[str] = None


# PUBLIC_INTERFACE
def load_config() -> JiraConfig:
    """
    Load and validate Jira configuration from environment variables.

    Reads from the process environment. The caller is responsible for loading
    .env files before calling this function (see main()).

    Returns:
        JiraConfig with validated, non-empty fields.

    Raises:
        SystemExit: If any required variable is missing or empty.
    """
    # Try to load .env file if python-dotenv is available
    _try_load_dotenv()

    url = os.environ.get("JIRA_URL", "").strip()
    email = os.environ.get("JIRA_USER_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip()

    missing = []
    if not url:
        missing.append("JIRA_URL")
    if not email:
        missing.append("JIRA_USER_EMAIL")
    if not token:
        missing.append("JIRA_API_TOKEN")

    if missing:
        logger.error(
            "Missing required environment variables: %s. "
            "Set them in your .env file or export them in your shell.",
            ", ".join(missing),
        )
        sys.exit(1)

    # Normalize: strip trailing slashes from URL
    url = url.rstrip("/")
    logger.info("Configuration loaded — Jira URL: %s, User: %s", url, email)
    return JiraConfig(url=url, user_email=email, api_token=token)


def _try_load_dotenv() -> None:
    """Attempt to load .env file using python-dotenv if available. Silent no-op otherwise."""
    try:
        from dotenv import load_dotenv

        # Look for .env in the current working directory and common project locations
        env_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "typescript-node-starter-337516", ".env"),
        ]
        for env_path in env_paths:
            if os.path.isfile(env_path):
                load_dotenv(env_path, override=False)
                logger.info("Loaded .env from: %s", env_path)
                return
    except ImportError:
        pass  # python-dotenv not installed; rely on exported env vars


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments to determine ticket listing mode.

    Args:
        argv: Optional list of CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Namespace with 'open_only' boolean attribute.
    """
    parser = argparse.ArgumentParser(
        description="List Jira tickets assigned to the current user.",
        epilog=(
            "By default, ALL tickets are listed regardless of status. "
            "Use --open-only to restrict to open/unresolved issues."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="List all tickets assigned to you, regardless of status (default).",
    )
    group.add_argument(
        "--open-only",
        action="store_true",
        default=False,
        help="List only open/unresolved tickets assigned to you.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Adapter / I-O Layer — Jira REST API
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
def fetch_issues_from_jira(
    config: JiraConfig,
    jql: str,
    fields: str = JIRA_FIELDS,
    max_results: int = MAX_RESULTS,
) -> Dict[str, Any]:
    """
    Execute a JQL search against the Jira REST API and return the raw JSON response.

    Args:
        config: Validated JiraConfig with connection credentials.
        jql: JQL query string.
        fields: Comma-separated list of Jira fields to include.
        max_results: Maximum number of issues to return.

    Returns:
        Parsed JSON response dict from the Jira search endpoint.

    Raises:
        requests.HTTPError: On non-2xx responses (with context in the message).
        requests.ConnectionError: On network failures.
    """
    search_url = f"{config.url}/rest/api/3/search/jql"
    params = {
        "jql": jql,
        "maxResults": max_results,
        "fields": fields,
    }
    headers = {
        "Accept": "application/json",
    }

    logger.info("Fetching issues — JQL: %s (maxResults=%d)", jql, max_results)

    response = requests.get(
        search_url,
        params=params,
        headers=headers,
        auth=(config.user_email, config.api_token),
        timeout=30,
    )

    if response.status_code != 200:
        # Add context to the error for debuggability
        body_excerpt = response.text[:500] if response.text else "(empty body)"
        error_msg = (
            f"Jira API returned HTTP {response.status_code}. "
            f"URL: {search_url}. Response: {body_excerpt}"
        )
        if response.status_code == 401:
            error_msg += (
                "\n\nAuthentication failed. Your JIRA_API_TOKEN may be invalid or expired. "
                "Generate a new token at: "
                "https://id.atlassian.com/manage-profile/security/api-tokens"
            )
        logger.error(error_msg)
        response.raise_for_status()

    return response.json()


# ---------------------------------------------------------------------------
# Domain / Core Logic Layer — Parse and transform
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
def parse_issues(raw_response: Dict[str, Any]) -> List[JiraIssue]:
    """
    Parse raw Jira API response into a list of JiraIssue objects.

    Args:
        raw_response: Parsed JSON dict from the Jira search endpoint.

    Returns:
        List of JiraIssue with fields extracted safely (defaults to 'N/A' on missing data).

    Invariants:
        - Output list length <= len(raw_response.get('issues', []))
        - Each JiraIssue has all string fields populated (never None).
    """
    issues: List[JiraIssue] = []
    for raw_issue in raw_response.get("issues", []):
        fields = raw_issue.get("fields", {})
        issues.append(
            JiraIssue(
                key=raw_issue.get("key", "N/A"),
                summary=_safe_get(fields, "summary", "N/A"),
                status=_safe_nested(fields, "status", "name", "N/A"),
                priority=_safe_nested(fields, "priority", "name", "N/A"),
                issue_type=_safe_nested(fields, "issuetype", "name", "N/A"),
                project=_safe_nested(fields, "project", "name", "N/A"),
                updated=_safe_get(fields, "updated", "N/A"),
            )
        )
    return issues


def _safe_get(data: Dict, key: str, default: str = "N/A") -> str:
    """Safely get a string value from a dict, returning default if missing or None."""
    value = data.get(key)
    return str(value) if value is not None else default


def _safe_nested(data: Dict, outer_key: str, inner_key: str, default: str = "N/A") -> str:
    """Safely get a nested string value (data[outer_key][inner_key])."""
    outer = data.get(outer_key)
    if isinstance(outer, dict):
        value = outer.get(inner_key)
        return str(value) if value is not None else default
    return default


# ---------------------------------------------------------------------------
# Display Layer — Format output
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
def format_issues_table(issues: List[JiraIssue], mode_label: str = "all") -> str:
    """
    Format a list of JiraIssue objects into a human-readable table string.

    Args:
        issues: List of parsed JiraIssue objects.
        mode_label: A label describing the current listing mode (e.g., "all" or "open-only").

    Returns:
        Formatted table string ready for stdout.
    """
    if not issues:
        if mode_label == "open-only":
            return "No open/unresolved issues found assigned to you."
        return "No issues found assigned to you."

    # Column definitions: (header, accessor, min_width)
    columns = [
        ("Key", lambda i: i.key, 12),
        ("Type", lambda i: i.issue_type, 10),
        ("Priority", lambda i: i.priority, 10),
        ("Status", lambda i: i.status, 14),
        ("Project", lambda i: i.project, 16),
        ("Summary", lambda i: _truncate(i.summary, 50), 50),
        ("Updated", lambda i: _format_date(i.updated), 20),
    ]

    # Calculate column widths (max of header, min_width, and data)
    widths = []
    for header, accessor, min_w in columns:
        max_data = max((len(accessor(issue)) for issue in issues), default=0)
        widths.append(max(len(header), min_w, min(max_data, 60)))

    # Build header
    header_line = " | ".join(
        columns[i][0].ljust(widths[i]) for i in range(len(columns))
    )
    separator = "-+-".join("-" * w for w in widths)

    # Build rows
    rows = []
    for issue in issues:
        row = " | ".join(
            columns[i][1](issue).ljust(widths[i]) for i in range(len(columns))
        )
        rows.append(row)

    return "\n".join([header_line, separator, *rows])


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, appending '...' if truncated."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_date(iso_date: str) -> str:
    """Format an ISO date string to a shorter, readable form."""
    if iso_date == "N/A":
        return iso_date
    # Jira dates look like: 2024-01-15T10:30:00.000+0000
    # Extract just the date and time portion
    try:
        return iso_date[:16].replace("T", " ")
    except (IndexError, TypeError):
        return iso_date


# ---------------------------------------------------------------------------
# Flow / Orchestration Layer — ListJiraTicketsFlow
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
def list_jira_tickets(config: JiraConfig, open_only: bool = False) -> ListTicketsResult:
    """
    Orchestrate fetching and parsing of Jira tickets assigned to the current user.

    By default fetches ALL tickets (any status). When open_only=True, fetches only
    open/unresolved tickets.

    Flow: ListJiraTicketsFlow
    Entrypoint: This function.

    Args:
        config: Validated JiraConfig.
        open_only: If True, restrict to open/unresolved tickets only.

    Returns:
        ListTicketsResult with success status, parsed issues, and total count.

    Failure modes:
        1. Authentication failure (invalid/expired token) → result.error_message set
        2. Network error (timeout, DNS) → result.error_message set
        3. Unexpected API response format → result.error_message set
    """
    jql = OPEN_TICKETS_JQL if open_only else ALL_TICKETS_JQL
    mode = "open-only" if open_only else "all"
    logger.info("ListJiraTicketsFlow — START (user=%s, mode=%s)", config.user_email, mode)

    try:
        # Step 1: Fetch raw issues from Jira API
        raw_response = fetch_issues_from_jira(config, jql=jql)
        total = raw_response.get("total", 0)
        logger.info("ListJiraTicketsFlow — API returned total=%d issues", total)

        # Step 2: Parse raw response into structured issue objects
        issues = parse_issues(raw_response)
        logger.info("ListJiraTicketsFlow — Parsed %d issues", len(issues))

        # Step 3: Return structured result
        result = ListTicketsResult(success=True, issues=issues, total=total)
        logger.info("ListJiraTicketsFlow — END (success, %d issues)", len(issues))
        return result

    except requests.exceptions.HTTPError as exc:
        error_msg = f"HTTP error from Jira API: {exc}"
        logger.error("ListJiraTicketsFlow — FAILED: %s", error_msg)
        return ListTicketsResult(success=False, error_message=error_msg)

    except requests.exceptions.ConnectionError as exc:
        error_msg = f"Connection error reaching Jira: {exc}"
        logger.error("ListJiraTicketsFlow — FAILED: %s", error_msg)
        return ListTicketsResult(success=False, error_message=error_msg)

    except requests.exceptions.Timeout as exc:
        error_msg = f"Timeout reaching Jira API: {exc}"
        logger.error("ListJiraTicketsFlow — FAILED: %s", error_msg)
        return ListTicketsResult(success=False, error_message=error_msg)

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        error_msg = f"Unexpected response format from Jira API: {exc}"
        logger.error("ListJiraTicketsFlow — FAILED: %s", error_msg)
        return ListTicketsResult(success=False, error_message=error_msg)


# Backward-compatible alias for the old function name
# PUBLIC_INTERFACE
def list_open_jira_tickets(config: JiraConfig) -> ListTicketsResult:
    """
    Backward-compatible wrapper that lists only open/unresolved Jira tickets.

    Equivalent to calling list_jira_tickets(config, open_only=True).

    Args:
        config: Validated JiraConfig.

    Returns:
        ListTicketsResult with only open/unresolved issues.
    """
    return list_jira_tickets(config, open_only=True)


# ---------------------------------------------------------------------------
# Entry Point (Boundary Layer)
# ---------------------------------------------------------------------------

def main() -> None:
    """
    CLI entry point for listing Jira tickets assigned to the current user.

    By default lists ALL tickets. Use --open-only to restrict to unresolved issues.

    Responsibilities:
        - Parse CLI arguments to determine listing mode
        - Load and validate configuration from environment
        - Invoke the ListJiraTicketsFlow
        - Format and display results
        - Map errors to appropriate exit codes
    """
    # Parse CLI arguments
    args = parse_args()
    open_only = args.open_only
    jql = OPEN_TICKETS_JQL if open_only else ALL_TICKETS_JQL
    mode_label = "open-only" if open_only else "all"

    print("=" * 80)
    if open_only:
        print("  Jira Tickets — Open/Unresolved — Assigned to Current User")
    else:
        print("  Jira Tickets — All Statuses — Assigned to Current User")
    print("  JQL: " + jql)
    print("=" * 80)
    print()

    # Step 1: Load configuration (exits on failure)
    config = load_config()

    # Step 2: Execute the flow
    result = list_jira_tickets(config, open_only=open_only)

    # Step 3: Display results or error
    if not result.success:
        print(f"\nERROR: {result.error_message}", file=sys.stderr)
        print(
            "\nTroubleshooting steps:",
            "  1. Verify JIRA_API_TOKEN is a valid Atlassian API token (not a password)",
            "  2. Generate a new token at: https://id.atlassian.com/manage-profile/security/api-tokens",
            "  3. Ensure JIRA_USER_EMAIL matches your Atlassian account",
            "  4. Verify your account has access to projects on the Jira instance",
            sep="\n",
            file=sys.stderr,
        )
        sys.exit(1)

    if open_only:
        print(f"Found {result.total} open/unresolved issue(s) assigned to you.\n")
    else:
        print(f"Found {result.total} issue(s) assigned to you (all statuses).\n")

    if result.issues:
        print(format_issues_table(result.issues, mode_label=mode_label))
    else:
        if open_only:
            print("No open/unresolved issues found assigned to you.")
        else:
            print("No issues found assigned to you.")

    print(f"\n(Showing {len(result.issues)} of {result.total} total)")
    print(f"Jira instance: {config.url}")
    print(f"User: {config.user_email}")


if __name__ == "__main__":
    main()
