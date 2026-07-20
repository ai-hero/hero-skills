---
name: one-shot
# prettier-ignore
description: Drive a small task end-to-end — plan, implement, simplify, push (tests included), self-review, mark ready, await review, respond, ship. No args: resume the current goal (gated). Small, low-risk PRs only.
argument-hint: "[ISSUE_ID [additional-context] | DESCRIPTION]"
disable-model-invocation: true
---

# One-Shot — Ticket to Merged PR in a Single Pipeline

Take a small task from a ticket (or plain description) — or, **without arguments**, the current in-progress goal — all the way through to a merged PR and a clean local checkout, by chaining the existing hero skills in order. This is the orchestrator for **Pipeline 2** in `PIPELINES.md`.

> **Scope guard:** one-shot is for small, low-risk PRs only — **one work-item, one PR**. If the `plan` step resolves or produces more than one work-item, or the item is flagged `one_way_door: true`, STOP and hand back to the user (Step 1e). Do NOT push a large PR through unattended automation.

## Pipeline DAG

```
plan → implement → simplify → push → self-review → mark-ready → await-review → respond → ship
```

Testing is not a separate node: `push` delegates to `hero-skills:push-pr`, whose Step 2 test phase (verification + UI smoke, absorbed from the former `test-changes` skill) runs before anything is committed.

Print this line at the start of every step, marking progress:

```
[N/9] (✓) plan → (✓) implement → (▶) simplify → ( ) push → ( ) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship

Now running: simplify
```

When a step is skipped (e.g., `await-review`/`respond` if the repo has no review bot configured), use `(–)` and continue. When the user declines a gate (mark-ready, merge) or push-pr's test phase flags a UI smoke regression, use `(✗)` and stop.

### Step → skill mapping

Each DAG node delegates to a single skill (or runs inline when the work is just a poll / a user gate). Run any of these standalone when you don't want the whole pipeline:

| # | Step | Skill to run standalone |
|---|------|-------------------------|
| 1 | `plan` | `hero-skills:think-it-through` (only when nothing resolves from `my-work/` or the tracker) |
| 2 | `implement` | inline (executes the resolved work-item) |
| 3 | `simplify` | `/simplify` (external skill) |
| 4 | `push` | `hero-skills:push-pr` (tests — verification + UI smoke — then commits + pushes a draft PR) |
| 5 | `self-review` | `hero-skills:review-pr --no-mark-ready` |
| 6 | `mark-ready` | `hero-skills:review-pr`'s own Step 9 gate, or `gh pr ready` |
| 7 | `await-review` | inline poll (no separate skill) |
| 8 | `respond` | `hero-skills:respond-to-comments` |
| 9 | `ship` | `hero-skills:ship-pr` |

## Arguments

