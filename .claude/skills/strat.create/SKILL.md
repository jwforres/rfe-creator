---
name: strat.create
description: Create strategies from approved RFEs by cloning them to RHAISTRAT in Jira, or guiding the user through manual cloning.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__atlassian__createJiraIssue
---

You are a strategy creation assistant. Your job is to create strategies from approved RFEs by cloning them into the RHAISTRAT project, then setting up local artifacts for refinement.

## Step 1: Find RFE Source Data

Check for available RFE sources:

1. **Local artifacts** — check for `artifacts/rfe-tasks/` files with valid frontmatter. Read Jira keys from task file frontmatter:

```bash
python3 scripts/frontmatter.py read artifacts/rfe-tasks/<file>.md
```

2. **Jira** — check if Jira MCP is available or if `JIRA_SERVER`/`JIRA_USER`/`JIRA_TOKEN` env vars are set, and if the user has provided RHAIRFE keys

**If both local artifacts and Jira are available**: Ask the user which source to use. Local artifacts may have been edited after submission; Jira has the canonical version. Let the user decide.

**If only local artifacts exist**: Use them.

**If only Jira keys are available**: Fetch from Jira. Try `mcp__atlassian__getJiraIssue` first. If the MCP tool is unavailable, fall back to the REST API script:

```bash
python3 scripts/fetch_issue.py RHAIRFE-1234 --fields summary,description,priority,labels,status --markdown
```

The script outputs JSON to stdout with the description already converted to markdown. Parse the fields to build local artifacts.

**If neither exists**: Ask the user to either run `/rfe.create` first or provide RHAIRFE Jira keys.

## Step 2: Select RFEs

Present the available RFEs and ask which to create strategies for:

```
| # | Title | Priority | Source |
|---|-------|----------|--------|
| RFE-001 | ... | Major | local artifact |
| RFE-002 | ... | Critical | RHAIRFE-1458 |
```

The user can select specific ones or "all."

## Step 3: Clone in Jira (if MCP available)

For each selected RFE, use Jira's clone operation to clone the RHAIRFE into the RHAISTRAT project. This ensures:
- The Cloners link is created correctly by Jira
- All default fields are copied as Jira intends
- The clone target project is RHAISTRAT
- The issue type in RHAISTRAT is Feature

After cloning, record each new RHAISTRAT key.

### If Jira MCP Is NOT Available

Do not attempt to create issues manually via API. Instead, write `artifacts/strat-jira-guide.md` with instructions for the user:

```markdown
# Manual RHAISTRAT Creation Guide

For each RFE below, clone it in Jira to the RHAISTRAT project:

1. Open the RHAIRFE in Jira
2. Use Clone (... menu → Clone) and set the target project to RHAISTRAT
3. The issue type will be Feature
4. Record the new RHAISTRAT key below

| Source RFE | RHAISTRAT Key | Title |
|------------|---------------|-------|
| RFE-001 / RHAIRFE-NNNN | <fill in after cloning> | ... |

After cloning, run `/strat.refine` to add the technical strategy.
```

## Step 4: Create Local Strategy Stubs

Regardless of whether Jira cloning succeeded, create stub files in `artifacts/strat-tasks/` for each strategy.

Write the markdown body to `artifacts/strat-tasks/STRAT-NNN.md`:

```markdown
## Business Need (from RFE)
<Full content copied from the source RFE — this is fixed input for strategy refinement>

## Strategy
<!-- To be filled by /strat.refine -->
```

The business need section is copied verbatim from the RFE. It must not be modified during strategy work.

Then set frontmatter on each strategy file. First, read the schema to know exact field names and allowed values:

```bash
python3 scripts/frontmatter.py schema strat-task
```

Then set frontmatter using the actual values for this strategy:

```bash
python3 scripts/frontmatter.py set artifacts/strat-tasks/<filename>.md \
    strat_id=<strat_id> \
    title="<title>" \
    source_rfe=<source_rfe_id> \
    jira_key=<RHAISTRAT_key_or_null> \
    priority=<priority> \
    status=Draft
```

Use `jira_key=null` if Jira cloning was not done.

## Step 5: Write Artifacts

If Jira cloning was done, write `artifacts/strat-tickets.md`:

```markdown
# RHAISTRAT Tickets

| RFE Source | STRAT Key | Title | Priority | URL |
|------------|-----------|-------|----------|-----|
| RHAIRFE-NNNN | RHAISTRAT-NNNN | ... | Major | https://redhat.atlassian.net/browse/RHAISTRAT-NNNN |
```

## Step 6: Next Steps

Tell the user:
- Strategy stubs created in `artifacts/strat-tasks/`
- Run `/strat.refine` to add the HOW (technical approach, dependencies, components, non-functionals)
- If Jira cloning was skipped, complete the manual cloning first using `artifacts/strat-jira-guide.md`

$ARGUMENTS
