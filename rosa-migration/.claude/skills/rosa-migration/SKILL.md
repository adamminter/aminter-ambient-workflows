---
name: rosa-migration
description: "Migrate Jira issues from legacy project boards to the ROSAENG project. Guides managers through team selection, board identification, migration mode (lazy vs interactive), sprint preservation, and custom JQL rules."
---

# ROSA Migration Workflow

Migrate Jira issues from legacy team boards (OCM, SREP, HCMSEC, SLSRE, etc.) into the centralized ROSAENG project. Each team gets their own board in ROSAENG with the Team field set, so issues automatically appear on the correct board.

## Context Management

Migrations can involve hundreds of issues. To avoid filling the conversation context window with per-issue output:
- **Always use `--log-file`** on `--migrate` and `--dry-run` commands. This writes per-issue details to a file while keeping stdout to a compact summary.
- **Never read entire log files** into context. Use `head`, `tail`, or `grep` to check specific sections.
- **Summarize results from the JSON log** (`migration-log.json`) rather than the text output — it's structured and compact.

## Phase 0: Credential Setup

Before any migration work, ensure the user's environment is configured.

### Check Environment Variables

Run a quick test to see if credentials are already set:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --list-teams
```

If this fails with a missing environment variable error, help the user set them up.

### JIRA_URL and ATLASSIAN_ORG_ID

These are constants — the same for everyone:

```bash
export JIRA_URL="https://redhat.atlassian.net"
export ATLASSIAN_ORG_ID="4k7c08c0-9kb0-1aca-k606-d1417cc24104"
```

### JIRA_EMAIL

Ask the user for their Red Hat email address:

```bash
export JIRA_EMAIL="<their-email>@redhat.com"
```

### JIRA_API_TOKEN

If the user doesn't have one, walk them through it:

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a label like "ROSA Migration"
4. Copy the token (it won't be shown again)
5. Set it:

```bash
export JIRA_API_TOKEN="<paste-token-here>"
```

After all four are set, re-run `--list-teams` to verify the connection works.

## Phase 1: Team Selection

Ask the manager which team(s) they manage. Show them the team list:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --list-teams
```

This shows each team, their suggested source project/board, and the ROSAENG board they'll migrate to. The manager should confirm which team(s) are theirs.

For team details and pre-computed mappings, see `resources/team_mapping.md`.

## Phase 2: Source Board Confirmation

For each team the manager selects, confirm their source board. The script suggests boards based on what we know, but the manager may use a different one. They can provide:
- A board ID (e.g., `3833`)
- A board URL (e.g., `https://redhat.atlassian.net/jira/software/c/projects/OCM/boards/3833`)

If they provide a URL, extract the board ID from it (the number after `/boards/`).

If the manager wants to use custom JQL instead of a board filter, they can provide that directly and use `--jql` instead of `--board`.

## Phase 3: Discovery

Run discovery to show what issues will be migrated:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --discover --board <board_id> --team "<team>"
```

Or with custom JQL:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --discover --jql "<jql>" --team "<team>"
```

This shows issue counts by status, type, and component. Review the output with the manager. Point out any unmapped statuses, types, or components — these will matter in Phase 6.

## Phase 4: Sprint Migration (Scrum Boards Only)

If the source board is scrum and has sprints, ask if they want to migrate sprint data.

