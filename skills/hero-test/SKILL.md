---
name: hero-test
# prettier-ignore
description: Verify an implementation. Runs lint, typecheck, and unit tests on changed files, then detects project type (CLI, backend, frontend, MCP) and runs smoke tests. Use after /hero-plan implements.
argument-hint: [all|verify|smoke|backend|frontend|cli|mcp] [test-description]
disable-model-invocation: true
---

# Hero Test - Verify and Smoke Test

Verify an implementation works end to end. Runs static checks (lint, typecheck) and unit tests against changed files, then auto-detects project type and runs smoke tests against running services. Works for standalone projects, monorepo subprojects, or full-stack apps with multiple layers.

This is the verification step in the hero workflow:

```
/hero-plan → /hero-test → /hero-commit → /hero-push → /hero-self-review
```

## Arguments

- `$ARGUMENTS` - Optional target and/or test description:
  - `all` (default) - Run verification (Step 3) AND smoke tests (Steps 4-6)
  - `verify` - Run only verification (lint, typecheck, unit tests on changed files)
  - `smoke` - Run only smoke tests (skip verification)
  - `backend` - Only smoke test backend API
  - `frontend` - Only smoke test frontend app
  - `cli` - Only smoke test CLI/library
  - `mcp` - Only smoke test MCP server
  - Any other text is treated as a test description (e.g., "test the login flow")

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters, formatters, type checkers (commands run during verification)
- **Projects** → language, framework, install/test/dev commands, ports (skips auto-detection)

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection below.

### Step 1: Detect Project Structure

Scan current directory (and immediate subdirectories) for project indicators:

| Indicator | Type | Default Port |
|-----------|------|-------------|
| `pyproject.toml` + `fastmcp`/`mcp` dep | MCP Server | 8000 |
| `pyproject.toml` + FastAPI/Flask import in `app/` | Backend API | 8000 |
| `pyproject.toml` + `[project.scripts]` or `__main__.py` | CLI/Library | - |
| `package.json` + `next.config.*` | Frontend (Next.js) | 3000 |
| `package.json` + `vite.config.*` | Frontend (Vite) | 5173 |
| `backend/` + `frontend/` subdirs | Full-stack | both |

```bash
ls pyproject.toml package.json next.config.* vite.config.* 2>/dev/null
ls backend/pyproject.toml frontend/package.json 2>/dev/null
```

Check the project's `CLAUDE.md` for specific run instructions.

Report what was detected. If nothing detected, ask the user.

### Step 2: Install Dependencies

```bash
# Python
uv sync

# Node
npm install
```

For full-stack with subdirs, install in each.

### Step 3: Verify Implementation (Lint, Typecheck, Unit Tests)

Skip this step if `$ARGUMENTS` is `smoke`, `backend`, `frontend`, `cli`, or `mcp` — those target smoke testing only.

Capture the list of changed files first (uncommitted, then last commit, fallback to empty):

```bash
mapfile -t CHANGED_FILES < <(git diff --name-only; git diff --name-only HEAD~1 HEAD 2>/dev/null)
# Dedupe
CHANGED_FILES=($(printf "%s\n" "${CHANGED_FILES[@]}" | sort -u))
```

If `CHANGED_FILES` is empty, run the checks on the whole project (replace `"${CHANGED_FILES[@]}"` with `.` or the project root).

Use commands from `HERO.md` **Code Quality** and **Projects** sections when available. Otherwise auto-detect:

#### 3a: Lint changed files

```bash
# Python
uv run ruff check "${CHANGED_FILES[@]}"

# TypeScript / JavaScript
npx eslint "${CHANGED_FILES[@]}"

# Go
go vet ./...
```

#### 3b: Typecheck changed files

```bash
# Python
uv run mypy "${CHANGED_FILES[@]}"

# TypeScript
npx tsc --noEmit
```

#### 3c: Run unit tests

Use the `test-command` from HERO.md per project. Otherwise auto-detect:

```bash
# Python
uv run pytest

# Node
npm test
```

If a test file maps directly to a changed source file, prefer running just those tests for speed.

#### 3d: Pre-commit (if configured)

```bash
which pre-commit && pre-commit run --files "${CHANGED_FILES[@]}" || echo "NO_PRECOMMIT"
```

#### 3e: Report verification results

```
Verification
============
Lint:      PASSED (0 issues)
Typecheck: PASSED (0 errors)
Unit tests: 42 passed, 0 failed
Pre-commit: PASSED
```

If any check fails, report the failures clearly and **stop** before running smoke tests. Ask the user how to proceed (fix now vs continue to smoke tests).

### Step 4: Run Smoke Tests by Type

#### CLI / Library

1. Find entry points in `pyproject.toml` (`[project.scripts]`) or `__main__.py`
2. Run with `--help` or basic invocation:

```bash
uv run <script-name> --help
```

1. For libraries with no CLI:

```bash
uv run python -c "import <package>; print('OK')"
```

#### Backend API

1. Start server in background:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

1. Wait for ready, then smoke test:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/openapi.json | head -50
```

1. Note: Swagger UI at `http://localhost:8000/docs`

#### Frontend App

1. Start dev server in background (`npm run dev`)
2. Use Playwright MCP:

```
mcp__playwright__browser_navigate to http://localhost:<port>
mcp__playwright__browser_snapshot
```

1. Interact with elements using refs from snapshot

#### MCP Server

1. Start the server
2. Launch MCP Inspector: `npx @modelcontextprotocol/inspector`
3. Connect via Playwright at `http://localhost:6274`
4. Select "Streamable HTTP", enter server URL, click Connect
5. Test available tools through the Inspector UI

### Step 5: Full-Stack Orchestration (target = all)

When multiple layers detected:

1. **Backend first** (APIs need to be ready for frontend)
2. **Frontend second** (may proxy to backend)
3. Run smoke tests for each layer

### Step 6: Cleanup

1. Close browser: `mcp__playwright__browser_close`
2. Stop background servers: `TaskStop`
3. Report results

### Result Format

```
Hero Test Results
=================
Project: {name}
Mode: all (verification + smoke)

Verification:
  Lint:      PASSED (0 issues)
  Typecheck: PASSED (0 errors)
  Unit tests: 42 passed, 0 failed
  Pre-commit: PASSED

Smoke Tests:
  Backend (FastAPI on :8000):
    GET /health -> 200 OK
    OpenAPI spec: 12 endpoints discovered

  Frontend (Next.js on :3000):
    Home page: renders OK
    Navigation: 5 links found

Servers stopped.
```

## Examples

```
/hero-test                              # Verify + smoke test everything (default)
/hero-test verify                       # Only run lint, typecheck, unit tests
/hero-test smoke                        # Only run smoke tests (skip verification)
/hero-test backend                      # Only smoke-test the API
/hero-test frontend test the login form # Smoke test a specific UI flow
/hero-test mcp                          # Smoke test MCP server via Inspector
/hero-test cli run the export command   # Smoke test a specific CLI command
```

## Notes

- Always check project's CLAUDE.md first for custom run instructions
- Use `browser_snapshot` (not screenshots) for reliable element interaction
- Stop all background servers when testing completes
- For full-stack, backend must be ready before frontend tests that call APIs
- Verification runs against changed files first, then full project if no changes detected
- Stop and ask the user before continuing to smoke tests if verification fails
