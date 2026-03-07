---
name: hero-test
# prettier-ignore
description: Smoke test any project or nested subproject. Auto-detects type (CLI, backend API, frontend app, MCP server) and runs appropriate tests. Supports targeting specific layers. Works with single repos and monorepos.
argument-hint: [all|backend|frontend|cli|mcp] [test-description]
disable-model-invocation: true
---

# Hero Test - Smoke Test Any Project

Auto-detect project type and run smoke tests. Works for standalone projects, monorepo subprojects, or full-stack apps with multiple layers.

## Arguments

- `$ARGUMENTS` - Optional target and/or test description:
  - `all` (default) - Detect and test all layers
  - `backend` - Only test backend API
  - `frontend` - Only test frontend app
  - `cli` - Only test CLI/library
  - `mcp` - Only test MCP server
  - Any other text is treated as a test description (e.g., "test the login flow")

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Projects** → language, framework, test commands, dev commands, ports (skips auto-detection)

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

### Step 3: Run Smoke Tests by Type

#### CLI / Library

1. Find entry points in `pyproject.toml` (`[project.scripts]`) or `__main__.py`
2. Run with `--help` or basic invocation:

```bash
uv run <script-name> --help
```

3. For libraries with no CLI:

```bash
uv run python -c "import <package>; print('OK')"
```

#### Backend API

1. Start server in background:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

2. Wait for ready, then smoke test:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/openapi.json | head -50
```

3. Note: Swagger UI at `http://localhost:8000/docs`

#### Frontend App

1. Start dev server in background (`npm run dev`)
2. Use Playwright MCP:

```
mcp__playwright__browser_navigate to http://localhost:<port>
mcp__playwright__browser_snapshot
```

3. Interact with elements using refs from snapshot

#### MCP Server

1. Start the server
2. Launch MCP Inspector: `npx @modelcontextprotocol/inspector`
3. Connect via Playwright at `http://localhost:6274`
4. Select "Streamable HTTP", enter server URL, click Connect
5. Test available tools through the Inspector UI

### Step 4: Full-Stack Orchestration (target = all)

When multiple layers detected:

1. **Backend first** (APIs need to be ready for frontend)
2. **Frontend second** (may proxy to backend)
3. Run smoke tests for each layer

### Step 5: Cleanup

1. Close browser: `mcp__playwright__browser_close`
2. Stop background servers: `TaskStop`
3. Report results

### Result Format

```
Smoke Test Results
==================
Project: <name>
Layers tested: Backend API, Frontend

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
/hero-test                              # Auto-detect and test everything
/hero-test backend                      # Only test the API
/hero-test frontend test the login form # Test specific UI flow
/hero-test mcp                          # Test MCP server via Inspector
/hero-test cli run the export command   # Test specific CLI command
```

## Notes

- Always check project's CLAUDE.md first for custom run instructions
- Use `browser_snapshot` (not screenshots) for reliable element interaction
- Stop all background servers when testing completes
- For full-stack, backend must be ready before frontend tests that call APIs
