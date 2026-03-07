---
name: hero-new-skill
# prettier-ignore
description: Create Claude Code skills, subagents, rules, or hooks. Guides through creating well-structured, reusable components that extend Claude's capabilities. Use for "create a skill", "add guidelines", "slash command", or teaching Claude new behaviors.
argument-hint: <description of what you want Claude to do>
---

# Hero New Skill - Create Claude Code Components

Create skills and other components that extend Claude's capabilities.

## Core Principles

### Context is Precious

The context window is shared by system prompt, conversation, all skills' metadata, and user requests. Only add what Claude cannot know: company-specific schemas, proprietary workflows, domain knowledge, tool integrations.

### Match Freedom to Fragility

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| **High** (prose) | Multiple valid approaches | "Review code for security issues" |
| **Medium** (pseudocode) | Preferred pattern, some variation OK | "Run pre-commit, then commit" |
| **Low** (exact scripts) | Fragile ops, consistency critical | "Execute this exact migration" |

## Skill Anatomy

```
skill-name/
├── SKILL.md              # Required: frontmatter + instructions
├── scripts/              # Deterministic, reusable code
├── references/           # Domain docs loaded on-demand
└── assets/               # Output templates
```

### Frontmatter (Required)

```yaml
---
name: kebab-case-name
# prettier-ignore
description: What it does AND when to trigger.
argument-hint: [args]                    # Optional
disable-model-invocation: true           # Optional: manual-only
supplementary-files:                     # Optional: on-demand
  - references/schema.md
---
```

### Body Guidelines

- **Target**: Under 500 lines, under 5k words
- **Include**: Procedures Claude cannot infer, decision trees, tool integrations
- **Exclude**: Explanations Claude already knows

## Component Types

| Type | Location | Use When |
|------|----------|----------|
| **Skill** | `.claude/skills/[name]/SKILL.md` | Workflows, guidelines |
| **Subagent** | `.claude/agents/[name].md` | Isolated execution |
| **Rule** | `.claude/rules/[name].md` | Always-on constraints |
| **Hook** | `settings.json` | Event-triggered automation |

**User-level skills** go in `~/.claude/skills/` for cross-project availability.

## Creation Process

1. **Understand**: Ask for trigger conditions, example requests, success criteria
2. **Plan**: Identify scripts/, references/, assets/ needs
3. **Create**: `mkdir -p .claude/skills/<name>` and write SKILL.md
4. **Validate**: Description has triggers, body under 500 lines, references exist
5. **Iterate**: Use the skill, notice struggles, update

## Anti-patterns

| Don't | Do Instead |
|-------|------------|
| "When to Use" section in body | Put triggers in frontmatter description |
| 1000-line SKILL.md | Split into references |
| Duplicate info across files | Single source of truth |
| Scripts without error handling | Fail loudly, early |

---

## Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. Use it to understand the project's tech stack and conventions when creating skills that reference project-specific tools, commands, or patterns.

---

Now analyze `$ARGUMENTS` and create the appropriate component.
