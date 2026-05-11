---
name: one-shot
# prettier-ignore
description: Drive a small task end-to-end — plan, implement, test, commit, push draft, self-review, respond to bots, auto-approve, merge, reset. Use only for small, low-risk PRs.
argument-hint: ISSUE_ID_OR_DESCRIPTION [additional-context]
disable-model-invocation: true
---

# One-Shot — Ticket to Merged PR in a Single Pipeline

Take a small task from a ticket (or plain description) all the way through to a merged PR and a clean local checkout, by chaining the existing hero skills in order. This is the orchestrator for **Pipeline 2** in `PIPELINES.md`.

> **Scope guard:** one-shot is for small, low-risk PRs only. If, during planning, the change looks larger than a single focused diff (multiple subsystems, schema changes, breaking API changes, anything you would normally split into a stack), STOP after the `plan` step and tell the user to fall back to running the individual skills. Do NOT push a large PR through unattended automation.

## Pipeline DAG

```
plan → implement → test → e2e → commit → push-draft → self-review → respond → ship
```

Print this line at the start of every step, marking progress:

```
[N/9] (✓) plan → (✓) implement → (✓) test → (▶) e2e → ( ) commit → ( ) push-draft → ( ) self-review → ( ) respond → ( ) ship

Now running: e2e
```

When a step is skipped (e.g., `e2e` on a backend-only PR with no UI project in HERO.md, or `respond` if the repo has no review bot configured), use `(–)` and continue. When the user declines a gate (mark-ready, merge) or a smoke test fails, use `(✗)` and stop.

## Arguments

- `$ARGUMENTS` — Same as `hero-skills:plan-work`: an issue ID (e.g., `PROJ-123`) or a plain-text description. Required.

## Prerequisites

- `gh` CLI installed and authenticated
- `HERO.md` exists (run `hero-skills:init-hero` first if not)
- `.github/workflows/auto-approve.yml` is on the default branch (Step 9 needs it). If missing, run `hero-skills:init-hero --update` to install it (Step 6a of init-hero handles this), then merge that workflow file to the default branch before running one-shot.
- For UI projects: Playwright MCP available so Step 4 (`e2e`) can drive the dev server. (Backend-only PRs skip Step 4 with `(–)`.)
- The task is small — see scope guard above

## Cross-step contract

Every chained skill in this orchestrator can fail in the middle of a long
session. Before deciding to advance to the next step, you MUST:

1. Read the child skill's reported state — last bash exit code, the verdict
   it printed, and any "STOP" / "Stopped:" lines. Do NOT infer success from
   the absence of an error.
2. Echo a one-line "Step N result:" summary to the user with what just
   happened and what you intend to do next.
3. If the child skill stopped, render the pipeline DAG with `(✗)` on the
   failed node and a `Stopped: REASON` line per `PIPELINES.md`, then halt.
   Never auto-advance past a `(✗)`.
4. **DAG state preservation.** Every "Render DAG with X active" instruction
   below means: render the line with steps before `RESUME_STEP` marked `(✓)`
   only when `RESUME_STEP` was set in Step 0.5 to a value that genuinely
   completed those steps in a prior session. For a fresh-start invocation
   (`RESUME_STEP=1`), prior-step markers are absent. For a manual override
   chosen at the Step 0.5 prompt, prior-step markers are `( )`, not `(✓)` —
   the override path makes no claim that earlier work happened. The current
   step is `(▶)`; later steps are `( )` until they run; skipped steps are
   `(–)`; failed/declined steps are `(✗)`.

Apply this contract at every Step 1–9 transition below (or every transition from `RESUME_STEP` onward when resuming).

## Instructions

### Step 0: Load Hero Configuration and Confirm Scope

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

If `HERO.md` is missing, STOP and tell the user to run `hero-skills:init-hero` first. one-shot relies on every downstream skill having a config to read; running blind through 9 steps is unsafe.

### Step 0.4: Auto-branch off Default Branch (if needed)

one-shot never works on the default branch. If we're on it with any uncommitted files or unpushed local commits, branch off automatically — **no prompt** — so the rest of the pipeline has a feature branch to commit and push to. This runs before resume detection so Step 0.5 always sees a feature-branch state.

