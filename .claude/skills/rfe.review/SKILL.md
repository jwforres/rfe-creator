---
name: rfe.review
description: Review and improve RFEs. Accepts one or more Jira keys (e.g., /rfe.review RHAIRFE-1234 RHAIRFE-5678) to fetch and review existing RFEs, or reviews local artifacts from /rfe.create. Runs rubric scoring, technical feasibility checks, and auto-revises issues it finds.
user-invocable: true
allowed-tools: Glob, Bash, Agent, AskUserQuestion
---

You are an RFE review orchestrator. Your job is to coordinate reviews and revisions by launching agents and reading structured results. **Critical: never read file contents into your context — only read frontmatter via `scripts/frontmatter.py read` and check file existence via Glob.** All content-heavy work (reading RFE bodies, assessment results, writing review files, doing revisions) is delegated to agents.

## Step 0: Parse Arguments and Persist Flags

Parse `$ARGUMENTS` for flags and IDs:
- Strip `--headless` flag if present (suppresses end-of-run summary)
- Remaining arguments are one or more space-separated RFE IDs (RHAIRFE-NNNN or RFE-NNN)

Persist parsed flags (survives context compression):

```bash
mkdir -p tmp && cat > tmp/review-config.yaml << 'EOF'
headless: <true/false>
EOF
```

