---
inclusion: always
---

# Spec Naming Convention

All specs must follow a strict naming pattern to ensure traceability and version control.

## Directory Name Format

```
{year}.{sequential}.[{version}]-{short-description}
```

### Components

| Component | Format | Example |
|---|---|---|
| `year` | Current 4-digit year | `2026` |
| `sequential` | 6-digit zero-padded number | `000001` |
| `version` | Semantic version with SNAPSHOT suffix | `1.0.0-SNAPSHOT` |
| `short-description` | Kebab-case summary of the spec goal | `user-authentication` |

### Full Example

```
.kiro/specs/2026.000001.[1.0.0-SNAPSHOT]-user-authentication/
```

## Version Control Rules

- All specs start at `1.0.0-SNAPSHOT`
- **New feature** → increment minor version: `1.0.0-SNAPSHOT` → `1.1.0-SNAPSHOT`
- **Bugfix** → increment patch version: `1.0.0-SNAPSHOT` → `1.0.1-SNAPSHOT`
- Version always keeps the `-SNAPSHOT` suffix during development

## Sequential Number Rules

- Always check existing specs under `.kiro/specs/{year}/` to determine the next sequential number
- If no specs exist for the current year, start at `000001`
- Increment by 1 for each new spec regardless of type (feature or bugfix)
- Sequential numbers are scoped per year (reset to `000001` each new year)

## Required Files

Each spec directory must contain:
- `requirements.md`
- `design.md`
- `tasks.md`
