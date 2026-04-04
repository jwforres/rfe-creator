---
name: rfe.auto-fix
description: Review and fix batches of RFEs automatically. Accepts explicit IDs or a JQL query. Reviews, auto-revises, and splits oversized RFEs. Non-interactive.
user-invocable: true
allowed-tools: Glob, Bash, Skill
---

You are a non-interactive RFE auto-fix pipeline. Your job is to review and fix batches of RFEs — including splitting oversized ones. Do not ask questions or wait for confirmation. Make all decisions autonomously.

## Step 0: Parse Arguments and Persist Flags

Parse `$ARGUMENTS` for:
- `--jql "<query>"`: JQL query to fetch IDs from Jira
- `--limit N`: Cap the number of IDs to process (useful for testing JQL queries)
- `--batch-size N`: Override batch size (default: 5)
- `--data-dir "<path>"`: Local directory with previous run results (for snapshot diffing)
- `--headless`: Suppress summaries (when called by speedrun)
- `--announce-complete`: Print completion marker when done (for CI / eval harnesses)
- Remaining arguments: explicit RFE IDs (RHAIRFE-NNNN)

Persist parsed flags (survives context compression):

```bash
python3 scripts/state.py init tmp/autofix-config.yaml headless=<true/false> announce_complete=<true/false> batch_size=<N>
```

**JQL mode**: If `--jql` is present, run the snapshot fetch:

```bash
python3 scripts/snapshot_fetch.py fetch "<query>" --ids-file tmp/autofix-all-ids.txt --changed-file tmp/autofix-changed-ids.txt [--limit N] [--data-dir "<path>"]
```

The script prints the actual JQL to stderr. Output this to the user: `[AUTOFIX] JQL: <jql>`. The script writes all IDs to process to `tmp/autofix-all-ids.txt` and changed-only IDs to `tmp/autofix-changed-ids.txt`. Parse stdout for counts: `TOTAL=N`, `CHANGED=N`, `NEW=N`, `UNCHANGED=N`.

**Explicit mode**: Use the provided IDs directly. Persist to disk:

```bash
python3 scripts/state.py write-ids tmp/autofix-all-ids.txt <all_IDs>
python3 scripts/state.py write-ids tmp/autofix-changed-ids.txt
```

If no IDs and no JQL query, stop with usage instructions.

Output: `[AUTOFIX] Step 0: Parsed N IDs (C changed, W new, U unchanged), batch_size=M`
Then read `tmp/autofix-all-ids.txt` and output: `[AUTOFIX] Selected IDs: <space-separated list>`

## Step 1: Bootstrap Pre-flight

Output: `[AUTOFIX] Step 1: Bootstrap`

Run bootstrap once before any batching:

```bash
bash scripts/bootstrap-assess-rfe.sh
```

If it fails, retry once:

```bash
bash scripts/bootstrap-assess-rfe.sh
```

If the retry also fails, stop entirely: "assess-rfe bootstrap failed — cannot proceed. Check network connectivity and retry."

## Step 2: Resume Check

Output: `[AUTOFIX] Step 2: Resume Check`

Run the resume check. The script reads IDs and changed IDs from files, bypasses the resume check for changed IDs (their Jira content changed, so local reviews are stale), and writes the final process list:

```bash
python3 scripts/check_resume.py --ids-file tmp/autofix-all-ids.txt --changed-file tmp/autofix-changed-ids.txt --output-file tmp/autofix-process-ids.txt
```

Parse stdout for counts: `PROCESS=N`, `SKIP=N`, `CHANGED=N`.

Output: `[AUTOFIX] Step 2: N to process (C changed), M skipped`

## Step 3: Batch Processing

Re-read the filtered ID list from disk (in case context was compressed):

```bash
python3 scripts/state.py read-ids tmp/autofix-process-ids.txt
```

Output: `[AUTOFIX] Recovered N IDs from autofix-process-ids.txt`

Split remaining IDs into batches of `batch-size` (default 5). Output: `[AUTOFIX] Step 3: Batch Processing (M batches of K)`

Persist the start time, batch count, and per-batch ID lists so they survive context compression:

```bash
python3 scripts/state.py set tmp/autofix-config.yaml start_time=$(python3 scripts/state.py timestamp) total_batches=<M>
```

```bash
python3 scripts/state.py write-ids tmp/autofix-batch-1-ids.txt <batch_1_IDs>
python3 scripts/state.py write-ids tmp/autofix-batch-2-ids.txt <batch_2_IDs>
# ... one file per batch
```

For each batch:

Re-read config to recover batch position after potential context compression, then update the current batch tracker:

```bash
python3 scripts/state.py read tmp/autofix-config.yaml
python3 scripts/state.py set tmp/autofix-config.yaml current_batch=<N>
```

Re-read this batch's IDs from disk (do not use IDs from memory — they may be hallucinated after compression):

```bash
python3 scripts/state.py read-ids tmp/autofix-batch-N-ids.txt
```

Output: `[AUTOFIX] Batch N/M: K IDs`

### 3a: Review

