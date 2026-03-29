"""
Domain logic for handling the issue-created webhook.

This is intentionally minimal:
  - validate shared secret
  - extract issue key from payload
  - do small processing (create a static comment text)
  - write back by adding a comment to the issue
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.services.jira_client import JiraClient

logger = logging.getLogger("jira_webhook_app.triage")


@dataclass(frozen=True)
class TriageResult:
    """Result returned from handling the webhook."""

    issue_key: str
    comment_posted: bool


class TriageService:
    """Orchestrates webhook validation, parsing, and Jira write-back."""

    def __init__(self, webhook_secret: str, jira_client: JiraClient) -> None:
        self._webhook_secret = webhook_secret
        self._jira_client = jira_client

    # PUBLIC_INTERFACE
    def handle_issue_created_webhook(self, payload: Dict[str, Any], received_secret: Optional[str]) -> TriageResult:
        """
        Validate and handle a Jira Automation issue-created webhook payload.

        Args:
            payload: The JSON body sent by Jira Automation.
            received_secret: Value from header X-Webhook-Secret.

        Returns:
            TriageResult containing issue_key and whether the comment was posted.

        Raises:
            PermissionError: if the secret is missing/incorrect.
            ValueError: if the payload cannot be parsed for an issue key.
        """
        self._validate_secret(received_secret)

        issue_key = self._extract_issue_key(payload)
        comment = self._build_comment(issue_key=issue_key, payload=payload)

        # Write-back: add a comment to the same issue.
        comment_result = self._jira_client.add_comment(issue_key=issue_key, comment_body=comment)

        return TriageResult(issue_key=issue_key, comment_posted=comment_result.success)

    def _validate_secret(self, received_secret: Optional[str]) -> None:
        """Validate secret header against configured shared secret."""
        if not received_secret or received_secret.strip() != self._webhook_secret:
            raise PermissionError("Invalid or missing X-Webhook-Secret")

    def _extract_issue_key(self, payload: Dict[str, Any]) -> str:
        """
        Extract issue key from common Jira Automation payload shapes.

        Typical shapes include:
          - {"issue": {"key": "ABC-123", ...}, ...}
          - {"issue": {"key": "...", "id": "..."}} etc.
        """
        issue = payload.get("issue")
        if isinstance(issue, dict):
            key = issue.get("key")
            if isinstance(key, str) and key.strip():
                return key.strip()

        # Fallbacks sometimes appear in other fields; keep minimal but tolerant.
        key2 = payload.get("issueKey") or payload.get("key")
        if isinstance(key2, str) and key2.strip():
            return key2.strip()

        raise ValueError("Unable to determine issue key from webhook payload (expected payload.issue.key).")

    def _build_comment(self, issue_key: str, payload: Dict[str, Any]) -> str:
        """
        Minimal processing to generate a comment.

        Keep this static/simple as requested; include the issue key and a tiny hint that it's automated.
        """
        summary = ""
        issue = payload.get("issue")
        if isinstance(issue, dict):
            fields = issue.get("fields")
            if isinstance(fields, dict):
                maybe_summary = fields.get("summary")
                if isinstance(maybe_summary, str):
                    summary = maybe_summary.strip()

        summary_part = f"\n\nSummary: {summary}" if summary else ""
        return (
            "Auto-triage webhook received.\n"
            f"Issue: {issue_key}\n"
            "Processing: minimal (static response for now)."
            f"{summary_part}\n"
        )
