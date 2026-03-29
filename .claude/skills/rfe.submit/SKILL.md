---
name: rfe.submit
description: Submit or update RFEs in Jira. Creates new RHAIRFE tickets for new RFEs, or updates existing tickets for RFEs fetched from Jira. Use after /rfe.review.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

You are an RFE submission assistant. Your job is to create or update RHAIRFE Jira tickets from reviewed RFE artifacts.

All submission goes through Python scripts that use the Jira REST API directly with Basic Auth (`JIRA_SERVER`, `JIRA_USER`, `JIRA_TOKEN` env vars), not the Atlassian MCP server. This ensures the exact sequence of Jira API calls is deterministic and not dependent on LLM tool-calling decisions.

**This skill is non-interactive.** Do not prompt the user for confirmation before submitting. The user invoked `/rfe.submit` — that is the confirmation. Run the script directly without asking "are you sure?" or presenting a dry run for approval.

## Step 0: Check Credentials

Check if `JIRA_SERVER`, `JIRA_USER`, and `JIRA_TOKEN` environment variables are set. If not, tell the user:

> RFE submission requires Jira API credentials. Set these environment variables:
> ```
> export JIRA_SERVER=https://your-site.atlassian.net
> export JIRA_USER=your-email@example.com
> export JIRA_TOKEN=your-api-token
> ```
> To create an API token, go to https://id.atlassian.com/manage-profile/security/api-tokens
>
> After environment variables are set, re-run `/rfe.submit`.

## Step 1: Conflict Detection

Before submitting, check for concurrent modifications to any Jira-sourced RFEs (those with `rfe_id` starting with `RHAIRFE-`).

For each Jira-sourced RFE being submitted, check if an original snapshot exists at `artifacts/rfe-originals/<rfe_id>.md`. If it does:

1. Re-fetch the current Jira description using the REST API script:

```bash
python3 scripts/fetch_issue.py <rfe_id> --fields summary,description --markdown
```

2. Compare the fetched `fields.description` against the contents of the original snapshot file (which contains the raw Jira description, not the templated version). If they differ, someone modified the RFE in Jira since we last fetched it.

3. **If a conflict is detected**: Stop submission for that RFE. Report the conflict:

> **Conflict detected for `<rfe_id>`**: The RFE was modified in Jira since it was last fetched. Submitting would overwrite those changes.
>
> To resolve: re-fetch from Jira by running `/rfe.review <rfe_id>`, then re-apply your changes.

4. **If no conflict**: Proceed with submission.

If no original snapshot exists (e.g., for locally-created RFEs with `RFE-NNN` IDs), skip conflict detection — there is no Jira state to conflict with.

## Step 2: Detect Mode and Run

Check task file frontmatter to determine whether this is a split submission or standard submission.

### Split Submission

If any task file has `status: Archived` and other task files have a matching `parent_key`, this is a split submission. Find the parent's `rfe_id` from its frontmatter and run:

```bash
python3 scripts/split_submit.py <PARENT_KEY> [--dry-run] [--artifacts-dir artifacts]
```

The split submit script handles:
- Persisting child RFE content as comments on the parent (durable backup)
- Creating child tickets with proper "Issue split" linking to the parent
- Closing the parent ticket as Obsolete
- Idempotent recovery if interrupted
- Renaming local files from RFE-NNN to RHAIRFE-NNNN after submission
- Rebuilding the rfes.md index

### Standard Submission

Otherwise, run:

```bash
python3 scripts/submit.py [--dry-run] [--artifacts-dir artifacts]
```

The standard submit script handles:
- Reading review recommendations from `rfe-reviews/` frontmatter and skipping rejected RFEs
- Creating new RHAIRFE tickets for RFEs with local IDs (RFE-NNN)
- Updating existing tickets for RFEs with Jira IDs (RHAIRFE-NNNN)
- Applying labels from the labeling scheme (see below)
- Posting removed-context comments where applicable
- Renaming local files from RFE-NNN to RHAIRFE-NNNN after submission
- Rebuilding the rfes.md index

## Step 3: Report Results

After the script completes, read `artifacts/rfes.md` (rebuilt by the script) and report the results.

If the script fails, report the error and suggest the user check credentials or use `--dry-run` to validate locally.

## Labeling Scheme

The scripts automatically apply labels based on what happened during the pipeline:

| Label | When applied |
|-------|-------------|
| `rfe-creator-auto-created` | Ticket was created by the pipeline (new RFEs, not updates) |
| `rfe-creator-auto-revised` | Ticket content was modified by automation (review frontmatter `revised: true`) |
| `rfe-creator-split-original` | Parent ticket that was decomposed into smaller RFEs |
| `rfe-creator-split-result` | Child ticket produced by splitting another RFE |
| `rfe-creator-needs-attention` | Automation couldn't fully resolve all issues — human review needed (review frontmatter `needs_attention: true`) |

$ARGUMENTS
