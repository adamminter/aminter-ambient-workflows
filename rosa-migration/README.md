# ROSA Jira Project Migration

An Ambient workflow that guides ROSA engineering managers through migrating their team's Jira issues from legacy project boards (OCM, SREP, HCMSEC, SLSRE) into the centralized **ROSAENG** project.

## What It Does

1. **Sets up credentials** — walks you through creating a Jira API token if you don't have one
2. **Identifies your team** — shows pre-mapped source boards and ROSAENG destinations
3. **Discovers issues** — previews what will be migrated with status/type/component breakdowns
4. **Preserves sprints** — optionally saves sprint names as labels on migrated issues
5. **Migrates issues** — moves issues to ROSAENG with correct Team field, status, type, and components
6. **Generates a report** — produces a migration report for the ROSA Project Manager to review

## Supported Teams

| Team | Source Project | Board Type |
|------|---------------|------------|
| AMS | OCM | Scrum |
| Aurora | SREP | Kanban |
| CLI/Terraform | OCM | Scrum |
| Coffee | OCM | Scrum |
| FedRAMP Core | HCMSEC | Kanban |
| Fleet Manager | OCM | Kanban |
| Focaccia | OCM | Scrum |
| GovCloud SRE | HCMSEC | Scrum |
| Hulk | SREP | Scrum |
| OSD GCP | OCM | Scrum |
| Operators | OCM | Scrum |
| Orange | SREP | Scrum |
| Regionality | ROSAENG | Kanban |
| Rocket | SREP | Scrum |
| Service Lifecycle | SLSRE | Scrum |
| Thor | SREP | Scrum |

## Prerequisites

- **Jira Cloud access** to `redhat.atlassian.net`
- **"Move Issues" permission** on both your source project and ROSAENG
- **A Jira API token** — the workflow will help you create one if needed

## Usage

### In Ambient

Select **"ROSA Jira Project Migration"** from the workflow list, or load as a Custom Workflow:

- **URL**: `https://github.com/adamminter/aminter-ambient-workflows.git`
- **Branch**: `main`
- **Path**: `rosa-migration`

### In Claude Code (local)

If you received this as a zip file or cloned the repo, run Claude Code from the workflow directory:

```bash
unzip rosa-migration.zip   # if using the zip distribution
cd rosa-migration
claude
```

Claude will automatically load the workflow configuration and guide you through the migration. Just tell it which team you want to migrate.

## Migration Modes

### Lazy Mode
Fully automated. The script handles all mapping decisions using built-in tables for statuses, issue types, and components.

### Interactive Mode
The script scans for conflicts first (unmapped components, types, statuses) and asks you to resolve each one before proceeding. Your decisions are remembered for similar conflicts.

## Outputs

| Artifact | Path |
|----------|------|
| Migration Report | `artifacts/rosa-migration/migration-report.md` |
| Migration Log | `artifacts/rosa-migration/migration-log.json` |

## Questions?

Contact **aminter** (aminter@redhat.com) — ROSA Project Manager.
