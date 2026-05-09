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
plan → implement → test → commit → push-draft → self-review → respond → ship
```

Print this line at the start of every step, marking progress:

```
[N/8] (✓) plan → (✓) implement → (▶) test → ( ) commit → ( ) push-draft → ( ) self-review → ( ) respond → ( ) ship

Now running: test
```

When a step is skipped (e.g., `respond` if the repo has no review bot configured), use `(–)` and continue. When the user declines a gate (mark-ready, merge), use `(✗)` and stop.

## Arguments

- `$ARGUMENTS` — Same as `hero-skills:plan-work`: an issue ID (e.g., `PROJ-123`) or a plain-text description. Required.

## Prerequisites

- `gh` CLI installed and authenticated
- `HERO.md` exists (run `hero-skills:init-hero` first if not)
- `.github/workflows/auto-approve.yml` is on the default branch (Step 8 needs it). If missing, run `hero-skills:init-hero --update` to install it (Step 6a of init-hero handles this), then merge that workflow file to the default branch before running one-shot.
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

Apply this contract at every Step 1–8 transition below.

## Instructions

### Step 0: Load Hero Configuration and Confirm Scope

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

HERO_TIME=$(git log -1 --format=%ct -- HERO.md 2>/dev/null || echo 0)
CONFIG_TIME=$(git log -1 --format=%ct -- \
  pyproject.toml package.json go.mod Cargo.toml \
  .github/workflows .pre-commit-config.yaml \
  CLAUDE.md Makefile justfile Taskfile.yml 2>/dev/null || echo 0)
if [ "${CONFIG_TIME:-0}" -gt "${HERO_TIME:-0}" ]; then
  echo "note: HERO.md may be out of date — run hero-skills:init-hero --update to refresh."
fi
```

If `HERO.md` is missing, STOP and tell the user to run `hero-skills:init-hero` first. one-shot relies on every downstream skill having a config to read; running blind through 8 steps is unsafe.

Confirm with the user before starting:

```
hero-skills:one-shot will run 8 chained steps end-to-end:
  plan → implement → test → commit → push-draft → self-review → respond → ship

Stop conditions (any of these aborts and hands control back to you):
  - The plan looks too large for a single PR
  - test-changes fails and the failure is not a quick fix
  - You decline to mark the PR ready for review
  - Auto-approve returns REQUEST_CHANGES and the fixes are non-trivial
  - You decline to merge

Continue? [y/N]
```

Wait for explicit `y` before running anything.

### Step 1: plan

Render the DAG with `plan` as the active step:

```
[1/8] (▶) plan → ( ) implement → ( ) test → ( ) commit → ( ) push-draft → ( ) self-review → ( ) respond → ( ) ship

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

### Step 4: commit

Render DAG with `commit` active. Run `hero-skills:commit-changes`. Trust its grouping logic — do not skip pre-commit hooks.

### Step 5: push-draft

Render DAG with `push-draft` active. Run `hero-skills:push-pr` (no arguments — defaults to a draft PR). Capture the PR number from its output for downstream steps.

### Step 6: self-review

Render DAG with `self-review` active. Run `hero-skills:review-pr` (no arguments — auto-detects your draft PR and runs the pr-review-toolkit agents in parallel, applies fixes, and asks before marking ready).

This is a **hard gate**: `review-pr` will ask before marking the PR ready. If the user declines, STOP. Do not bypass — auto-approve in Step 8 refuses draft PRs anyway.

### Step 7: respond

Render DAG with `respond` active. If `HERO.md` declares a Code Review Agent (CodeRabbit, Greptile, Copilot review, etc.), poll the PR comments for the bot's first comment for **up to 60 seconds total, polling every 15 seconds**. If the bot has not posted by then, proceed to Step 8 (auto-approve will gate on unresolved threads anyway). If the bot has posted, run `hero-skills:respond-to-pr` to address its inline comments and resolve threads.

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

If no review bot is configured (`agent: none`), mark this step `(–)` and skip to Step 8.

If the bot's feedback exceeds a small set of trivial fixes, render `(✗) respond` plus `Stopped: bot feedback non-trivial — escalate to a human reviewer` per `PIPELINES.md` skip/error semantics, and halt. Do not advance to Step 8.

### Step 8: ship

Render DAG with `ship` active. Run `hero-skills:ship-pr`. This:

1. Checks the auto-approve gates (prior review present, no unresolved threads, no active CHANGES_REQUESTED, no unanswered reviewer questions).
2. Posts `@auto-approve` and waits for the verdict.
3. On APPROVE, asks before merging. The user must say `y`.
4. After merge, switches to the default branch, pulls latest, and deletes the merged head branch (remote + local).

If auto-approve returns REQUEST_CHANGES or WORKFLOW_FAILED, STOP. The user should run `hero-skills:respond-to-pr` again or fix the workflow before re-attempting.

### Step 9: Summary

After ship-pr completes successfully, print the final pipeline DAG and a one-shot summary:

```
[8/8] (✓) plan → (✓) implement → (✓) test → (✓) commit → (✓) push-draft → (✓) self-review → (✓) respond → (✓) ship

One-Shot Summary
================
Task:        ISSUE_ID — TASK_TITLE
PR:          #PR_NUMBER — PR_TITLE
Branch:      PR_BRANCH (deleted) → DEFAULT_BRANCH
Merged:      MERGE_SHA
Duration:    HH:MM (from Step 1 start to Step 8 finish)

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