```bash
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
CURRENT_BRANCH=$(git branch --show-current)

UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)

if [ "$CURRENT_BRANCH" = "$DEFAULT_BRANCH" ] && { [ "${UNCOMMITTED:-0}" -gt 0 ] || [ "${AHEAD:-0}" -gt 0 ]; }; then
  # SUGGESTED_BRANCH derivation (see "Naming rules" below). The user can rename later if needed.
  echo "On $DEFAULT_BRANCH with $UNCOMMITTED uncommitted file(s) and $AHEAD unpushed commit(s)."
  echo "Auto-branching to '$SUGGESTED_BRANCH' (one-shot never works on $DEFAULT_BRANCH)."
  git checkout -b "$SUGGESTED_BRANCH"
  CURRENT_BRANCH="$SUGGESTED_BRANCH"
fi
```

**Naming rules** (no prompt — derive a sensible name and proceed):

- `$ARGUMENTS` starts with an issue ID like `PROJ-123`: use `PROJ-123-SLUG_FROM_REST` (or just `PROJ-123` if nothing follows).
- `$ARGUMENTS` is plain text: use `feat/SLUG`, `fix/SLUG`, `refactor/SLUG`, or `chore/SLUG`, picking the prefix from verbs in the description (`add/create/implement` → feat, `fix/repair/resolve` → fix, `refactor/clean/restructure` → refactor, `update/bump/upgrade` → chore). Slug is lowercased, hyphenated, ≤50 chars, with filler words stripped.
- `$ARGUMENTS` is empty: derive from the diff via `git diff --stat HEAD` — pick the most-changed top-level directory plus a 2–3 word summary, e.g. `feat/store-trust-tier`.

**On `AHEAD > 0`:** `git checkout -b` carries the local default-branch commits onto the feature branch, but the local default branch will still point at them (origin/`$DEFAULT_BRANCH` will not, until the resulting PR merges). Print one line so the user knows:

```
Note: $AHEAD local commit(s) on $DEFAULT_BRANCH are now on $SUGGESTED_BRANCH.
$DEFAULT_BRANCH still points at them locally. After this PR merges, switch back
and `git pull` to align with origin.
```

Do NOT silently reset `$DEFAULT_BRANCH` — that is destructive and out of scope here.

### Step 0.5: Detect Resume Point

Before doing anything destructive, read the current git/PR state and figure out where in the pipeline this invocation should pick up. Users often hit `hero-skills:one-shot` after they've already done some of the work — possibly in a previous session — and the orchestrator should never silently re-do completed steps.

```bash
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}

CURRENT_BRANCH=$(git branch --show-current)

# A failed fetch silently makes AHEAD/UPSTREAM judgments wrong (offline,
# auth expired, network blip). Surface the failure rather than fall through.
FETCH_OK=true
if ! git fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1; then
  FETCH_OK=false
  echo "WARN: 'git fetch origin $DEFAULT_BRANCH' failed — origin/$DEFAULT_BRANCH may be stale."
  echo "      Resume detection will refuse rows that depend on AHEAD or remote PR state."
  echo "      Fix the network/auth issue and re-run, or fall back to running the individual skills."
fi

UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)

# UNPUSHED counts commits past the branch's *upstream* (the PR's head ref),
# not past origin/$DEFAULT_BRANCH. Distinct from AHEAD: a user who pushed
# once and then made local follow-up commits has AHEAD>0 AND UNPUSHED>0;
# we must push those follow-ups before any review/respond/ship step.
#
# When no upstream is configured yet (common before the first push),
# `git rev-list --count '@{u}..HEAD'` errors silently and would yield 0,
# which would route the user past Step 6 (push-draft) and skip the
# initial push entirely. Detect that case explicitly and fall back to
# AHEAD — every commit past the default branch needs a push.
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  UNPUSHED=$(git rev-list --count '@{u}..HEAD' 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
else
  UNPUSHED=$AHEAD
fi

# gh pr list silently returns "[]" if no PR exists OR if gh fails — distinguish
# the two by checking the exit code separately so empty PR_* values don't
# masquerade as "no PR" when the real cause is a transient API failure.
GH_OK=true
if ! PR_LIST=$(gh pr list --head "$CURRENT_BRANCH" \
  --json number,url,isDraft,reviewDecision,state 2>/dev/null); then
  GH_OK=false
  echo "WARN: 'gh pr list' failed — cannot read PR state for resume detection."
  PR_LIST="[]"
fi
PR_JSON=$(printf '%s' "$PR_LIST" | jq -r '.[0] // empty')
PR_NUMBER=$(printf '%s' "$PR_JSON" | jq -r '.number // empty')
PR_STATE=$(printf '%s' "$PR_JSON" | jq -r '.state // empty')           # OPEN | CLOSED | MERGED | ""
PR_IS_DRAFT=$(printf '%s' "$PR_JSON" | jq -r '.isDraft // empty')      # "true" | "false" | ""
PR_REVIEW=$(printf '%s' "$PR_JSON" | jq -r '.reviewDecision // empty') # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ""

PR_EXISTS=false
[ -n "$PR_NUMBER" ] && PR_EXISTS=true

# Check for the durable Hero Self-Review marker so we know review-pr ran.
# Surface API failures rather than fall through to "0 → re-review".
SELF_REVIEW_DONE=0
BOT_REPLIED=false
if [ "$PR_EXISTS" = "true" ]; then
  if ! COMMENTS=$(gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" 2>/dev/null); then
    echo "note: gh api comments fetch failed; treating SELF_REVIEW_DONE/BOT_REPLIED as unknown."
  else
    SELF_REVIEW_DONE=$(printf '%s' "$COMMENTS" \
      | jq '[.[] | select(.body | test("Hero Self-Review"; "i"))] | length')
    BOT_USER=$(awk -F': ' '/^- bot-username:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null \
      | tr -d '[:space:]"'"'"'')
    if [ -n "$BOT_USER" ]; then
      BOT_COUNT=$(printf '%s' "$COMMENTS" \
        | jq "[.[] | select(.user.login == \"$BOT_USER\")] | length")
      [ "${BOT_COUNT:-0}" -gt 0 ] && BOT_REPLIED=true
    fi
  fi
fi
```

