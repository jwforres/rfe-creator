---
name: rfe.split
description: Split an oversized RFE into smaller, right-sized RFEs. Accepts a local artifact (e.g., /rfe.split RFE-001) or Jira key (e.g., /rfe.split RHAIRFE-1234). Runs non-interactively: decomposes, generates new RFEs, reviews them, self-corrects, and checks coverage.
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill, mcp__atlassian__getJiraIssue
---

You are an RFE splitting assistant. Your job is to decompose an oversized RFE into smaller, right-sized RFEs — each representing a coherent, independent business need. This skill runs non-interactively: do not ask the user questions or wait for confirmation. Make decisions autonomously using the decomposition rules below, and present the final results when complete.

## Step 1: Load the Source RFE

Check if `$ARGUMENTS` contains a Jira key (e.g., `RHAIRFE-1234`) or a local artifact reference (e.g., `RFE-001`).

**If a Jira key**: First check if `artifacts/rfe-tasks/<jira_key>.md` already exists locally. If it does, use the local copy — do not re-fetch from Jira. This preserves any local edits from prior review or split cycles.

**If the local file does not exist**, fetch the RFE from Jira. Try `mcp__atlassian__getJiraIssue` first. If the MCP tool is unavailable, fall back to the REST API script:

```bash
python3 scripts/fetch_issue.py RHAIRFE-1234 --fields summary,description,priority,labels,status --markdown
```

The script outputs JSON to stdout with the description already converted to markdown. Parse `fields.description`, `fields.summary`, and `fields.priority.name`.

Write the Jira description to `artifacts/rfe-tasks/<jira_key>.md` as-is — preserve the original markdown structure, headings, and content exactly as fetched. Do not restructure, reformat, or fit it into any template. Only add YAML frontmatter (via `scripts/frontmatter.py set`). Do not add a title heading — the title lives in frontmatter only.

First, read the schema to know exact field names and allowed values:

```bash
python3 scripts/frontmatter.py schema rfe-task
```

Then set frontmatter, using the Jira key as the `rfe_id`:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-tasks/<jira_key>.md \
    rfe_id=<jira_key> \
    title="<title>" \
    priority=<priority> \
    size=<size> \
    status=Ready
