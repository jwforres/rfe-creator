---
name: rfe.auto-fix
description: Review and fix batches of RFEs automatically. Accepts explicit IDs or a JQL query. Reviews, auto-revises, and splits oversized RFEs. Non-interactive.
user-invocable: true
allowed-tools: Glob, Bash, Agent
---

You are a non-interactive RFE auto-fix pipeline. Do not ask questions or wait for confirmation. Make all decisions autonomously.

## Setup

Parse `$ARGUMENTS` for:
- `--jql "<query>"`, `--limit N`, `--batch-size N` (default 50), `--data-dir "<path>"`
- `--headless`, `--announce-complete`, `--reprocess`
- Remaining arguments: explicit RFE IDs

### 1. Init

```bash
python3 scripts/pipeline_state.py init [--batch-size N] [--headless] [--announce-complete]
```

### 2. IDs

**JQL mode** (`--jql`):

```bash
python3 scripts/snapshot_fetch.py fetch "<query>" --ids-file tmp/pipeline-all-ids.txt --changed-file tmp/pipeline-changed-ids.txt [--limit N] [--data-dir "<path>"] [--reprocess]
```

Print `[AUTOFIX] JQL: <jql>` from stderr output. Pass `--reprocess` if set.

**Reprocess-only mode** (`--reprocess` without `--jql`):

```bash
python3 scripts/snapshot_fetch.py fetch --reprocess --ids-file tmp/pipeline-all-ids.txt --changed-file tmp/pipeline-changed-ids.txt
```

**Explicit mode**:

```bash
python3 scripts/state.py write-ids tmp/pipeline-all-ids.txt <IDs>
python3 scripts/state.py write-ids tmp/pipeline-changed-ids.txt
```

If no IDs and no JQL and not `--reprocess`, stop with usage instructions.

### 3. Bootstrap

```bash
bash scripts/bootstrap-assess-rfe.sh
```

Retry once on failure. If retry fails, stop: "bootstrap failed."

### 4. Resume check + batch

```bash
python3 scripts/check_resume.py --ids-file tmp/pipeline-all-ids.txt --changed-file tmp/pipeline-changed-ids.txt --output-file tmp/pipeline-process-ids.txt
```

Read process IDs: `python3 scripts/state.py read-ids tmp/pipeline-process-ids.txt`

Split into batches of `batch_size`. Write each:

```bash
python3 scripts/state.py write-ids tmp/pipeline-batch-1-ids.txt <batch_1_IDs>
python3 scripts/state.py write-ids tmp/pipeline-batch-2-ids.txt <batch_2_IDs>
```

Start the pipeline:

```bash
python3 scripts/pipeline_state.py set total_batches=<M>
python3 scripts/pipeline_state.py set-phase BATCH_START
```

## Dispatch Loop

Repeat until phase is `DONE`:

### Step 1: Read config

```bash
python3 scripts/pipeline_state.py get-phase-config
```

Parse YAML for: `type`, `prompt`, `ids_file`, `vars`, `poll_phase`, `post_verify`, `pre_script`, `subagent_type`, `parallel`.

### Step 2: Dispatch

**noop**: Skip to advance.

**script**: Run `python3 scripts/pipeline_state.py run-phase`.

**agent**:

1. Read IDs from `ids_file`.
2. Pre-filter already done: `python3 scripts/check_review_progress.py --phase <poll_phase> <IDs>` — remove COMPLETED IDs from the working set.
3. Compute wave size: `max_concurrent` (default `batch_size`) divided by `(1 + number of parallel entries)`, rounded down (minimum 1). Process remaining IDs in waves of that size:

   a. For each ID in the wave:
      - If `pre_script`: run it with `{ID}` replaced by the current ID.
      - Build the agent environment string from `vars`: for each key-value pair, replace `{ID}` with the current ID, producing lines like `ID=RHAIRFE-1234`, `ASSESS_PATH=/tmp/rfe-assess/single/RHAIRFE-1234.result.md`, etc.
      - Launch a background Agent with `subagent_type` (if set). The prompt is:
        `"<vars as KEY=VALUE lines>\n\nRead <prompt> and follow all instructions exactly."`
      - If `parallel` entries exist: for each entry, launch one additional background Agent using the same pattern with the entry's `prompt`.

   b. Poll until wave completes:

      ```bash
      python3 scripts/check_review_progress.py --poll --phase <poll_phase> [--also-phase <p> for each parallel entry's poll_phase] [--fast-poll if not headless] --id-file <ids_file>
      ```

      Blocks ~90s (sleeps internally), then exits 0 (done) or 3 (pending).
      On exit 3, re-run the exact same command until exit 0 — this is a required retry, not polling.

4. After all waves: if `post_verify` is set, run it.

### Step 3: Advance

```bash
python3 scripts/pipeline_state.py advance
```

Print the transition summary. Loop back to step 1.

## Teardown

After phase reaches `DONE`:

```bash
python3 scripts/batch_summary.py --counts-only $(python3 scripts/state.py read-ids tmp/pipeline-all-ids.txt)
```

$ARGUMENTS
