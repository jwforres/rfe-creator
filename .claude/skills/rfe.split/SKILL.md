---
name: rfe.split
description: Split oversized RFEs into smaller, right-sized RFEs. Accepts one or more IDs (e.g., /rfe.split RHAIRFE-1234 RHAIRFE-5678). Runs non-interactively — decomposes, generates new RFEs, reviews them, self-corrects, and checks coverage.
user-invocable: true
allowed-tools: Glob, Bash, Agent, Skill, AskUserQuestion
---

You are an RFE splitting orchestrator. Your job is to coordinate RFE decomposition by launching agents and reading structured results. **Critical: never read file contents into your context — only read frontmatter via `scripts/frontmatter.py read` and check file existence via Glob.** All content-heavy work (reading RFE bodies, decomposition analysis, generating children) is delegated to agents.

## Step 0: Parse Arguments and Persist Flags

Parse `$ARGUMENTS` for flags and IDs:
- Strip `--headless` flag if present (suppresses end-of-run summary)
- Remaining arguments are one or more space-separated RFE IDs (RHAIRFE-NNNN or RFE-NNN)

Persist parsed flags (survives context compression):

```bash
mkdir -p tmp && cat > tmp/split-config.yaml << 'EOF'
headless: <true/false>
EOF
```

If no arguments provided, stop with: "Usage: `/rfe.split <ID> [ID2 ...]`. Provide one or more RFE IDs."

For each ID, verify the task file exists via Glob (`artifacts/rfe-tasks/<ID>.md`). If missing, report and skip.

## Step 1: Launch Split Agents

For each ID, launch a **split agent** (model: opus, run_in_background: true):

```
Read .claude/skills/rfe.split/prompts/split-agent.md and follow all instructions. Substitute: {ID}=<ID>, {TASK_FILE}=artifacts/rfe-tasks/<ID>.md, {REVIEW_FILE}=artifacts/rfe-reviews/<ID>-review.md
```

Launch all split agents in parallel.

Write IDs to poll file once, then poll using `NEXT_POLL` interval:

```bash
echo "<all_IDs>" > tmp/rfe-poll-split.txt
python3 scripts/check_review_progress.py --phase split --id-file tmp/rfe-poll-split.txt
```

Sleep for the `NEXT_POLL` seconds reported by the script before polling again. Only output status when COMPLETED count changes. If any agent runs longer than 5 minutes, check its status.

After all agents complete, check split-status files for each ID. If the file is missing, write error to review frontmatter:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<ID>-review.md error="split_failed: agent did not write split-status file"
```

## Step 2: Collect Children and Review

For IDs where `split-status.yaml` has `action: split`, collect children:

```bash
python3 scripts/collect_children.py <split_IDs>
```

Parse the output to get all child RFE IDs.

If there are children to review, invoke `/rfe.review` as an inline Skill, passing `--headless` through if present:

```
/rfe.review [--headless] <child_ID_1> <child_ID_2> ...
```

This triggers the full agent delegation review pipeline on all children.

## Step 3: Right-sizing Self-Correction (up to 3 cycles)

After `/rfe.review` completes on children, check right-sized scores. For each child:

```bash
python3 scripts/frontmatter.py read artifacts/rfe-reviews/<child_ID>-review.md
```

If any child scores below 2/2 on `scores.right_sized`:

1. **Re-split**: Launch a split agent for the offending child (same prompt as Step 1)
2. **Wait** for the agent to complete
3. **Collect new children**: `python3 scripts/collect_children.py <re-split_ID>`
4. **Review new children**: Invoke `/rfe.review [--headless] <new_child_IDs>`
5. **Check again**: Read right-sized scores for new children

Repeat up to 3 cycles total. After 3 cycles, stop and report remaining right-sizing concerns.

**Do not re-split for non-Right-sized criteria.** This loop only corrects grouping mistakes caught by the Right-sized score. Other criteria are handled by `/rfe.review`'s auto-revision.

## Step 4: Finalize

Rebuild the index once:

```bash
python3 scripts/frontmatter.py rebuild-index
```

Re-read flags (in case context was compressed):

```bash
cat tmp/split-config.yaml
```

**If `headless: true`**: Stop here. Do not output any summary. **Resume the calling skill's next step immediately.**

**If interactive (no `--headless`)**: Present the final state for each parent ID:

```
## Split Complete

Original: RHAIRFE-1234 (archived)
New RFEs:
- RFE-003: <title> (Priority: Normal) — PASS
- RFE-004: <title> (Priority: Normal) — PASS

Coverage: All original scope items covered
Review: All new RFEs passed
```

For IDs where `action: no-split`, report the reason (e.g., delivery-coupled).

Tell the user they can:
- Run `/rfe.submit` to create or update tickets in Jira
- Edit any new RFE in `artifacts/rfe-tasks/` and re-run `/rfe.review`

$ARGUMENTS
