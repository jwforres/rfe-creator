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
- `--headless`: Suppress summaries (when called by speedrun)
- `--announce-complete`: Print completion marker when done (for CI / eval harnesses)
- Remaining arguments: explicit RFE IDs (RHAIRFE-NNNN)

Persist parsed flags (survives context compression):

```bash
mkdir -p tmp && cat > tmp/autofix-config.yaml << 'EOF'
headless: <true/false>
announce_complete: <true/false>
batch_size: <N>
EOF
```

**JQL mode**: If `--jql` is present, run the query:

```bash
python3 scripts/jql_query.py "<query>" [--limit N]
```

Parse the output: first line is `TOTAL=N`, remaining lines are IDs. These become the processing list.

**Explicit mode**: Use the provided IDs directly.

If no IDs and no JQL query, stop with usage instructions.

## Step 1: Bootstrap Pre-flight

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

Check which IDs are already processed:

```bash
python3 scripts/check_resume.py <all_IDs>
```

Parse output for `PROCESS=` and `SKIP=` lines. Remove already-processed IDs (pass=true, no error) from the processing list. Report skipped count if any.

## Step 3: Batch Processing

Split remaining IDs into batches of `batch-size` (default 5). Record the start time for the run report.

For each batch:

### 3a: Review

Invoke `/rfe.review` as an inline Skill:

```
/rfe.review --headless <batch_IDs>
```

This runs the full review pipeline (fetch, assess, feasibility, review-and-revise, re-assess if needed). Wait for it to complete.

### 3b: Collect Results

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

After all regular batches complete, scan ALL processed IDs for errors:

```bash
python3 scripts/collect_recommendations.py <all_processed_IDs>
```

Parse the `ERRORS=` line. If empty, skip to Step 5. For each error ID:

1. For IDs with `split_failed` errors: clean up first:

```bash
python3 scripts/cleanup_partial_split.py <ID>
```

2. For all retried IDs: clear the error field:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-reviews/<ID>-review.md error=null
```

3. Run the retry batch through the full pipeline (Steps 3a-3c)

4. If they fail again, report as permanent failures

## Step 5: Generate Reports

Generate the run report:

```bash
python3 scripts/generate_run_report.py --start-time "<start_time>" --batch-size <N> [--retried <retry_IDs>] [--retry-successes <success_IDs>] <all_IDs>
```

Generate the HTML review report:

```bash
python3 scripts/generate_review_pdf.py --revised-only --output artifacts/auto-fix-runs/<timestamp>-report.html
```

## Step 6: Final Summary

Present consolidated results:

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
- Run report: artifacts/auto-fix-runs/<timestamp>.yaml
- Review report: artifacts/auto-fix-runs/<timestamp>-report.html

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