Invoke `/rfe.review` as an inline Skill, using IDs from the batch file:

```
/rfe.review --headless <batch_IDs_from_file>
```

This runs the full review pipeline (fetch, assess, feasibility, review, revise, re-assess if needed). Wait for it to complete.

### 3b: Collect Results

Re-read config and batch IDs from disk (context compression may have corrupted in-memory state):

```bash
python3 scripts/state.py read tmp/autofix-config.yaml
python3 scripts/state.py read-ids tmp/autofix-batch-N-ids.txt
```

Use the IDs from the file (not memory) for all subsequent steps in this batch:

```bash
python3 scripts/collect_recommendations.py <batch_IDs>
```

Parse output for `SPLIT=`, `SUBMIT=`, `ERRORS=` lines.

### 3c: Split if Needed

If any IDs have `recommendation=split`, invoke `/rfe.split`:

```
/rfe.split --headless <split_IDs>
```

Wait for completion. The split skill handles its own review cycles internally.

### 3d: Between-Batch Summary

Output a progress update:

```
### Batch N/M
- Review: X submitted, Y passed, Z needs split
- Split: <IDs> → <child IDs>
- Errors: N
- Running total: A/B processed, C passed, D split
```

## Step 4: Retry Queue

Output: `[AUTOFIX] Step 4: Retry Queue`

After all regular batches complete, re-read the full ID list from disk:

```bash
python3 scripts/state.py read-ids tmp/autofix-all-ids.txt
```

Output: `[AUTOFIX] Recovered N IDs from autofix-all-ids.txt`

Scan ALL processed IDs for errors:

```bash
python3 scripts/collect_recommendations.py <all_IDs_from_file>
```

Parse the `ERRORS=` line. If empty, output `[AUTOFIX] Step 4: No errors, skipping retry` and skip to Step 5.

If errors found, **persist retry IDs to disk** (do not rely on in-memory parsing — they may be lost to compression during the retry run):

```bash
python3 scripts/state.py write-ids tmp/autofix-retry-ids.txt <error_IDs>
```

Output: `[AUTOFIX] Step 4: Retrying N IDs: <error_IDs>`

For each error ID:

1. For IDs with `split_failed` errors: clean up first:

```bash
python3 scripts/cleanup_partial_split.py <ID>
```

2. For all retried IDs: clear the error field:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<ID>-review.md error=null
```

3. Re-read retry IDs from disk before running the pipeline (compression may have lost them during cleanup):

```bash
python3 scripts/state.py read-ids tmp/autofix-retry-ids.txt
```

4. Run the retry batch through the full pipeline (Steps 3a-3c) using IDs from the file

5. If they fail again, report as permanent failures

## Step 5: Generate Reports

Output: `[AUTOFIX] Step 5: Generate Reports`

Re-read persisted config and ID list to recover after potential context compression:

```bash
python3 scripts/state.py read tmp/autofix-config.yaml
python3 scripts/state.py read-ids tmp/autofix-all-ids.txt
```

Output: `[AUTOFIX] Recovered N IDs from autofix-all-ids.txt`

Parse `start_time` from the config. Use IDs from the file. Generate the run report:

```bash
python3 scripts/generate_run_report.py --start-time "<start_time>" --batch-size <N> [--retried <retry_IDs>] [--retry-successes <success_IDs>] <all_IDs_from_file>
```

Parse the `run_id` from the script output (format: `YYYYMMDD-HHMMSS`). Generate the HTML review report using that `run_id`:

```bash
python3 scripts/generate_review_pdf.py --revised-only --output artifacts/auto-fix-runs/<run_id>-report.html
```

## Step 6: Final Summary

Output: `[AUTOFIX] Step 6: Final Summary`

Re-read config and IDs from disk (context compression may have lost flags like `announce_complete`):

```bash
python3 scripts/state.py read tmp/autofix-config.yaml
python3 scripts/state.py read-ids tmp/autofix-all-ids.txt
```

List split children (these are created during processing and are not in the persisted ID list):

```bash
ls artifacts/rfe-reviews/RFE-*-review.md 2>/dev/null | sed 's|artifacts/rfe-reviews/||;s|-review.md||'
```

Present consolidated results (combine persisted IDs with any split children found above):

```
## Auto-fix Complete

### Summary
- Total: N processed
- Passed: N
- Failed: N
- Split: N (into M children)
- Errors: N
- Retried: N (N succeeded)

### Per-RFE Results
<output from batch_summary.py on all IDs>

### Reports
- Run report: artifacts/auto-fix-runs/<run_id>.yaml
- Review report: artifacts/auto-fix-runs/<run_id>-report.html
- Snapshot: artifacts/auto-fix-runs/issue-snapshot-<ts>.yaml (written during fetch)

### Remaining Issues
<Any issues that could not be auto-fixed, or "None">

### Next Steps
<e.g., /rfe.submit for passing RFEs, manual edits for failures>
```

If `--announce-complete` was set, after outputting the final summary run:

```bash
python3 scripts/finish.py
```

$ARGUMENTS
