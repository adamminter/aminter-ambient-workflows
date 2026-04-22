# aminter-ambient-workflows

Personal collection of [Ambient Code](https://ambient.anthropic.com) workflows for automating recurring engineering tasks. Each workflow is a self-contained, Claude-guided automation that can be loaded into the Ambient Code Platform (ACP) and run interactively.

## Available Workflows

| Workflow | Description |
|----------|-------------|
| [rosa-migration](rosa-migration/) | Migrate Jira issues from legacy project boards (OCM, SREP, HCMSEC, SLSRE) into the centralized ROSAENG project. Supports 16 teams, two migration modes, sprint preservation, and guided conflict resolution. |

## Loading a Custom Workflow

You can load any workflow from this repository into ACP using one of the methods below.

### From the ACP UI

1. Open [ambient.anthropic.com](https://ambient.anthropic.com)
2. Click **Custom Workflow...** (or the **+** button on the workflow picker)
3. Enter the following details:
   - **Git URL**: `https://github.com/adamminter/aminter-ambient-workflows`
   - **Branch**: `main`
   - **Path**: the workflow directory name (e.g. `rosa-migration`)
4. Click **Load** — the workflow will start a new session with its guided prompts

### From the Claude Code CLI

If you prefer the terminal, clone this repo and point Claude Code at the workflow directory:

```bash
git clone https://github.com/adamminter/aminter-ambient-workflows.git
cd aminter-ambient-workflows/rosa-migration
claude
```

Claude will automatically pick up the `.ambient/ambient.json`, `CLAUDE.md`, and skills defined in the workflow.

### Testing a Branch

To test changes on a feature branch before merging, use the **Custom Workflow...** option in the ACP UI and specify your branch name instead of `main`. ACP caches workflows for ~5 minutes, so allow a short delay after pushing before reloading.

## Repository Structure

```
aminter-ambient-workflows/
├── README.md                          # This file
└── rosa-migration/                    # Workflow directory
    ├── .ambient/ambient.json          # Workflow metadata (required)
    ├── .claude/settings.json          # Permission allowlist
    ├── .claude/skills/                # Skill definitions
    ├── CLAUDE.md                      # Persistent context
    ├── README.md                      # Workflow-specific docs
    ├── scripts/                       # Automation scripts
    └── artifacts/                     # Generated output
```

Each workflow follows the structure defined by the [Ambient Code Workflow Development Guide](https://github.com/ambient-code/workflows).

## Adding a New Workflow

1. Create a new directory in kebab-case (e.g. `my-new-workflow/`)
2. Add `.ambient/ambient.json` with the required fields: `name`, `description`, `systemPrompt`, `startupPrompt`
3. Add skills under `.claude/skills/<skill-name>/SKILL.md`
4. Add a `README.md` describing the workflow's purpose and usage
5. Test on a feature branch via **Custom Workflow...** before merging to `main`
