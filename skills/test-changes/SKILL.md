---
name: test-changes
# prettier-ignore
description: Verify an implementation. Runs lint, typecheck, and unit tests on changed files, then detects project type (CLI, backend, frontend, MCP) and runs smoke tests.
argument-hint: [all|verify|smoke|backend|frontend|cli|mcp] [test-description|routes...]
disable-model-invocation: true
---

# Test — Verify and Smoke Test

Verify an implementation works end to end. Runs static checks (lint, typecheck) and unit tests against changed files, then auto-detects project type and runs smoke tests against running services. Works for standalone projects, monorepo subprojects, or full-stack apps with multiple layers.

## Arguments

- `$ARGUMENTS` - Optional target and/or test description:
  - `all` (default) - Run verification (Step 3) AND smoke tests (Steps 4-6)
  - `verify` - Run only verification (lint, typecheck, unit tests on changed files)
  - `smoke` - Run only smoke tests (skip verification)
  - `backend` - Only smoke test backend API
  - `frontend [routes...]` - Only smoke test frontend app. Optional trailing tokens are routes to exercise verbatim (e.g., `/dashboard /settings/api`); if omitted, routes are derived from the diff (capped at 5)
  - `cli` - Only smoke test CLI/library
  - `mcp` - Only smoke test MCP server
  - Any other text is treated as a test description (e.g., "test the login flow")

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Stale-HERO check — fast subset of the plugin's check-hero-staleness.sh.
# Keep aligned with the copies in push-pr/one-shot.
HERO_TIME=$(git -C "$ROOT" log -1 --format=%ct -- HERO.md 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
CONFIG_TIME=$(git -C "$ROOT" log -1 --format=%ct -- \
  pyproject.toml ':(glob)**/pyproject.toml' \
  package.json ':(glob)**/package.json' \
  go.mod ':(glob)**/go.mod' \
  Cargo.toml ':(glob)**/Cargo.toml' \
  .github/workflows .pre-commit-config.yaml \
  CLAUDE.md Makefile justfile Taskfile.yml 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
if [ "${CONFIG_TIME:-0}" -gt "${HERO_TIME:-0}" ]; then
  echo "note: HERO.md may be out of date — run hero-skills:init-hero --update to refresh."
fi
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters, formatters, type checkers (commands run during verification)
- **Projects** → language, framework, install/test/dev commands, ports (skips auto-detection)

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with auto-detection below. If the stale-HERO hint fired, mention it once to the user but do not block.

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

Capture the list of changed files first (uncommitted, then last commit, fallback to empty). Read the dedupe back into the array via `mapfile` so filenames containing spaces, tabs, or globs survive intact — `($(...))` would word-split and corrupt them:

```bash
mapfile -t CHANGED_FILES < <(git diff --name-only; git diff --name-only HEAD~1 HEAD 2>/dev/null)
# Newline-safe dedupe (preserves spaces in filenames).
mapfile -t CHANGED_FILES < <(printf "%s\n" "${CHANGED_FILES[@]}" | sort -u)
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
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --files "${CHANGED_FILES[@]}"
else
  echo "NO_PRECOMMIT"
fi
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

**Skip Step 4 entirely if `$ARGUMENTS` is `verify`.** That mode is documented as "verification only" — Step 3 already ran lint, typecheck, unit tests, and pre-commit; running smoke tests would contradict the documented contract.

```bash
FIRST_ARG=$(printf '%s' "$ARGUMENTS" | awk '{print $1}')
if [ "$FIRST_ARG" = "verify" ]; then
  echo "Skipping smoke tests (verify mode)."
  # Jump to Step 7: Final Report.
fi
```

#### CLI / Library

1. Find entry points in `pyproject.toml` (`[project.scripts]`) or `__main__.py`
2. Run with `--help` or basic invocation:

```bash
uv run SCRIPT_NAME --help
```

1. For libraries with no CLI:

```bash
uv run python -c "import PACKAGE; print('OK')"
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

Full recipe: detect whether this is a UI project, confirm/start its dev server under `.test-output/`, derive up to 5 routes from the diff (or use explicit routes passed after `frontend`), drive each route with Playwright MCP, and apply the console-noise allowlist and failure rules below. If no UI project is detected, skip this section gracefully — that is expected on backend-only PRs, not a failure.

##### Detect UI project

If Step 1 detected no frontend indicator at all (no `next.config.*`, `vite.config.*`, and no HERO.md project with a UI-ish `framework`), skip this section and print:

```
(–) frontend: no UI project detected — skipping frontend smoke.
This is expected on backend-only PRs.
```

Otherwise, confirm which project to drive using HERO.md's `## Projects` section (already loaded in Step 0). UI detection there is **heuristic, not closed-enum** — `init-hero` does not constrain the `framework` value, so treat the list below as a hint and fall back to asking the user when nothing matches.

**Known-UI frameworks (auto-detected as UI):**

```
next nextjs nuxt remix astro vite svelte sveltekit solid solid-start qwik
gatsby angular react cra create-react-app
```

**Known-non-UI frameworks (auto-detected as backend, skip silently):**

```
fastapi flask django starlette express nestjs hono fiber gin echo actix axum
rails sinatra laravel
```

**Decision:**

1. If any project's `framework` is in the known-UI set → that's the UI project. Continue.
2. If every project's `framework` is in the known-non-UI set OR there are no HERO.md projects with a `framework` field → fall back to Step 1's file-based detection (`next.config.*`, `vite.config.*`). If that also found nothing, skip as above.
3. If a project's `framework` is in **neither** list (custom value, typo, or a UI framework not yet on the list), ask the user once:

   ```
   Project 'PROJECT_NAME' declares framework: FRAMEWORK_VALUE.
   Treat as a UI project for smoke testing?
     [y] Yes — drive the dev server with Playwright MCP
     [n] No — skip (recommended for non-UI frameworks)
     [a] Add 'FRAMEWORK_VALUE' to the known-UI list in skills/test-changes/SKILL.md and continue (asks once per session, not durable)
   ```

   Default to `n` if the user answers ambiguously — silently smoking a backend project is worse than silently skipping a UI one.

If multiple UI projects exist, ask the user which one to smoke-test (or pass it explicitly via the project's path). One per run keeps the dev-server lifecycle simple.

Record `UI_PORT`, `UI_DEV_COMMAND`, `UI_PATH` from the matched project. Validate that `UI_PATH` resolves under `$ROOT`:

```bash
if [ ! -d "$ROOT/$UI_PATH" ]; then
  echo "ERROR: UI project path '$ROOT/$UI_PATH' does not exist."
  echo "       Check the 'path:' field for this project in HERO.md, or run"
  echo "       hero-skills:init-hero --update to re-detect."
  exit 1
fi
```

##### Confirm or start the dev server

Check whether the dev server is already up on `UI_PORT`:

```bash
DEV_URL="http://localhost:$UI_PORT"
if curl -sf -o /dev/null -m 3 "$DEV_URL"; then
  echo "Dev server already running at $DEV_URL — using it."
  STARTED_BY_US=false
else
  echo "Dev server is not responding at $DEV_URL."
  STARTED_BY_US=true
fi
```

If `STARTED_BY_US=true`, ask the user before starting it:

```
The dev server is not running. Start it now?
  [y] Start `UI_DEV_COMMAND` in the background — leaves it running after this skill finishes.
  [n] Cancel — start it yourself, then re-run this skill.
```

On `y`, start the dev server with output captured to a log under `.test-output/` and PID tracked:

```bash
# Centralize all frontend-smoke artifacts under .test-output/ so they live
# next to the screenshots and are covered by the same exclude entry. The
# `mkdir -p` and exclude-append also happen below before the first
# screenshot — doing them here too is cheap and lets the dev-server log
# exist before the drive phase ever runs.
mkdir -p "$ROOT/.test-output"
# Write the ignore rule to .git/info/exclude (repo-local, untracked) rather
# than .gitignore (tracked) — modifying a tracked file would leave the
# working tree dirty and contradict this skill's "never modifies tracked
# source files" contract. Resolve the path via git so worktrees / bare repos
# / non-default gitdirs work too.
EXCLUDE_FILE=$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)
case "$EXCLUDE_FILE" in
  /*) ;;
  *)  EXCLUDE_FILE="$ROOT/$EXCLUDE_FILE" ;;
esac
mkdir -p "$(dirname "$EXCLUDE_FILE")"
grep -qxF '.test-output/' "$EXCLUDE_FILE" 2>/dev/null \
  || printf '\n.test-output/\n' >> "$EXCLUDE_FILE"
DEV_LOG="$ROOT/.test-output/dev-server.log"
# Truncate any stale log from a previous run so this run's diagnostics
# only reflect the current invocation.
: > "$DEV_LOG"

# Run UI_DEV_COMMAND without `eval` — bash's normal field-splitting on the
# unquoted variable handles compound commands like `pnpm -C web dev --port
# 3001` correctly, and we avoid the second round of shell expansion that
# `eval` would add.
# shellcheck disable=SC2086  # intentional word-splitting on UI_DEV_COMMAND
( cd "$ROOT/$UI_PATH" && $UI_DEV_COMMAND > "$DEV_LOG" 2>&1 ) &
DEV_PID=$!
echo "Started dev server (pid $DEV_PID, log $DEV_LOG)."

# Wait up to 60s for the server to come up. Bail early if the spawned
# process has already died (typo'd UI_DEV_COMMAND, missing dep, port in use).
for i in $(seq 1 30); do
  if ! kill -0 "$DEV_PID" 2>/dev/null; then
    echo "Dev server process died before responding. Last 30 log lines:"
    tail -30 "$DEV_LOG"
    exit 1
  fi
  if curl -sf -o /dev/null -m 2 "$DEV_URL"; then
    echo "Dev server is up after ${i}x2s."
    break
  fi
  sleep 2
done

if ! curl -sf -o /dev/null -m 2 "$DEV_URL"; then
  # Server did not respond on $DEV_URL. Probe alternates: dev servers often
  # bind 0.0.0.0 (devcontainers / CI runners) or 127.0.0.1 only, and IPv6
  # localhost can resolve to an unreachable address. Surface that case
  # rather than reporting "did not come up" when it actually did.
  # 0.0.0.0 is a *bind* address, not a routable connect target — only
  # probe addresses that are actually reachable as clients.
  ALT_URL=""
  for HOST in 127.0.0.1 ::1; do
    # Wrap IPv6 literal in brackets for curl's URL syntax.
    case "$HOST" in
      ::*) PROBE_URL="http://[$HOST]:$UI_PORT" ;;
      *)   PROBE_URL="http://$HOST:$UI_PORT" ;;
    esac
    if curl -sf -o /dev/null -m 2 "$PROBE_URL"; then
      ALT_URL="$PROBE_URL"
      break
    fi
  done
  # Also grep the log for the framework's announced URL (Next, Vite, etc.
  # all print "Local:" / "ready on" / "Listening on" with a URL).
  LOG_URL=$(grep -Eom1 'https?://[a-zA-Z0-9.:-]+' "$DEV_LOG" 2>/dev/null || true)

  if [ -n "$ALT_URL" ] || [ -n "$LOG_URL" ]; then
    echo "Dev server is up but not on $DEV_URL."
    [ -n "$ALT_URL" ] && echo "  Reachable at: $ALT_URL"
    [ -n "$LOG_URL" ] && echo "  Server reports: $LOG_URL"
    echo "  Update HERO.md 'port:' (or 'host:' if your config supports it)"
    echo "  for project '$PROJECT_NAME' and re-run."
  else
    echo "Dev server did not come up within 60s. Last 30 log lines:"
    tail -30 "$DEV_LOG"
  fi

  echo ""
  echo "Cleaning up the process we started:"
  kill "$DEV_PID" 2>/dev/null || true
  # Verify the kill worked — frameworks like `next dev` spawn worker
  # processes; killing the parent can leave the port bound. Re-curl after
  # a beat; if it still answers, surface the orphan so the user can clean up.
  sleep 1
  if curl -sf -o /dev/null -m 2 "$DEV_URL"; then
    echo "WARN: stale process still bound to :$UI_PORT after kill."
    echo "      Investigate: lsof -i :$UI_PORT"
  fi
  exit 1
fi
```

Note the log path so the user can `tail -f` it in another terminal if a smoke-test failure needs deeper diagnosis. Do NOT auto-tail it into this conversation — it will flood the context.

##### Identify routes

If routes were passed after `frontend` (e.g., `hero-skills:test-changes frontend /dashboard /settings/api`), use those verbatim.

Otherwise, derive from the diff. For each changed file under the UI project, map to its owning route(s):

- Next.js App Router: `app/foo/bar/page.tsx` → `/foo/bar`; `app/(group)/x/page.tsx` → `/x` (route groups are URL-invisible); route handlers (`route.ts`) excluded.
- Next.js dynamic / catch-all segments: `app/posts/[slug]/page.tsx`, `app/[...slug]/page.tsx`, `app/[[...slug]]/page.tsx` — there is no canonical URL for these. Ask the user once for a sample value (e.g., a real `slug` from the dev DB), or skip the route with `(–)` and a note. Do not invent values like `/posts/example` — those usually 404.
- Next.js parallel and intercepted routes: `app/@modal/...`, `app/(.)photo/...`, `app/(..)settings/...` — exclude entirely. They have no free-standing URL; navigating to a literal `@modal` returns 404 and pollutes the smoke result.
- Next.js Pages Router: `pages/foo/bar.tsx` → `/foo/bar`; `pages/index.tsx` → `/`; `pages/[slug].tsx` → ask for a sample value or skip.
- Vite + React Router / SvelteKit / Remix / etc.: walk the routing config (`routes.tsx`, `+page.svelte`, `routes/`) and emit the canonical paths. Apply the same dynamic-segment rule (ask for a sample or skip).
- Shared components (`components/Button.tsx`, `lib/`, `hooks/`): no direct route. Pick the **landing page** (`/`) plus the **most-changed page** as a fallback so we exercise the rendering path at all.

If the diff touches no UI files at all (despite the project being a UI project — e.g., the change was server actions only), exercise just the landing page `/` so we still detect a hard regression like a build break.

Cap the route list at **5 routes** for a smoke test. More than that and the user should run a real E2E suite.

Print the route list before driving so the user can object:

```
Smoke routes (N):
  - /
  - /dashboard
  - /settings/api
```

##### Drive the browser

Mark `BROWSER_OPENED=true` after the first successful `browser_navigate` so Step 6 (Cleanup) knows whether to call `browser_close`.

For each route in order, run the same recipe via Playwright MCP:

1. `mcp__playwright__browser_navigate` to `$DEV_URL$ROUTE`. Set `expectedStatus` to 200-399 if the tool supports it; otherwise check status from a follow-up `browser_network_requests` call.
2. `mcp__playwright__browser_wait_for` until the page is interactive (look for a stable selector — `body`, the route's `<h1>`, or a known landmark from the snapshot).
3. `mcp__playwright__browser_snapshot` — capture the accessibility tree as the canonical "did it render" check.
4. `mcp__playwright__browser_console_messages` — read messages emitted since the last navigate.
5. `mcp__playwright__browser_take_screenshot` — save a PNG named `smoke-ROUTE_SLUG.png` under `$ROOT/.test-output/playwright-mcp/`. **Before the first screenshot of this run**, do the three-step setup once:

   ```bash
   mkdir -p "$ROOT/.test-output/playwright-mcp"
   # Ensure the exclude file covers .test-output/. Use .git/info/exclude
   # (repo-local, untracked) instead of .gitignore so we don't modify a
   # tracked file — see the dev-server note above.
   EXCLUDE_FILE=$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)
   case "$EXCLUDE_FILE" in
     /*) ;;
     *)  EXCLUDE_FILE="$ROOT/$EXCLUDE_FILE" ;;
   esac
   mkdir -p "$(dirname "$EXCLUDE_FILE")"
   grep -qxF '.test-output/' "$EXCLUDE_FILE" 2>/dev/null \
     || printf '\n.test-output/\n' >> "$EXCLUDE_FILE"
   # Clear stale artifacts from previous runs so this report only reflects
   # the current diff. Scope the delete to this skill's artifacts so
   # co-located Playwright traces / videos from unrelated sessions are not
   # touched.
   rm -f "$ROOT/.test-output/playwright-mcp"/smoke-*.png
   ```

   `$ROOT/.test-output/` is the canonical local-only test-artifacts directory for hero-skills. All disposable outputs from any hero skill — Playwright screenshots, traces, videos, network logs, dev-server logs, coverage reports — land somewhere under it so the repo root stays clean and a single `.gitignore` entry covers them all.

For routes that involve a form change (detected by reading the diff: `<form>` / `useForm` / `onSubmit` added or modified), additionally:

1. `mcp__playwright__browser_fill_form` with placeholder-but-plausible values for the visible inputs (keep it under 5 inputs — refuse if the form is huge; that's a real E2E test, not a smoke test).
2. Click the submit control, `browser_wait_for` the success state, `browser_console_messages` again.

###### Console noise allowlist

Dev-mode frameworks emit benign warnings on every page load. The allowlist below is **the only set of console messages this skill ignores**; everything else (including any console message of `type=error`) is treated as a failure. Do not invent additional patterns at runtime.

```
Next.js / React (development mode):
  - "[Fast Refresh]"
  - "[HMR]"
  - "Download the React DevTools"
  - "Warning: ReactDOM.render is no longer supported"
  - any message whose body starts with "Warning:" AND contains "in development"

Vite:
  - "[vite] connecting…"
  - "[vite] connected."
  - "[vite] hot updated:"

SvelteKit / Svelte:
  - "[vite] connecting…"  (same as Vite — Kit uses Vite under the hood)

General:
  - any message whose URL is a `chrome-extension://` source (browser extensions
    emitting in the page context — not the app's fault).
```

If a future framework has its own benign-warnings set, the user must update this list explicitly via a follow-up edit to this skill — the frontend smoke does not silently expand its filter set.

###### Failure rules

A route fails the smoke if any of:

- The HTTP status of the document request is 4xx or 5xx.
- An entry in `browser_console_messages` has `type=error` AND its body does NOT match an allowlist entry from the section above. Match the allowlist conservatively: if you are not sure whether a message is benign, treat it as a failure and let the user decide.
- An uncaught exception appears in the dev server log (covers a broad set of common failures and ignores nothing):

  ```bash
  grep -Ei '\b(Error|Warning|Exception|Traceback|Unhandled[A-Z][a-zA-Z]*Rejection):' "$DEV_LOG"
  grep -E '\bat [A-Za-z_$][A-Za-z0-9_$.]* \(.*:[0-9]+:[0-9]+\)' "$DEV_LOG"   # JS stack frames
  grep -E '\bModule(Not)?Found|SyntaxError|RangeError|TypeError|ReferenceError' "$DEV_LOG"
  ```

- `browser_wait_for` times out — the page never became interactive.
- A form submission's `wait_for` fails — the success state never rendered.

On any failure: stop driving further routes, surface the failing route + the console message + the screenshot path, and treat the run as failed. Do **not** auto-retry; the model is a poor judge of "transient vs real" for UI bugs.

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

```bash
# Close the browser session — only if the frontend drive step actually
# opened one. Skipping this when no UI project was found (or the server
# failed to come up) avoids noisy "no session to close" errors from the
# MCP server.
if [ "${BROWSER_OPENED:-false}" = "true" ]; then
  mcp__playwright__browser_close
fi

# If we started the frontend dev server ourselves, leave it running by
# default — most users want it for follow-up work. Offer to stop only if
# the user explicitly asked for cleanup.
if [ "${STARTED_BY_US:-false}" = "true" ]; then
  echo ""
  echo "Dev server is still running (pid $DEV_PID, log $DEV_LOG)."
  echo "Stop it now? [y/N]"
fi
```

If the user says yes, `kill "$DEV_PID"` and remove the log. Otherwise leave both in place — the user is back at their terminal and can clean up at will. Stop any other background servers (backend, MCP inspector) started for this run via `TaskStop`, then report results.

### Result Format

```
Test Results
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
    Started by:  test-changes | already-running
    Routes:      N tested (/, /dashboard, /settings/api)
    Console:     X errors, Y warnings (filtered framework noise)
    Screenshots: $ROOT/.test-output/playwright-mcp/*.png
    Result:      OK | FAILED at ROUTE — REASON

Servers stopped.

Next steps:
  /simplify                    # tidy the dirty diff before committing
  hero-skills:push-pr          # commit and push — opens a draft PR
```

## Examples

```
hero-skills:test-changes                                    # Verify + smoke test everything (default)
hero-skills:test-changes verify                             # Only run lint, typecheck, unit tests
hero-skills:test-changes smoke                              # Only run smoke tests (skip verification)
hero-skills:test-changes backend                             # Only smoke-test the API
hero-skills:test-changes frontend                            # Smoke test frontend; routes derived from the diff
hero-skills:test-changes frontend /dashboard /settings/api   # Smoke test specific routes (verbatim)
hero-skills:test-changes mcp                                 # Smoke test MCP server via Inspector
hero-skills:test-changes cli run the export command          # Smoke test a specific CLI command
```

## Notes

- Always check project's CLAUDE.md first for custom run instructions
- Use `browser_snapshot` (not screenshots) for reliable element interaction; screenshots are captured separately as evidence for the report
- The frontend smoke is a **smoke** test, not a full E2E: cap routes at 5, skip large forms, do not chase flaky tests. If a real E2E suite already exists in the repo (Playwright config, Cypress, etc.), prefer running it directly instead.
- The frontend smoke never modifies tracked source files. It only reads, drives, and reports, but writes disposable local artifacts under `$ROOT/.test-output/`: screenshots in `.test-output/playwright-mcp/` and the dev-server log at `.test-output/dev-server.log`. `.test-output/` is the shared test-artifact directory for every hero skill. The ignore rule lives in `.git/info/exclude` (repo-local, untracked) — *not* `.gitignore` — so the working tree never gets dirtied.
- Console-error filtering: the framework's hot-reload / dev-mode warnings (e.g., `[HMR]`, React strict-mode double-render notices) are not failures. Match conservatively: if in doubt about whether a message is real, surface it as a warning rather than a hard fail, and let the user decide.
- Stop all background servers when testing completes
- For full-stack, backend must be ready before frontend tests that call APIs
- Verification runs against changed files first, then full project if no changes detected
- Stop and ask the user before continuing to smoke tests if verification fails
