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

If `HERO.md` is missing, suggest `hero-skills:init-hero` and exit. This skill needs `framework`, `dev-command`, and `port` to know what to drive.

### Step 1: Detect UI Project (`detect`)

Parse the `## Projects` section of HERO.md. UI detection is **heuristic, not closed-enum** — `init-hero` does not constrain the `framework` value, so we treat the list below as a hint and fall back to asking the user when nothing matches.

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
2. If every project's `framework` is in the known-non-UI set OR there are no projects with a `framework` field → backend-only PR. Print and exit 0:

   ```
   (–) e2e: no UI project in HERO.md — skipping smoke-ui.
   This is expected on backend-only PRs.
   ```

3. If a project's `framework` is in **neither** list (custom value, typo, or a UI framework not yet on the list), ask the user once:

   ```
   Project 'PROJECT_NAME' declares framework: FRAMEWORK_VALUE.
   Treat as a UI project for smoke testing?
     [y] Yes — drive the dev server with Playwright MCP
     [n] No — skip with `(–) e2e` (recommended for non-UI frameworks)
     [a] Add 'FRAMEWORK_VALUE' to the known-UI list in skills/smoke-ui/SKILL.md and continue (asks once per session, not durable)
   ```

   Default to `n` if the user answers ambiguously — silently smoking a backend project is worse than silently skipping a UI one (the latter shows up as a `(–)` the user can object to; the former wastes time and may produce false errors).

Callers (one-shot in particular) should treat the skip as `(–)` in the DAG, not `(✗)`.

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

On `y`, start the dev server with output captured to a log under `.test-output/` and PID tracked:

```bash
# Centralize all smoke-ui artifacts under .test-output/ so they live next
# to the screenshots and are covered by the same .gitignore entry. The
# `mkdir -p` and gitignore-append also happen in Step 4 before the first
# screenshot — doing them here too is cheap and lets the dev-server log
# exist before Step 4 ever runs.
mkdir -p "$ROOT/.test-output"
grep -qxF '.test-output/' "$ROOT/.gitignore" 2>/dev/null \
  || printf '\n.test-output/\n' >> "$ROOT/.gitignore"
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

### Step 3: Identify Routes (`routes`)

If `$ARGUMENTS` is non-empty, use those routes verbatim.

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

### Step 4: Drive the Browser (`drive`)

Mark `BROWSER_OPENED=true` after the first successful `browser_navigate` so Step 5 knows whether to call `browser_close`.

For each route in order, run the same recipe via Playwright MCP:

1. `mcp__playwright__browser_navigate` to `$DEV_URL$ROUTE`. Set `expectedStatus` to 200-399 if the tool supports it; otherwise check status from a follow-up `browser_network_requests` call.
2. `mcp__playwright__browser_wait_for` until the page is interactive (look for a stable selector — `body`, the route's `<h1>`, or a known landmark from the snapshot).
3. `mcp__playwright__browser_snapshot` — capture the accessibility tree as the canonical "did it render" check.
4. `mcp__playwright__browser_console_messages` — read messages emitted since the last navigate.
5. `mcp__playwright__browser_take_screenshot` — save a PNG named `smoke-ui-ROUTE_SLUG.png` under `$ROOT/.test-output/playwright-mcp/`. **Before the first screenshot of this run**, do the three-step setup once:

   ```bash
   mkdir -p "$ROOT/.test-output/playwright-mcp"
   # Ensure .gitignore covers the whole .test-output/ tree (append if absent —
   # never commit test artifacts).
   grep -qxF '.test-output/' "$ROOT/.gitignore" 2>/dev/null \
     || printf '\n.test-output/\n' >> "$ROOT/.gitignore"
   # Clear stale artifacts from previous runs so this report only reflects
   # the current diff. Scope the delete to smoke-ui artifacts so co-located
   # Playwright traces / videos from unrelated sessions are not touched.
   rm -f "$ROOT/.test-output/playwright-mcp"/smoke-ui-*.png
   ```

   `$ROOT/.test-output/` is the canonical local-only test-artifacts directory for hero-skills. All disposable outputs from any hero skill — Playwright screenshots, traces, videos, network logs, dev-server logs, coverage reports — land somewhere under it so the repo root stays clean and a single `.gitignore` entry covers them all.

For routes that involve a form change (detected by reading the diff: `<form>` / `useForm` / `onSubmit` added or modified), additionally:

1. `mcp__playwright__browser_fill_form` with placeholder-but-plausible values for the visible inputs (keep it under 5 inputs — refuse if the form is huge; that's a real E2E test, not a smoke test).
2. Click the submit control, `browser_wait_for` the success state, `browser_console_messages` again.

#### Console noise allowlist

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

If a future framework has its own benign-warnings set, the user must update this list explicitly via a follow-up edit to this skill — the smoke test does not silently expand its filter set.

#### Failure rules

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

On any failure: stop driving further routes, surface the failing route + the console message + the screenshot path, and exit non-zero. Do **not** auto-retry; the model is a poor judge of "transient vs real" for UI bugs.

### Step 5: Cleanup

```bash
# Close the browser session — only if Step 4 actually opened one. Skipping
# this on early-exit paths (no UI project, server failed to come up) avoids
# noisy "no session to close" errors from the MCP server.
if [ "${BROWSER_OPENED:-false}" = "true" ]; then
  mcp__playwright__browser_close
fi

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
Screenshots: $ROOT/.test-output/playwright-mcp/*.png

Result:      OK | FAILED at ROUTE — REASON

Next steps (when Result is OK):
  /simplify                    # Step 5 — tidy the dirty diff before commit
  hero-skills:commit-changes   # Step 6 — review and commit
  hero-skills:push-pr          # Step 7 — push and open a draft PR
```

If FAILED, surface:

- The failing route and the verbatim console error / status / wait-for timeout message.
- The screenshot path so the user can open it.
- The last 30 lines of `$DEV_LOG` if the failure looks server-side.
- Suggested next step: usually `hero-skills:plan-work "fix smoke-ui regression at ROUTE"`.

## Notes

- This is a **smoke** test, not a full E2E. Cap routes at 5, skip large forms, do not chase flaky tests. If a real E2E suite exists in the repo (Playwright config, Cypress, etc.), prefer running it via `hero-skills:test-changes` instead.
- The skill never modifies tracked source files. It only reads, drives, and reports — but it does write disposable local artifacts under `$ROOT/.test-output/`: screenshots in `.test-output/playwright-mcp/` (the canonical Playwright MCP artifact directory) and the dev-server log at `.test-output/dev-server.log`. `.test-output/` is the shared test-artifact directory for every hero skill; a single `.gitignore` entry covers all of it. Both Step 2 (dev-server start) and Step 4 (first screenshot) `mkdir -p` the directory and append `.test-output/` to `.gitignore` if absent, *and* clear stale artifacts from prior runs so the report only reflects the current diff.
- Console-error filtering: the framework's hot-reload / dev-mode warnings (e.g., `[HMR]`, React strict-mode double-render notices) are not failures. Match conservatively: if in doubt about whether a message is real, surface it as a warning rather than a hard fail, and let the user decide.
