# ROSA Team Migration Mapping

## Team → Source Project → ROSAENG Board

| Team | Source Project | Source Board ID | Source Board Name | Board Type | ROSAENG Board ID | ROSAENG Filter ID | Jira Team ID |
|------|---------------|----------------|-------------------|------------|-----------------|-------------------|-------------|
| AMS | OCM | 3844 | ROSA Service Eng - AMS | scrum | 11887 | 107277 | 971fb543-5d1b-4b9b-84f6-e70cb43e24b0 |
| Aurora | SREP | 11464 | SREP Aurora | kanban | 11688 | 107278 | d82adfd4-85ef-442a-b3f7-1fb533082fdd |
| CLI/Terraform | OCM | 10756 | ROSA CLI/TF | scrum | 11888 | 107279 | a23288d3-e663-4c68-8580-ce719fc78cfc |
| Coffee | OCM | 3833 | ROSA Coffee | scrum | 11889 | 107280 | b1d72bb9-7e1c-4fc4-96f0-44eb3aebea7e |
| FedRAMP Core | HCMSEC | 4970 | HCC - FRH Kanban Board | kanban | 11692 | 107282 | f9ad3210-48ec-40d0-b65a-068bc6f222f3 |
| Fleet Manager | OCM | 3853 | OSD Fleet Manager | kanban | 11693 | 107283 | bd8a0aae-863d-4ea3-a697-028b5043fc08 |
| Focaccia | OCM | 3841 | ROSA Focaccia | scrum | 11890 | 107284 | 461df7eb-f4e2-4492-84f4-b24ad53f3201 |
| GovCloud SRE | HCMSEC | 4973 | ROSA GovCloud SRE | scrum | 11891 | 107285 | 6c51c1cd-5997-4938-8bef-00cbb8168cd9 |
| HCP Platform | ROSAENG | — | (already in ROSAENG) | kanban | 11696 | 107286 | a5267ed5-eaa8-4cd6-90e3-d0ce145dbfbf |
| Hulk | SREP | 7932 | Hulk | scrum | 11892 | 107287 | da409b64-3cdc-409c-939c-417b93001f22 |
| OSD GCP | OCM | 3856 | OSD-GCP Scrum | scrum | 11893 | 107288 | 1513346b-e10f-419a-925a-8da9e7e83369 |
| Operators | OCM | 10446 | ROSA Service Engineering Operators | scrum | 11894 | 107289 | 375bfc7d-06e7-492d-b1ca-f14d2e0145ea |
| Orange | SREP | 7814 | Orange | scrum | 11895 | 107290 | 48d0de77-cfe4-424a-a34e-2800a9c44862 |
| Regionality | ROSAENG | 5266 | Regionality | kanban | 5266 | 19806 | 0c538cd9-152b-49f6-ad7c-e2fa2f865809 |
| Rocket | SREP | 8029 | Rocket | scrum | 11896 | 107291 | a0f44498-f22b-4cd4-a98f-f298cc375a94 |
| Service Lifecycle | SLSRE | 2543 | Copy of SLSRE ROSA | scrum | 11897 | 107292 | 16c10b5d-b9d1-4b9a-949d-39888ef9455a |
| Thor | SREP | 8201 | Thor | scrum | 11898 | 107293 | 51fd486e-45a1-48de-955e-57899973d2b3 |

## Source Board Filter JQLs

These are the JQL filters on the source boards. During migration, all issues matching this JQL are candidates.

| Team | Source Filter JQL |
|------|------------------|
| AMS | `project = OCM AND component = account-manager ORDER BY Rank ASC` |
| CLI/Terraform | `project in (ACM, OCM) AND (component in (rosa-cli, rosa-tf, ocm-qe, rosa-experience) OR labels in (rosa-cli, rosa-tf)) ORDER BY Rank ASC` |
| Coffee | `project in ("Openshift Cluster Manager") AND component in (rosa-team) AND type != Epic AND (labels not in (focaccia) OR labels is EMPTY) ORDER BY priority DESC, updatedDate DESC, type ASC` |
| Fleet Manager | `project = OCM AND component = fleet-manager ORDER BY Rank ASC` |
| Focaccia | `project in ("Openshift Cluster Manager") AND component in (clusters-service, rosa, rosa-team, service-log, access-transparency, fedramp, rosa-tf, rosa-cli) AND component not in (account-manager) AND labels not in (service-engineering-operators) AND type != Epic ORDER BY priority DESC, updatedDate DESC, type ASC` |
| GovCloud SRE | `project = "HCM Security" AND component in ("[FRH] Infrastructure", "[FRH] Platform Security", "[FRH] SRE Tooling", "[FRH] Dynatrace") ORDER BY key DESC, Rank ASC` |
| OSD GCP | `project in ("Openshift Cluster Manager") AND (component in (osd-gcp) OR labels in (gcp, osd-gcp)) AND (labels is EMPTY OR labels not in (osd-gcp-backlog-hide)) ORDER BY Rank ASC` |
| Operators | `project = OCM AND (labels = xcmstrat-480 OR labels = service-engineering-operators) OR project = srep AND labels = service-engineering-operators ORDER BY Rank ASC` |
| Service Lifecycle | `project = SLSRE ORDER BY Rank ASC` |

## Status Mapping

ROSAENG uses the OJA-WF-AG workflow with 6 statuses.

| Source Status | ROSAENG Status | Notes |
|--------------|---------------|-------|
| New | New | 1:1 |
| Refinement | Refinement | 1:1 |
| Backlog | Backlog | 1:1 |
| In Progress | In-Progress | 1:1 |
| In-Progress | In-Progress | 1:1 |
| Review | Review | 1:1 |
| Code Review | Review | Maps to Review |
| Closed | Closed | 1:1 |
| To Do | Backlog | Best fit |
| Release Pending | Review | Best fit |
| Waiting | Backlog | Best fit |
| Analysis | Refinement | Best fit |

## Issue Type Mapping

| Source Type | ROSAENG Type | Notes |
|-----------|-------------|-------|
| Task | Task | 1:1 |
| Sub-task | Sub-task | 1:1 |
| Story | Story | 1:1 |
| Bug | Bug | 1:1 |
| Epic | Epic | 1:1 |
| Risk | Risk | 1:1 |
| Weakness | Weakness | 1:1 |
| Vulnerability | Vulnerability | 1:1 |
| Spike | Spike | 1:1 |
| Initiative | Epic | HCMSEC-specific |
| Release tracker | Epic | HCMSEC-specific |
| Release Milestone | Task | HCMSEC-specific |
| Ticket | Task | HCMSEC-specific |
| Outcome | Story | HCMSEC-specific |

## ROSAENG Components (92 total)

Components are matched by exact name. The full list is available via:
```bash
python3 scripts/migrate.py --list-components
```

## ROSAENG Board Filter Pattern

All ROSAENG boards use this filter pattern:
```
project = ROSAENG AND Team = "[ROSA] <team>" ORDER BY Rank ASC
```

Issues automatically appear on the correct board once they are in ROSAENG with the Team field set.
