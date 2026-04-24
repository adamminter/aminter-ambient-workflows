#!/usr/bin/env python3
"""
Migrate Jira issues from legacy project boards to the ROSAENG project.

Usage:
    python3 migrate.py --list-teams
    python3 migrate.py --list-components
    python3 migrate.py --discover --board 3833 --team "Coffee"
    python3 migrate.py --discover --jql "project=OCM AND ..." --team "Coffee"
    python3 migrate.py --list-sprints --board 3833
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode lazy --dry-run
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode lazy
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode interactive --decisions '{...}' --dry-run
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode lazy --sprint-labels --log-file migration.log
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode lazy --sprint-records --log-file migration.log
    python3 migrate.py --migrate --board 3833 --team "Coffee" --mode lazy --fallback-clone --log-file migration.log
    python3 migrate.py --diagnose --issue HCMSEC-123 --team "FedRAMP Core"
    python3 migrate.py --update-filter --team "Coffee" --extra-jql "AND component = clusters-service"
    python3 migrate.py --rename-legacy --board 3833

Environment variables required:
    JIRA_EMAIL, JIRA_API_TOKEN
Environment variables with defaults (no change needed):
    JIRA_URL (default: https://redhat.atlassian.net)
    ATLASSIAN_ORG_ID (default: 4k7c08c0-9kb0-1aca-k606-d1417cc24104)
"""

import os
import re
import sys
import json
import time
import argparse
import datetime
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = os.environ.get("JIRA_URL", "https://redhat.atlassian.net").rstrip("/")
AUTH = None
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
ORG_ID = os.environ.get("ATLASSIAN_ORG_ID", "4k7c08c0-9kb0-1aca-k606-d1417cc24104")
ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts/rosa-migration")

TARGET_PROJECT = "ROSAENG"
LOG_FILE = None


def log_detail(msg):
    """Print a detail line to the log file if set, otherwise to stdout."""
    if LOG_FILE:
        LOG_FILE.write(msg + "\n")
        LOG_FILE.flush()
    else:
        print(msg)

# ---------------------------------------------------------------------------
# Team mapping: source boards, ROSAENG boards, Jira team IDs
# ---------------------------------------------------------------------------

TEAM_MAP = {
    "AMS": {
        "source_project": "OCM",
        "source_board_id": 3844,
        "source_board_name": "ROSA Service Eng - AMS",
        "rosaeng_board_id": 11887,
        "rosaeng_filter_id": 107277,
        "jira_team_id": "971fb543-5d1b-4b9b-84f6-e70cb43e24b0",
        "jira_team_name": "[ROSA] AMS",
    },
    "Aurora": {
        "source_project": "SREP",
        "source_board_id": 11464,
        "source_board_name": "SREP Aurora",
        "rosaeng_board_id": 11688,
        "rosaeng_filter_id": 107278,
        "jira_team_id": "d82adfd4-85ef-442a-b3f7-1fb533082fdd",
        "jira_team_name": "[ROSA] Aurora",
    },
    "CLI/Terraform": {
        "source_project": "OCM",
        "source_board_id": 10756,
        "source_board_name": "ROSA CLI/TF",
        "rosaeng_board_id": 11888,
        "rosaeng_filter_id": 107279,
        "jira_team_id": "a23288d3-e663-4c68-8580-ce719fc78cfc",
        "jira_team_name": "[ROSA] CLI/Terraform",
    },
    "Coffee": {
        "source_project": "OCM",
        "source_board_id": 3833,
        "source_board_name": "ROSA Coffee",
        "rosaeng_board_id": 11889,
        "rosaeng_filter_id": 107280,
        "jira_team_id": "b1d72bb9-7e1c-4fc4-96f0-44eb3aebea7e",
        "jira_team_name": "[ROSA] Coffee",
    },
    "FedRAMP Core": {
        "source_project": "HCMSEC",
        "source_board_id": 4970,
        "source_board_name": "HCC - FRH Kanban Board",
        "rosaeng_board_id": 11692,
        "rosaeng_filter_id": 107282,
        "jira_team_id": "f9ad3210-48ec-40d0-b65a-068bc6f222f3",
        "jira_team_name": "[ROSA] FedRAMP Core",
    },
    "Fleet Manager": {
        "source_project": "OCM",
        "source_board_id": 3853,
        "source_board_name": "OSD Fleet Manager",
        "rosaeng_board_id": 11693,
        "rosaeng_filter_id": 107283,
        "jira_team_id": "bd8a0aae-863d-4ea3-a697-028b5043fc08",
        "jira_team_name": "[ROSA] Fleet Manager",
    },
    "Focaccia": {
        "source_project": "OCM",
        "source_board_id": 3841,
        "source_board_name": "ROSA Focaccia",
        "rosaeng_board_id": 11890,
        "rosaeng_filter_id": 107284,
        "jira_team_id": "461df7eb-f4e2-4492-84f4-b24ad53f3201",
        "jira_team_name": "[ROSA] Focaccia",
    },
    "GovCloud SRE": {
        "source_project": "HCMSEC",
        "source_board_id": 4973,
        "source_board_name": "ROSA GovCloud SRE",
        "rosaeng_board_id": 11891,
        "rosaeng_filter_id": 107285,
        "jira_team_id": "6c51c1cd-5997-4938-8bef-00cbb8168cd9",
        "jira_team_name": "[ROSA] GovCloud SRE",
    },
    "Hulk": {
        "source_project": "SREP",
        "source_board_id": 7932,
        "source_board_name": "Hulk",
        "rosaeng_board_id": 11892,
        "rosaeng_filter_id": 107287,
        "jira_team_id": "da409b64-3cdc-409c-939c-417b93001f22",
        "jira_team_name": "[ROSA] Hulk",
    },
    "OSD GCP": {
        "source_project": "OCM",
        "source_board_id": 3856,
        "source_board_name": "OSD-GCP Scrum",
        "rosaeng_board_id": 11893,
        "rosaeng_filter_id": 107288,
        "jira_team_id": "1513346b-e10f-419a-925a-8da9e7e83369",
        "jira_team_name": "[ROSA] OSD GCP",
    },
    "Operators": {
        "source_project": "OCM",
        "source_board_id": 10446,
        "source_board_name": "ROSA Service Engineering Operators",
        "rosaeng_board_id": 11894,
        "rosaeng_filter_id": 107289,
        "jira_team_id": "375bfc7d-06e7-492d-b1ca-f14d2e0145ea",
        "jira_team_name": "[ROSA] Operators",
    },
    "Orange": {
        "source_project": "SREP",
        "source_board_id": 7814,
        "source_board_name": "Orange",
        "rosaeng_board_id": 11895,
        "rosaeng_filter_id": 107290,
        "jira_team_id": "48d0de77-cfe4-424a-a34e-2800a9c44862",
        "jira_team_name": "[ROSA] Orange",
    },
    "Regionality": {
        "source_project": "ROSAENG",
        "source_board_id": 5266,
        "source_board_name": "Regionality",
        "rosaeng_board_id": 5266,
        "rosaeng_filter_id": 19806,
        "jira_team_id": "0c538cd9-152b-49f6-ad7c-e2fa2f865809",
        "jira_team_name": "[ROSA] Regionality",
    },
    "Rocket": {
        "source_project": "SREP",
        "source_board_id": 8029,
        "source_board_name": "Rocket",
        "rosaeng_board_id": 11896,
        "rosaeng_filter_id": 107291,
        "jira_team_id": "a0f44498-f22b-4cd4-a98f-f298cc375a94",
        "jira_team_name": "[ROSA] Rocket",
    },
    "Service Lifecycle": {
        "source_project": "SLSRE",
        "source_board_id": 2543,
        "source_board_name": "Copy of SLSRE ROSA",
        "rosaeng_board_id": 11897,
        "rosaeng_filter_id": 107292,
        "jira_team_id": "16c10b5d-b9d1-4b9a-949d-39888ef9455a",
        "jira_team_name": "[ROSA] Service Lifecycle",
    },
    "Thor": {
        "source_project": "SREP",
        "source_board_id": 8201,
        "source_board_name": "Thor",
        "rosaeng_board_id": 11898,
        "rosaeng_filter_id": 107293,
        "jira_team_id": "51fd486e-45a1-48de-955e-57899973d2b3",
        "jira_team_name": "[ROSA] Thor",
    },
}

