"""
Configuration loading for the Jira webhook service.

All configuration is sourced from environment variables (optionally via a .env file
when python-dotenv is installed). This keeps secrets out of source code and allows
easy deployment configuration.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("jira_webhook_app.config")


@dataclass(frozen=True)
class AppConfig:
    """Validated config values required by the service."""

    jira_base_url: str
    jira_user_email: str
    jira_api_token: str
    webhook_shared_secret: str


def _try_load_dotenv() -> None:
    """Attempt to load a .env file using python-dotenv if it is installed."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(override=False)
        logger.info("Loaded .env (python-dotenv).")
    except Exception:
        # Silent no-op if python-dotenv isn't installed (or if any other non-critical error occurs).
        return


# PUBLIC_INTERFACE
def load_config() -> AppConfig:
    """
    Load and validate AppConfig from environment variables.

    Required environment variables:
      - JIRA_BASE_URL (e.g., https://kavia-team.atlassian.net)
      - JIRA_USER_EMAIL
      - JIRA_API_TOKEN
      - WEBHOOK_SHARED_SECRET

    Returns:
        AppConfig: validated configuration.

    Raises:
        RuntimeError: if any required variables are missing.
    """
    _try_load_dotenv()

    jira_base_url = os.environ.get("JIRA_BASE_URL", "").strip().rstrip("/")
    jira_user_email = os.environ.get("JIRA_USER_EMAIL", "").strip()
    jira_api_token = os.environ.get("JIRA_API_TOKEN", "").strip()
    webhook_shared_secret = os.environ.get("WEBHOOK_SHARED_SECRET", "").strip()

    missing: List[str] = []
    if not jira_base_url:
        missing.append("JIRA_BASE_URL")
    if not jira_user_email:
        missing.append("JIRA_USER_EMAIL")
    if not jira_api_token:
        missing.append("JIRA_API_TOKEN")
    if not webhook_shared_secret:
        missing.append("WEBHOOK_SHARED_SECRET")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Create python_webhook_app/.env (or export them) and restart the service."
        )

    return AppConfig(
        jira_base_url=jira_base_url,
        jira_user_email=jira_user_email,
        jira_api_token=jira_api_token,
        webhook_shared_secret=webhook_shared_secret,
    )
