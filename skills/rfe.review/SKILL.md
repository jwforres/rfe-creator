---
name: rfe.review
description: Review and improve RFEs. Accepts a Jira key (e.g., /rfe.review RHAIRFE-1234) to fetch and review an existing RFE, or reviews local artifacts from /rfe.create. Runs rubric scoring, technical feasibility checks, and auto-revises issues it finds.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion, mcp__atlassian__getJiraIssue
---

You are an RFE review orchestrator. Your job is to review RFEs for quality and technical feasibility, and auto-revise issues when possible.

## Step 0: Resolve Input

Check if `$ARGUMENTS` contains a Jira key (e.g., `RHAIRFE-1234`).

**If a Jira key is provided**: First check if `artifacts/rfe-tasks/<jira_key>.md` already exists locally. If it does, use the local copy — do not re-fetch from Jira. This preserves any local edits from prior review cycles.

**If the local file does not exist**, fetch the RFE from Jira. Try `mcp__atlassian__getJiraIssue` first. If the MCP tool is unavailable, fall back to the REST API script:

```bash
python3 scripts/fetch_issue.py RHAIRFE-1234 --fields summary,description,priority,labels,status,comment --markdown
```

The script outputs JSON to stdout with description and comment bodies already converted to markdown. Parse `fields.description`, `fields.summary`, `fields.priority.name`, and `comments` array.

Write the Jira description to `artifacts/rfe-tasks/<jira_key>.md` as-is — preserve the original markdown structure, headings, and content exactly as fetched. Do not restructure, reformat, or fit it into any template. Only add YAML frontmatter (via `scripts/frontmatter.py set`). Do not add a title heading — the title lives in frontmatter only.

First, read the schema to know exact field names and allowed values:

```bash
python3 scripts/frontmatter.py schema rfe-task
```

Then set frontmatter, using the Jira key as the `rfe_id`:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-tasks/<jira_key>.md \
    rfe_id=<jira_key> \
    title="<title from Jira>" \
    priority=<priority from Jira> \
    size=<inferred size> \
    status=Ready
```

**Save an original snapshot** of the raw Jira description to `artifacts/rfe-originals/<jira_key>.md`. Write the `fields.description` value as-is (the raw markdown from Jira, not the templated version). This snapshot is used for (1) before/after data analysis of what remediation changed, and (2) optimistic conflict detection at submit time — the submit skill re-fetches the description from Jira and compares it against this file to detect concurrent modifications. Create the `artifacts/rfe-originals/` directory if it doesn't exist. This file is never modified by review or revision — it is only overwritten by a fresh Jira fetch.

**Also write a separate comments file** to `artifacts/rfe-tasks/<jira_key>-comments.md` with the Jira comment history. Format each comment as:

```markdown
# Comments: RHAIRFE-1234

## <Author Name> — <date>
<comment body>