# ---------------------------------------------------------------------------
# Status mapping: source status -> ROSAENG status (OJA-WF-AG workflow)
# ---------------------------------------------------------------------------

STATUS_MAP = {
    "New": "New",
    "Refinement": "Refinement",
    "Backlog": "Backlog",
    "In Progress": "In-Progress",
    "In-Progress": "In-Progress",
    "Review": "Review",
    "Code Review": "Review",
    "Closed": "Closed",
    "To Do": "Backlog",
    "Release Pending": "Review",
    "Waiting": "Backlog",
    "Analysis": "Refinement",
}

# ---------------------------------------------------------------------------
# Issue type mapping: source type -> ROSAENG type
# ---------------------------------------------------------------------------

ISSUE_TYPE_MAP = {
    "Task": "Task",
    "Sub-task": "Sub-task",
    "Story": "Story",
    "Bug": "Bug",
    "Epic": "Epic",
    "Risk": "Risk",
    "Weakness": "Weakness",
    "Vulnerability": "Vulnerability",
    "Spike": "Spike",
    "Initiative": "Epic",
    "Release tracker": "Epic",
    "Release Milestone": "Task",
    "Ticket": "Task",
    "Outcome": "Story",
}

TEAM_FIELD = "customfield_10001"


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def init_auth():
    global AUTH
    missing = []
    for v in ["JIRA_EMAIL", "JIRA_API_TOKEN"]:
        if not os.environ.get(v):
            missing.append(v)
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print(f"\nTo set them up:")
        print(f"  export JIRA_EMAIL=\"you@redhat.com\"")
        print(f"  export JIRA_API_TOKEN=\"your-api-token\"")
        print(f"\nGenerate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens")
        sys.exit(1)
    AUTH = HTTPBasicAuth(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])


# ---------------------------------------------------------------------------
# Jira API helpers
# ---------------------------------------------------------------------------

def jira_search(jql, fields=None, max_results=1000):
    """Search for issues using the JQL search API. Returns list of issues."""
    all_issues = []
    if fields is None:
        fields = ["summary", "status", "issuetype", "components", "labels",
                  TEAM_FIELD, "project"]

    fields_str = ",".join(fields)
    next_page_token = None

    while len(all_issues) < max_results:
        params = {
            "jql": jql,
            "maxResults": min(100, max_results - len(all_issues)),
            "fields": fields_str,
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        r = requests.get(
            f"{JIRA_URL}/rest/api/3/search/jql",
            params=params, auth=AUTH, headers=HEADERS, timeout=60,
        )
        if r.status_code != 200:
            print(f"  Search error: {r.status_code} {r.text[:200]}")
            break

        data = r.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)

        if data.get("isLast", True) or not issues:
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return all_issues