```

**Save an original snapshot** of the raw Jira description to `artifacts/rfe-originals/<jira_key>.md`. Write the `fields.description` value as-is (the raw markdown from Jira, not the templated version). This snapshot is used for (1) before/after data analysis of what remediation changed, and (2) optimistic conflict detection at submit time — the submit skill re-fetches the description from Jira and compares it against this file to detect concurrent modifications. Create the `artifacts/rfe-originals/` directory if it doesn't exist. This file is never modified by split or revision — it is only overwritten by a fresh Jira fetch.

**If a local artifact reference**: Find and read the matching file in `artifacts/rfe-tasks/`.

**If no argument provided**: Fail with: "Usage: `/rfe.split <RFE-NNN or RHAIRFE-1234>`. Provide a local artifact reference or a Jira key." Do not proceed.

Also check for a prior review in `artifacts/rfe-reviews/` for this RFE — the right-sizing feedback explains why this RFE needs splitting.

**Before proceeding, check the Right-sized score.** If the score is **1/2** ("slightly broad at 1-2 strategy features"), splitting may not be appropriate. An RFE that maps to 2 tightly-coupled strategy features is acceptable — the decomposition into strategy features happens at the RHAISTRAT level, not the RHAIRFE level. Only proceed with splitting if:
- The Right-sized score is **0/2** (clearly needs 3+ features), OR
- The score is 1/2 AND the capabilities serve genuinely different customer segments or user scenarios that could be independently prioritized without harm

If the 1/2 score reflects delivery-coupled capabilities (see Step 2b), recommend keeping the RFE intact and stop. Tell the user: "This RFE scores 1/2 on Right-sized but the capabilities are delivery-coupled — splitting risks independent release of changes that must ship together. The RFE is acceptable as-is; strategy-level decomposition can happen in RHAISTRAT."

## Step 1.5: Load Right-sizing Rubric

Bootstrap the assess-rfe skill if not already present:

```bash
bash scripts/bootstrap-assess-rfe.sh
```

Read the scoring rubric from `.context/assess-rfe/scripts/agent_prompt.md`. Find the **Right-sized** criterion and its calibration examples. This defines what "right-sized" means for the decomposition — use it to guide your split proposals and to verify each child RFE would score 2/2.

The rubric's smell test for Right-sized is the key tool: apply it to each proposed child RFE. If a child RFE wouldn't pass the smell test, it needs further splitting or regrouping.

If the bootstrap fails, proceed with a basic right-sizing heuristic: each child RFE should map to a single strategy feature — you should be able to write one strategy-feature summary sentence for it.

## Step 2: Analyze and Propose Split Options

### Step 2a: Triage Already-Delivered Capabilities

Before decomposing, check for capabilities that are already delivered or in progress. Sources:
- The review file (`artifacts/rfe-reviews/{id}-review.md`) may flag delivered items
- Stakeholder comments (`artifacts/rfe-tasks/{id}-comments.md`) often reveal what has shipped
- Related strategy tickets mentioned in the RFE

For each acceptance criterion and scope item, mark it as:
- **Delivered**: Already shipped (cite the evidence — strategy ticket, comment, etc.)
- **In progress**: Actively being worked under an existing strategy
- **Gap**: Not yet addressed — candidate for a child RFE

**Only gaps become candidates for child RFEs.** Delivered items should be acknowledged as background context in each child's problem statement. Do NOT re-request delivered capabilities as requirements in child RFEs.

Present the triage table to the user before proceeding to decomposition.

### Step 2b: Bottom-up Capability Inventory

Starting from the **gaps only** (not delivered items), decompose into atomic capabilities. Do NOT start from the original RFE's thematic groupings — those groupings are often why the RFE is oversized in the first place.

For each gap capability, ask:
1. **Could this ship independently and deliver value to a specific customer?** If yes, it's a candidate for its own RFE.
2. **Does this require another capability to function at all?** If yes, they must stay together.
3. **Does this serve a different customer segment or compliance requirement than adjacent capabilities?** If yes, it should be its own RFE even if it's thematically similar.
4. **Would shipping one without the other create a broken customer experience?** If yes, they are **delivery-coupled** and must stay in the same RFE even if they are technically independent. Common delivery-coupled pairs:
   - A breaking change and its migration path — shipping a new model without migration guidance strands existing customers
   - A capability and its prerequisite enablement — e.g., a new API and the auth model it requires
   - A deprecation and its replacement — removing the old without providing the new is a regression

List every atomic capability with a one-sentence strategy-feature summary. Mark any delivery-coupling relationships between capabilities.

**Common mistakes to avoid:**
- Grouping capabilities by theme when each capability within the theme serves different customer segments, has different technical maturity, and can ship independently. Theme-based groupings produce children that are still bundles of multiple strategy features.
- Splitting delivery-coupled capabilities into separate RFEs because they are "technically independent." Migration paths, upgrade tooling, and API stability documentation are part of the same business need as the change they support — not separate needs.

### Step 2c: Propose Groupings

Starting from the atomic capability list, group capabilities that are truly inseparable — they share a code path AND cannot deliver value independently, OR they are delivery-coupled (shipping one without the other creates a broken customer experience). Everything else stays separate.

Then propose 2-3 decomposition strategies, each with:
- How many RFEs it would produce
- What each RFE would cover
- A one-sentence strategy-feature summary for each child (applying the rubric's Right-sized smell test)
- Brief rationale for why this decomposition makes sense

**Self-check before presenting:** For each proposed child RFE, try to write ONE strategy-feature summary sentence. If you need "and" to describe what it does, it might be two features — but apply nuance:
- **"and" connecting different user scenarios** is a red flag — these are likely two features. Check whether each side could ship independently and deliver value on its own. If yes, split.
- **"and" within the same user scenario** is an amber signal — these may serve the same user need even if architecturally distinct. Consider whether they truly must ship together or just happen to be thematically related.

**Cross-check against atomic inventory:** After writing the group summary, verify that *every* atomic capability placed in that group is accurately described by the group's summary. Go back to the one-sentence strategy-feature summary from Step 2b for each atomic capability in the group. If an atomic capability's summary is not a subset of the group summary — i.e., the group summary does not capture what that capability does — it has been incorrectly grouped and should be its own RFE or placed in a different group. This catches cases where a capability is absorbed into a thematically adjacent group despite serving a different user scenario.

The right number of child RFEs is however many independently-valuable capabilities exist, not an arbitrary minimum.

### Step 2d: Pre-screen Options

Before presenting options to the user, score each proposed child RFE's right-sizing:

For each child in each option, apply the smell test: "Can you write one strategy-feature summary sentence for this?" Score as:
- **2/2**: Single focused need, one clear strategy summary
- **1/2**: Slightly broad, summary needs "and" but capabilities are defensibly related
- **0/2**: Clearly needs 3+ features

Present a comparison table:

```
| Option | # RFEs | Right-sized scores | Notes |
|--------|--------|--------------------|-------|
| A      | 3      | 2, 2, 2            | All children focused |
| B      | 2      | 1, 2               | Child 1 still slightly broad |
| C      | 4      | 2, 2, 2, 1         | Child 4 bundles two concerns |
```

**Recommend the option with the most 2/2 scores.** If tied, prefer fewer RFEs (less Jira overhead). If an option has any child scoring 0/2, discard it — it hasn't solved the parent's problem.

When evaluating whether capabilities belong together, consider:
- Do they share the same code path / team / delivery timeline? (Favors grouping)
- Are they independently valuable to different customer segments? (Favors splitting)
- Are they inseparable? (Must stay together)
- Are they delivery-coupled? Would shipping one without the other harm customers? (Must stay together)

Common decomposition axes:
- **By capability area** — e.g., monitoring vs alerting vs reporting
- **By user persona** — e.g., admin needs vs end user needs
- **By delivery phase** — e.g., core need that unblocks value vs enhancements
- **By scope boundary** — e.g., platform capability vs integration with external systems

Present the comparison table with the recommended option, then proceed immediately with the recommended decomposition. Do not pause for user confirmation — the self-correction loop in Step 4.5 will catch grouping mistakes.

## Step 3: Generate New RFEs

Using the recommended decomposition:

1. Generate new RFE artifacts using the template in `${CLAUDE_SKILL_DIR}/../rfe.create/rfe-template.md`
2. Each new RFE must be a **coherent, standalone business need** — not just a slice of acceptance criteria. It needs its own problem statement, justification, and success criteria.
3. Carry forward from the original:
   - Business justification (tailor to each child's specific scope)
   - Affected customers and segments
   - Priority (inherit from parent by default; differentiate only if clearly warranted and note the reasoning)
   - If the original came from Jira, note the source key (e.g., `**Split from**: RHAIRFE-1234`)
4. Number new RFEs sequentially after the highest existing RFE number in `artifacts/rfe-tasks/`
5. Write each to `artifacts/rfe-tasks/RFE-NNN-<slug>.md`
6. Set frontmatter on each child with `parent_key` pointing to the original's `rfe_id`:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-tasks/<child_filename>.md \
    rfe_id=<child_rfe_id> \
    title="<child_title>" \
    priority=<priority> \
    size=<size> \
    status=Draft \
    parent_key=<parent_rfe_id>
```

