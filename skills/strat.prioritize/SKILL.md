---
name: strat.prioritize
description: "[NOT YET IMPLEMENTED] Prioritize new strategies against the existing RHAISTRAT backlog in Jira."
user-invocable: true
allowed-tools: Read
---

This skill is **not yet implemented**. It will not perform any actions.

When invoked, inform the user:

> `/strat.prioritize` is not yet implemented. This skill needs design work before it can be built — specifically, how to filter hundreds of existing STRATs to a meaningful comparison set, and how backlog ordering is represented in Jira (board position, rank field, or other mechanism).
>
> For now, use the strategy review report in `artifacts/strat-review-report.md` and your team's existing backlog grooming process to prioritize new strategies manually.

---

## Design Intent (for future implementation)

### Goal
Help the PM place new strategies into the existing RHAISTRAT backlog ordering. The backlog has hundreds of items — the skill needs to filter to a relevant comparison set rather than dumping everything into context.

### Planned Approach

1. **Read new strategies** from `artifacts/strat-tasks/` and review results from `artifacts/strat-review-report.md`
2. **Ask for scope** — PM specifies product area or the skill infers from components/labels
3. **Pull comparison set from Jira** — query RHAISTRAT with JQL, filter to 10-30 comparable items by product area, dependencies, or team capacity
4. **Present both lists** — existing backlog (filtered) + new strategies side by side, with key, summary, priority, status, labels
5. **Collaborative ordering** — suggest placement with reasoning (priority, dependencies, business urgency, review feedback), PM makes final call
6. **Update Jira** — update rank/priority/labels on RHAISTRAT tickets
7. **Document decisions** — write `artifacts/strat-prioritization.md` with ordering rationale

### Open Questions

- What fields/labels/components reliably narrow hundreds of STRATs to a comparable set of 10-30?
- How is backlog ordering represented in Jira — board position, custom rank field, or something else?
- Can the Jira MCP update rank/ordering, or is that a board-only operation?
- What does the non-Jira fallback look like — a recommendation document for manual grooming?

$ARGUMENTS