## <Author Name> — <date>
<comment body>
```

This file provides stakeholder context to the review forks. It is NOT part of the RFE content and must NOT be pushed back to Jira during submission.

**If no Jira key**: Proceed with existing local artifacts.

## Step 1: Verify Artifacts Exist

List files in `artifacts/rfe-tasks/`. If no RFE artifacts exist and no Jira key was provided, tell the user to run `/rfe.create` first or provide a Jira key (e.g., `/rfe.review RHAIRFE-1234`) and stop.

Check if prior reviews exist in `artifacts/rfe-reviews/`. If any exist for the RFEs being reviewed, read them — this is a re-review after revisions.

## Step 1.5: Fetch Architecture Context

```bash
bash scripts/fetch-architecture-context.sh
```

The architecture context path for the feasibility fork is `.context/architecture-context/architecture/$LATEST`.

If the fetch fails (network issue, repo unavailable, API rate limit), proceed without architecture context. Note it in the review output.

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

**If the bootstrap failed** (network issue, git unavailable): Skip rubric validation. Note in the review that rubric validation was skipped because assess-rfe could not be fetched. Perform a basic quality check instead:
- Does each RFE describe a business need (WHAT/WHY), not a task or technical activity?
- Does each RFE avoid prescribing architecture, technology, or implementation?
- Does each RFE name specific affected customers?
- Does each RFE include evidence-based business justification?
- Is each RFE right-sized for a single strategy feature?

### Stakeholder Context

Both review forks should read any `artifacts/rfe-tasks/*-comments.md` files that exist for the RFEs being reviewed. Comments from stakeholders provide context about what is intentional in the RFE, what has already been discussed, and what related work exists. This context should inform the review — e.g., if a stakeholder has already confirmed a technology choice is deliberate, the rubric should not penalize it.

### Review 2: Technical Feasibility (Forked)

Invoke the `rfe-feasibility-review` skill on the RFE artifacts. This runs in a forked context with architecture context (if available) to assess whether each RFE is technically feasible without the business context influencing the assessment. If comments files exist in `artifacts/rfe-tasks/`, include them in the feasibility reviewer's context.

## Step 3: Write Per-Issue Review Files

For each reviewed RFE, write a review file to `artifacts/rfe-reviews/`. First, read the schema to know exact field names and allowed values:

```bash
python3 scripts/frontmatter.py schema rfe-review
```

Then for each RFE, write the review body (assessor feedback, feasibility details, strategy considerations, revision history) to `artifacts/rfe-reviews/{id}-review.md`, then set frontmatter using the actual review results:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<id>-review.md \
    rfe_id=<rfe_id> \
    score=<total_score> \
    pass=<true_or_false> \
    recommendation=<recommendation> \
    feasibility=<feasibility> \
    revised=<true_or_false> \
    needs_attention=<true_or_false> \
    scores.what=<what_score> \
    scores.why=<why_score> \
    scores.open_to_how=<open_to_how_score> \
    scores.not_a_task=<not_a_task_score> \
    scores.right_sized=<right_sized_score>
```

**Before scores**: On the **first** scoring pass (before any auto-revision), also write the initial scores as `before_score` and `before_scores.*`. These capture the as-fetched quality baseline for the review report. On subsequent passes (after auto-revision), do NOT include `before_score`/`before_scores` — the `set` command merges fields, so the originals are preserved automatically.

```bash
# First pass only — write before scores alongside the initial scores:
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<id>-review.md \
    before_score=<total_score> \
    before_scores.what=<what_score> \
    before_scores.why=<why_score> \
    before_scores.open_to_how=<open_to_how_score> \
    before_scores.not_a_task=<not_a_task_score> \
    before_scores.right_sized=<right_sized_score>
```

**Re-review guard**: If `before_scores` already exists in the frontmatter (check with `frontmatter.py read`), do NOT overwrite it — it represents the original baseline, not the previous revision's scores.

Use the RFE's `rfe_id` for the filename prefix (e.g., `RHAIRFE-1234-review.md` for Jira-fetched RFEs, `RFE-001-slug-review.md` for local RFEs).

The review file body should contain:

```markdown
## Assessor Feedback
<Full rubric feedback verbatim — scores, notes, verdict, and actionable suggestions.>

## Technical Feasibility
<feasible / infeasible — with details>

## Strategy Considerations
<Items flagged for /strat.refine, or "none">

## Revision History
<What changed across auto-revision cycles, or "none">
```

After writing all review files, rebuild the index:

```bash
python3 scripts/frontmatter.py rebuild-index
```

## Step 4: Auto-Revise

Always attempt at least one auto-revision cycle when any criterion scores below full marks. Improve what you can with available information. If a revision requires information you don't have (e.g., named customer accounts), make the best improvement possible and note the gap in the review file's Revision History for the user. Only skip auto-revision entirely if the RFE is technically infeasible or the problem statement needs to be rethought from scratch.

### Revision Principles

**Only edit sections that directly caused a rubric failure.** If the rubric didn't flag a section, don't touch it. If you're unsure whether a section contributed to a score, leave it alone. Never rewrite the entire artifact from scratch — this destroys author context that wasn't scored.

**Reframe, don't remove.** When the assessor flags sections for HOW violations, the problem may not be the information — it's the framing. Prescriptive architecture and implementation directives can almost always be reframed into non-prescriptive context that preserves useful information while fixing the rubric score. For example, a section that assigns components to architectural roles can be reframed as a flat context list with a disclaimer that engineering should determine the design. Only remove content as a last resort when there is nothing reframeable (pure implementation detail with no business-facing content).

**If content must be removed**, it will be tracked automatically. The content preservation check (`check_content_preservation.py --write-yaml`) detects missing blocks and writes them to `artifacts/rfe-tasks/{id}-removed-context.yaml` as structured blocks with `type: unclassified`. This file must NOT be merged back into the RFE description.

**When a section mixes WHAT and HOW and the assessor did not flag it**, leave it alone. Do not proactively scan for additional HOW content beyond what the assessor identified.

**Right-sizing is a recommendation, never auto-applied.** If the rubric scores Right-sized at 0 or 1, report the recommendation to split in the review file. Do NOT remove acceptance criteria, scope items, or capabilities from the artifact to force a different shape. Splitting an RFE is a structural decision that changes what the RFE *is* — only the author can make that call.

**Do not invent missing evidence.** If the rubric flags weak business justification due to missing named customers or revenue data, flag the gap in the review file's Revision History for the author to fill. Do not fabricate evidence.

### Revision Steps

1. Read the **full** review feedback for each failing RFE (from the review file just written)
2. Read the comments file (`artifacts/rfe-tasks/{id}-comments.md`) if it exists — stakeholder comments may explain why certain content is intentional
3. For each criterion the assessor flagged, follow its specific recommendations:
   - **Open to HOW**: Reframe flagged sections to remove prescriptive framing while preserving useful context. If content cannot be reframed, remove it from the RFE — the preservation check will track it automatically. **Critical distinction**: When the RFE is about integrating with or providing a specific vendor project, product, or API, naming that project/product is part of the WHAT (the business need), not the HOW. Do not generalize away named vendor solutions that are the subject of the integration. Only reframe language that prescribes *internal implementation choices* (architecture patterns, specific K8s resources, build tooling, deployment ratios).
   - **WHY**: Strengthen with available evidence (stakeholder comments, strategic alignment references); flag gaps the author must fill (named customers, revenue data)
   - **Right-sized**: Report the recommendation only; do not split or remove scope. For **0/2** (needs 3+ features), advise the user to run `/rfe.split`. For **1/2** (slightly broad at 1-2 features), note that this is an acceptable score — the RFE may map to multiple strategy features at the RHAISTRAT level without needing to be split as an RFE. Only suggest `/rfe.split` for 1/2 if the capabilities clearly serve different customer segments or user scenarios that could be independently prioritized. Do NOT suggest splitting when capabilities are delivery-coupled (e.g., a breaking change and its migration path).
   - **WHAT / Not a task**: Follow assessor guidance if provided
4. **Content preservation check**: After each revision, run:
   ```bash
   python3 scripts/check_content_preservation.py artifacts/rfe-originals/<id>.md artifacts/rfe-tasks/<id>.md --write-yaml
   ```
   The `--write-yaml` flag automatically writes any missing blocks to `artifacts/rfe-tasks/{id}-removed-context.yaml` with `type: unclassified`. This ensures no content is silently dropped.

5. **Classify removed blocks**: Read the YAML file and update each block's `type` field:
   - **`reworded`**: The same intent is still in the RFE, just expressed differently (e.g., prescriptive rules reframed as user outcomes). This block will NOT be posted to Jira. **Exception**: If the original text names specific vendor projects/products, specific APIs or libraries, or specific technology choices that were generalized away during reframing, classify as `genuine` instead — those specifics are useful engineering context even if the capability intent is preserved.
   - **`genuine`**: Implementation specifics (API names, parameter schemas, architecture decisions, named vendor projects/products, specific libraries) not present in the RFE that would be useful RHAISTRAT context. This block WILL be posted as a Jira comment during `/rfe.submit`.
   - **`non-substantive`**: Marketing filler, empty template placeholders, or generic statements with no recoverable substance. This block will NOT be posted to Jira.

   **After classifying, verify all blocks have been classified** — scan the YAML for any remaining `type: unclassified` entries and fix them. As a safety net, `/rfe.submit` treats `unclassified` blocks the same as `genuine` (they get posted) to prevent unintentional data loss.
6. Document what changed and why in the review file's `## Revision History` section. Do NOT add revision notes to the RFE artifact itself — keep RFE files clean with only frontmatter and business content. Gaps that require author input (e.g., missing named customers) also belong in the review file, not in the artifact.
7. Update the review file frontmatter: set `revised=true` if content was modified, set `needs_attention=true` if human review is still needed
8. Re-run the review (go back to Step 2) on the revised artifacts

**Revision limits**:
- Maximum 2 auto-revision cycles
- If RFEs still fail after 2 cycles, stop and present the results to the user

## Step 5: Advise the User

Based on the results:
- **All pass**: Tell the user RFEs are ready for `/rfe.submit`.
- **Some need revision after auto-revise failed**: List the remaining issues. Tell the user to edit the artifact files and re-run `/rfe.review`.
- **Fundamental problems**: Recommend re-running `/rfe.create` if the RFEs need to be rethought entirely.

$ARGUMENTS
