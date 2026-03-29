---
name: hero-new-project
# prettier-ignore
description: Initialize a new project. Supports standalone repos or adding a subproject to an existing monorepo. Scaffolds Python (uv), full-stack (FastAPI + Next.js/Vite with shadcn), or Node.js projects with CLAUDE.md and pre-commit config.
argument-hint: <project-name> [description]
disable-model-invocation: true
---

# Hero New - Initialize a New Project

Scaffold a new project, either standalone or as a subproject in an existing repo.

## Arguments

- `$ARGUMENTS` - Project name (required) and optional description

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → type (single vs monorepo) to decide where to scaffold
- **Code Quality** → pre-commit, linters, formatters to configure in new project
- **Repository** → commit convention for initial commit

If `HERO.md` is missing, proceed normally. After scaffolding, suggest running `/hero-init` if no config exists yet.

### Step 1: Parse Arguments

- **Project name** (required): First word
- **Description** (optional): Remaining text

If no name provided, ask the user.

### Step 2: Determine Context

```bash
# Are we in an existing git repo?
git rev-parse --is-inside-work-tree 2>/dev/null && echo "IN_REPO" || echo "STANDALONE"

# Are there sibling projects? (monorepo detection)
ls */pyproject.toml */package.json 2>/dev/null | head -5
```

Ask the user:

| Context | Question |
|---------|----------|
| Not in a repo | "Create a new standalone repo, or add to an existing one?" |
| In a repo with siblings | "Add as a new subproject in this repo?" |
| In an empty repo | "Initialize this repo with the new project?" |

### Step 3: Choose Project Type

Ask the user:

1. **Python backend** - API service (FastAPI with uv)
2. **Python library** - Reusable package (uv)
3. **Python CLI** - Command-line tool (uv)
4. **Full-stack** - Backend (FastAPI) + Frontend (Next.js or Vite with shadcn)
5. **Frontend only** - Next.js or Vite with shadcn
6. **Node.js service** - Express/Fastify backend

### Step 4: Scaffold the Project

#### Python Backend (FastAPI)

Read uv FastAPI guide at <https://docs.astral.sh/uv/guides/integration/fastapi/>

```bash
# Standalone or subproject
uv init <project-name>
cd <project-name>
```

Create structure:

```
<project-name>/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── routers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── pyproject.toml
└── uv.lock
```

Add FastAPI dependency:

```bash
uv add fastapi uvicorn[standard]
```

#### Python Library

```bash
uv init --lib <project-name>
```

#### Python CLI

```bash
uv init <project-name>
cd <project-name>
```

Add entry point in `pyproject.toml`:

```toml
[project.scripts]
<project-name> = "<project_name>:main"
```

#### Full-stack

Create parent directory with backend + frontend:

```
<project-name>/
├── backend/    # FastAPI (same as Python Backend above)
└── frontend/   # Next.js or Vite
```

**Backend:**

```bash
mkdir -p <project-name>
cd <project-name>
uv init backend
cd backend
uv add fastapi uvicorn[standard]
```

Create the FastAPI app structure inside `backend/app/`.

**Frontend (ask Next.js or Vite):**

- Next.js: Follow <https://ui.shadcn.com/docs/installation/next>

  ```bash
  npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
  cd frontend
  npx shadcn@latest init -d
  ```

  Add API proxy in `next.config.js`:

  ```javascript
  async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
  }
  ```

- Vite: Follow <https://ui.shadcn.com/docs/installation/vite>

  Add API proxy in `vite.config.ts`:

  ```typescript
  server: {
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }
  }
  ```

#### Frontend Only

Same as full-stack frontend, but at project root instead of `frontend/` subdirectory.

#### Node.js Service

```bash
mkdir <project-name> && cd <project-name>
npm init -y
npm install express typescript @types/node @types/express tsx
npx tsc --init
```

### Step 5: Create CLAUDE.md

Create a `CLAUDE.md` in the project root with:

```markdown
# <Project Name>

<description>

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
chore: initialize <project-name>

<description>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 7: Run /hero-commit init

Suggest running `/hero-commit init` to set up pre-commit hooks.

### Step 8: Summary

```
Hero New Summary
================
Project: <project-name>
Type: [Python Backend | Full-stack | ...]
Location: <path>

Created:
  - Project structure
  - CLAUDE.md
  - [Git repo initialized]

Next steps:
  cd <project-name>
  /hero-commit init    # Set up pre-commit hooks
  /hero-test              # Verify it runs
```

## Examples

```
/hero-new my-api                           # Interactive - asks project type
/hero-new my-api a REST API for inventory  # With description
```

## Notes

- Always creates CLAUDE.md for project documentation
- Uses uv for all Python projects (not pip/poetry)
- Uses shadcn for frontend UI components
- For monorepos, adds the project as a subdirectory
- Does not push or create remote repos - just local scaffolding
