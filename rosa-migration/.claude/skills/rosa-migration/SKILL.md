---
name: rosa-migration
description: "Migrate Jira issues from legacy project boards to the ROSAENG project using a hybrid approach: API move (first attempt) with pre-move/UI-move/post-move fallback. Guides managers through team selection, board identification, migration mode, sprint preservation, and custom JQL rules."
---

# ROSA Migration Workflow

Migrate Jira issues from legacy team boards (OCM, SREP, HCMSEC, SLSRE, etc.) into the centralized ROSAENG project. Each team gets their own board in ROSAENG with the Team field set, so issues automatically appear on the correct board.

## Context Management

Migrations can involve hundreds of issues. To avoid filling the conversation context window with per-issue output:
- **Always use `--log-file`** on `--migrate`, `--dry-run`, `--pre-move`, and `--post-move` commands. This writes per-issue details to a file while keeping stdout to a compact summary.
- **Never read entire log files** into context. Use `head`, `tail`, or `grep` to check specific sections.
- **Summarize results from the JSON log** (`migration-log.json`) rather than the text output — it's structured and compact.

## Migration Approach Overview

The migration uses a **two-track approach**:

1. **API Move (first attempt)**: The script tries to move issues directly via the Jira REST API. This is the simplest path and works on some projects.
2. **Hybrid Pre-Move/UI-Move/Post-Move (recommended fallback)**: When the API move silently fails (which happens on most projects including SREP, AAP, HCMSEC), the workflow switches to a three-phase hybrid approach:
   - **Pre-move**: Script tags issues with a `rosa-migrate-{team}` label and saves a manifest JSON with pre-move field values and target mappings
   - **UI bulk move**: The user moves the tagged issues through Jira's web UI bulk move wizard (which bypasses the screen restrictions that block the API)
   - **Post-move**: Script reads the manifest, finds each issue by its old key (Jira redirects), and applies Team field, status transitions, component mappings, and sprint data

Always try the API move first. If it fails silently (returns 204 but the issue stays in the source project), switch to the hybrid approach.

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

**Note on hybrid approach**: When using the hybrid pre-move/UI-move/post-move workflow, sprint records and labels are applied during the `--post-move` phase (Phase 8b). The pre-move manifest captures the sprint data needed to apply them after the UI move completes.

## Phase 5: Custom JQL Rules

Ask if the manager wants to add custom JQL rules to their ROSAENG board filter. This is optional — the default filter (`project = ROSAENG AND Team = "<team-uuid>"`) is usually sufficient.

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

## Phase 7: Dry Run and API Move Attempt

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

### Attempting API Move

After manager approval, try the direct API move first:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --migrate --board <board_id> --team "<team>" --mode lazy --log-file artifacts/rosa-migration/migration.log
```

Add sprint flags based on the manager's Phase 4 choice:
- Sprint records: `--sprint-records` (and optionally `--sprint-count N`)
- Sprint labels: `--sprint-labels` (and optionally `--sprint-count N`)
- Both: `--sprint-records --sprint-labels`

**Always use `--log-file`** to keep per-issue output out of the conversation context.

The script processes issues one at a time with rate limiting. It reports progress and any failures.

### Checking for Silent Failures

After the API move completes, check the log output carefully. If you see "Silent move failure" errors or the summary shows issues that were reported as successful but remain in the source project, the API move is silently failing. This is common — it happens on most source projects (SREP, AAP, HCMSEC, and others).

If the API move works, proceed to Phase 9 (Rename Legacy Board). If it fails, proceed to Phase 8 (Hybrid Migration).

## Phase 8: Hybrid Migration (Pre-Move / UI Move / Post-Move)

This is the recommended fallback when the API move silently fails, which happens on most projects. The Jira Cloud REST API returns 204 but ignores the project change when the `project` field is not on the source project's edit screen.

### Phase 8a: Pre-Move Tagging

Run the pre-move step to tag all target issues and save a manifest:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --pre-move --board <board_id> --team "<team>" --mode lazy --log-file artifacts/rosa-migration/pre-move.log
```

Or with custom JQL:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --pre-move --jql "<jql>" --team "<team>" --mode lazy --log-file artifacts/rosa-migration/pre-move.log
```

For interactive mode, include `--decisions '<json>'`.

This does two things:
1. **Tags every issue** with a `rosa-migrate-<team>` label (e.g., `rosa-migrate-aurora`) so they can be found in the Jira UI
2. **Saves a manifest** JSON file (e.g., `artifacts/rosa-migration/pre-move-manifest-aurora.json`) containing each issue's pre-move field values and target mappings (status, type, components, sprint data)

After pre-move completes, tell the manager how many issues were tagged and confirm the manifest was saved.

### Phase 8b: UI Bulk Move (User Action)

Guide the manager through the Jira UI bulk move. This must be done by the user in their browser — Claude cannot do this step.

Give the manager these instructions:

1. **Open the source project in Jira** — go to `https://redhat.atlassian.net/projects/<SOURCE_PROJECT>/board`

2. **Find the tagged issues** — use this JQL in the issue navigator:
   ```
   project = <SOURCE_PROJECT> AND labels = "rosa-migrate-<team>"
   ```
   For example: `project = SREP AND labels = "rosa-migrate-aurora"`

