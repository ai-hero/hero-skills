---
name: smoke-ui
# prettier-ignore
description: Browser-driven UI smoke test using Playwright MCP. Navigates to routes affected by the diff, captures console errors, screenshots evidence. Skips with `(–)` if no UI project in HERO.md.
argument-hint: [routes...]
disable-model-invocation: true
---

# Smoke UI — Playwright-Driven Smoke Test of the Changed Routes

Drive the running dev server with Playwright MCP to make sure the diff did not obviously break the UI. Designed for the `e2e` step of `hero-skills:one-shot`, but runs standalone too. Skips with a clear "no UI project" message when HERO.md has no frontend framework configured — that is the expected outcome on backend-only PRs, not a failure.

## Pipeline DAG

When invoked from `hero-skills:one-shot`, this skill drives the `e2e` node of Pipeline 2:

```
[4/9] (✓) plan → (✓) implement → (✓) test → (▶) e2e → ( ) commit → ( ) push-draft → ( ) self-review → ( ) respond → ( ) ship

Now running: e2e
```

When run standalone, omit the orchestrator DAG and just print the internal phases below.

## Internal phases

```
detect → server → routes → drive → report
```

## Arguments

- `$ARGUMENTS` (optional) — Space-separated list of routes to exercise (e.g., `/dashboard /settings/api`). If omitted, derive routes from the diff: changed page / route / component files → their owning routes.

## Prerequisites

