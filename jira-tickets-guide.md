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
| Only open tickets | `assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC` |
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

## Option 3: Use the Script to Fetch and Display Tickets

A utility script is provided at `utils/list_jira_tickets.py`.

### Default: Show ALL Tickets Assigned to You

By default the script now fetches **all tickets** (any status) assigned to the current user using the JQL:

```
assignee = currentUser() ORDER BY updated DESC
```

```bash
# Set environment variables (or they'll be read from .env)
export JIRA_URL="https://kavia-team.atlassian.net"
export JIRA_USER_EMAIL="aditimishra@kavia.ai"
export JIRA_API_TOKEN="<your-valid-api-token>"

# List ALL tickets assigned to you (default)
python3 utils/list_jira_tickets.py

# Equivalent — explicitly pass --all
python3 utils/list_jira_tickets.py --all
```

### Open-Only Mode

To restrict to open/unresolved tickets only (the previous default behavior), use the `--open-only` flag:

```bash
# List only open/unresolved tickets
python3 utils/list_jira_tickets.py --open-only
```

This uses the JQL:

```
assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC
```

### Export Tickets to CSV

Use the `--csv` flag to export fetched issues to a CSV file. If no file path is specified, the default output file is `jira_tickets.csv` in the current working directory.

```bash
# Export all tickets to the default CSV file (jira_tickets.csv)
python3 utils/list_jira_tickets.py --csv

# Export all tickets to a specific file path
python3 utils/list_jira_tickets.py --csv my_tickets.csv

# Export only open/unresolved tickets to CSV
python3 utils/list_jira_tickets.py --open-only --csv open_issues.csv

# Export to a path in another directory
python3 utils/list_jira_tickets.py --csv reports/jira_export.csv
```

The CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| **Key** | Jira issue key (e.g., `PROJ-123`) |
| **Type** | Issue type (e.g., Bug, Story, Task) |
| **Priority** | Priority level (e.g., High, Medium, Low) |
| **Status** | Current status (e.g., To Do, In Progress, Done) |
| **Project** | Project name |
| **Summary** | Issue title/summary |
| **Updated** | Last updated date and time |

The `--csv` flag can be combined with `--open-only` or used alone (which defaults to all tickets). The table output is always printed to stdout regardless of whether CSV export is enabled — the CSV is written in addition to the console output.

### CLI Flags Summary

| Flag | Behavior |
|------|----------|
| *(no flag)* | List **all** tickets assigned to you (any status) |
| `--all` | Same as no flag — list all tickets (explicit) |
| `--open-only` | List only **open/unresolved** tickets |
| `--csv` | Export results to `jira_tickets.csv` (default path) |
| `--csv FILE` | Export results to the specified CSV file path |

### Output

The script displays a formatted table with columns: **Key**, **Type**, **Priority**, **Status**, **Project**, **Summary**, and **Updated** date. If `--csv` is specified, the same data is also written to a CSV file. If no issues are found, it prints a clear message. On authentication errors, it provides actionable troubleshooting steps.

---

## Next Steps

1. **Generate a valid Jira API token** from [Atlassian API Tokens page](https://id.atlassian.com/manage-profile/security/api-tokens)
2. **Update the `.env` file** with the new token
3. **Use any of the 3 options above** to list your assigned tickets
4. Use `--csv` to export your tickets for offline review or sharing
5. If you still see 0 results after updating the token, verify that your Atlassian account has access to projects on the `kavia-team` Jira instance