def get_board_filter_jql(board_id):
    """Get the JQL filter for a board."""
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/configuration",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code != 200:
        return None

    filt = r.json().get("filter", {})
    fid = filt.get("id")
    if not fid:
        return None

    r2 = requests.get(
        f"{JIRA_URL}/rest/api/3/filter/{fid}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r2.status_code == 200:
        return r2.json().get("jql")
    return None


def get_board_type(board_id):
    """Get board type (scrum or kanban)."""
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        return r.json().get("type")
    return None


def get_board_sprints(board_id, states="active,closed,future"):
    """Get sprints for a board."""
    sprints = []
    start = 0
    while True:
        r = requests.get(
            f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint",
            params={"maxResults": 50, "startAt": start, "state": states},
            auth=AUTH, headers=HEADERS, timeout=60,
        )
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("values", [])
        sprints.extend(batch)
        if data.get("isLast", True):
            break
        start += len(batch)
    return sprints


def get_sprint_issues(board_id, sprint_id):
    """Get issues in a specific sprint."""
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint/{sprint_id}/issue",
        params={"maxResults": 200, "fields": "key"},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        return [i["key"] for i in r.json().get("issues", [])]
    return []


def create_sprint(board_id, name, start_date=None, end_date=None, goal=None):
    """Create a new sprint on a board. Returns sprint ID or None."""
    body = {"name": name, "originBoardId": board_id}
    if start_date:
        body["startDate"] = start_date
    if end_date:
        body["endDate"] = end_date
    if goal:
        body["goal"] = goal
    r = requests.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint",
        json=body, auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code in (200, 201):
        return r.json().get("id")
    log_detail(f"    Failed to create sprint '{name}': {r.status_code} {r.text[:200]}")
    return None


def update_sprint_state(sprint_id, state, complete_date=None):
    """Update a sprint's state (active, closed)."""
    body = {"state": state}
    if state == "closed" and complete_date:
        body["completeDate"] = complete_date
    r = requests.put(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}",
        json=body, auth=AUTH, headers=HEADERS, timeout=60,
    )
    return r.status_code == 200


def add_issues_to_sprint(sprint_id, issue_keys):
    """Move issues into a sprint. Processes in batches of 50."""
    for i in range(0, len(issue_keys), 50):
        batch = issue_keys[i:i + 50]
        r = requests.post(
            f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
            json={"issues": batch},
            auth=AUTH, headers=HEADERS, timeout=60,
        )
        if r.status_code not in (200, 204):
            log_detail(f"    Failed to add {len(batch)} issues to sprint {sprint_id}: {r.status_code} {r.text[:200]}")
            return False
        time.sleep(0.3)
    return True


def get_issue(issue_key):
    """Get full issue details."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        return r.json()
    return None


def get_transitions(issue_key):
    """Get available transitions for an issue."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        return r.json().get("transitions", [])
    return []


def transition_issue(issue_key, transition_id):
    """Transition an issue to a new status."""
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": transition_id}},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    return r.status_code == 204


def move_issue(issue_key, target_project, target_type_name):
    """Move an issue to a different project (and optionally change type).

    Tries API v2 with override parameters first. Verifies the move actually
    took effect since Jira can return 204 while silently ignoring project changes.
    """
    body = {"fields": {"project": {"key": target_project}}}
    if target_type_name:
        body["fields"]["issuetype"] = {"name": target_type_name}

    override_params = {
        "overrideScreenSecurity": "true",
        "overrideEditableFlag": "true",
        "notifyUsers": "false",
    }

    # Try API v2 first (more permissive for cross-project moves)
    for api_version in ["2", "3"]:
        r = requests.put(
            f"{JIRA_URL}/rest/api/{api_version}/issue/{issue_key}",
            params=override_params,
            json=body, auth=AUTH, headers=HEADERS, timeout=90,
        )
        if r.status_code not in (200, 204):
            if api_version == "3":
                return False, f"HTTP {r.status_code}: {r.text[:300]}"
            continue

        # Verify the move actually took effect
        time.sleep(0.5)
        verify = get_issue(issue_key)
        if not verify:
            return False, f"API v{api_version} returned {r.status_code} but issue not found after move"

        actual_project = verify.get("fields", {}).get("project", {}).get("key", "")
        if actual_project == target_project:
            return True, None

        # Silent failure — the PUT succeeded but project didn't change
        if api_version == "3":
            return False, (
                f"Silent move failure: API returned {r.status_code} but issue "
                f"remained in project {actual_project}. This indicates workflow or "
                f"field configuration incompatibility between {actual_project} and "
                f"{target_project}. Verify: (1) issue type '{target_type_name}' exists "
                f"in {target_project}, (2) user has Move Issues permission in "
                f"{actual_project}, (3) required fields in {target_project} are satisfied."
            )
        # Otherwise try next API version

    return False, "Move failed on both API v2 and v3"


def update_issue_fields(issue_key, fields):
    """Update fields on an issue."""
    r = requests.put(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        params={
            "overrideScreenSecurity": "true",
            "overrideEditableFlag": "true",
            "notifyUsers": "false",
        },
        json={"fields": fields},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code not in (200, 204):
        return False, r.text[:200]
    return True, None


def clone_issue_to_project(issue_key, target_project, target_type_name):
    """Fallback: create a clone in the target project and link to the original.

    Used when move_issue fails due to workflow/field incompatibility.
    Preserves: summary, description, components, labels, assignee, priority.
    Does NOT preserve: comments, attachments, work logs, history.
    """
    source = get_issue(issue_key)
    if not source:
        return False, f"Could not fetch source issue {issue_key}", None

    sf = source["fields"]
    new_fields = {
        "project": {"key": target_project},
        "issuetype": {"name": target_type_name or sf["issuetype"]["name"]},
        "summary": sf.get("summary", ""),
    }

    if sf.get("description"):
        new_fields["description"] = sf["description"]
    if sf.get("priority"):
        new_fields["priority"] = {"name": sf["priority"]["name"]}
    if sf.get("assignee"):
        new_fields["assignee"] = {"accountId": sf["assignee"]["accountId"]}
    if sf.get("labels"):
        new_fields["labels"] = sf["labels"]

    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        json={"fields": new_fields},
        auth=AUTH, headers=HEADERS, timeout=90,
    )
    if r.status_code not in (200, 201):
        return False, f"Clone create failed: HTTP {r.status_code}: {r.text[:300]}", None

    new_key = r.json().get("key")

    # Link new issue to original
    requests.post(
        f"{JIRA_URL}/rest/api/3/issueLink",
        json={
            "type": {"name": "Cloners"},
            "inwardIssue": {"key": new_key},
            "outwardIssue": {"key": issue_key},
        },
        auth=AUTH, headers=HEADERS, timeout=60,
    )

    # Add a label on original marking it as migrated
    update_issue_fields(issue_key, {
        "labels": sf.get("labels", []) + [f"migrated-to-{new_key}"],
    })

    return True, None, new_key