- Playwright MCP is available (the model can call `mcp__playwright__browser_*` tools).
- A frontend project is declared in HERO.md with `framework`, `dev-command`, and `port`.
- The user is okay with the dev server running for the duration of the smoke test (and afterward, if this skill started it).

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Stale-HERO check — fast subset of the plugin's check-hero-staleness.sh.
# Keep aligned with the copies in commit-changes/push-pr/plan-work/test-changes.
HERO_TIME=$(git log -1 --format=%ct -- HERO.md 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
CONFIG_TIME=$(git log -1 --format=%ct -- \
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

If `HERO.md` is missing, suggest `hero-skills:init-hero` and exit. This skill needs `framework`, `dev-command`, and `port` to know what to drive.

### Step 1: Detect UI Project (`detect`)

Parse the `## Projects` section of HERO.md. A "UI project" is any project whose `framework` is in this set:

```
next nuxt remix astro vite svelte sveltekit solid solid-start qwik gatsby angular create-react-app cra
```

If none of the declared projects matches the UI set:

```
(–) e2e: no UI project in HERO.md — skipping smoke-ui.
This is expected on backend-only PRs.
```

Exit 0 with that message. Callers (one-shot in particular) should treat the skip as `(–)` in the DAG, not `(✗)`.

If multiple UI projects exist, ask the user which one to smoke-test (or pass it explicitly via the project's path). One per run keeps the dev-server lifecycle simple.

Record `UI_PORT`, `UI_DEV_COMMAND`, `UI_PATH` from the matched project.

### Step 2: Confirm Dev Server (`server`)

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

On `y`, start the dev server with output captured to a tempfile and PID tracked:

```bash
DEV_LOG=$(mktemp /tmp/hero-smoke-ui-XXXXXX.log)
( cd "$ROOT/$UI_PATH" && eval "$UI_DEV_COMMAND" > "$DEV_LOG" 2>&1 ) &
DEV_PID=$!
echo "Started dev server (pid $DEV_PID, log $DEV_LOG)."

# Wait up to 60s for the server to come up.
for i in $(seq 1 30); do
  if curl -sf -o /dev/null -m 2 "$DEV_URL"; then
    echo "Dev server is up after ${i}x2s."
    break
  fi
  sleep 2
done

if ! curl -sf -o /dev/null -m 2 "$DEV_URL"; then
  echo "Dev server did not come up within 60s. Last 30 log lines:"
  tail -30 "$DEV_LOG"
  echo ""
  echo "Cleaning up the process we started:"
  kill "$DEV_PID" 2>/dev/null || true
  exit 1
fi
```

Note the log path so the user can `tail -f` it in another terminal if a smoke-test failure needs deeper diagnosis. Do NOT auto-tail it into this conversation — it will flood the context.

### Step 3: Identify Routes (`routes`)

If `$ARGUMENTS` is non-empty, use those routes verbatim.

Otherwise, derive from the diff. For each changed file under the UI project, map to its owning route(s):

- Next.js App Router: `app/foo/bar/page.tsx` → `/foo/bar`; `app/(group)/x/page.tsx` → `/x`; route handlers (`route.ts`) excluded.
- Next.js Pages Router: `pages/foo/bar.tsx` → `/foo/bar`; `pages/index.tsx` → `/`.
- Vite + React Router / SvelteKit / Remix / etc.: walk the routing config (`routes.tsx`, `+page.svelte`, `routes/`) and emit the canonical paths.
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

### Step 4: Drive the Browser (`drive`)

For each route in order, run the same recipe via Playwright MCP:

1. `mcp__playwright__browser_navigate` to `$DEV_URL$ROUTE`. Set `expectedStatus` to 200-399 if the tool supports it; otherwise check status from a follow-up `browser_network_requests` call.
2. `mcp__playwright__browser_wait_for` until the page is interactive (look for a stable selector — `body`, the route's `<h1>`, or a known landmark from the snapshot).
3. `mcp__playwright__browser_snapshot` — capture the accessibility tree as the canonical "did it render" check.
4. `mcp__playwright__browser_console_messages` — read messages emitted since the last navigate.
5. `mcp__playwright__browser_take_screenshot` — save a PNG named `smoke-ui-ROUTE_SLUG.png` under `$ROOT/.smoke-ui/` (gitignored — add to `.gitignore` if absent).

For routes that involve a form change (detected by reading the diff: `<form>` / `useForm` / `onSubmit` added or modified), additionally:

1. `mcp__playwright__browser_fill_form` with placeholder-but-plausible values for the visible inputs (keep it under 5 inputs — refuse if the form is huge; that's a real E2E test, not a smoke test).
2. Click the submit control, `browser_wait_for` the success state, `browser_console_messages` again.

#### Failure rules

A route fails the smoke if any of:

- The HTTP status of the document request is 4xx or 5xx.
- An entry in `browser_console_messages` has type `error` (skip the dev-only Next.js / Vite hydration warnings — match against the framework's known noise list before promoting).
- An uncaught exception appears in the dev server log (`grep -E 'Error:|TypeError:|ReferenceError:' "$DEV_LOG"`).
- `browser_wait_for` times out — the page never became interactive.
- A form submission's `wait_for` fails — the success state never rendered.

On any failure: stop driving further routes, surface the failing route + the console message + the screenshot path, and exit non-zero. Do **not** auto-retry; the model is a poor judge of "transient vs real" for UI bugs.

### Step 5: Cleanup

Always (success or failure):

```bash
# Close the browser session.
mcp__playwright__browser_close

# If we started the dev server, leave it running by default — most users
# want it for follow-up work. Offer to stop only if the user explicitly
# asked for cleanup.
if [ "$STARTED_BY_US" = "true" ]; then
  echo ""
  echo "Dev server is still running (pid $DEV_PID, log $DEV_LOG)."
  echo "Stop it now? [y/N]"
fi
```

If the user says yes, `kill "$DEV_PID"` and remove the log. Otherwise leave both in place — the user is back at their terminal and can clean up at will.

### Step 6: Report

```
Smoke UI Summary
================
Project:     PROJECT_NAME (FRAMEWORK at :PORT)
Started by:  smoke-ui | already-running

Phases:      (✓) detect → (✓) server → (✓) routes → (✓) drive → (✓) report

Routes:      N tested (LIST)
Console:     X errors, Y warnings (filtered framework noise)
Screenshots: $ROOT/.smoke-ui/*.png

Result:      OK | FAILED at ROUTE — REASON
```

If FAILED, surface:

- The failing route and the verbatim console error / status / wait-for timeout message.
- The screenshot path so the user can open it.
- The last 30 lines of `$DEV_LOG` if the failure looks server-side.
- Suggested next step: usually `hero-skills:plan-work "fix smoke-ui regression at ROUTE"`.

## Notes

- This is a **smoke** test, not a full E2E. Cap routes at 5, skip large forms, do not chase flaky tests. If a real E2E suite exists in the repo (Playwright config, Cypress, etc.), prefer running it via `hero-skills:test-changes` instead.
- The skill never modifies the user's code. It only reads, drives, and reports.
- Screenshots and the dev-server log live under `$ROOT/.smoke-ui/` — add that directory to `.gitignore` before saving anything if it is not already ignored.
- Console-error filtering: the framework's hot-reload / dev-mode warnings (e.g., `[HMR]`, React strict-mode double-render notices) are not failures. Match conservatively: if in doubt about whether a message is real, surface it as a warning rather than a hard fail, and let the user decide.
