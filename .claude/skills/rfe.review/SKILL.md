---
name: rfe.review
description: Review and improve RFEs. Accepts a Jira key (e.g., /rfe.review RHAIRFE-1234) to fetch and review an existing RFE, or reviews local artifacts from /rfe.create. Runs rubric scoring, technical feasibility checks, and auto-revises issues it finds.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion, mcp__atlassian__jira_get_issue
---

You are an RFE review orchestrator. Your job is to review RFEs for quality and technical feasibility, and auto-revise issues when possible.

## Step 0: Resolve Input

Check if `$ARGUMENTS` contains a Jira key (e.g., `RHAIRFE-1234`).

**If a Jira key is provided**: Fetch the RFE from Jira using `mcp__atlassian__jira_get_issue`. Write it to `artifacts/rfe-tasks/` as a local artifact using the RFE template format (read `${CLAUDE_SKILL_DIR}/../rfe.create/rfe-template.md` for the format). Update `artifacts/rfes.md` with the RFE summary. Record the Jira key in the artifact metadata so `/rfe.submit` knows to update rather than create.

**If no Jira key**: Proceed with existing local artifacts.

## Step 1: Verify Artifacts Exist

Read `artifacts/rfes.md` and list files in `artifacts/rfe-tasks/`. If no RFE artifacts exist and no Jira key was provided, tell the user to run `/rfe.create` first or provide a Jira key (e.g., `/rfe.review RHAIRFE-1234`) and stop.

Check if a prior review report exists at `artifacts/rfe-review-report.md`. If it does, read it — this is a re-review after revisions.

## Step 1.5: Fetch Architecture Context

Fetch only the latest RHOAI architecture version from the architecture-context repo using a sparse checkout:

```bash
# Step 1: Find the latest rhoai-* folder via GitHub API
LATEST=$(curl -sL https://api.github.com/repos/opendatahub-io/architecture-context/contents/architecture | jq -r '[.[] | select(.name | startswith("rhoai-")) | .name] | sort | last')

if [ -z "$LATEST" ] || [ "$LATEST" = "null" ]; then
  echo "Could not detect latest architecture version"
else
  # Step 2: Sparse checkout just that folder
  mkdir -p .context
  if [ -d .context/architecture-context ]; then
    cd .context/architecture-context
    git sparse-checkout set "architecture/$LATEST"
    git pull --quiet
    cd -
  else
    git clone --depth 1 --filter=blob:none --sparse https://github.com/opendatahub-io/architecture-context .context/architecture-context
    cd .context/architecture-context
    git sparse-checkout set "architecture/$LATEST"
    cd -
  fi
  echo "Architecture context ready: .context/architecture-context/architecture/$LATEST"
fi
```

The architecture context path for the feasibility fork is `.context/architecture-context/architecture/$LATEST`.

If the fetch fails (network issue, repo unavailable, API rate limit), proceed without architecture context. Note it in the review report.

## Step 2: Run Reviews

Run two independent reviews. These assessments must remain separate — "this RFE is poorly written" is a different concern from "this RFE is technically infeasible."

### Review 1: Rubric Validation

<!-- TEMPORARY: This bootstrap approach clones assess-rfe from GitHub and copies
     the skill locally because the Claude Agent SDK doesn't yet support marketplace
     plugin resolution. Once the SDK or ambient runner adds plugin support, this
     can be replaced with a direct /assess-rfe:assess-rfe plugin invocation. -->

Bootstrap the assess-rfe skill by running:

```bash
bash scripts/bootstrap-assess-rfe.sh
```

This clones the assess-rfe repo into `.context/assess-rfe/` and copies the skills into `.claude/skills/`. If the clone already exists, it reuses it.

When any assess-rfe skill resolves its `{PLUGIN_ROOT}`, it should use the absolute path of `.context/assess-rfe/` in the project working directory.

**If the bootstrap succeeded**: Invoke `/assess-rfe` to score each RFE against the rubric. The plugin owns the scoring logic, criteria, and calibration. Do not reimplement or second-guess its scores.

**If the bootstrap failed** (network issue, git unavailable): Skip rubric validation. Note in the review report that rubric validation was skipped because assess-rfe could not be fetched. Perform a basic quality check instead:
- Does each RFE describe a business need (WHAT/WHY), not a task or technical activity?
- Does each RFE avoid prescribing architecture, technology, or implementation?
- Does each RFE name specific affected customers?
- Does each RFE include evidence-based business justification?
- Is each RFE right-sized for a single strategy feature?

### Review 2: Technical Feasibility (Forked)

Invoke the `rfe-feasibility-review` skill on the RFE artifacts. This runs in a forked context with architecture context (if available) to assess whether each RFE is technically feasible without the business context influencing the assessment.

## Step 3: Combine Results

Write `artifacts/rfe-review-report.md` with the following structure:

```markdown
# RFE Review Report

**Date**: <date>
**RFEs reviewed**: <count>
**Rubric validation**: <pass/fail/skipped>
**Technical feasibility**: <pass/conditional/fail>

## Summary
<Overall assessment: are these RFEs ready for submission?>

## Per-RFE Results

### RFE-001: <title>

**Rubric score**: <score>/10 <PASS/FAIL> (or "skipped — plugin not installed")
<Rubric feedback details if available>

**Technical feasibility**: <feasible / infeasible / needs RFE revision>
**Strategy considerations**: <none / list of items flagged for /strat.refine>

**Recommendation**: <submit / revise / split / reject>
<Specific actionable suggestions if revision needed>

### RFE-002: <title>
...

## Revision History
<If this is a re-review, note what changed since the prior review:>
- What concerns from the prior review were addressed
- What concerns remain
- What new issues the revisions introduced
```

## Step 4: Auto-Revise

Always attempt at least one auto-revision cycle when any criterion scores below full marks. Improve what you can with available information. If a revision requires information you don't have (e.g., named customer accounts), make the best improvement possible and note the gap in Revision Notes for the user. Only skip auto-revision entirely if the RFE is technically infeasible or the problem statement needs to be rethought from scratch.

1. Read the review feedback for each failing RFE
2. Edit the artifact files to address the specific issues
3. Add a `### Revision Notes` section at the end of each revised RFE documenting what changed and what gaps remain for the user to fill
4. Re-run the review (go back to Step 2) on the revised artifacts

Missing details, weak justification, ambiguous language, and scope issues are all auto-revisable — fix what you can and flag what you can't in the revision notes.

**Revision limits**:
- Maximum 2 auto-revision cycles
- If RFEs still fail after 2 cycles, stop and present the review report to the user

## Step 5: Advise the User

Based on the results:
- **All pass**: Tell the user RFEs are ready for `/rfe.submit`.
- **Some need revision after auto-revise failed**: List the remaining issues. Tell the user to edit the artifact files and re-run `/rfe.review`.
- **Fundamental problems**: Recommend re-running `/rfe.create` if the RFEs need to be rethought entirely.

$ARGUMENTS
