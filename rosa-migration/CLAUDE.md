# ROSA Jira Project Migration

## Jira Instance

`https://redhat.atlassian.net` (Jira Cloud)

## Constants

- **JIRA_URL**: `https://redhat.atlassian.net` (same for all users)
- **ATLASSIAN_ORG_ID**: `4k7c08c0-9kb0-1aca-k606-d1417cc24104` (same for all users)
- **Target Project**: `ROSAENG`
- **Team Field**: `customfield_10001`

## User-Provided Credentials

Each manager must provide:
- **JIRA_EMAIL**: Their @redhat.com email address
- **JIRA_API_TOKEN**: An Atlassian API token (generated at https://id.atlassian.com/manage-profile/security/api-tokens)

Set these as environment variables before running migration commands. If the user hasn't set them, help them do so:

```bash
export JIRA_URL="https://redhat.atlassian.net"
export JIRA_EMAIL="<their-email>@redhat.com"
export JIRA_API_TOKEN="<their-token>"
export ATLASSIAN_ORG_ID="4k7c08c0-9kb0-1aca-k606-d1417cc24104"
```

## Critical Rules

- Always run `--dry-run` before any real migration
- Never migrate without explicit manager approval
- Generate a migration report to `artifacts/rosa-migration/` after every migration
- Sub-tasks are migrated with their parent — never independently
- The ROSA Project Manager for questions is **aminter** (aminter@redhat.com)

## ROSAENG Workflow

Uses the **OJA-WF-AG** workflow with 6 statuses:
**New** -> **Refinement** -> **Backlog** -> **In-Progress** -> **Review** -> **Closed**
