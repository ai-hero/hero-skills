---
name: create-skill
# prettier-ignore
description: Create a new Claude Code skill, subagent, rule, or hook. Guides through trigger conditions, success criteria, and writes a well-structured SKILL.md. Use when extending Claude with a new slash command.
argument-hint: DESCRIPTION_OF_WHAT_YOU_WANT_CLAUDE_TO_DO
---

# Create Skill — Create Claude Code Components

Create skills and other components that extend Claude's capabilities.

## Arguments

- `$ARGUMENTS` — Description of what you want the skill to do

## Core Principles

**Context is Precious** — Only add what Claude cannot infer: company-specific schemas, proprietary workflows, domain knowledge, tool integrations.

**Match Freedom to Fragility:**

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| High (prose) | Multiple valid approaches | "Review code for security issues" |
| Medium (pseudocode) | Preferred pattern, some variation OK | "Run pre-commit, then commit" |
| Low (exact scripts) | Fragile ops, consistency critical | "Execute this exact migration" |

## Component Types

| Type | Location | Use When |
|------|----------|----------|
| **Skill** | `.claude/skills/[name]/SKILL.md` | Workflows, guidelines |
| **Subagent** | `.claude/agents/[name].md` | Isolated execution |
| **Rule** | `.claude/rules/[name].md` | Always-on constraints |
| **Hook** | `settings.json` | Event-triggered automation |

User-level skills go in `~/.claude/skills/` for cross-project availability.

## Frontmatter

```yaml
---
name: verb-object
# prettier-ignore
description: What it does AND when to trigger it. (50-200 chars)
argument-hint: [args]
disable-model-invocation: true
---
```

## Body Guidelines

- **Target**: Under 500 lines, under 5k words
- **Include**: Procedures Claude cannot infer, decision trees, tool integrations
- **Exclude**: Explanations Claude already knows

## Anti-patterns

| Don't | Do Instead |
|-------|------------|
| "When to Use" section in body | Put triggers in frontmatter description |
| 1000-line SKILL.md | Split into supplementary reference files |
| Duplicate info across files | Single source of truth |
| Lowercase angle bracket placeholders | Use UPPER_CASE (e.g., PROJECT_NAME) |

## Instructions

### Step 0: Load Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Use `HERO.md` to understand the project's stack and conventions when creating skills that reference project-specific tools.

### Step 1: Understand the Goal

Ask for:

1. What should this do? (use a verb-object name — e.g., `deploy-service`, `notify-slack`)
2. When should it trigger? (what signals or user requests)
3. What does success look like?

### Step 2: Plan the Component

Identify what files are needed:

```
skill-name/
├── SKILL.md              # Required: frontmatter + instructions
├── scripts/              # Deterministic, reusable code
├── references/           # Domain docs loaded on-demand
└── assets/               # Output templates
```

### Step 3: Create the Files

```bash
mkdir -p .claude/skills/SKILL_NAME
```

Write `SKILL.md` with frontmatter and instructions.

### Step 4: Validate

- Name follows verb-object pattern (e.g., `deploy-service`)
- Description has trigger context (50-200 chars)
- Body is under 500 lines
- No lowercase angle bracket placeholders
- Referenced files in `supplementary-files` exist

### Step 5: Summary

```
Create Skill Summary
====================
Component: skill | subagent | rule | hook
Name: SKILL_NAME
Location: PATH

Created:
  - SKILL.md (N lines)

Test: Invoke with hero-skills:SKILL_NAME in a new conversation
```