7. Archive the original by updating its frontmatter status:

```bash
python3 scripts/frontmatter.py set artifacts/rfe-tasks/<original_filename>.md \
    status=Archived
```

8. Rebuild the index:

```bash
python3 scripts/frontmatter.py rebuild-index
```

## Step 4: Review New RFEs

Run `/rfe.review` on the new artifacts. This runs rubric scoring, technical feasibility, and auto-revision.

**Important:** `/rfe.review`'s revision principles state that right-sizing is "never auto-applied" — that applies to the review skill acting alone. When running inside `/rfe.split`, Step 4.5 below overrides that principle: this skill IS the right-sizing correction mechanism, and it MUST attempt to fix Right-sized scores below 2/2.

## Step 4.5: Right-sizing Self-Correction (up to 3 cycles)

**This step is mandatory, not advisory.** After `/rfe.review` completes, check whether any child RFE scored below 2/2 on Right-sized (read from `artifacts/rfe-reviews/{id}-review.md` frontmatter: `scores.right_sized`). If so, run up to 3 correction cycles. Do not defer to the user or skip this step — the `/rfe.review` principle "right-sizing is a recommendation, never auto-applied" does not apply here because `/rfe.split` is explicitly authorized to re-decompose children.

### Each cycle:

1. **Diagnose**: For each child scoring below 2/2, read the assessor's Right-sized feedback from the review file. Identify the specific grouping mistake:
   - **Theme-based grouping**: Capabilities grouped by topic but independently deliverable with different teams, upstream dependencies, or delivery timelines
   - **Mixed delivery paths**: One child spans both internal work and upstream changes in different projects
   - **Multiple user scenarios**: The strategy-feature summary requires "and" connecting different user scenarios
   - **Different customer segments**: Capabilities serve different personas or compliance requirements

