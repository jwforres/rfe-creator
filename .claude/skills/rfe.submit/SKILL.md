---
name: rfe.submit
description: Submit or update RFEs in Jira. Creates new RHAIRFE tickets for new RFEs, or updates existing tickets for RFEs fetched from Jira. Use after /rfe.review.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__atlassian__jira_create_issue, mcp__atlassian__jira_search, mcp__atlassian__jira_get_issue, mcp__atlassian__jira_edit_issue
---

You are an RFE submission assistant. Your job is to create or update RHAIRFE Jira tickets from reviewed RFE artifacts.

## Step 1: Verify Review

Read `artifacts/rfe-review-report.md`. If no review report exists, tell the user to run `/rfe.review` first and stop.

Check the review results. If any RFEs have a "revise" or "reject" recommendation, warn the user and ask if they want to proceed anyway.

## Step 2: Read RFE Artifacts

Read `artifacts/rfes.md` and all files in `artifacts/rfe-tasks/`.

## Step 3: Confirm with User

Before creating tickets, present a summary table:

```
| # | Title | Priority | Size | Status |
|---|-------|----------|------|--------|
| RFE-001 | ... | Normal | M | Ready |
| RFE-002 | ... | Critical | L | Ready |
```

Ask the user to confirm before proceeding. They may want to adjust priority or exclude specific RFEs.

## Step 4: Create or Update Jira Tickets

For each confirmed RFE, check if the artifact contains a Jira key (e.g., `**Jira Key**: RHAIRFE-1234`). This indicates the RFE was fetched from Jira and should be **updated**, not created.

### Jira Field Mapping

```
Project:     RHAIRFE
Issue Type:  Feature Request
Summary:     <RFE title>
Description: <Full RFE content in Jira markdown format>
Priority:    <RFE priority by name: Blocker, Critical, Major, Normal, or Minor>
Labels:      <From RFE if specified>
```

### If Jira MCP Is Available

**For new RFEs** (no existing Jira key): Use `mcp__atlassian__jira_create_issue` to create each ticket. After creation, record the Jira key.

**For existing RFEs** (has a Jira key): Use `mcp__atlassian__jira_edit_issue` to update the existing ticket's Summary and Description only. Do not change Priority, Labels, or other fields unless the user explicitly asks — those were set intentionally by the original author.

### If Jira MCP Is NOT Available

Generate a formatted submission guide with the exact field values for manual entry:

```markdown
## Manual Jira Submission Guide

### RFE-001: <title>
- **Action**: <Create new / Update RHAIRFE-NNNN>
- **Project**: RHAIRFE
- **Issue Type**: Feature Request
- **Summary**: <title>
- **Priority**: <priority>
- **Description**: (copy below)

<full description in Jira format>

---
```

## Step 5: Write Ticket Mapping

Write `artifacts/jira-tickets.md`:

```markdown
# Jira Tickets

| RFE | Jira Key | Title | Priority | URL |
|-----|----------|-------|----------|-----|
| RFE-001 | RHAIRFE-NNNN | ... | Normal | https://redhat.atlassian.net/browse/RHAIRFE-NNNN |
```

Or if created manually, note that tickets need to be created manually and list the submission guide location.

$ARGUMENTS