To discover sprints:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --list-sprints --board <board_id>
```

Ask the manager which sprint migration approach they prefer:

### Option A: Sprint Records (recommended)
Recreates actual sprint records on the ROSAENG board with full metadata: start/end dates, sprint goals, and issue membership. Closed sprints are created, started, and immediately completed to preserve history. Active and future sprints are created in their matching state.

Use `--sprint-records` and optionally `--sprint-count N` to limit to the last N sprints.

This gives the team full sprint history on their new board — velocity charts, burndown data, and the ability to inspect what was in each sprint.

### Option B: Sprint Labels (lightweight)
Sprint names are preserved as labels on each issue (e.g., `sprint:Sprint-42`). Use `--sprint-labels` and optionally `--sprint-count N`.

This is simpler but loses sprint metadata (dates, goals). Issues won't appear in sprint history views.

### Option C: Both
Use `--sprint-records --sprint-labels` to get full sprint records AND labels as a backup. Labels persist even if sprint records are later modified.

### Option D: None
Issues are migrated without any sprint data.

## Phase 5: Custom JQL Rules

Ask if the manager wants to add custom JQL rules to their ROSAENG board filter. This is optional — the default filter (`project = ROSAENG AND Team = "[ROSA] <team>"`) is usually sufficient.

If they want custom rules:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --update-filter --team "<team>" --extra-jql "AND component = clusters-service"
```

## Phase 6: Migration Mode

Ask the manager to choose a migration mode:

### Lazy Mode
Fully automated. The script makes all mapping decisions:
- Status: mapped using a built-in table (see `resources/team_mapping.md`)
- Components: exact name match to ROSAENG components; unmatched components are skipped
- Issue types: mapped 1:1 where possible; unmapped types converted to Task
- Team field: set automatically

### Interactive Mode
The script scans all issues first and reports any conflicts:
- Components that don't exist in ROSAENG
- Issue types that need mapping
- Statuses that don't have a 1:1 mapping

Present each conflict to the manager and collect their decision. They can say "use this for all similar conflicts." Pass decisions back to the script as JSON via `--decisions`.

The decisions JSON format:
```json
{
  "type_map": {"SourceType": "TargetType"},
  "status_map": {"SourceStatus": "TargetStatus"},
  "component_map": {"SourceComponent": "TargetComponent"}
}
```

## Phase 7: Dry Run

**Always run a dry run first.** This is not optional.

**Important: Always use `--log-file` to avoid flooding the conversation context with per-issue output.** The log file captures full detail; stdout shows only the summary.

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --migrate --board <board_id> --team "<team>" --mode lazy --dry-run --log-file artifacts/rosa-migration/dry-run.log
```

Or for interactive with decisions:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --migrate --board <board_id> --team "<team>" --mode interactive --decisions '<json>' --dry-run --log-file artifacts/rosa-migration/dry-run.log
```

After the dry run, read the summary from stdout and share it with the manager. If they want to see specific issues, read targeted sections from the log file (e.g., `head -20` or `grep FAILED`). **Do not read the entire log file into context** — it can be very large. Get explicit approval before proceeding.

## Phase 8: Execute Migration

After manager approval:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --migrate --board <board_id> --team "<team>" --mode lazy --log-file artifacts/rosa-migration/migration.log
```

Add sprint flags based on the manager's Phase 4 choice:
- Sprint records: `--sprint-records` (and optionally `--sprint-count N`)
- Sprint labels: `--sprint-labels` (and optionally `--sprint-count N`)
- Both: `--sprint-records --sprint-labels`

**Always use `--log-file`** to keep per-issue output out of the conversation context.

The script processes issues one at a time with rate limiting. It reports progress and any failures.

### If Moves Fail

If moves fail or return "Silent move failure" errors, run diagnostics on a single issue first:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --diagnose --issue <ISSUE_KEY> --team "<team>"
```

This checks permissions, issue type compatibility, and field configuration. Common causes:
- Missing `Move Issues` permission in the source project
- Issue type doesn't exist in ROSAENG
- Workflow/field configuration incompatibility between source and target projects

If the move API is fundamentally blocked (e.g., some HCMSEC configurations), use the clone fallback:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --migrate --board <board_id> --team "<team>" --mode lazy --fallback-clone --log-file artifacts/rosa-migration/migration.log
```

The `--fallback-clone` flag creates a new issue in ROSAENG with the same fields and links it to the original when a direct move fails. This preserves summary, description, labels, components, assignee, and priority, but does **not** preserve comments, attachments, or history.

**After migration completes, generate the migration report** (see Phase 10).

## Phase 9: Rename Legacy Board

After successful migration, rename the old board:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --rename-legacy --board <board_id>
```

