# Strategy Template

Scale the output to match the strategy size. Use the appropriate section set below.

## Size Guide

- **S** (Small): Single component, single team, well-understood change. Use Concise format.
- **M** (Medium): 1-2 components, may involve coordination. Use Standard format.
- **L** (Large): Multiple components, cross-team coordination required. Use Full format.
- **XL** (Extra Large): Platform-wide impact, multiple teams, significant new infrastructure. Use Full format with all optional sections.

---

## Concise Format (S)

```markdown
## Strategy

**Effort**: S
**Components**: <list>

### Technical Approach
<2-3 paragraphs: what changes, where, and why this approach>

### Dependencies
<List or "None">

### Non-Functional Requirements
<List key NFRs>

### Risks
<List or "None identified">
```

---

## Standard Format (M)

```markdown
## Strategy

**Effort**: M
**Components**: <list>
**Impacted Teams**: <list>

### Technical Approach
<What changes, where, why this approach. Include component interactions.>

### Affected Components
<For each component: what changes and why>

### Dependencies
- <dependency>: <why it's needed, what's blocked without it>

### Non-Functional Requirements
- **Performance**: <requirements>
- **Security**: <requirements>
- **Backwards Compatibility**: <requirements>

### Risks
- <risk>: <impact and mitigation>

### Open Questions
- <question>
```

---

## Full Format (L/XL)

```markdown
## Strategy

**Effort**: <L|XL>
**Components**: <list>
**Impacted Teams**: <list>

### Technical Approach
<Detailed approach: what changes across which components, how they interact, why this approach over alternatives>

### Affected Components
| Component | Change | Owner Team |
|-----------|--------|------------|
| <name>    | <what changes> | <team> |

### Dependencies
| Dependency | Type | Status | Impact if Missing |
|------------|------|--------|-------------------|
| <name>     | <internal/external> | <exists/needed/unknown> | <what's blocked> |

### Non-Functional Requirements
- **Performance**: <requirements, benchmarks>
- **Scalability**: <requirements>
- **Security**: <requirements, threat considerations>
- **Availability**: <requirements, failure modes>
- **Backwards Compatibility**: <migration path, deprecation timeline>

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <risk> | <H/M/L> | <description> | <mitigation> |

### Open Questions
- <question>: <why it matters, who can answer>

### Scope Boundary
**Delivers**: <what the RFE asks for>
**Does NOT deliver**: <what's explicitly excluded>
**Assumptions**: <what we're assuming to be true>
```