def diagnose_move(issue_key, target_project, target_type_name):
    """Run diagnostics on why a move might fail."""
    results = []

    # Check source issue exists
    issue = get_issue(issue_key)
    if not issue:
        results.append(f"FAIL: Issue {issue_key} not found")
        return results
    results.append(f"OK: Source issue {issue_key} exists in project {issue['fields']['project']['key']}")

    src_type = issue["fields"]["issuetype"]["name"]
    results.append(f"INFO: Source issue type: {src_type}, target type: {target_type_name}")

    # Check target project exists and get its issue types
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/project/{target_project}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code != 200:
        results.append(f"FAIL: Target project {target_project} not accessible (HTTP {r.status_code})")
        return results
    results.append(f"OK: Target project {target_project} accessible")

    # Check create meta for target project
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/createmeta/{target_project}/issuetypes",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        issue_types = [it["name"] for it in r.json().get("issueTypes", r.json().get("values", []))]
        results.append(f"INFO: Available issue types in {target_project}: {issue_types}")
        if target_type_name and target_type_name not in issue_types:
            results.append(f"FAIL: Target type '{target_type_name}' not found in {target_project}")
        elif target_type_name:
            results.append(f"OK: Target type '{target_type_name}' exists in {target_project}")
    else:
        results.append(f"WARN: Could not fetch create meta (HTTP {r.status_code})")

    # Check user permissions
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/mypermissions",
        params={"projectKey": issue["fields"]["project"]["key"], "permissions": "MOVE_ISSUES"},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        perms = r.json().get("permissions", {})
        move_perm = perms.get("MOVE_ISSUES", {})
        if move_perm.get("havePermission"):
            results.append(f"OK: User has MOVE_ISSUES permission in source project")
        else:
            results.append(f"FAIL: User lacks MOVE_ISSUES permission in source project")

    r = requests.get(
        f"{JIRA_URL}/rest/api/3/mypermissions",
        params={"projectKey": target_project, "permissions": "CREATE_ISSUES"},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        perms = r.json().get("permissions", {})
        create_perm = perms.get("CREATE_ISSUES", {})
        if create_perm.get("havePermission"):
            results.append(f"OK: User has CREATE_ISSUES permission in {target_project}")
        else:
            results.append(f"FAIL: User lacks CREATE_ISSUES permission in {target_project}")

    return results


def update_filter_jql(filter_id, new_jql):
    """Update a filter's JQL."""
    r = requests.put(
        f"{JIRA_URL}/rest/api/3/filter/{filter_id}",
        json={"jql": new_jql},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    return r.status_code == 200


def rename_board(board_id, new_name):
    """Rename a board. Jira Agile API doesn't support renaming directly,
    so we update the board configuration."""
    r = requests.put(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/configuration",
        json={"name": new_name},
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    return r.status_code == 200


def get_rosaeng_components():
    """Get all ROSAENG components."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/project/{TARGET_PROJECT}/components",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code == 200:
        return {c["name"]: c["id"] for c in r.json()}
    return {}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list_teams():
    """List all teams with their source and ROSAENG board info."""
    print(f"\n{'='*100}")
    print("ROSA TEAM MIGRATION MAP")
    print(f"{'='*100}\n")
    print(f"  {'Team':<22s} | {'Source Project':<8s} | {'Source Board':<40s} | {'ROSAENG Board':>14s}")
    print(f"  {'-'*22}-+-{'-'*8}-+-{'-'*40}-+-{'-'*14}")

    for name, info in sorted(TEAM_MAP.items()):
        src = info["source_project"]
        sboard = f"{info['source_board_name']} ({info['source_board_id']})"
        rboard = info["rosaeng_board_id"]
        print(f"  {name:<22s} | {src:<8s} | {sboard:<40s} | {rboard:>14d}")

    print(f"\n  Note: HCP Platform and Regionality are already in ROSAENG (no migration needed).")
    print()


def cmd_list_components():
    """List all ROSAENG components."""
    comps = get_rosaeng_components()
    print(f"\nROSAENG Components ({len(comps)} total):")
    for name in sorted(comps.keys()):
        print(f"  {name}")
    print()


def cmd_discover(board_id=None, jql=None, team_name=None):
    """Discover issues on a source board or from custom JQL."""
    if board_id:
        jql = get_board_filter_jql(board_id)
        if not jql:
            print(f"Error: Could not get filter JQL for board {board_id}")
            return
        print(f"Board {board_id} filter JQL: {jql}")

    if not jql:
        print("Error: No board or JQL provided")
        return

    print(f"\nSearching for issues...")
    issues = jira_search(jql)
    print(f"Found {len(issues)} issues\n")

    if not issues:
        return

    # Group by status
    by_status = {}
    by_type = {}
    by_component = {}
    already_in_rosaeng = 0

    for issue in issues:
        fields = issue["fields"]
        status = fields["status"]["name"]
        itype = fields["issuetype"]["name"]
        comps = [c["name"] for c in fields.get("components", [])]
        proj = fields.get("project", {}).get("key", "?")

        if proj == TARGET_PROJECT:
            already_in_rosaeng += 1

        by_status[status] = by_status.get(status, 0) + 1
        by_type[itype] = by_type.get(itype, 0) + 1
        for c in comps:
            by_component[c] = by_component.get(c, 0) + 1

    print(f"  By Status:")
    for s, count in sorted(by_status.items(), key=lambda x: -x[1]):
        mapped = STATUS_MAP.get(s, "???")
        marker = "" if mapped != "???" else " <-- UNMAPPED"
        print(f"    {s:<20s} -> {mapped:<15s} : {count:4d}{marker}")

    print(f"\n  By Issue Type:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        mapped = ISSUE_TYPE_MAP.get(t, "???")
        marker = "" if mapped != "???" else " <-- UNMAPPED"
        print(f"    {t:<25s} -> {mapped:<15s} : {count:4d}{marker}")

    print(f"\n  By Component:")
    rosaeng_comps = get_rosaeng_components()
    for c, count in sorted(by_component.items(), key=lambda x: -x[1]):
        exists = "OK" if c in rosaeng_comps else "NOT IN ROSAENG"
        print(f"    {c:<45s} : {count:4d} ({exists})")

    if already_in_rosaeng:
        print(f"\n  Note: {already_in_rosaeng} issue(s) already in ROSAENG (will be skipped)")

    # Check for sub-tasks
    subtask_count = sum(1 for i in issues if i["fields"]["issuetype"]["name"] == "Sub-task")
    parent_count = sum(1 for i in issues if i["fields"].get("subtasks"))
    if subtask_count or parent_count:
        print(f"\n  Sub-tasks: {subtask_count}, Issues with sub-tasks: {parent_count}")

    print()


def cmd_list_sprints(board_id):
    """List sprints on a board."""
    board_type = get_board_type(board_id)
    if board_type != "scrum":
        print(f"Board {board_id} is {board_type} (no sprint support)")
        return

    sprints = get_board_sprints(board_id)
    if not sprints:
        print(f"No sprints found for board {board_id}")
        return

    print(f"\nSprints for board {board_id} ({len(sprints)} total):\n")
    print(f"  {'ID':>6s} | {'Name':<45s} | {'State':<8s} | {'Start':<12s} | {'End':<12s}")
    print(f"  {'-'*6}-+-{'-'*45}-+-{'-'*8}-+-{'-'*12}-+-{'-'*12}")

    for s in sprints[-20:]:
        start = s.get("startDate", "")[:10] if s.get("startDate") else ""
        end = s.get("endDate", "")[:10] if s.get("endDate") else ""
        print(f"  {s['id']:>6d} | {s['name']:<45s} | {s.get('state','?'):<8s} | {start:<12s} | {end:<12s}")

    if len(sprints) > 20:
        print(f"\n  (showing last 20 of {len(sprints)})")
    print()


def cmd_diagnose(issue_key, team_name=None):
    """Diagnose why a move might fail for a specific issue."""
    target_type = None
    if team_name and team_name in TEAM_MAP:
        issue = get_issue(issue_key)
        if issue:
            src_type = issue["fields"]["issuetype"]["name"]
            target_type = ISSUE_TYPE_MAP.get(src_type, "Task")

    results = diagnose_move(issue_key, TARGET_PROJECT, target_type or "Task")
    print(f"\nDiagnostics for moving {issue_key} -> {TARGET_PROJECT}:\n")
    for r in results:
        print(f"  {r}")
    print()


def cmd_migrate(board_id=None, jql=None, team_name=None, mode="lazy",
                dry_run=False, decisions=None, sprint_labels=False,
                sprint_records=False, sprint_board_id=None,
                sprint_count=None, fallback_clone=False):
    """Migrate issues to ROSAENG."""
    if team_name not in TEAM_MAP:
        print(f"Error: Unknown team '{team_name}'. Use --list-teams to see options.")
        return

    team = TEAM_MAP[team_name]

    # Resolve JQL from board if needed
    source_jql = jql
    if board_id and not source_jql:
        source_jql = get_board_filter_jql(board_id)
        if not source_jql:
            print(f"Error: Could not get filter JQL for board {board_id}")
            return

    if not source_jql:
        print("Error: No board or JQL provided")
        return

    print(f"Migration: {team_name} -> ROSAENG")
    print(f"Mode: {mode}")
    print(f"JQL: {source_jql}")
    if dry_run:
        print("*** DRY RUN — no changes will be made ***")
    print()

    # Get issues
    issues = jira_search(source_jql)
    print(f"Found {len(issues)} issues")

    # Filter out issues already in ROSAENG
    to_migrate = []
    skipped_rosaeng = 0
    for issue in issues:
        proj = issue["fields"].get("project", {}).get("key", "")
        if proj == TARGET_PROJECT:
            skipped_rosaeng += 1
        else:
            to_migrate.append(issue)

    if skipped_rosaeng:
        print(f"Skipping {skipped_rosaeng} issues already in ROSAENG")

    if not to_migrate:
        print("No issues to migrate.")
        return

    # Build sprint data if either sprint mode is requested
    sprint_label_map = {}
    source_sprints = []
    sprint_issue_map = {}
    if (sprint_labels or sprint_records) and (sprint_board_id or board_id):
        sid = sprint_board_id or board_id
        source_sprints = get_board_sprints(sid)
        if sprint_count:
            source_sprints = source_sprints[-sprint_count:]

        for sprint in source_sprints:
            sprint_issues = get_sprint_issues(sid, sprint["id"])
            sprint_issue_map[sprint["id"]] = sprint_issues

            if sprint_labels:
                label = f"sprint:{sprint['name'].replace(' ', '-')}"
                for key in sprint_issues:
                    if key not in sprint_label_map:
                        sprint_label_map[key] = []
                    sprint_label_map[key].append(label)

        if sprint_labels:
            print(f"Sprint labels prepared for {len(sprint_label_map)} issues across {len(source_sprints)} sprints")
        if sprint_records:
            state_counts = {}
            for s in source_sprints:
                st = s.get("state", "unknown")
                state_counts[st] = state_counts.get(st, 0) + 1
            state_summary = ", ".join(f"{v} {k}" for k, v in sorted(state_counts.items()))
            print(f"Sprint records to recreate: {len(source_sprints)} sprints ({state_summary})")

    # Load ROSAENG components for validation
    rosaeng_comps = get_rosaeng_components()

    # Parse decisions for interactive mode
    decision_map = {}
    if decisions:
        try:
            decision_map = json.loads(decisions)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in --decisions")
            return

    # Interactive mode: scan for conflicts first
    if mode == "interactive" and not decision_map:
        conflicts = scan_conflicts(to_migrate, rosaeng_comps)
        if conflicts:
            print(f"\n{'='*80}")
            print("CONFLICTS FOUND — resolve these before migrating:")
            print(f"{'='*80}")
            print(json.dumps(conflicts, indent=2))
            print(f"\nPass resolved decisions via --decisions '<json>'")
            return
        else:
            print("No conflicts found, proceeding with migration.")

    # Migrate
    print(f"\n{'='*80}")
    mode_label = "DRY RUN" if dry_run else "MIGRATING"
    print(f"{mode_label}: {len(to_migrate)} issues -> ROSAENG ({team_name})")
    print(f"{'='*80}\n")

    migrated = []
    failed = []
    key_map = {}

    for i, issue in enumerate(to_migrate):
        key = issue["key"]
        fields = issue["fields"]
        summary = fields.get("summary", "")[:50]
        src_status = fields["status"]["name"]
        src_type = fields["issuetype"]["name"]
        src_comps = [c["name"] for c in fields.get("components", [])]

        # Determine target type
        target_type = ISSUE_TYPE_MAP.get(src_type)
        if not target_type:
            target_type = decision_map.get("type_map", {}).get(src_type, "Task")

        # Determine target status
        target_status = STATUS_MAP.get(src_status)
        if not target_status:
            target_status = decision_map.get("status_map", {}).get(src_status, "New")

        # Determine target components
        target_comps = []
        for c in src_comps:
            if c in rosaeng_comps:
                target_comps.append(c)
            elif c in decision_map.get("component_map", {}):
                mapped = decision_map["component_map"][c]
                if mapped and mapped in rosaeng_comps:
                    target_comps.append(mapped)

        # Sprint labels
        extra_labels = sprint_label_map.get(key, [])

        if dry_run:
            log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {key:12s} | {src_type:15s} -> {target_type:15s} | {src_status:15s} -> {target_status:12s} | {summary}")
            if src_comps != target_comps:
                log_detail(f"               components: {src_comps} -> {target_comps}")
            if extra_labels:
                log_detail(f"               sprint labels: {extra_labels}")
            migrated.append(key)
            if LOG_FILE and (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(to_migrate)} issues previewed")
            continue

        # --- REAL MIGRATION ---
        # Step 1: Move issue to ROSAENG
        ok, err = move_issue(key, TARGET_PROJECT, target_type)
        cloned = False
        if not ok:
            if fallback_clone:
                log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {key:12s} | Move failed, trying clone fallback...")
                ok, err, clone_key = clone_issue_to_project(key, TARGET_PROJECT, target_type)
                if not ok:
                    log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {key:12s} | Clone also FAILED: {err}")
                    failed.append({"key": key, "error": f"Move failed, clone failed: {err}"})
                    time.sleep(0.3)
                    continue
                cloned = True
            else:
                log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {key:12s} | FAILED to move: {err}")
                failed.append({"key": key, "error": err})
                time.sleep(0.3)
                continue

        # The key might change after move — get the new key
        if cloned:
            new_key = clone_key
            moved_issue = get_issue(new_key)
        else:
            moved_issue = get_issue(key)
            new_key = moved_issue["key"] if moved_issue else key

        # Step 2: Set Team field
        team_update = {TEAM_FIELD: {"id": team["jira_team_id"]}}
        ok, err = update_issue_fields(new_key, team_update)
        if not ok:
            log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {new_key:12s} | Moved but failed to set Team: {err}")

        # Step 3: Set components
        if target_comps:
            comp_update = {"components": [{"name": c} for c in target_comps]}
            update_issue_fields(new_key, comp_update)

        # Step 4: Add sprint labels
        if extra_labels:
            existing_labels = moved_issue.get("fields", {}).get("labels", []) if moved_issue else []
            all_labels = list(set(existing_labels + extra_labels))
            update_issue_fields(new_key, {"labels": all_labels})

        # Step 5: Transition to target status
        if target_status != "New":
            transitions = get_transitions(new_key)
            target_transition = None
            for t in transitions:
                if t["to"]["name"] == target_status:
                    target_transition = t["id"]
                    break

            if target_transition:
                transition_issue(new_key, target_transition)
            else:
                # May need multi-step transition
                # Try: New -> target (some workflows require intermediate steps)
                pass

        old_key_display = f" (was {key})" if new_key != key else ""
        method = "CLONED" if cloned else "moved"
        log_detail(f"  [{i+1:4d}/{len(to_migrate)}] {new_key:12s}{old_key_display} | {method:7s} | {target_type:15s} | {target_status:12s} | {summary}")
        migrated.append(new_key)
        key_map[key] = new_key
        time.sleep(0.3)

        if LOG_FILE and (i + 1) % 25 == 0:
            print(f"  Progress: {i+1}/{len(to_migrate)} ({len(migrated)} ok, {len(failed)} failed)")

    # Recreate sprint records on ROSAENG board
    sprint_results = []
    if sprint_records and source_sprints and not dry_run and migrated:
        rosaeng_board = team["rosaeng_board_id"]
        print(f"\nRecreating {len(source_sprints)} sprint records on ROSAENG board {rosaeng_board}...")

        for sprint in source_sprints:
            src_id = sprint["id"]
            src_state = sprint.get("state", "future")
            src_name = sprint["name"]
            src_issues = sprint_issue_map.get(src_id, [])

            # Map old keys to new keys
            new_keys = [key_map[k] for k in src_issues if k in key_map]

            new_sprint_id = create_sprint(
                rosaeng_board, src_name,
                start_date=sprint.get("startDate"),
                end_date=sprint.get("endDate"),
                goal=sprint.get("goal"),
            )
            if not new_sprint_id:
                log_detail(f"  Sprint '{src_name}': FAILED to create")
                sprint_results.append({"name": src_name, "status": "create_failed"})
                continue

            # Add issues to the sprint
            if new_keys:
                add_issues_to_sprint(new_sprint_id, new_keys)

            # Transition sprint state to match source
            if src_state in ("active", "closed"):
                update_sprint_state(new_sprint_id, "active")
            if src_state == "closed":
                update_sprint_state(
                    new_sprint_id, "closed",
                    complete_date=sprint.get("completeDate"),
                )

            log_detail(f"  Sprint '{src_name}': created (id={new_sprint_id}), "
                       f"state={src_state}, {len(new_keys)}/{len(src_issues)} issues added")
            sprint_results.append({
                "name": src_name, "status": "ok",
                "new_sprint_id": new_sprint_id,
                "state": src_state,
                "issues_added": len(new_keys),
                "issues_total": len(src_issues),
            })
            time.sleep(0.3)

        ok_sprints = sum(1 for s in sprint_results if s["status"] == "ok")
        print(f"Sprint records: {ok_sprints}/{len(source_sprints)} created successfully")

    elif sprint_records and dry_run and source_sprints:
        print(f"\nSprint records (dry run): would recreate {len(source_sprints)} sprints on ROSAENG board {team['rosaeng_board_id']}")
        for sprint in source_sprints:
            src_issues = sprint_issue_map.get(sprint["id"], [])
            goal_preview = f" | goal: {sprint['goal'][:40]}..." if sprint.get("goal") else ""
            log_detail(f"  {sprint['name']:<40s} | {sprint.get('state','?'):<8s} | "
                       f"{sprint.get('startDate','')[:10]:>10s} -> {sprint.get('endDate','')[:10]:>10s} | "
                       f"{len(src_issues)} issues{goal_preview}")

    # Summary
    print(f"\n{'='*80}")
    if dry_run:
        print(f"DRY RUN COMPLETE: Would migrate {len(migrated)} issues")
        if sprint_records and source_sprints:
            print(f"  Would recreate {len(source_sprints)} sprint records")
    else:
        print(f"MIGRATION COMPLETE: Migrated {len(migrated)}, Failed {len(failed)}")
        if sprint_results:
            ok_sprints = sum(1 for s in sprint_results if s["status"] == "ok")
            print(f"  Sprint records: {ok_sprints}/{len(sprint_results)} created")
        if failed:
            shown = failed[:10]
            print(f"\nFailed issues ({len(failed)} total):")
            for f in shown:
                print(f"  {f['key']}: {f['error'][:120]}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more (see migration-log.json for full list)")
    if LOG_FILE:
        print(f"\nPer-issue details written to log file (not shown here to save context).")
    print()

    # Write migration log artifact
    log_data = {
        "team": team_name,
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": mode,
        "dry_run": dry_run,
        "source_jql": source_jql,
        "source_board_id": board_id,
        "rosaeng_board_id": team["rosaeng_board_id"],
        "total_found": len(issues),
        "skipped_already_in_rosaeng": skipped_rosaeng,
        "migrated_count": len(migrated),
        "failed_count": len(failed),
        "migrated_keys": migrated,
        "failed": failed,
        "sprint_labels_applied": bool(sprint_label_map),
        "sprint_label_count": len(sprint_label_map) if sprint_label_map else 0,
        "sprint_records": sprint_results if sprint_results else None,
        "decisions": decision_map if decision_map else None,
    }
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    log_path = os.path.join(ARTIFACTS_DIR, "migration-log.json")
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"Migration log saved to: {log_path}")


def scan_conflicts(issues, rosaeng_comps):
    """Scan issues for mapping conflicts. Returns dict of conflicts."""
    conflicts = {
        "unmapped_statuses": {},
        "unmapped_types": {},
        "unmapped_components": {},
    }

    for issue in issues:
        fields = issue["fields"]
        status = fields["status"]["name"]
        itype = fields["issuetype"]["name"]
        comps = [c["name"] for c in fields.get("components", [])]

        if status not in STATUS_MAP:
            conflicts["unmapped_statuses"][status] = conflicts["unmapped_statuses"].get(status, 0) + 1

        if itype not in ISSUE_TYPE_MAP:
            conflicts["unmapped_types"][itype] = conflicts["unmapped_types"].get(itype, 0) + 1

        for c in comps:
            if c not in rosaeng_comps:
                conflicts["unmapped_components"][c] = conflicts["unmapped_components"].get(c, 0) + 1

    # Remove empty categories
    return {k: v for k, v in conflicts.items() if v}


def cmd_update_filter(team_name, extra_jql):
    """Add custom JQL to a ROSAENG board filter."""
    if team_name not in TEAM_MAP:
        print(f"Error: Unknown team '{team_name}'")
        return

    team = TEAM_MAP[team_name]
    filter_id = team["rosaeng_filter_id"]

    # Get current filter
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/filter/{filter_id}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code != 200:
        print(f"Error: Could not read filter {filter_id}: {r.status_code}")
        return

    current = r.json()
    current_jql = current.get("jql", "")
    print(f"Current filter JQL: {current_jql}")

    new_jql = f"{current_jql} {extra_jql}"
    print(f"New filter JQL:     {new_jql}")

    ok = update_filter_jql(filter_id, new_jql)
    if ok:
        print("Filter updated successfully.")
    else:
        print("Error: Failed to update filter.")


def cmd_rename_legacy(board_id):
    """Rename a source board to include (Legacy)."""
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}",
        auth=AUTH, headers=HEADERS, timeout=60,
    )
    if r.status_code != 200:
        print(f"Error: Board {board_id} not found")
        return

    board = r.json()
    current_name = board.get("name", "")

    if "(Legacy)" in current_name:
        print(f"Board already marked as legacy: {current_name}")
        return

    new_name = f"{current_name} (Legacy)"
    print(f"Renaming: {current_name} -> {new_name}")

    ok = rename_board(board_id, new_name)
    if ok:
        print("Board renamed successfully.")
    else:
        # Fallback: try updating via the filter name instead
        print("Note: Board rename via API may not be supported. The Jira admin may need to rename it manually.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Migrate Jira issues to ROSAENG")

    parser.add_argument("--list-teams", action="store_true",
                       help="List teams with source and ROSAENG board info")
    parser.add_argument("--list-components", action="store_true",
                       help="List ROSAENG components")
    parser.add_argument("--discover", action="store_true",
                       help="Discover issues on a source board")
    parser.add_argument("--list-sprints", action="store_true",
                       help="List sprints on a board")
    parser.add_argument("--migrate", action="store_true",
                       help="Migrate issues to ROSAENG")
    parser.add_argument("--diagnose", action="store_true",
                       help="Diagnose why a move might fail for a specific issue")
    parser.add_argument("--update-filter", action="store_true",
                       help="Update ROSAENG board filter JQL")
    parser.add_argument("--rename-legacy", action="store_true",
                       help="Rename source board to (Legacy)")

    parser.add_argument("--board", type=int, help="Source board ID")
    parser.add_argument("--jql", type=str, help="Custom JQL (instead of board filter)")
    parser.add_argument("--team", type=str, help="Team name (e.g., 'Coffee', 'Thor')")
    parser.add_argument("--mode", choices=["lazy", "interactive"], default="lazy",
                       help="Migration mode")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--decisions", type=str,
                       help="JSON decisions for interactive mode")
    parser.add_argument("--extra-jql", type=str,
                       help="Additional JQL to append to ROSAENG filter")
    parser.add_argument("--sprint-labels", action="store_true",
                       help="Preserve sprint names as labels (lightweight)")
    parser.add_argument("--sprint-records", action="store_true",
                       help="Recreate full sprint records on ROSAENG board (dates, goals, issues)")
    parser.add_argument("--sprint-board", type=int,
                       help="Board ID to read sprints from (if different from --board)")
    parser.add_argument("--sprint-count", type=int,
                       help="Number of recent sprints to include")
    parser.add_argument("--fallback-clone", action="store_true",
                       help="If move fails, clone issue to ROSAENG and link to original")
    parser.add_argument("--issue", type=str,
                       help="Issue key for --diagnose (e.g., HCMSEC-123)")
    parser.add_argument("--log-file", type=str,
                       help="Write per-issue details to this file instead of stdout (reduces context usage)")

    args = parser.parse_args()

    global LOG_FILE
    if args.log_file:
        os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)
        LOG_FILE = open(args.log_file, "w")
        print(f"Per-issue details will be written to: {args.log_file}")

    init_auth()

    try:
        if args.list_teams:
            cmd_list_teams()
        elif args.list_components:
            cmd_list_components()
        elif args.discover:
            cmd_discover(board_id=args.board, jql=args.jql, team_name=args.team)
        elif args.list_sprints:
            if not args.board:
                print("Error: --list-sprints requires --board")
                sys.exit(1)
            cmd_list_sprints(args.board)
        elif args.diagnose:
            if not args.issue:
                print("Error: --diagnose requires --issue (e.g., --issue HCMSEC-123)")
                sys.exit(1)
            cmd_diagnose(args.issue, args.team)
        elif args.migrate:
            if not args.team:
                print("Error: --migrate requires --team")
                sys.exit(1)
            cmd_migrate(
                board_id=args.board,
                jql=args.jql,
                team_name=args.team,
                mode=args.mode,
                dry_run=args.dry_run,
                decisions=args.decisions,
                sprint_labels=args.sprint_labels,
                sprint_records=args.sprint_records,
                sprint_board_id=args.sprint_board,
                sprint_count=args.sprint_count,
                fallback_clone=args.fallback_clone,
            )
        elif args.update_filter:
            if not args.team or not args.extra_jql:
                print("Error: --update-filter requires --team and --extra-jql")
                sys.exit(1)
            cmd_update_filter(args.team, args.extra_jql)
        elif args.rename_legacy:
            if not args.board:
                print("Error: --rename-legacy requires --board")
                sys.exit(1)
            cmd_rename_legacy(args.board)
        else:
            parser.print_help()
    finally:
        if LOG_FILE:
            LOG_FILE.close()


if __name__ == "__main__":
    main()