For each ID, check if `artifacts/rfe-tasks/<id>.md` already exists locally (use Glob, don't read the file). Separate IDs into:
- **Local**: task file exists — skip fetch
- **Remote**: task file missing — needs Jira fetch

## Step 1: Fetch Missing RFEs

For each remote ID, launch a **fetch agent** (model: opus, run_in_background: true):

```
Read .claude/skills/rfe.review/prompts/fetch-agent.md and follow all instructions. Substitute {KEY} with <ID> throughout.
```

Write IDs to poll file once, then poll using `NEXT_POLL` interval:

```bash
echo "<all_remote_IDs>" > tmp/rfe-poll-fetch.txt
python3 scripts/check_review_progress.py --phase fetch --id-file tmp/rfe-poll-fetch.txt
```

Sleep for the `NEXT_POLL` seconds reported by the script before polling again. Only output a status line when COMPLETED count changes. If any agent runs longer than 5 minutes, check its status.

After all fetch agents complete, verify task files exist via Glob. For any missing, write an error to the review file:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<ID>-review.md rfe_id=<ID> score=0 pass=false recommendation=revise feasibility=feasible revised=false needs_attention=true scores.what=0 scores.why=0 scores.open_to_how=0 scores.not_a_task=0 scores.right_sized=0 error="fetch_failed: task file not created"
```

Remove failed IDs from the processing list and continue with remaining IDs.

## Step 1.5: Setup

Run these in parallel (two Bash calls):

```bash
bash scripts/fetch-architecture-context.sh
```

```bash
bash scripts/bootstrap-assess-rfe.sh
```

If architecture fetch fails, proceed without it. If bootstrap fails, note it — review-and-revise agents will do basic quality checks instead.

## Step 2: Launch Assessment + Feasibility Agents

For each ID being reviewed:

**Prepare assessment:**

```bash
python3 .context/assess-rfe/scripts/prep_single.py <ID>
```

```bash
cp artifacts/rfe-tasks/<ID>.md /tmp/rfe-assess/single/<ID>.md
```

**Launch assess agent** (model: opus, run_in_background: true):

```
Read .claude/skills/rfe.review/prompts/assess-agent.md and follow all instructions. Substitute: {KEY}=<ID>, {DATA_FILE}=/tmp/rfe-assess/single/<ID>.md, {RUN_DIR}=/tmp/rfe-assess/single, {PROMPT_PATH}=.context/assess-rfe/scripts/agent_prompt.md
```

**Launch feasibility agent** (model: opus, run_in_background: true) — one per ID:

```
Read the skill file at .claude/skills/rfe-feasibility-review/SKILL.md and follow all instructions in the body (everything after the YAML frontmatter). The RFE ID to review is: <ID>
```

Launch all agents for all IDs in parallel (2N agents total for N IDs).

Write IDs to poll files once, then poll every 60 seconds:

```bash
echo "<all_IDs>" > tmp/rfe-poll-assess.txt
echo "<all_IDs>" > tmp/rfe-poll-feasibility.txt
python3 scripts/check_review_progress.py --phase assess --id-file tmp/rfe-poll-assess.txt
python3 scripts/check_review_progress.py --phase feasibility --id-file tmp/rfe-poll-feasibility.txt
```

Sleep for the `NEXT_POLL` seconds reported by the script before polling again. Only output status when COMPLETED count changes. Wait for all to complete.

After completion, check prerequisites for each ID via Glob:
- If assess result (`/tmp/rfe-assess/single/<ID>.result.md`) is missing → write error: `assess_failed`
- If feasibility file (`artifacts/rfe-reviews/<ID>-feasibility.md`) is missing → write error: `feasibility_failed`
- If either is missing for an ID, write the error to review frontmatter and remove from processing list

## Step 3: Launch Review Agents

For each remaining ID, launch a **review agent** (model: opus, run_in_background: true):

```
Read .claude/skills/rfe.review/prompts/review-and-revise-agent.md and follow all instructions. Substitute: {ID}=<ID>, {ASSESS_PATH}=/tmp/rfe-assess/single/<ID>.result.md, {FEASIBILITY_PATH}=artifacts/rfe-reviews/<ID>-feasibility.md, {FIRST_PASS}=true
```

Launch all review agents in parallel.

Write IDs to poll file once, then poll using `NEXT_POLL` interval:

```bash
echo "<all_IDs>" > tmp/rfe-poll-review.txt
python3 scripts/check_review_progress.py --phase review --id-file tmp/rfe-poll-review.txt
```

Sleep for the `NEXT_POLL` seconds reported by the script before polling again. Wait for all to complete. For any ID where the review file is missing or has no frontmatter, write error: `review_failed`.

## Step 3.5: Launch Revise Agents

After all review agents complete, determine which IDs need revision. For each ID, read review frontmatter:

```bash
python3 scripts/frontmatter.py read artifacts/rfe-reviews/<ID>-review.md
```

Launch a **revise agent** (model: opus, run_in_background: true) for each ID where `pass=false` and `feasibility` is not `infeasible`:

```
Read .claude/skills/rfe.review/prompts/revise-agent.md and follow all instructions. Substitute: {ID}=<ID>
```

Launch all revise agents in parallel.

Write IDs to poll file once, then poll using `NEXT_POLL` interval:

```bash
echo "<all_IDs_being_revised>" > tmp/rfe-poll-revise.txt
python3 scripts/check_review_progress.py --phase revise --id-file tmp/rfe-poll-revise.txt
```

Sleep for the `NEXT_POLL` seconds reported by the script before polling again. Wait for all to complete.

**Post-processing: fix revised flag.** The revise agent may run out of budget before setting `revised=true`. After all agents complete, for each revised ID, verify the flag is correct:

```bash
python3 scripts/check_revised.py artifacts/rfe-originals/<ID>.md artifacts/rfe-tasks/<ID>.md
```

If the script reports files differ and frontmatter shows `revised=false`, fix it:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<ID>-review.md revised=true
```

## Step 4: Re-assess if Revised (max 2 cycles)

After all revise agents complete, check which IDs need re-assessment:

```bash
python3 scripts/collect_recommendations.py --reassess <all_IDs>
```

Parse output for `REASSESS=` line. For each ID needing re-assessment (revised=true, pass=false), and this is cycle 1:

1. Save cumulative state and remove review files so progress detection works:

```bash
python3 scripts/preserve_review_state.py save <all_reassess_IDs>
rm artifacts/rfe-reviews/<ID>-review.md  # for each reassess ID
```

2. Re-run assessment: prep_single, cp, launch assess agent (background)
3. Wait for all re-assess agents to complete
4. Launch review agents again with `{FIRST_PASS}=false`
5. Wait for all review agents to complete (file existence check works because review files were removed)
6. Restore before_scores and revision history:

```bash
python3 scripts/preserve_review_state.py restore <all_reassess_IDs>
```

7. Launch revise agents for IDs where `pass=false` and `feasibility` is not `infeasible`
8. Wait for all revise agents to complete, run post-processing revised flag fix

After cycle 2, stop regardless of results.

## Step 5: Finalize

Rebuild the index once:

```bash
python3 scripts/frontmatter.py rebuild-index
```

Re-read flags (in case context was compressed):

```bash
cat tmp/review-config.yaml
```

**If `headless: true`**: Stop here. Do not output any summary. The calling orchestrator handles reporting. **Resume the calling skill's next step immediately.**

**If interactive (no `--headless`)**: Read results and present summary:

```bash
python3 scripts/batch_summary.py <all_IDs>
```

Based on the output:
- **All pass**: Tell the user RFEs are ready for `/rfe.submit`.
- **Some need revision**: List the remaining issues (from summary output). Tell the user to edit artifacts and re-run `/rfe.review`.
- **Some recommend split**: Tell the user to run `/rfe.split <ID>` for those IDs.
- **Errors**: Report which IDs had errors and suggest retrying.

$ARGUMENTS
