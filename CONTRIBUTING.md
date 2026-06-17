# Contributing a Skill

Each skill lives in its own directory and **must** contain a `SKILL.md` file.
This file serves as both the skill's entry point and its metadata header.

---

## Required Format

Every `SKILL.md` **must** start with YAML-style frontmatter delimited by `---`:

```yaml
---
name: my-skill
description: Use this when doing a specific workflow.
---

# My Skill

Instructions for the agent here.
```

### Mandatory Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | **Yes** | Lowercase letters, digits, and hyphens (e.g. `api-review`). Should match the parent directory name. |
| `description` | **Yes** | What the skill does and when the agent should invoke it. Must be non-empty. |

A skill **without** `name` or `description`, or with an **empty** `description`, will **not** be loaded correctly.

---

## Naming Conventions

- **`name`** must use only lowercase letters (`a-z`), digits (`0-9`), and hyphens (`-`).
  - ✅ `api-review` `web-search` `db-migration-check`
  - ❌ `API_Review` `web search` `db.migration`
- Invalid names will still load, but a warning will be emitted. Fix them anyway.
- Directory names should match the skill name.

---

## Description

`description` tells the agent **what** the skill does and **when** to use it. It can be:

**Single line:**

```yaml
---
name: migration-review
description: Use this when reviewing database migrations.
---
```

**Multi-line** (use `|` for a literal block scalar):

```yaml
---
name: api-review
description: |
  Use when reviewing API changes.
  Checks compatibility, error contracts, and docs.
---
```

Put trigger criteria in `description`, not in the body. The body is loaded only after the
skill has already been selected, so it should focus on execution instructions.

---

## Skill Body

Write the body as a compact operator guide for an agent that is already using the skill.
Prefer sections like:

- `Run`: the exact command or workflow to execute
- `Parameters`: accepted inputs, defaults, and constraints
- `Dependencies`: required environment variables and packages
- `Handling Results`: how to interpret output, errors, truncation, or next steps

Avoid a `When to Use` section in the body unless it helps choose between sub-workflows inside
the same skill. Skill-to-skill pairing notes should stay loose and capability-based, not hard
dependencies on another skill.

---

## Directory Structure

- A directory containing `SKILL.md` is treated as a **skill root**. Subdirectories beneath it will **not** be scanned for additional skills.
- Keep auxiliary files (scripts, references, assets) **inside** the skill directory and reference them with **relative paths**:

```
my-skill/
├── SKILL.md
├── scripts/
│   └── run.ts
└── references/
    └── api.md
```

In `SKILL.md`:

```markdown
Use relative paths from this skill directory:
- `scripts/run.ts`
- `references/api.md`
```

---

## Duplicate Names

If two skills share the same `name`, only the **first one discovered** is kept. Avoid duplicates.

---

## Quick Checklist

Before committing a new skill, verify:

- [ ] `SKILL.md` exists at the skill root
- [ ] Frontmatter is valid YAML between `---` delimiters
- [ ] `name` is present and uses `kebab-case`
- [ ] `description` is present and non-empty
- [ ] No other skill shares the same name
- [ ] Internal paths in the skill body are relative to the skill directory

---

## Examples

### ✅ Correct

```yaml
---
name: web-search
description: |
  Use this when you need to search the web for real-time information,
  recent news, documentation, or any topic requiring up-to-date results.
  Powered by Tavily Search API.
---

# Web Search

...
```

```yaml
---
name: migration-review
description: Use this when reviewing database migrations.
---

# Migration Review

Check schema changes, rollback safety, and data migration risks.
```

### ❌ Incorrect (will not load)

```yaml
# Missing description entirely
---
name: my-skill
---

# My Skill
```

```yaml
# Empty description
---
name: my-skill
description:
---

# My Skill
```

```yaml
# No frontmatter at all
# My Skill

Some instructions...
```