This appends " (Legacy)" to the source board name.

## Phase 10: Generate Report and Wrap Up

### Generate Migration Report

After the migration, create a report at `artifacts/rosa-migration/migration-report.md` with the following structure:

```markdown
# ROSA Migration Report

**Team**: <team name>
**Manager**: <manager name/email>
**Date**: <date>
**Migration Mode**: <lazy/interactive>

## Summary

| Metric | Count |
|--------|-------|
| Total issues found | X |
| Successfully migrated | X |
| Failed | X |
| Skipped (already in ROSAENG) | X |

## Source

- **Project**: <source project>
- **Board**: <source board name> (ID: <board_id>)
- **Filter JQL**: <source JQL>

## Destination

- **Project**: ROSAENG
- **Board ID**: <rosaeng_board_id>
- **Board URL**: https://redhat.atlassian.net/jira/software/c/projects/ROSAENG/boards/<rosaeng_board_id>

## Migration Details

### Status Mapping Applied
| Source Status | ROSAENG Status | Count |
|...|...|...|

### Issue Type Mapping Applied
| Source Type | ROSAENG Type | Count |
|...|...|...|

### Component Mapping
| Source Component | ROSAENG Component | Count |
|...|...|...|

## Sprint Labels Applied
(if applicable — list sprint names and issue counts)

## Custom Decisions
(if interactive mode — list all conflict resolutions the manager made)

## Failures
(if any — list issue keys and error messages)

## Legacy Board
- **Renamed**: <old name> -> <old name> (Legacy)

## Notes
(any additional observations or things the ROSA PM should review)
```

Also save a machine-readable log to `artifacts/rosa-migration/migration-log.json`.

### Tell the Manager

- Migration is complete
- Their new board is at `https://redhat.atlassian.net/jira/software/c/projects/ROSAENG/boards/<board_id>`
- The migration report has been saved and can be shared with the ROSA Project Manager
- Reach out to **aminter** (aminter@redhat.com) with any questions

## Important Caveats

### Sub-tasks
Sub-tasks are migrated with their parent. If a parent is in the migration set, its sub-tasks are included automatically. Do not migrate sub-tasks independently.

### Epics
Epics are migrated like any other issue. Epic-child links are preserved since both end up in ROSAENG.

### Issue Links
Cross-project issue links are preserved by Jira automatically after the move.

### Sprint Data
ROSAENG scrum boards support sprints. Two approaches are available:
- **Sprint records** (`--sprint-records`): Full sprint history is recreated on the ROSAENG board with dates, goals, and issue membership. Closed sprints appear in sprint history/velocity charts.
- **Sprint labels** (`--sprint-labels`): Lightweight — sprint names are added as issue labels for reference. The manager can create new sprints in ROSAENG and drag issues in manually.

### What Moves, What Stays
- Only issues matching the board filter (or custom JQL) are migrated
- The original issue key becomes a redirect to the new ROSAENG key
- Attachments, comments, and history are preserved
- Watchers and votes are preserved

### Permissions
The manager needs "Move Issues" permission on both the source project and ROSAENG. If they get permission errors, they should contact aminter.

### Known Issues: HCMSEC Project Moves
The Jira Cloud REST API may silently fail to move issues from HCMSEC to ROSAENG due to workflow or field configuration differences. The `PUT /rest/api/3/issue/{key}` endpoint returns 204 but doesn't actually change the project, and the bulk move API (`POST /rest/api/3/bulk/issues/move`) returns 500.

The script now:
1. Verifies every move actually took effect (detects silent failures)
2. Uses `overrideScreenSecurity` and `overrideEditableFlag` parameters to bypass field restrictions
3. Tries both API v2 and v3
4. Offers `--fallback-clone` to create new issues in ROSAENG when moves fail
5. Provides `--diagnose` to check permissions and configuration before attempting migration

If even the clone fallback fails, escalate to a Jira admin to investigate the project configuration.
