"""
Jira REST API client used by the webhook service.

Currently supports:
  - Add comment to an issue
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger("jira_webhook_app.jira_client")


@dataclass(frozen=True)
class JiraCommentResult:
    """Result of attempting to add a comment to a Jira issue."""

    success: bool
    status_code: int
    response_text: str


class JiraClient:
    """Minimal Jira Cloud REST client (Basic Auth with email + API token)."""

    def __init__(self, base_url: str, user_email: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_email = user_email
        self._api_token = api_token

    # PUBLIC_INTERFACE
    def add_comment(self, issue_key: str, comment_body: str) -> JiraCommentResult:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123").
            comment_body: Comment text (ADF not required; Jira accepts simple text via {"body": "..."}).

        Returns:
            JiraCommentResult with success status and HTTP response details.

        Raises:
            requests.RequestException: on network errors/timeouts.
        """
        url = f"{self._base_url}/rest/api/3/issue/{issue_key}/comment"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"body": comment_body}

        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            auth=(self._user_email, self._api_token),
            timeout=30,
        )

        success = 200 <= resp.status_code < 300
        if success:
            logger.info("Added comment to %s (status=%s)", issue_key, resp.status_code)
        else:
            logger.warning(
                "Failed to add comment to %s (status=%s, body=%s)",
                issue_key,
                resp.status_code,
                (resp.text or "")[:500],
            )

        return JiraCommentResult(
            success=success,
            status_code=resp.status_code,
            response_text=resp.text or "",
        )