Use the decision tree below to pick the **resume step** (1–9). Each row is the first that matches top-to-bottom; rows below the line require `PR_EXISTS=true` so empty PR_* values can't accidentally match.

| Condition | Resume at | Reason |
|-----------|-----------|--------|
| `FETCH_OK=false` OR `GH_OK=false` | exit with diagnostic | resume rows depend on remote state — fix network/auth and re-run, or invoke individual skills |
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED == 0` | exit | nothing to do |
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED > 0` | exit with hint | merged/closed PR but local edits exist — branch off `DEFAULT_BRANCH` for follow-up work |
| `CURRENT_BRANCH == DEFAULT_BRANCH` and `UNCOMMITTED == 0` and `AHEAD == 0` | Step 1 (plan) | fresh start (Step 0.4 already auto-branched if there was any work to preserve) |
| Feature branch, `UNCOMMITTED > 0` | Step 3 (test) | mid-implement; re-run test + e2e on the latest diff before committing. If a PR is already open and non-draft, Step 6 will push the new commit to it. |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED > 0` | Step 6 (push-draft) | committed but not pushed (covers both the "no PR yet" case and the "pushed-once + local follow-up" case). After push-draft updates the PR, advance to Step 7 normally. |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "true"`, `SELF_REVIEW_DONE == 0` | Step 7 (self-review) | PR up but never reviewed |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "true"`, `SELF_REVIEW_DONE >= 1` | Step 7 (self-review, already-ran branch) | re-review or mark ready — `review-pr` handles the "already self-reviewed once" case itself |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW != APPROVED`, `BOT_REPLIED=false` | Step 8 (respond — bot wait) | ready PR, no bot reply yet — Step 8's poll will wait |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW != APPROVED`, `BOT_REPLIED=true` | Step 8 (respond) | bot has commented, run respond-to-pr |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW == APPROVED` | Step 9 (ship) | go straight to auto-approve + merge |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=false`, `AHEAD == 0` | exit with hint | branch has no work — suggest fresh `hero-skills:plan-work` |
| any other combination | exit with diagnostic | unrouted state — print the detected variables and exit; user falls back to individual skills |

**Default for non-default branches:** when on a feature branch, one-shot resumes that branch. `$ARGUMENTS` is treated as additional context for the in-progress work. To start a *new* ticket from `$DEFAULT_BRANCH` instead, switch back to `$DEFAULT_BRANCH` first and re-run.

**No confirmation prompt.** Announce the detected state and the inferred resume point, then proceed straight into that step. Do NOT ask the user to confirm or pick an override — broken states already exit with a diagnostic above; everything else routes deterministically.

