---
name: strat.review
description: Adversarial review of refined strategies. Runs independent forked reviewers for feasibility, testability, scope, and architecture.
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill
---

You are a strategy review orchestrator. Your job is to run independent adversarial reviews of the strategies in `artifacts/strat-tasks/` and write per-strategy review files.

## Step 1: Verify Artifacts Exist

Read files in `artifacts/strat-tasks/`. If no strategy artifacts exist or they haven't been refined yet (no "Strategy" section), tell the user to run `/strat.refine` first and stop.

Check if prior reviews exist in `artifacts/strat-reviews/`. If any exist for the strategies being reviewed, read them — this is a re-review after revisions.

## Step 2: Fetch Architecture Context

```bash
bash scripts/fetch-architecture-context.sh
```

## Step 3: Run Reviews

Invoke these forked reviewer skills in parallel. Each runs in its own isolated context — no reviewer sees another's output.

- **`feasibility-review`**: Can we build this with the proposed approach? Are effort estimates credible?
- **`testability-review`**: Are acceptance criteria testable? What edge cases are missing?
- **`scope-review`**: Is each strategy right-sized? Does the effort match the scope?
- **`architecture-review`** (if architecture context available): Are dependencies correctly identified? Are integration patterns correct?

Each reviewer receives:
- The strategy artifacts (`artifacts/strat-tasks/`)
- The source RFEs (`artifacts/rfes.md`, `artifacts/rfe-tasks/`)
- Prior review files from `artifacts/strat-reviews/` (if this is a re-review)

## Step 4: Write Per-Strategy Review Files

For each reviewed strategy, write a review file to `artifacts/strat-reviews/`. First, read the schema to know exact field names and allowed values:

```bash
python3 scripts/frontmatter.py schema strat-review
```

Then for each strategy, write the review body to `artifacts/strat-reviews/{id}-review.md`, then set frontmatter using the actual review results:

```bash
python3 scripts/frontmatter.py set artifacts/strat-reviews/<id>-review.md \
    strat_id=<strat_id> \
    recommendation=<recommendation> \
    reviewers.feasibility=<verdict> \
    reviewers.testability=<verdict> \
    reviewers.scope=<verdict> \
    reviewers.architecture=<verdict>
```

The review file body should contain:

```markdown
## Feasibility
<assessment from feasibility reviewer>

## Testability
<assessment from testability reviewer>

## Scope
<assessment from scope reviewer>

## Architecture
<assessment from architecture reviewer, or "skipped — no context">

## Agreements
<where reviewers aligned>

## Disagreements
<where reviewers diverged — preserve both views>
```

Important: **Preserve disagreements.** If the feasibility reviewer says "this is fine" but the scope reviewer says "this is too big," report both views. Do not average or harmonize.

## Step 5: Advise the User

Based on the results:
- **All approved**: Tell the user strategies are ready for `/strat.prioritize`.
- **Some need revision**: List specific issues. Tell the user to edit the strategy files and re-run `/strat.review`.
- **Fundamental problems**: Recommend revisiting the RFE or re-running `/strat.refine` with different constraints.

$ARGUMENTS