3. **Select all issues** — click the checkbox at the top of the list to select all visible issues. If there are more than one page, you may need to do this in batches.

4. **Start bulk change** — click the "..." menu (or "Bulk change") at the top right, then select **"Bulk change all X issues"**

5. **Choose "Move Issues"** — on the Operation step, select **Move Issues** and click Next

6. **Select target project** — choose **ROSAENG** as the target project

7. **Map issue types** — keep the same issue types where possible. If a type does not exist in ROSAENG, map it to **Task**

8. **Map statuses** — Jira will ask for status mappings for each type. Map them as closely as possible to the ROSAENG workflow:
   - New/Open/To Do -> **New**
   - In Progress/In Development -> **In-Progress**
   - Code Review/In Review -> **Review**
   - Done/Closed/Resolved -> **Closed**
   - Backlog -> **Backlog**
   - Refinement/Grooming -> **Refinement**

9. **Confirm and execute** — review the summary and click **Confirm**. Jira will process the moves in the background and send an email when done.

10. **Wait for completion** — the bulk move may take a few minutes for large batches. The user will receive an email from Jira when it finishes.

Tell the manager to let you know when the bulk move is complete so you can proceed with the post-move step.

### Phase 8c: Post-Move Field Application

After the user confirms the UI bulk move is complete, run the post-move step:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --post-move --team "<team>" --log-file artifacts/rosa-migration/post-move.log
```

Add sprint flags based on the manager's Phase 4 choice:
- Sprint records: `--sprint-records` (and optionally `--sprint-count N`)
- Sprint labels: `--sprint-labels` (and optionally `--sprint-count N`)
- Both: `--sprint-records --sprint-labels`

**Always use `--log-file`** to keep per-issue output out of the conversation context.

The post-move step reads the manifest and for each issue:
1. Looks up the issue by its old key (Jira redirects old keys to the new ROSAENG key)
2. Sets the **Team field** to the correct ROSA team
3. Applies **status transitions** to match the pre-move status (mapped to ROSAENG workflow)
4. Sets **component mappings** from the manifest
5. Applies **sprint data** (records and/or labels, based on flags)
6. **Removes the migration tag** (`rosa-migrate-<team>` label)

After post-move completes, check the summary for any failures. If individual issues failed, you can re-run post-move — it is idempotent and will skip issues that are already correct.

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
**Migration Method**: <API Move / Hybrid (Pre-Move + UI Bulk Move + Post-Move)>

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

### Migration Method
<Describe which method was used: API move or hybrid. If hybrid, note that pre-move tagging, UI bulk move, and post-move field application were performed.>

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

When using the hybrid approach, sprint data is applied during the `--post-move` phase after the UI bulk move is complete.

### What Moves, What Stays
- Only issues matching the board filter (or custom JQL) are migrated
- The original issue key becomes a redirect to the new ROSAENG key
- Attachments, comments, and history are preserved
- Watchers and votes are preserved

### Permissions
The manager needs "Move Issues" permission on both the source project and ROSAENG. If they get permission errors, they should contact aminter.

### Team Field and JQL (UUID Requirement)
The Team field (`customfield_10001`) is a Jira Teams field. In JQL, it must be queried by **team UUID**, not display name. For example:
- **Correct**: `Team = d82adfd4-85ef-442a-b3f7-1fb533082fdd`
- **Incorrect**: `Team = "[ROSA] Aurora"` (returns 0 results even if the team exists)

This is a Jira Cloud platform limitation. All ROSAENG board filters use the UUID format. The script's `--update-filter` command handles this automatically using the team mapping. If you ever need to write JQL that filters by Team, always use the UUID from the team mapping, never the display name.

### Known Issues: Silent Move API Failures
The Jira Cloud REST API silently fails to move issues between projects when the `project` field is not on the source project's edit screen. The `PUT /rest/api/3/issue/{key}` endpoint returns 204 but ignores the project change. The bulk move API (`POST /rest/api/3/bulk/issues/move`) returns 500. This affects SREP, AAP, HCMSEC, and likely most other source projects.

**The recommended approach is the hybrid pre-move/UI-move/post-move workflow** (Phase 8), which bypasses this limitation entirely by using Jira's web UI for the actual move operation.

The script also includes these API-level mitigations (tried automatically before falling back to hybrid):
1. Verifies every API move actually took effect (detects silent failures)
2. Tries without override params first, then with `overrideScreenSecurity`/`overrideEditableFlag` as fallback
3. Tries both API v2 and v3
4. Provides `--diagnose` to check permissions and configuration before attempting migration

If API moves fail, always use the hybrid approach. Do not use clone-based fallbacks.

### Diagnosing Move Failures

If moves fail or return "Silent move failure" errors, run diagnostics on a single issue first:

```bash
python3 .claude/skills/rosa-migration/scripts/migrate.py --diagnose --issue <ISSUE_KEY> --team "<team>"
```

This checks permissions, issue type compatibility, and field configuration. Common causes:
- The `project` field is not on the source project's edit screen (most common — use hybrid approach)
- Missing `Move Issues` permission in the source project
- Issue type doesn't exist in ROSAENG
- Workflow/field configuration incompatibility between source and target projects
