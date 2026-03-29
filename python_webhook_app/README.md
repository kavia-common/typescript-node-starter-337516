# Jira Webhook MockAPI (FastAPI) — `/triage/auto`

This is a small FastAPI backend that receives **Jira Automation issue-created webhooks**, validates a shared secret header, extracts the issue key, and **adds a comment back to the same Jira issue**.

## Endpoint

- **POST** `/triage/auto`
- Header required: `X-Webhook-Secret: <shared-secret>`
- Body: Jira Automation **issue-created** payload (must include `issue.key`)
- Response: static JSON object (plus parsed `issue_key` and whether comment posted)

## Configuration (environment variables)

Create environment variables (or a `.env` file in `python_webhook_app/`):

- `JIRA_BASE_URL` (e.g. `https://kavia-team.atlassian.net`)
- `JIRA_USER_EMAIL` (your Atlassian email)
- `JIRA_API_TOKEN` (your Atlassian API token)
- `WEBHOOK_SHARED_SECRET` (shared secret you also configure in Jira Automation)

Example:

```bash
export JIRA_BASE_URL="https://kavia-team.atlassian.net"
export JIRA_USER_EMAIL="aditimishra@kavia.ai"
export JIRA_API_TOKEN="***"
export WEBHOOK_SHARED_SECRET="kavia-triage-..."
```

## Run locally

From the repo root:

```bash
cd python_webhook_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Your webhook URL will be:

- `http://<your-host>:8000/triage/auto`

## Jira Automation setup

In Jira:

1. Go to **Project settings → Automation**
2. Create rule:
   - **Trigger:** *Issue created*
3. Add **Action:** *Send web request*
   - **Webhook URL:** `https://<public-host>/triage/auto`
   - **HTTP method:** `POST`
   - **Headers:**
     - `X-Webhook-Secret` = `<your WEBHOOK_SHARED_SECRET>`
     - `Content-Type` = `application/json`
   - **Webhook body:**
     - Choose **"Issue data (JSON)"** (or the default issue-created payload option)

When an issue is created, the rule will call this service, which will add a comment back on that issue.

## Notes / Troubleshooting

- If you receive `401 Invalid or missing X-Webhook-Secret`, ensure the header matches `WEBHOOK_SHARED_SECRET`.
- If the service returns `400 Unable to determine issue key...`, ensure the payload contains `issue.key`.
- If comment posting fails, confirm `JIRA_USER_EMAIL` + `JIRA_API_TOKEN` are valid and have permission to comment.
