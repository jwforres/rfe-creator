# RFE Creator

A Claude Code plugin for creating, reviewing, and submitting RFEs to the RHAIRFE Jira project.

Inspired by the [PRD/RFE workflow](https://github.com/ambient-code/workflows/tree/main/workflows/prd-rfe-workflow) in ambient, which established the pipeline pattern and multi-perspective review concept.

## Installation

Install as a Claude Code plugin from the marketplace or directly from GitHub:

```bash
claude plugin add --from https://github.com/jwforres/rfe-creator
```

### Configuration

Set your Jira credentials as environment variables (required for submit/update operations):

```
JIRA_URL=https://your-site.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

To create an API token: https://id.atlassian.com/manage-profile/security/api-tokens

The plugin includes an Atlassian MCP server configuration for read operations. Write operations use Python scripts with the Jira REST API directly for deterministic, transactional workflows.

## Skills

### RFE Pipeline

| Skill | Description |
|-------|-------------|
| `/rfe.create` | Write a new RFE from a problem statement |
| `/rfe.review [RHAIRFE-key]` | Review, improve, and auto-revise RFEs |
| `/rfe.split [RFE-NNN / RHAIRFE-key]` | Split an oversized RFE into right-sized pieces |
| `/rfe.submit` | Submit new or update existing RFEs in Jira |
| `/rfe.speedrun [idea / RHAIRFE-key]` | Full pipeline end-to-end with minimal interaction |

### Strategy Pipeline (after RFE approval)

| Skill | Description |
|-------|-------------|
| `/strat.create` | Clone approved RFEs to RHAISTRAT in Jira |
| `/strat.refine` | Add the HOW — dependencies, components, NFRs |
| `/strat.review` | Adversarial review (4 independent reviewers) |
| `/strat.prioritize` | Place in existing backlog (not yet implemented) |

### Maintenance

| Skill | Description |
|-------|-------------|
| `/rfe-creator.update-deps` | Force update vendored dependencies |

## Pipeline

### New RFEs

```
/rfe.create → /rfe.review → /rfe.submit
```

`/rfe.review` auto-revises issues it finds (up to 2 cycles). You can also edit artifacts manually between steps.

`/rfe.speedrun` runs the full pipeline with reasonable defaults and minimal interaction.

### Existing Jira RFEs

```
/rfe.review RHAIRFE-1234 → /rfe.submit
```

Or in one step: `/rfe.speedrun RHAIRFE-1234`

### Strategy (after RFE approval)

```
/strat.create → /strat.refine → /strat.review → /strat.prioritize
```

## Plugin Structure

```
rfe-creator/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── .mcp.json                # Atlassian MCP server config
├── skills/                  # Skill definitions
│   ├── rfe.create/          # Create RFEs
│   ├── rfe.review/          # Review and revise RFEs
│   ├── rfe.split/           # Split oversized RFEs
│   ├── rfe.submit/          # Submit to Jira
│   ├── rfe.speedrun/        # Full pipeline
│   ├── rfe-feasibility-review/  # Technical feasibility (forked)
│   ├── strat.create/        # Clone to RHAISTRAT
│   ├── strat.refine/        # Add technical approach
│   ├── strat.review/        # Adversarial review
│   ├── strat.prioritize/    # Backlog ordering
│   ├── feasibility-review/  # Strategy feasibility
│   ├── testability-review/  # Strategy testability
│   ├── scope-review/        # Strategy scope
│   ├── architecture-review/ # Strategy architecture
│   └── rfe-creator.update-deps/  # Update vendored deps
├── scripts/                 # Python utilities
└── CLAUDE.md                # Artifact conventions and Jira mappings
```

## assess-rfe Integration

Skills automatically bootstrap the [assess-rfe](https://github.com/n1hility/assess-rfe) plugin from GitHub on first use:

- **During creation**: The rubric is exported to `artifacts/rfe-rubric.md` and used to guide clarifying questions.
- **During review**: `/rfe.review` invokes assess-rfe for rubric scoring.
- **Without network access**: The skills still work — creation uses built-in questions, review runs only the technical feasibility check.

Run `/rfe-creator.update-deps` to force-refresh to the latest version.

## Architecture Context

For RHOAI work, the technical feasibility and strategy reviews use architecture context from [opendatahub-io/architecture-context](https://github.com/opendatahub-io/architecture-context). This is fetched automatically via sparse checkout on first use.