- `$ARGUMENTS` — Optional. An issue ID (e.g., `PROJ-123`), fetched via the Linear MCP, or a plain-text description of the task, plus optional additional context.
  - **With arguments** — start work on that ticket/description; on a feature branch with work in flight, arguments are additional context (see Step 0.5's "Default for non-default branches").
  - **Without arguments** — finish the **current goal**: Step 0.5 detects the in-progress state and resumes the pipeline from the inferred step, through `ship`'s merge and reset to the default branch. Step 0.5's decision table is the single source of truth for that routing — states with nothing left to resume exit with a hint or diagnostic per the table, and a truly fresh start on the default branch reaches Step 1, which asks what to plan.

## Prerequisites

- **GitHub CLI (`gh`) installed and authenticated with the `repo` scope**. Steps 4 (push), 5 (self-review), 8 (respond), and 9 (ship) all fail without it. Install via `brew install gh` (macOS), `sudo apt install gh` (Debian/Ubuntu), or <https://cli.github.com/>. Authenticate with `gh auth login -s repo`.
- `HERO.md` exists (run `hero-skills:init-hero` first if not)
- `.github/workflows/auto-approve.yml` is on the default branch (Step 9 needs it). If missing, run `hero-skills:init-hero --update` to install it (Step 6a of init-hero handles this), then merge that workflow file to the default branch before running one-shot.
- **`pr-review-toolkit` plugin installed** so Step 5 (`self-review`) gets all six review agents — five from the plugin plus the security pass, which needs no extra install. From inside Claude Code: `/plugin install pr-review-toolkit`. From a shell: `claude plugins add pr-review-toolkit@claude-plugins-official`. Without it, `hero-skills:review-pr` runs with a thinner review.
- **Playwright MCP server registered** so Step 4 (`push`)'s test phase can drive the dev server for UI smoke. Requires Node.js 18+. Run `claude mcp add playwright npx @playwright/mcp@latest` (add `--scope user` to share across projects, `--scope project` to commit it). Backend-only PRs skip the UI-smoke portion of the test phase with `(–)` even without this.
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
   only when Step 0.5 inferred `RESUME_STEP` from a state that genuinely
   completed those steps in a prior session. For a fresh-start invocation
   (`RESUME_STEP=1`), prior-step markers are absent. The current step is
   `(▶)`; later steps are `( )` until they run; skipped steps are `(–)`;
   failed/declined steps are `(✗)`.

Apply this contract at every Step 1–9 transition below (or every transition from `RESUME_STEP` onward when resuming).

## Instructions

### Step 0: Load Hero Configuration and Confirm Scope

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Stale-HERO check — fast subset of the plugin's check-hero-staleness.sh.
# Keep aligned with the copy in push-pr.
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

### Step 0.3: Pre-flight Checks

Before auto-branching or any other destructive work, run the full pre-flight to catch failures that would otherwise only surface at Step 4 (push), Step 5 (self-review), or Step 9 (ship) — after you've already done the work.

```bash
# DEFAULT_BRANCH is needed *here* — Step 0.4 sets it too, but the
# committed-diff lookup below runs before Step 0.4 in a fresh shell.
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}

PREFLIGHT="${CLAUDE_PLUGIN_ROOT:-$ROOT/.claude/plugins/hero-skills}/scripts/preflight.sh"
[ -x "$PREFLIGHT" ] || PREFLIGHT="$ROOT/.claude/plugins/hero-skills/scripts/preflight.sh"
[ -x "$PREFLIGHT" ] || PREFLIGHT="$HOME/.claude/plugins/hero-skills/scripts/preflight.sh"

# Scope runtime checks to the projects touched by the diff (uncommitted +
# committed-but-unpushed). On a truly fresh start (default branch, clean
# tree, nothing ahead) there's nothing to runtime-check yet — skip the
# bucket entirely; Step 1 will re-run preflight with proper scope once
# files start changing.
CHANGED_PATHS=$( { git -C "$ROOT" diff --name-only HEAD 2>/dev/null;
                   git -C "$ROOT" diff --name-only "origin/$DEFAULT_BRANCH...HEAD" 2>/dev/null;
                 } | awk -F/ 'NF > 1 {print $1}' | sort -u | paste -sd, -)

if [ -z "$CHANGED_PATHS" ] \
   && [ "$(git -C "$ROOT" branch --show-current)" = "$DEFAULT_BRANCH" ] \
   && [ -z "$(git -C "$ROOT" status --porcelain)" ]; then
  "$PREFLIGHT" --bucket tooling
  RC1=$?
  "$PREFLIGHT" --bucket repo
  RC2=$?
  "$PREFLIGHT" --bucket pipeline
  RC3=$?
  PREFLIGHT_RC=$(( RC1 | RC2 | RC3 ))
else
  PROJECT_ARGS=()
  [ -n "$CHANGED_PATHS" ] && PROJECT_ARGS=(--projects "$CHANGED_PATHS")
  "$PREFLIGHT" --bucket all "${PROJECT_ARGS[@]}"
  PREFLIGHT_RC=$?
fi
```

If `PREFLIGHT_RC` is non-zero, **STOP**. Print the recommended fix from each `[BLOCKER]` line (the script prints these inline) and do not advance to Step 0.4 — every blocker is something that would have failed a later step on a half-finished branch.

If `PREFLIGHT_RC` is zero but the script printed `[WARN]` lines, surface them to the user once and continue. Warnings are advisory — the user can choose to fix them or proceed.

### Step 0.4: Auto-branch off Default Branch (if needed)

one-shot never works on the default branch. If we're on it with any uncommitted files or unpushed local commits, branch off automatically — **no prompt** — so the rest of the pipeline has a feature branch to commit and push to. This runs before resume detection so Step 0.5 sees a feature-branch state whenever there is work to preserve.

First, **derive `SUGGESTED_BRANCH` as a reasoning step** per the Naming rules below — this is a model task, not a shell function. Inspect `$ARGUMENTS` (and the diff if `$ARGUMENTS` is empty) and produce a concrete, non-empty branch name. Then run the snippet below with that value exported in the environment. The snippet asserts the variable is set; it will not invent one.

```bash
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
CURRENT_BRANCH=$(git branch --show-current)

# Fetch origin so AHEAD reflects current remote state. Step 0.5 below does its
# own fetch — that one is the canonical FETCH_OK source for resume-detection
# guards; this fetch is for AHEAD freshness. Both are intentional and read the
# same origin/$DEFAULT_BRANCH ref; the second call is a no-op when the first
# succeeded.
git fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || true

UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)

if [ "$CURRENT_BRANCH" = "$DEFAULT_BRANCH" ] && { [ "${UNCOMMITTED:-0}" -gt 0 ] || [ "${AHEAD:-0}" -gt 0 ]; }; then
  # Refuse to branch out of a half-resolved merge / cherry-pick / rebase —
  # `git checkout -b` would silently abort or carry conflict markers forward.
  if [ -e .git/MERGE_HEAD ] || [ -e .git/CHERRY_PICK_HEAD ] \
     || [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    echo "ERROR: a merge / cherry-pick / rebase is in progress. Resolve it, then re-run one-shot."
    exit 1
  fi

  # SUGGESTED_BRANCH must already be set by the reasoning step above. Empty
  # or unset is a hard error — `${VAR:?msg}` aborts the shell with the given
  # message rather than silently running `git checkout -b ""`.
  : "${SUGGESTED_BRANCH:?SUGGESTED_BRANCH must be derived per the Naming rules before this snippet runs.}"

  echo "On $DEFAULT_BRANCH with $UNCOMMITTED uncommitted file(s) and $AHEAD unpushed commit(s)."
  echo "Auto-branching to '$SUGGESTED_BRANCH' (one-shot never works on $DEFAULT_BRANCH)."

  if ! git checkout -b "$SUGGESTED_BRANCH"; then
    echo "ERROR: 'git checkout -b $SUGGESTED_BRANCH' failed (likely a name collision)."
    echo "       Pick a different name and re-run, or 'git checkout' the existing branch first."
    exit 1
  fi
  CURRENT_BRANCH="$SUGGESTED_BRANCH"

  # When AHEAD > 0 the local $DEFAULT_BRANCH ref still points at those commits
  # (origin/$DEFAULT_BRANCH does not, until the PR merges). Surface this so
  # the user isn't surprised when they switch back later.
  if [ "${AHEAD:-0}" -gt 0 ]; then
    echo ""
    echo "Note: $AHEAD local commit(s) on $DEFAULT_BRANCH are now on $SUGGESTED_BRANCH."
    echo "The local $DEFAULT_BRANCH ref still points at those commits. After this PR"
    echo "merges, switch back and 'git pull' to align with origin."
  fi
fi
```

**Naming rules** (no prompt — derive a sensible name and proceed). Rules are checked in order; the first match wins.

1. `$ARGUMENTS` matches `^[A-Z][A-Z0-9]{1,9}-[0-9]+(\s|$)` (an issue ID anchored to the start): use `PROJ-123-SLUG_FROM_REST` — slug derived from whatever follows the ID; just `PROJ-123` if nothing follows. The match must be at position 0, so `Fix CVE-2024-1234 in auth` does **not** match this rule and falls through to rule 2.
2. `$ARGUMENTS` is plain text (non-empty, no leading issue ID): use `feat/SLUG`, `fix/SLUG`, `refactor/SLUG`, `chore/SLUG`, or `docs/SLUG`, picking the prefix from verbs in the description (`add/create/implement` → feat, `fix/repair/resolve` → fix, `refactor/clean/restructure` → refactor, `update/bump/upgrade` → chore, `document/explain` → docs). Slug is lowercased, hyphenated, ≤50 chars, with filler words stripped.
3. `$ARGUMENTS` is empty: derive from the diff. Use the union of committed-but-unpushed changes (`git log origin/$DEFAULT_BRANCH..HEAD --stat` plus the most recent commit's subject line) and uncommitted changes (`git diff --stat HEAD`) — picking the most-changed top-level directory and a 2–3 word summary, e.g. `feat/store-trust-tier`. The committed-and-uncommitted union matters because Step 0.4 triggers on either `AHEAD > 0` or `UNCOMMITTED > 0`; `git diff --stat HEAD` alone is empty in the committed-but-unpushed case.

Do NOT silently reset `$DEFAULT_BRANCH` after the branch — that is destructive and out of scope here. The post-checkout note inside the snippet (gated on `AHEAD > 0`) tells the user `$DEFAULT_BRANCH` still points at the local commits.

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
  echo "      Resume detection will refuse rows that depend on AHEAD or remote PR state and"
  echo "      will exit with diagnostic (see 'Diagnostic exit format' below). Resolve the"
  echo "      network/auth issue and re-run, or invoke the individual skills directly."
fi

UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
# AHEAD here counts commits past origin/$DEFAULT_BRANCH on the *current* branch.
# Note that this re-reads the value after Step 0.4 may have switched branches:
# pre-checkout it was "local $DEFAULT_BRANCH vs origin"; post-checkout it's
# "feature branch vs origin/$DEFAULT_BRANCH" — different semantics, same compare.
AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)

# UNPUSHED counts commits past the branch's *upstream* (the PR's head ref),
# not past origin/$DEFAULT_BRANCH. Distinct from AHEAD: a user who pushed
# once and then made local follow-up commits has AHEAD>0 AND UNPUSHED>0;
# we must push those follow-ups before any review/respond/ship step.
#
# When no upstream is configured yet (common before the first push),
# `git rev-list --count '@{u}..HEAD'` errors silently and would yield 0,
# which would route the user past Step 4 (push) and skip the
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

# Check for the durable self-review marker so we know review-pr ran.
# Surface API failures rather than fall through to "0 → re-review".
SELF_REVIEW_DONE=0
BOT_REPLIED=false
if [ "$PR_EXISTS" = "true" ]; then
  if ! COMMENTS=$(gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" 2>/dev/null); then
    echo "note: gh api comments fetch failed; treating SELF_REVIEW_DONE/BOT_REPLIED as unknown."
  else
    SELF_REVIEW_DONE=$(printf '%s' "$COMMENTS" \
      | jq '[.[] | select(.body | test("ai-hero:self-review"))] | length')
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
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED == 0`, `UNPUSHED == 0` | exit with hint | `MERGED` → done; suggest re-running `hero-skills:ship-pr` if the local checkout still has the branch (Step 7b retries the cleanup for an already-merged PR — `abandon-branch` refuses merged branches by design). `CLOSED` without merge → the work never landed; say so explicitly and suggest reopening the PR or starting a new branch |
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED == 0`, `UNPUSHED > 0` | exit with hint | local commits exist that never reached the merged/closed PR — do NOT suggest a reset; push them to a new branch (or reopen) so the work is saved remotely first |
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED > 0` | exit with hint | merged/closed PR but local edits exist — branch off `DEFAULT_BRANCH` for follow-up work |
| `CURRENT_BRANCH == DEFAULT_BRANCH` and `UNCOMMITTED == 0` and `AHEAD == 0` | Step 1 (plan) | fresh start (Step 0.4 already auto-branched if there was any work to preserve) |
| Feature branch, `UNCOMMITTED > 0` | Step 3 (simplify) | mid-implement; simplify the latest diff, then Step 4's push-pr test phase (verification + UI smoke) verifies it before pushing. If a PR is already open and non-draft, Step 4 will push the new commit to it. |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED > 0` | Step 4 (push) | committed but not pushed (covers both the "no PR yet" case and the "pushed-once + local follow-up" case). After push updates the PR, advance to Step 5 normally. |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "true"`, `SELF_REVIEW_DONE == 0` | Step 5 (self-review) | PR up but never reviewed |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "true"`, `SELF_REVIEW_DONE >= 1` | Step 6 (mark-ready) | self-review already ran on this draft — go straight to the mark-ready gate |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW != APPROVED`, `BOT_REPLIED=false` | Step 7 (await-review) | ready PR, no bot reply yet — Step 7's poll will wait |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW != APPROVED`, `BOT_REPLIED=true` | Step 8 (respond) | bot has commented, run respond-to-comments |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=true`, `PR_IS_DRAFT == "false"`, `PR_REVIEW == APPROVED` | Step 9 (ship) | go straight to auto-approve + merge |
| Feature branch, `UNCOMMITTED == 0`, `UNPUSHED == 0`, `PR_EXISTS=false`, `AHEAD == 0` | exit with hint | branch has no work — suggest a fresh `hero-skills:one-shot ISSUE_OR_DESCRIPTION` (Step 1 plans inline) |
| any other combination | exit with diagnostic | unrouted state — print the detected variables and exit; user falls back to individual skills |

**Diagnostic exit format.** When a row says "exit with diagnostic" or "exit with hint," print:

1. The detected state: `CURRENT_BRANCH`, `UNCOMMITTED`, `AHEAD`, `UNPUSHED`, `FETCH_OK`, `GH_OK`, and any non-empty `PR_*` values.
2. Which row in the table matched, paraphrased in one sentence.
3. The recommended individual skill(s) to invoke next (e.g., `hero-skills:push-pr test`, `hero-skills:push-pr`, `hero-skills:review-pr`).

Then **halt the orchestrator** — do not proceed to Step 1, do not silently skip into another step.

**Default for non-default branches:** when on a feature branch, one-shot resumes that branch. `$ARGUMENTS` is treated as additional context for the in-progress work. To start a *new* ticket from `$DEFAULT_BRANCH` instead, switch back to `$DEFAULT_BRANCH` first and re-run.

**No confirmation prompt.** Announce the detected state and the inferred resume point, then proceed straight into that step. Do NOT ask the user to confirm or pick an override — broken states already exit with a diagnostic above; everything else routes deterministically.

```
hero-skills:one-shot — resuming from detected state

Branch:        feat/foo (not default)
Uncommitted:   2 files
Unpushed:      3 commits ahead of origin/main
PR:            #42 (draft, 0 reviews)

Inferred resume point: Step 5 (self-review)

[5/9] (✓) plan → (✓) implement → (✓) simplify → (✓) push → (▶) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship

Reasoning: branch + unpushed commits + open draft PR + no self-review comment
yet → plan/implement/simplify/push are done;
running self-review next.

Hard stops (these halt the pipeline mid-flight when triggered — not asked up front):
  - Plan looks too large for a single PR (Step 1 scope check)
  - push-pr's test phase fails and the failure needs design judgment
  - push-pr's test phase flags a UI smoke regression on a changed route
  - You decline review-pr's mark-ready prompt (Step 6)
  - Auto-approve returns REQUEST_CHANGES and the fixes are non-trivial
  - You decline ship-pr's merge prompt
```

Set `RESUME_STEP` to the inferred value and run that step immediately. The Cross-step contract still applies for every step from `RESUME_STEP` onward — read each child skill's reported state before advancing.

When `RESUME_STEP > 1`, render the DAG with steps before `RESUME_STEP` marked `(✓)` so the visual model stays accurate.

> **Resume rule for Steps 1–9:** execute steps starting from `RESUME_STEP`. Earlier steps render as `(✓)` in the DAG **but are NOT re-executed** — do not re-run `push-pr`, `review-pr`, etc. for those steps. The first DAG render of the run shows `RESUME_STEP` as `(▶)`. Examples:
>
> - `RESUME_STEP=1` (fresh start) → run every step in order.
> - `RESUME_STEP=5` (resuming at self-review on an open draft PR) → skip Steps 1–4 entirely; render `[5/9] (✓) plan → (✓) implement → (✓) simplify → (✓) push → (▶) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship`; start running at Step 5.
> - `RESUME_STEP=6` (resuming at mark-ready, self-review comment already present) → skip Steps 1–5; render `[6/9] (✓) plan → (✓) implement → (✓) simplify → (✓) push → (✓) self-review → (▶) mark-ready → ( ) await-review → ( ) respond → ( ) ship`; ask the mark-ready confirmation directly.

### Step 1: plan

Render the DAG with `plan` as the active step:

```
[1/9] (▶) plan → ( ) implement → ( ) simplify → ( ) push → ( ) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship

Now running: plan
```

**one-shot does not plan from scratch.** `hero-skills:think-it-through` is the planning skill; this step's job is to arrive at exactly one work-item and confirm it is still outstanding. Resolve first, grill only if nothing resolves.

#### 1a: Parse `$ARGUMENTS`

If the first token matches an issue-ID pattern (e.g., `PROJ-123` — letters, dash, digits), treat it as an issue ID; otherwise treat the entire argument as a plain-text description. Any remaining text after the issue ID is additional context. If `$ARGUMENTS` is empty, fall through to 1b and offer the ready items — Step 0.5 routes here only when it found no current goal on the current branch to resume (PRs on other branches are not scanned).

#### 1b: Resolve against the work stores

Read both stores before considering a grill. `think-it-through`, `handoff`, and `harden` all emit into `my-work/`; `handoff --issue`/`--repo` also files to the tracker.

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls "$ROOT/my-work"/*.md 2>/dev/null || echo "my-work/ is empty"
```

Run think-it-through's **"What's Ready"** query (that skill's SKILL.md holds the canonical implementation — read and run it rather than reimplementing the readiness rule here) to classify every item as READY or blocked. Then, if a tracker is configured in HERO.md **Project Management**, list open issues assigned to the user:

```bash
gh issue list --assignee @me --state open --limit 20 \
  --json number,title,url 2>/dev/null || echo "NO_TRACKER"
```

Match `$ARGUMENTS` against both sets:

| Situation | Action |
|---|---|
| `$ARGUMENTS` names an issue ID that a `my-work/` item cross-links | That item is the plan → 1c |
| `$ARGUMENTS` matches exactly one READY item (id, filename slug, or title) | That item is the plan → 1c |
| `$ARGUMENTS` matches an open tracker issue but no `my-work/` item | Fetch the issue body; it is the plan → 1c |
| `$ARGUMENTS` matches a **blocked** item | STOP — print the item's unmet `depends_on` ids and their titles. Do not implement past a dependency. |
| `$ARGUMENTS` matches nothing, or is empty | Print the readiness view and ask: pick a READY item, or grill this as new work → 1d |
| `$ARGUMENTS` matches more than one READY item | Ask which one. Never guess. |

For an issue ID with a Linear MCP configured, fetch it for the fuller context:

```
mcp__linear-server__get_issue with id: ISSUE_ID
mcp__linear-server__list_comments with issueId: ISSUE_ID
```

If no Linear MCP is configured or the ID does not resolve, say so and fall back to treating `$ARGUMENTS` as a plain description.

#### 1c: Verify the item is still outstanding

**A `status: ready` item is a claim, not a fact.** Nothing in the plugin marks items `done` when work lands out-of-band — a teammate's PR, a previous session, or the user doing it by hand. Implementing already-finished work is worse than a wasted run: it produces a confusing empty-or-conflicting diff that the later pipeline steps will happily push.

Before implementing, check the item's `success` criteria and its `Verification` section against reality:

1. **Read the criteria** — they state observable behavior. Go observe it: read the files the item names, run the command it names.
2. **Search history** for the work having already landed:

   ```bash
   # Slug and issue id both appear in commit subjects/bodies by convention.
   git log --all --oneline --grep "ITEM_SLUG" --grep "ISSUE_ID" -i | head
   gh pr list --state merged --search "ITEM_SLUG" --limit 5 \
     --json number,title,mergedAt 2>/dev/null
   ```

3. **Classify** and act:

| Finding | Action |
|---|---|
| No evidence of the work → genuinely outstanding | Continue to Step 2 |
| Criteria already hold; history shows it landed | STOP the pipeline. Report the evidence, offer to mark the item `done` (edit its `status` frontmatter), and offer the next READY item. Do NOT implement. |
| Partially done (some criteria hold, some don't) | Report exactly which criteria still fail. Ask whether to scope this run to the remainder or re-grill the item via `hero-skills:think-it-through`. Never silently implement the delta. |

State the verdict explicitly before advancing — "verified outstanding: SUCCESS_CRITERION does not hold" — so a wrong resolution is visible rather than assumed.

#### 1d: Grill it (only when nothing resolved)

Invoke `hero-skills:think-it-through` via the Skill tool, passing `$ARGUMENTS`. It grills the idea one question at a time and emits dependency-aware work-items into `my-work/`. It gates on the user confirming shared understanding — one-shot does not bypass that gate.

Skip the grill and plan inline only when the task is one think-it-through itself calls out as not worth grilling (`think-it-through`'s "When to Use": a typo, a copy tweak, a dependency bump). Say which exemption applied. For anything else, grill.

When think-it-through returns, re-run the readiness query and pick the item to implement.

#### 1e: Scope check

one-shot drives **one work-item to one PR**. After 1b–1d:

- **Exactly one READY item** to implement → continue to Step 2.
- **think-it-through emitted more than one item** → STOP. This is the scope guard firing: the work decomposed into a stack, which is the signal it is too large for unattended automation. Print the readiness view and tell the user to run one-shot per item, starting with the READY one(s).
- **The single item is flagged `one_way_door: true`** → STOP and confirm with the user before proceeding. One-way doors (schema, public API, data model, money) do not belong in an unattended pipeline without an explicit go-ahead.

The item's own `Non-goals` and `success` fields replace the old file-count heuristics — think-it-through sizes items to "the smallest units that each deliver something testable and can be reviewed on their own", which is exactly one-shot's contract.

### Step 2: implement

Render DAG with `implement` active. Implement the work-item resolved in Step 1, working from its `Approach` section and holding its `success` criteria as the target. Mark the item `status: in-progress` in `my-work/` before the first edit, so a session that dies mid-flight leaves an honest store behind. Follow these rules:

- **Read before edit** — Always Read a file before modifying it.
- **Match existing patterns** — Follow naming, structure, and style already in the codebase. Don't introduce new conventions.
- **One step at a time** — Announce each step briefly, make the change, then move on. No commentary between steps unless something blocks you.
- **Stop and ask on ambiguity** — If a step is unclear or the codebase state contradicts the plan, stop and ask the user rather than guess.

After implementation, **always run a quick self-review-of-the-diff before moving on** — but do NOT run the full `review-pr` agent suite yet (that happens in Step 5 against the open PR). At minimum:

- `git status` — confirm only intended files changed
- `git diff` — read every line; reject sloppy edits
- Verify the change matches the plan; flag deviations to the user

### Step 3: simplify

Render DAG with `simplify` active. Invoke the `simplify` skill via the Skill tool — it reviews the dirty diff for reuse, quality, and efficiency and fixes any issues found before push runs.

`simplify` is **not** part of this plugin — it ships separately (see the user-invocable skills list). `hero-skills:push-pr` also invokes it internally when it commits, so running it here makes simplification visible as its own DAG step *and* the second invocation inside push-pr is a fast no-op once nothing is left to simplify.

If the `simplify` skill is unavailable in this environment, render `(–) simplify` and continue — push-pr's own commit step will catch anything we missed via its inline fallback checklist.

### Step 4: push

Render DAG with `push` active. Run `hero-skills:push-pr` (no arguments — runs its test phase first: verification plus smoke tests, including UI smoke via Playwright MCP when a UI project is detected; then commits any outstanding work with a smart conventional commit, branches off the default branch first if needed, pushes, and opens a draft PR). Trust its grouping/commit logic — do not skip pre-commit hooks. Capture the PR number from its output for downstream steps.

Because the test phase runs inside push-pr on every push, resumed runs are re-tested at push time — there is no stale-test window between sessions.

Test-phase failure semantics (owned by push-pr, surfaced here):

- If tests fail with a quick, mechanical fix (lint, typo, import order), push-pr applies the fix and re-runs.
- If they fail in a way that needs design judgment (test asserting wrong behavior, integration breakage, flaky CI), render `(✗) push` and STOP.
- If the test phase flags a UI smoke regression — a 4xx/5xx on a changed route, an uncaught console error, a `wait_for` timeout — render `(✗) push` plus `Stopped: test-phase regression on ROUTE` and hand back. Nothing is committed; we never want a known UI regression in git history if we can help it.
- On backend-only PRs (no UI project declared in HERO.md), the frontend-smoke portion is skipped with `(–)` internally and push continues — that's expected, not a failure.

The smoke portion of the test phase is intentionally narrow (≤5 routes, no large forms). For deeper coverage, run a real E2E suite directly.

### Step 5: self-review

Render DAG with `self-review` active. Run `hero-skills:review-pr --no-mark-ready` (auto-detects your draft PR and runs the pr-review-toolkit agents plus a security pass in parallel, applies fixes). The `--no-mark-ready` flag is **required** here so review-pr stops before its own Step 9 mark-ready prompt — one-shot's Step 6 below owns that gate, and double-prompting would be confusing.

This step covers `review-pr`'s functional work in Steps 1–8 only: post the review comment, ask permission to apply fixes, apply them, push the commit, post the improvements summary, and update the PR description. Mark-ready is deliberately deferred to one-shot's Step 6 so the DAG renders it as a visible, separately-tracked node. `review-pr`'s own Step 9 (mark-ready prompt) is skipped per `--no-mark-ready`; its Step 10 (summary print) still runs but is purely informational — one-shot's own DAG/summary is what's authoritative here, not review-pr's next-step suggestion.

### Step 6: mark-ready

Render DAG with `mark-ready` active. Now ask the user the gate question explicitly:

```
Convert draft PR #{number} to ready-for-review? [y/N]
```

On `y`:

```bash
gh pr ready "$PR_NUMBER"
```

This is a **hard gate**. If the user declines, render `(✗) mark-ready` plus `Stopped: user declined mark-ready` and STOP. Do not bypass — auto-approve in Step 9 refuses draft PRs anyway, and `gh pr ready` is the only way past the draft state.

### Step 7: await-review

Render DAG with `await-review` active. If `HERO.md` declares a Code Review Agent (CodeRabbit, Greptile, Copilot review, etc.), poll the PR comments for the bot's first comment for **up to 60 seconds total, polling every 15 seconds**. If the bot has not posted by then, render `(–) await-review` (the gate behavior is delegated to Step 9's auto-approve, which will refuse on unresolved threads) and advance to Step 8 only if `BOT_REPLIED=true` — otherwise skip Step 8 with `(–)` too and go straight to Step 9.

```bash
BOT_USER=$(awk -F': ' '/^- bot-username:/ {print $2; exit}' "$ROOT/HERO.md" \
  | tr -d '[:space:]"'"'"'')
# PR_NUMBER comes from Step 4's push-pr output. Re-derive owner/repo from gh
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

If no review bot is configured (`agent: none`), render `(–) await-review` and skip both Steps 7 and 8; advance directly to Step 9.

### Step 8: respond

Render DAG with `respond` active. Run `hero-skills:respond-to-comments` to address the bot's inline comments and resolve threads. This step only runs if Step 7 saw the bot reply.

If the bot's feedback exceeds a small set of trivial fixes, render `(✗) respond` plus `Stopped: bot feedback non-trivial — escalate to a human reviewer` per `PIPELINES.md` skip/error semantics, and halt. Do not advance to Step 9.

### Step 9: ship

Render DAG with `ship` active. Run `hero-skills:ship-pr`. This:

1. Checks the auto-approve gates (prior review present, no unresolved threads, no active CHANGES_REQUESTED, no unanswered reviewer questions).
2. Posts `@auto-approve` and waits for the verdict.
3. On APPROVE, asks before merging. The user must say `y`.
4. After merge, switches to the default branch, pulls latest, and deletes the merged head branch (remote + local).

If auto-approve returns REQUEST_CHANGES or WORKFLOW_FAILED, STOP. The user should run `hero-skills:respond-to-comments` again or fix the workflow before re-attempting.

**After a successful merge, close the loop on the work-item.** This is the only place the store gets marked `done`, and skipping it is what makes a later run re-implement finished work (Step 1c exists to catch that, but catching it late wastes the resolution):

1. Set the item's `status: done` in `my-work/NNN-slug.md`.
2. If the item cross-links a tracker issue, close it — `gh issue close ISSUE_NUMBER --repo TARGET_REPO --comment "Merged in PR_URL"`, or the Linear MCP equivalent. Use the item's recorded repo, which for a `handoff --repo` item is **not** this one.
3. Re-run the readiness query and report what the merge unblocked — items whose `depends_on` just went green are the natural next run.

If the pipeline stopped before merge, leave the item `in-progress`. Do not mark `done` on an unmerged PR.

### Final Summary

After ship-pr completes successfully, print the final pipeline DAG and a one-shot summary:

```
[9/9] (✓) plan → (✓) implement → (✓) simplify → (✓) push → (✓) self-review → (✓) mark-ready → (✓) await-review → (✓) respond → (✓) ship

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

If the pipeline stopped early, render the DAG with `(✗)` on the failed step, the reason, and the recommended skill to re-invoke once the blocker is cleared.

## Notes

- This skill **does not skip user gates**. think-it-through's shared-understanding gate, mark-ready, and merge confirmation are all explicit. Auto mode does not change that.
- **one-shot consumes work-items; it does not author them.** `think-it-through`, `handoff`, and `harden` are the producers into `my-work/`. Step 1 resolves against that store (and the tracker) before it will grill anything new, and Step 9 is what marks an item `done` — one-shot is the store's only consumer, so if it skips the close-out nothing else will do it.
- **Trust the criteria, not the status field.** `status: ready` only means "nobody has updated this file", which is not the same as "not yet done" — work lands out-of-band all the time. Step 1c re-verifies against the codebase before implementing.
- This skill **does not retry** on judgment-call failures (test design, large bot feedback). Retrying without human input is how small PRs become broken merges.
- Step 0.4's `git checkout -b` is unconfirmed by design — one-shot never works on the default branch and assumes the auto-derived name is acceptable. To rename later, use `git branch -m`. The sibling skill `push-pr` prompts for the name because it's invoked deliberately on an existing branch; one-shot's auto-mode contract precludes that prompt.
- For larger work, run the same skills individually so you can pause between them.
- Run `hero-skills:abandon-branch` separately if you abandon mid-pipeline — ship-pr's reset only fires after a successful merge.