```
hero-skills:one-shot — resuming from detected state

Branch:        feat/foo (not default)
Uncommitted:   2 files
Unpushed:      3 commits ahead of origin/main
PR:            #42 (draft, 0 reviews)

Inferred resume point: Step 7 (self-review)

[7/9] (✓) plan → (✓) implement → (✓) test → (✓) e2e → (✓) commit → (✓) push-draft → (▶) self-review → ( ) respond → ( ) ship

Reasoning: branch + unpushed commits + open draft PR + no Hero Self-Review
comment yet → plan/implement/test/e2e/commit/push-draft are done; running
self-review next.

Hard stops (these halt the pipeline mid-flight when triggered — not asked up front):
  - Plan looks too large for a single PR (Step 1 scope check)
  - test-changes fails and the failure needs design judgment
  - smoke-ui flags a UI regression on a changed route
  - You decline review-pr's mark-ready prompt
  - Auto-approve returns REQUEST_CHANGES and the fixes are non-trivial
  - You decline ship-pr's merge prompt
```

Set `RESUME_STEP` to the inferred value and run that step immediately. The Cross-step contract still applies for every step from `RESUME_STEP` onward — read each child skill's reported state before advancing.

When `RESUME_STEP > 1`, render the DAG with steps before `RESUME_STEP` marked `(✓)` so the visual model stays accurate.

> **Resume rule for Steps 1–9:** execute steps starting from `RESUME_STEP`. Earlier steps render as `(✓)` in the DAG **but are NOT re-executed** — do not call `plan-work`, `test-changes`, etc. for those. The first DAG render of the run shows `RESUME_STEP` as `(▶)`. Examples:
>
> - `RESUME_STEP=1` (fresh start) → run every step in order.
> - `RESUME_STEP=7` (resuming at self-review on an open draft PR) → skip Steps 1–6 entirely; render `[7/9] (✓) plan → (✓) implement → (✓) test → (✓) e2e → (✓) commit → (✓) push-draft → (▶) self-review → ( ) respond → ( ) ship`; start running at Step 7.

### Step 1: plan

Render the DAG with `plan` as the active step:

```
[1/9] (▶) plan → ( ) implement → ( ) test → ( ) e2e → ( ) commit → ( ) push-draft → ( ) self-review → ( ) respond → ( ) ship

Now running: plan
```

Run `hero-skills:plan-work "$ARGUMENTS"`. This handles ticket fetch (Linear/Jira/GitHub Issues), branch creation, and a Plan-Mode draft.

**Scope check after planning.** Read the plan output. If any of the following holds, STOP and hand back to the user:

- Touches >5 files across unrelated subsystems
- Adds or changes a public API contract / DB schema / CI workflow
- Plan has an "out-of-scope follow-up" list with non-trivial items
- The user did not approve the plan in Plan Mode

Otherwise continue.

### Step 2: implement

Render DAG with `implement` active. Implement the plan inline (Plan Mode exits naturally into implementation, same as `plan-work` Step 5).

After implementation, **always run a quick self-review-of-the-diff before moving on** — but do NOT run the full `review-pr` agent suite yet (that happens in Step 6 against the open PR). At minimum:

- `git status` — confirm only intended files changed
- `git diff` — read every line; reject sloppy edits
- Verify the change matches the plan; flag deviations to the user

### Step 3: test

Render DAG with `test` active. Run `hero-skills:test-changes`.

If tests fail with a quick, mechanical fix (lint, typo, import order), apply the fix and re-run. If they fail in a way that needs design judgment (test asserting wrong behavior, integration breakage, flaky CI), STOP and hand back.

### Step 4: e2e

Render DAG with `e2e` active. Run `hero-skills:smoke-ui`. The skill itself decides whether to drive the browser: if HERO.md declares no UI project (no `framework: next | vite | remix | …`), it exits immediately and one-shot must render `(–) e2e` per `PIPELINES.md` semantics and continue to Step 5.

If `smoke-ui` flags a regression — a 4xx/5xx on a changed route, an uncaught console error, a `wait_for` timeout — render `(✗) e2e` plus `Stopped: smoke-ui regression on ROUTE` and hand back. Do not advance to commit; we never want a known UI regression in git history if we can help it.

> **Resume caveat:** when one-shot resumes at Step 5 or later (the test+e2e steps were already done in a prior session), the smoke result reflects the diff at *that earlier* HEAD, not the current state. Step 0.5's table forces re-entry at Step 3 whenever `UNCOMMITTED > 0`, which covers mid-implement diffs. But a resume at Step 6 (push-draft, after a follow-up commit landed elsewhere) does *not* re-smoke. If you want a fresh smoke before pushing, override to Step 4 at the Step 0.5 prompt.

The smoke is intentionally narrow (≤5 routes, no large forms). For deeper coverage, run a real E2E suite via `hero-skills:test-changes` instead.

