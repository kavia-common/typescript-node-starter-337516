"""
FastAPI application entrypoint for the Jira "issue created" webhook mock backend.

This service exposes:
  - POST /triage/auto: Validates a shared secret header, extracts the Jira issue key,
    performs minimal processing, posts a comment back to the originating issue, and
    returns a static JSON response.

Run locally:
  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.config import AppConfig, load_config
from app.services.jira_client import JiraClient
from app.services.triage_service import TriageService

logger = logging.getLogger("jira_webhook_app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class TriageAutoResponse(BaseModel):
    """Response returned from the triage automation endpoint."""

    ok: bool = Field(..., description="Whether the webhook was accepted and processed.")
    action: str = Field(..., description="The automation action that was executed.")
    issue_key: str = Field(..., description="Jira issue key parsed from the webhook payload.")
    comment_posted: bool = Field(..., description="True if the comment was posted successfully.")
    message: str = Field(..., description="Human-readable message for debugging/integration logs.")


def _build_app() -> FastAPI:
    """Create and configure the FastAPI app instance."""
    openapi_tags = [
        {
            "name": "Triage",
            "description": "Endpoints for Jira webhook-driven triage automations.",
        },
        {
            "name": "Docs",
            "description": "Helper endpoints describing how to integrate with Jira Automation.",
        },
    ]

    app = FastAPI(
        title="Jira Webhook MockAPI (Triage)",
        description=(
            "A minimal FastAPI backend that receives Jira Automation webhooks, validates a shared "
            "secret, extracts the originating issue key, and writes back to the issue via a comment."
        ),
        version="1.0.0",
        openapi_tags=openapi_tags,
    )

    config: AppConfig = load_config()
    jira_client = JiraClient(
        base_url=config.jira_base_url,
        user_email=config.jira_user_email,
        api_token=config.jira_api_token,
    )
    triage_service = TriageService(
        webhook_secret=config.webhook_shared_secret,
        jira_client=jira_client,
    )

    @app.get("/docs/jira-automation", tags=["Docs"], summary="Jira Automation setup help")
    def jira_automation_help() -> Dict[str, Any]:
        """
        Return a short guide for configuring Jira Automation to call this service.

        This is provided as a convenience so the service is self-documenting.
        """
        return {
            "endpoint": "/triage/auto",
            "method": "POST",
            "required_headers": {"X-Webhook-Secret": "your-shared-secret"},
            "expected_payload": "Jira Automation issue-created webhook payload (contains issue.key).",
            "notes": [
                "Configure a Jira Automation rule: Trigger = Issue created.",
                "Action = Send web request (POST) to this endpoint.",
                "Set 'Headers' to include X-Webhook-Secret.",
                "Set 'Webhook body' to 'Issue data (JSON)' or the default issue payload.",
            ],
        }

    # PUBLIC_INTERFACE
    @app.post(
        "/triage/auto",
        tags=["Triage"],
        summary="Receive issue-created webhook and comment back on the issue",
        response_model=TriageAutoResponse,
        response_class=JSONResponse,
        operation_id="triageAuto",
    )
    def triage_auto(
        payload: Dict[str, Any],
        x_webhook_secret: Optional[str] = Header(
            default=None,
            alias="X-Webhook-Secret",
            description="Shared secret used to authenticate the webhook sender (Jira Automation).",
        ),
    ) -> TriageAutoResponse:
        """
        Receive a Jira "issue created" webhook, validate a shared secret, and write back.

        Parameters:
            payload: JSON payload sent by Jira Automation (issue-created). Must include an issue key.
            x_webhook_secret: Shared secret header value from `X-Webhook-Secret`.

        Returns:
            TriageAutoResponse: Static response plus the parsed issue key and whether a comment was posted.
        """
        try:
            result = triage_service.handle_issue_created_webhook(
                payload=payload,
                received_secret=x_webhook_secret,
            )
        except ValueError as exc:
            # Validation / payload issues
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected error handling webhook")
            raise HTTPException(status_code=500, detail="Internal error processing webhook") from exc

        return TriageAutoResponse(
            ok=True,
            action="triage/auto",
            issue_key=result.issue_key,
            comment_posted=result.comment_posted,
            message="Triage automation executed (static response).",
        )

    return app


app = _build_app()