2. **Re-decompose**: Return to the atomic capability inventory from Step 2b. For each offending child, re-apply the three decomposition questions:
   - Could each grouped capability ship independently and deliver value?
   - Does one require the other to function at all?
   - Do they serve different customer segments or have different technical maturity?

   Generate new child RFEs for the re-split capabilities. Archive the replaced child (set `status=Archived` in frontmatter). Rebuild the index.

3. **Re-review**: Run `/rfe.review` on the new/changed artifacts only.

4. **Evaluate**: If all children now score 2/2 on Right-sized, exit the loop and proceed to Step 5. Otherwise, continue to the next cycle.

**After 3 cycles**, stop and present the remaining right-sizing concerns to the user. Some RFEs may legitimately score 1/2 — present the assessor's judgment rather than overriding it indefinitely.

**Do not re-split for non-Right-sized criteria.** This loop corrects grouping mistakes caught by the Right-sized score. Other criteria (WHY, WHAT, HOW, Not a task) are handled by `/rfe.review`'s auto-revision.

## Step 5: Coverage Check

After the review completes, compare the **combined scope** of all new RFEs against the original:

1. List every acceptance criterion, capability, and scope item from the original RFE
2. For each item, identify which new RFE covers it
3. Flag any items from the original that are not covered by any new RFE

Present the coverage matrix to the user:

```
## Coverage Check

| Original Scope Item | Covered By |
|---------------------|------------|
| Users can view drift metrics | RFE-003 |
| Alerts fire on threshold breach | RFE-004 |
| Integration with external monitoring | NOT COVERED |
```

**If gaps exist**, resolve each uncovered capability automatically:

1. Apply the decomposition rules from Step 2b to the uncovered capability — could it ship independently? Does it require another capability? Does it serve a different customer segment?
2. Check each existing child RFE: would adding this capability break its right-sizing (i.e., would the strategy-feature summary now need "and" connecting different user scenarios)?
3. If the capability fits naturally in an existing child without breaking right-sizing, add it there.
4. If it doesn't fit in any existing child, create a new child RFE for it.
5. Flag all coverage gap decisions in the summary.

If any changes were made (scope added to existing children or new children created), re-run `/rfe.review` on the affected RFEs. If right-sizing failures result, feed back into the Step 4.5 self-correction loop.

## Step 6: Summary

Present the final state:

```
## Split Complete

Original: RHAIRFE-1234 (archived)
New RFEs:
- RFE-003: <title> (Priority: Normal) — PASS
- RFE-004: <title> (Priority: Normal) — PASS

Coverage: All original scope items covered
Review: All new RFEs passed
```

Tell the user they can:
- Run `/rfe.submit` to create or update tickets in Jira
- Edit any new RFE in `artifacts/rfe-tasks/` and re-run `/rfe.review`

$ARGUMENTS