### Step 5: commit

Render DAG with `commit` active. Run `hero-skills:commit-changes`. Trust its grouping logic — do not skip pre-commit hooks.

### Step 6: push-draft

Render DAG with `push-draft` active. Run `hero-skills:push-pr` (no arguments — defaults to a draft PR). Capture the PR number from its output for downstream steps.

### Step 7: self-review

Render DAG with `self-review` active. Run `hero-skills:review-pr` (no arguments — auto-detects your draft PR and runs the pr-review-toolkit agents in parallel, applies fixes, and asks before marking ready).

This is a **hard gate**: `review-pr` will ask before marking the PR ready. If the user declines, STOP. Do not bypass — auto-approve in Step 9 refuses draft PRs anyway.

### Step 8: respond

Render DAG with `respond` active. If `HERO.md` declares a Code Review Agent (CodeRabbit, Greptile, Copilot review, etc.), poll the PR comments for the bot's first comment for **up to 60 seconds total, polling every 15 seconds**. If the bot has not posted by then, proceed to Step 9 (auto-approve will gate on unresolved threads anyway). If the bot has posted, run `hero-skills:respond-to-pr` to address its inline comments and resolve threads.

```bash
BOT_USER=$(awk -F': ' '/^- bot-username:/ {print $2; exit}' "$ROOT/HERO.md" \
  | tr -d '[:space:]"'"'"'')
# PR_NUMBER comes from Step 5's push-pr output. Re-derive owner/repo from gh
# in case earlier steps did not export them.
PR_NUMBER=${PR_NUMBER:-$(gh pr list --head "$(git branch --show-current)" \
  --json number --jq '.[0].number')}
OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')
DEADLINE=$((SECONDS + 60))
BOT_COMMENT=""
while (( SECONDS < DEADLINE )); do
  BOT_COMMENT=$(gh api "/repos/$OWNER_REPO/issues/$PR_NUMBER/comments" \
    --jq "[.[] | select(.user.login == \"$BOT_USER\")] | first.id // empty")
  [ -n "$BOT_COMMENT" ] && break
  sleep 15
done
```

If no review bot is configured (`agent: none`), mark this step `(–)` and skip to Step 9.

If the bot's feedback exceeds a small set of trivial fixes, render `(✗) respond` plus `Stopped: bot feedback non-trivial — escalate to a human reviewer` per `PIPELINES.md` skip/error semantics, and halt. Do not advance to Step 9.

### Step 9: ship

Render DAG with `ship` active. Run `hero-skills:ship-pr`. This:

1. Checks the auto-approve gates (prior review present, no unresolved threads, no active CHANGES_REQUESTED, no unanswered reviewer questions).
2. Posts `@auto-approve` and waits for the verdict.
3. On APPROVE, asks before merging. The user must say `y`.
4. After merge, switches to the default branch, pulls latest, and deletes the merged head branch (remote + local).

If auto-approve returns REQUEST_CHANGES or WORKFLOW_FAILED, STOP. The user should run `hero-skills:respond-to-pr` again or fix the workflow before re-attempting.

### Step 9: Summary

After ship-pr completes successfully, print the final pipeline DAG and a one-shot summary:

```
[9/9] (✓) plan → (✓) implement → (✓) test → (✓) e2e → (✓) commit → (✓) push-draft → (✓) self-review → (✓) respond → (✓) ship

One-Shot Summary
================
Task:        ISSUE_ID — TASK_TITLE
PR:          #PR_NUMBER — PR_TITLE
Branch:      PR_BRANCH (deleted) → DEFAULT_BRANCH
Merged:      MERGE_SHA
Duration:    HH:MM (from Step 1 start to Step 9 finish)

You're on DEFAULT_BRANCH with the merge pulled.

Next:
  hero-skills:one-shot NEXT_TICKET   # next small task
  /clear                              # fresh context first
```

If the pipeline stopped early, render the DAG with `(✗)` on the failed step, the reason, and the recommended skill to resume from manually.

## Notes

- This skill **does not skip user gates**. Plan approval, mark-ready, merge confirmation are all explicit. Auto mode does not change that.
- This skill **does not retry** on judgment-call failures (test design, large bot feedback). Retrying without human input is how small PRs become broken merges.
- For larger work, run the same skills individually so you can pause between them.
- Run `hero-skills:reset-branch` separately if you abandon mid-pipeline — ship-pr's reset only fires after a successful merge.
