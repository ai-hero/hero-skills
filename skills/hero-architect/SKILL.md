---
name: hero-architect
# prettier-ignore
description: Create and update architecture specs in a project's specs/ folder. Generates Mermaid diagrams documenting system design, data flow, and component relationships. Works with any project structure.
argument-hint: <create|update|review|init> [spec-name]
disable-model-invocation: true
---

# Hero Architect - Architecture Specification Management

Create and maintain architecture documentation in the project's `specs/` folder using Mermaid diagrams and structured markdown.

## Arguments

- `$ARGUMENTS` - Command and optional spec name:
  - `create [spec-name]` - Create a new architecture spec
  - `update [spec-name]` - Update an existing spec
  - `review` - Review all specs and suggest updates based on current codebase
  - `init` - Initialize the specs/ folder with standard templates

## Important Constraint

**This skill only operates on specification documents in `specs/`.** It does NOT modify actual source code.

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → type (single vs monorepo) to know project layout
- **Projects** → list of subprojects, languages, frameworks for architecture context
- **Deployment** → platform and registry for deployment architecture diagrams

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

### Step 1: Identify Current Project

- Look for `pyproject.toml`, `package.json`, `backend/`, `frontend/` directories
- If in monorepo root, ask which project to document

### Step 2: Initialize or Verify specs/ Folder

```
<project>/
└── specs/
    ├── README.md           # Index of all specs
    ├── overview.md         # High-level system overview
    ├── components.md       # Component architecture
    ├── data-flow.md        # Data flow diagrams
    ├── api.md              # API specifications (if applicable)
    └── decisions/          # Architecture Decision Records (ADRs)
        └── 001-*.md
```

### Step 3: Execute Command

#### `init` - Create `specs/` folder with starter templates

#### `create [spec-name]`

1. Gather context by reading relevant source files
2. Ask clarifying questions (aspect, detail level, patterns)
3. Generate the spec using appropriate Mermaid diagrams
4. Write to `specs/[spec-name].md`
5. Update `specs/README.md`

#### `update [spec-name]`

1. Read existing spec
2. Analyze current codebase for changes
3. Update preserving structure, note changes with date

#### `review`

1. List all specs, compare against codebase
2. Report: up-to-date, needs update, missing specs
3. Do NOT auto-update - just report

## Mermaid Diagram Types

- **graph/flowchart**: System components, logic flow
- **sequenceDiagram**: Interactions over time
- **classDiagram**: Data models, relationships
- **stateDiagram-v2**: State machines, transitions
- **erDiagram**: Database schema

## Spec Document Template

```markdown
# [Spec Title]

> Last updated: [Date]
> Status: [Draft | Review | Approved]

## Overview
[1-2 paragraph description]

## Diagram
```mermaid
[appropriate diagram]
```

## Components

### [Component Name]

- **Purpose**: [What it does]
- **Location**: `path/to/code`
- **Dependencies**: [What it depends on]

## Key Decisions

- **[Decision]**: [Rationale]

```

## Markdown Linting

- Use `1.` for all ordered list items
- Wrap generic types in backticks (e.g., `Map<K, V>`)
- Add blank lines before/after code blocks, lists, headings

## Notes

- Always read relevant source code before creating/updating specs
- Keep diagrams focused - one concept per diagram
- Specs describe what IS, not what should be
