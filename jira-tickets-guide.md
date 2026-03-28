# How to List All Jira Tickets Assigned to You

## Summary of Findings

I attempted to retrieve your Jira tickets using the credentials found in the workspace `.env` file:

| Setting | Value |
|---------|-------|
| **Jira URL** | `https://kavia-team.atlassian.net` |
| **User Email** | `aditimishra@kavia.ai` |
| **API Token** | *(configured in `.env` as `JIRA_API_TOKEN`)* |

### Results

- **Authentication Issue**: The `/rest/api/3/myself` endpoint returned `"Client must be authenticated"`, indicating the `JIRA_API_TOKEN` value in `.env` may be a **password** rather than a valid **Jira Cloud API token**. Jira Cloud requires API tokens (not passwords) for REST API authentication.
- **Search Results**: The search endpoint returned **0 issues** and **0 projects**, which confirms either:
  1. The API token is invalid/expired, or
  2. The account has no project permissions on this Jira instance.

---

## How to Fix: Generate a Valid Jira API Token

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Log in with your Atlassian account (`aditimishra@kavia.ai`)
3. Click **"Create API token"**
4. Give it a label (e.g., "Kavia Workspace")
5. Copy the generated token
6. Update your `.env` file:
   ```
   JIRA_API_TOKEN=<your-new-api-token-here>
   ```

---

## Option 1: List Tickets via Jira Web UI (Quickest)

1. Go to [https://kavia-team.atlassian.net](https://kavia-team.atlassian.net)
2. Log in with your account
3. Click on **"Filters"** in the top navigation bar
4. Select **"My open issues"** — this shows all issues assigned to you
5. Alternatively, click **"Advanced issue search"** and enter this JQL:

```
assignee = currentUser() ORDER BY updated DESC
```

This will show all Jira tickets assigned to you, sorted by most recently updated.

### Useful JQL Variants

| What you want | JQL Query |
|---------------|-----------|
| All tickets assigned to me | `assignee = currentUser() ORDER BY updated DESC` |
| Only open tickets | `assignee = currentUser() AND status != Done ORDER BY updated DESC` |
| Tickets in a specific project | `assignee = currentUser() AND project = "PROJECT_KEY" ORDER BY updated DESC` |
| Tickets updated in last 7 days | `assignee = currentUser() AND updated >= -7d ORDER BY updated DESC` |
| High priority tickets | `assignee = currentUser() AND priority in (High, Highest) ORDER BY updated DESC` |

---

## Option 2: List Tickets via REST API (curl)

Once you have a valid API token, run this command:

```bash
curl -s -u "aditimishra@kavia.ai:<YOUR_API_TOKEN>" \
  "https://kavia-team.atlassian.net/rest/api/3/search/jql?jql=assignee%3DcurrentUser()%20ORDER%20BY%20updated%20DESC&maxResults=50&fields=key,summary,status,priority,issuetype,updated,project" \
  -H "Accept: application/json" | python3 -m json.tool
```

Replace `<YOUR_API_TOKEN>` with your actual Jira API token.

### Understanding the Response

The API returns a JSON object with an `issues` array. Each issue contains:
- `key` — The ticket ID (e.g., `PROJ-123`)
- `fields.summary` — The ticket title
- `fields.status.name` — Current status (e.g., "To Do", "In Progress", "Done")
- `fields.priority.name` — Priority level
- `fields.issuetype.name` — Issue type (e.g., "Bug", "Story", "Task")
- `fields.updated` — Last updated timestamp
- `fields.project.name` — Project name

---

## Option 3: Use a Script to Fetch and Display Tickets

A utility script has been provided at `utils/list_jira_tickets.py`. To use it:

```bash
# Set environment variables (or they'll be read from .env)
export JIRA_URL="https://kavia-team.atlassian.net"
export JIRA_USER_EMAIL="aditimishra@kavia.ai"
export JIRA_API_TOKEN="<your-valid-api-token>"

# Run the script
python3 utils/list_jira_tickets.py
```

---

## Next Steps

1. **Generate a valid Jira API token** from [Atlassian API Tokens page](https://id.atlassian.com/manage-profile/security/api-tokens)
2. **Update the `.env` file** with the new token
3. **Use any of the 3 options above** to list your assigned tickets
4. If you still see 0 results after updating the token, verify that your Atlassian account has access to projects on the `kavia-team` Jira instance
