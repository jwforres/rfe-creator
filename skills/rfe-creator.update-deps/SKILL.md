---
name: rfe-creator.update-deps
description: Force update all vendored dependencies — assess-rfe skills and architecture context. Use when you want the latest versions.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Glob
---

Force update all vendored dependencies by removing cached copies and re-fetching.

## Steps

### 1. Update assess-rfe

```bash
rm -rf .context/assess-rfe .claude/skills/assess-rfe .claude/skills/export-rubric
bash scripts/bootstrap-assess-rfe.sh
```

### 2. Update architecture context

```bash
rm -rf .context/architecture-context
bash scripts/fetch-architecture-context.sh
```

### 3. Report

List what was updated and the versions fetched.

$ARGUMENTS
