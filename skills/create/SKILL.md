---
name: create
# prettier-ignore
description: Scaffold a new project or skill. Use `create project` to initialize a Python, full-stack, or Node.js project. Use `create skill` to build a new Claude Code slash command, rule, or hook.
argument-hint: "project|skill [description]"
disable-model-invocation: true
---

# Create — Scaffold Projects and Skills

Scaffold new things. Routes on the first argument.

## Arguments

- `$ARGUMENTS` — Required mode plus optional description:
  - `project [name] [description]` — Scaffold a new project (standalone or monorepo subproject)
  - `skill [description]` — Create a new Claude Code skill, subagent, rule, or hook

If the first argument is missing or neither `project` nor `skill`, stop and show usage.

---

## Create Project

### Step 0: Load Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` for repo type (single vs monorepo), code quality tools, and coding conventions. If missing, suggest `hero-skills:init` then proceed with defaults.

### Step 1: Parse Arguments

- **Project name** (required): Second word. Ask if missing.
- **Description** (optional): Remaining text.

### Step 2: Determine Context

```bash
git rev-parse --is-inside-work-tree 2>/dev/null && echo "IN_REPO" || echo "STANDALONE"
ls */pyproject.toml */package.json 2>/dev/null | head -5
```

Ask based on context:

| Context | Question |
|---------|----------|
| Not in a repo | Create standalone repo, or add to an existing one? |
| In a repo with siblings | Add as a new subproject? |
| Empty repo | Initialize this repo with the new project? |

### Step 3: Choose Project Type

Ask the user:

1. **Python backend** — FastAPI with uv
2. **Python library** — Reusable package (uv)
3. **Python CLI** — Command-line tool (uv)
4. **Full-stack** — FastAPI + Next.js or Vite with shadcn
5. **Frontend only** — Next.js or Vite with shadcn
6. **Node.js service** — Express/Fastify backend

### Step 4: Scaffold

#### Python Backend (FastAPI)

Read uv FastAPI guide at <https://docs.astral.sh/uv/guides/integration/fastapi/>

```bash
uv init PROJECT_NAME
cd PROJECT_NAME
uv add fastapi uvicorn[standard]
```

Structure:

```
PROJECT_NAME/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routers/__init__.py
│   ├── services/__init__.py
│   └── schemas/__init__.py
├── pyproject.toml
└── uv.lock
```

#### Python Library

```bash
uv init --lib PROJECT_NAME
```

#### Python CLI

```bash
uv init PROJECT_NAME
```

Add entry point in `pyproject.toml`:

```toml
[project.scripts]
PROJECT_NAME = "project_name:main"
```

#### Full-stack

```
PROJECT_NAME/
├── backend/    # FastAPI
└── frontend/   # Next.js or Vite
```

Backend: same as Python Backend above.

Frontend (ask Next.js or Vite):

- **Next.js**: Follow <https://ui.shadcn.com/docs/installation/next>

  ```bash
  npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
  cd frontend && npx shadcn@latest init -d
  ```

  Add API proxy in `next.config.js`:

  ```javascript
  async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
  }
  ```

- **Vite**: Follow <https://ui.shadcn.com/docs/installation/vite>

  Add API proxy in `vite.config.ts`:

  ```typescript
  server: {
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }
  }
  ```

#### Frontend Only

Same as full-stack frontend, at project root instead of `frontend/`.

#### Node.js Service

```bash
mkdir PROJECT_NAME && cd PROJECT_NAME
npm init -y
npm install express typescript @types/node @types/express tsx
npx tsc --init
```

### Step 5: Create CLAUDE.md

```markdown
# PROJECT_NAME

DESCRIPTION

## Development

### Prerequisites
- [Python 3.12+ and uv | Node.js 20+]

### Setup
[How to install dependencies]

### Run
[How to start dev servers]

### Test
[How to run tests]

## Project Structure
[Brief description of key directories]
```

### Step 6: Initialize Git (if standalone)

```bash
git init
git add -A
git commit -m "$(cat <<'EOF'
chore: initialize PROJECT_NAME

DESCRIPTION

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 7: Summary

```
Create Project Summary
======================
Project: PROJECT_NAME
Type: [Python Backend | Full-stack | ...]
Location: PATH

Created:
  - Project structure
  - CLAUDE.md
  - [Git repo initialized]

Next steps:
  cd PROJECT_NAME
  hero-skills:commit   # Set up pre-commit hooks
  hero-skills:test     # Verify it runs
```

Notes: Always creates CLAUDE.md. Uses uv for all Python projects. Uses shadcn for frontend UI. Does not push or create remote repos.

---

## Create Skill

Create skills and other components that extend Claude's capabilities.

### Core Principles

**Context is Precious** — Only add what Claude cannot infer: company-specific schemas, proprietary workflows, domain knowledge, tool integrations.

**Match Freedom to Fragility:**

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| High (prose) | Multiple valid approaches | "Review code for security issues" |
| Medium (pseudocode) | Preferred pattern, some variation OK | "Run pre-commit, then commit" |
| Low (exact scripts) | Fragile ops, consistency critical | "Execute this exact migration" |

### Component Types

| Type | Location | Use When |
|------|----------|----------|
| **Skill** | `.claude/skills/[name]/SKILL.md` | Workflows, guidelines |
| **Subagent** | `.claude/agents/[name].md` | Isolated execution |
| **Rule** | `.claude/rules/[name].md` | Always-on constraints |
| **Hook** | `settings.json` | Event-triggered automation |

User-level skills go in `~/.claude/skills/` for cross-project availability.

### Frontmatter

```yaml
---
name: kebab-case-name
# prettier-ignore
description: What it does AND when to trigger it. (50-200 chars)
argument-hint: [args]                    # Optional
disable-model-invocation: true           # Optional: manual-only
---
```

### Body Guidelines

- **Target**: Under 500 lines, under 5k words
- **Include**: Procedures Claude cannot infer, decision trees, tool integrations
- **Exclude**: Explanations Claude already knows

### Anti-patterns

| Don't | Do Instead |
|-------|------------|
| "When to Use" section in body | Put triggers in frontmatter description |
| 1000-line SKILL.md | Split into supplementary reference files |
| Duplicate info across files | Single source of truth |
| Lowercase angle bracket placeholders in skill content | Use UPPER_CASE (e.g., PROJECT_NAME, not project-name) |

### Creation Process

#### Step 0: Load Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Use `HERO.md` to understand the project's stack and conventions when creating skills that reference project-specific tools.

#### Step 1: Understand the Goal

Ask for:

1. What should this do? (verb — what action does it take)
2. When should it trigger? (what signals or user requests)
3. What does success look like?

#### Step 2: Plan the Component

Identify what files are needed:

```
skill-name/
├── SKILL.md              # Required: frontmatter + instructions
├── scripts/              # Deterministic, reusable code
├── references/           # Domain docs loaded on-demand
└── assets/               # Output templates
```

#### Step 3: Create the Files

```bash
mkdir -p .claude/skills/SKILL_NAME
```

Write `SKILL.md` with frontmatter and instructions.

#### Step 4: Validate

- Description has trigger context (50-200 chars)
- Body is under 500 lines
- No angle bracket placeholders
- References exist if declared in `supplementary-files`

#### Step 5: Summary

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
