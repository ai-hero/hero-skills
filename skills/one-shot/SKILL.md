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
| 1 | `plan` | `hero-skills:think-it-through` (only when nothing resolves from `.plans/` or the tracker) |
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

Source the shared helper library once, at the top of the run — every later step assumes these functions are available:

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB" || { echo "ERROR: cannot source hero-lib.sh — reinstall the plugin."; exit 1; }

ROOT=$(hero_root)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
hero_check_staleness
```

If `HERO.md` is missing, STOP and tell the user to run `hero-skills:init-hero` first. one-shot relies on every downstream skill having a config to read; running blind through 9 steps is unsafe.

> Each bash block below runs in a fresh shell, so re-source `hero-lib.sh` at the top of any block that calls a `hero_*` function. The snippets show this.

### Step 0.3: Pre-flight Checks

Before auto-branching or any other destructive work, run the full pre-flight to catch failures that would otherwise only surface at Step 4 (push), Step 5 (self-review), or Step 9 (ship) — after you've already done the work.

`preflight.sh --auto-scope` derives its own project scope from the diff and skips the runtime bucket on a fresh start. Deciding which checks apply is preflight's job, not one-shot's:

```bash
PREFLIGHT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/preflight.sh"
[ -x "$PREFLIGHT" ] || PREFLIGHT="$(git rev-parse --show-toplevel)/scripts/preflight.sh"

"$PREFLIGHT" --bucket all --auto-scope
PREFLIGHT_RC=$?
```

If `PREFLIGHT_RC` is non-zero, **STOP**. Print the recommended fix from each `[BLOCKER]` line (the script prints these inline) and do not advance to Step 0.4 — every blocker is something that would have failed a later step on a half-finished branch.

If `PREFLIGHT_RC` is zero but the script printed `[WARN]` lines, surface them to the user once and continue. Warnings are advisory — the user can choose to fix them or proceed.

### Step 0.4: Auto-branch off Default Branch (if needed)

one-shot never works on the default branch. If we're on it with any uncommitted files or unpushed local commits, branch off automatically — **no prompt** — so the rest of the pipeline has a feature branch to commit and push to. This runs before resume detection so Step 0.5 sees a feature-branch state whenever there is work to preserve.

**Why one-shot branches at all, when `push-pr` also does:** push-pr branches at *push* time, which is Step 4 — too late, because Step 2 starts editing files. The timing is one-shot's own concern. The **naming policy is not** — that lives in `hero_branch_policy` and is shared with push-pr, so the two can't drift.

First, **derive `SUGGESTED_BRANCH` as a reasoning step** — this is a model task, not a shell function. Run `hero_branch_policy` to print the rules, apply them to `$ARGUMENTS` (or the diff if `$ARGUMENTS` is empty), and produce a concrete, non-empty branch name. Then run the snippet below with that value exported in the environment. The snippet asserts the variable is set; it will not invent one.

```bash
# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
hero_branch_policy   # apply these rules to derive SUGGESTED_BRANCH

DEFAULT_BRANCH=$(hero_default_branch)
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

**Naming** follows `hero_branch_policy` (shared with push-pr) with two one-shot specifics:

- **No prompt.** push-pr proposes a name and waits for confirmation; one-shot derives and proceeds. That is one-shot's auto-mode contract, not a naming difference — rename later with `git branch -m`.
- **When `$ARGUMENTS` is empty**, derive the slug from the union of committed-but-unpushed changes (`git log origin/$DEFAULT_BRANCH..HEAD --stat` plus the latest commit subject) *and* uncommitted changes (`git diff --stat HEAD`). The union matters because this step triggers on either `AHEAD > 0` or `UNCOMMITTED > 0`, and `git diff --stat HEAD` alone is empty in the committed-but-unpushed case.

Do NOT silently reset `$DEFAULT_BRANCH` after the branch — that is destructive and out of scope here. The post-checkout note inside the snippet (gated on `AHEAD > 0`) tells the user `$DEFAULT_BRANCH` still points at the local commits.

### Step 0.5: Detect Resume Point

Before doing anything destructive, read the current git/PR state and figure out where in the pipeline this invocation should pick up. Users often hit `hero-skills:one-shot` after they've already done some of the work — possibly in a previous session — and the orchestrator should never silently re-do completed steps.

```bash
PLUGIN="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}"
[ -x "$PLUGIN/scripts/resume-state.sh" ] || PLUGIN="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ ! -x "$PLUGIN/scripts/resume-state.sh" ]; then
  echo "ERROR: cannot find scripts/resume-state.sh — reinstall the plugin."
  exit 1
fi
eval "$("$PLUGIN/scripts/resume-state.sh")"
```

The existence guard matters: without it a missing script makes the command substitution empty, `eval` sets nothing, and every variable the table reads is **unset** — including `STATE_OK`, so the guard row would not match and the run would route on nothing at all.

`resume-state.sh` gathers the state and makes no routing decision — the decision table below stays the single source of truth for that. It sets `DEFAULT_BRANCH`, `CURRENT_BRANCH`, `UNCOMMITTED`, `AHEAD`, `UNPUSHED`, `PR_EXISTS`, `PR_NUMBER`, `PR_STATE`, `PR_IS_DRAFT`, `PR_REVIEW`, `SELF_REVIEW_DONE`, `BOT_REPLIED`, plus `STATE_OK` and `STATE_ERRORS`.

**Unknown is not zero.** Any value whose source call failed is emitted as the literal string `unknown`, never as a number. `AHEAD=0` means "verified nothing to push"; `AHEAD=unknown` means the fetch or the ref lookup failed and the count was never established. Because the rows below compare against `0`, an `unknown` cannot match them — the guard is structural rather than something to remember.

`STATE_OK` is `false` if any source failed, with `STATE_ERRORS` naming which: `lib`, `no-hero-md`, `default-branch-rejected`, `default-branch-invalid`, `detached-head`, `jq`, `fetch`, `default-ref`, `git-status`, `rev-list-ahead`, `rev-list-unpushed`, `gh-pr-list`, `gh-comments`, `self-review-count`, `bot-count`.

`default-branch-rejected` and `default-branch-invalid` are the most safety-relevant: they mean HERO.md's value was refused and every `AHEAD`/`UNPUSHED` measurement was taken against the `main` fallback rather than the repo's real base. One row guarding `STATE_OK` covers every case, so adding a source later cannot bypass a guard that enumerated the old ones.

Two distinctions the table depends on:

- **`AHEAD` vs `UNPUSHED`** — `AHEAD` counts commits past `origin/$DEFAULT_BRANCH`; `UNPUSHED` counts commits past this branch's own upstream. Someone who pushed once then committed again locally has both non-zero, and those follow-ups must reach the PR before any review step.
- **`AHEAD` before vs after Step 0.4** — pre-checkout it compares the local default branch to origin; post-checkout it compares the feature branch. Same command, different meaning.

Use the decision tree below to pick the **resume step** (1–9). Each row is the first that matches top-to-bottom; rows below the line require `PR_EXISTS=true` so empty PR_* values can't accidentally match.

| Condition | Resume at | Reason |
|-----------|-----------|--------|
| `STATE_OK=false` | STOP with diagnostic | print `STATE_ERRORS` (the only health variable emitted — `FETCH_OK`/`GH_OK` are script-internal and unset in your shell); every row below depends on state that was not established. `bot-username` alone is the one recoverable case — say the review bot cannot be identified and offer to continue at the user's chosen step. For anything else, fix it and re-run, or invoke the individual skills |
| `PR_EXISTS=true` AND `PR_STATE` is `MERGED` or `CLOSED`, `UNCOMMITTED == 0`, `UNPUSHED == 0` | exit with hint | `MERGED` → done; suggest re-running `hero-skills:ship-pr` if the local checkout still has the branch (Step 7b retries the cleanup for an already-merged PR — `abandon` refuses merged branches by design). `CLOSED` without merge → the work never landed; say so explicitly and suggest reopening the PR or starting a new branch |
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

1. The detected state: `CURRENT_BRANCH`, `UNCOMMITTED`, `AHEAD`, `UNPUSHED`, `STATE_OK`, `STATE_ERRORS`, and any non-empty `PR_*` values.
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

Read both stores before considering a grill. `think-it-through`, `handoff`, `harden`, and `wayfare` all emit into `.plans/`; `handoff --issue`/`--repo` also files to the tracker.

```bash
# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
hero_ready_items

# Tracker issues, when Project Management is configured in HERO.md.
gh issue list --assignee @me --state open --limit 20 \
  --json number,title,url 2>/dev/null || echo "NO_TRACKER"
```

Match `$ARGUMENTS` against both sets:

| Situation | Action |
|---|---|
| `$ARGUMENTS` names an issue ID that a `.plans/` item cross-links | That item is the plan → 1c |
| `$ARGUMENTS` matches exactly one READY item (id, filename slug, or title) | That item is the plan → 1c |
| `$ARGUMENTS` matches an open tracker issue but no `.plans/` item | Fetch the issue body; it is the plan → 1c |
| `$ARGUMENTS` matches a **blocked** item | STOP — print the item's unmet `depends_on` ids and their titles. Do not implement past a dependency. |
| `$ARGUMENTS` matches a **plan** (planning) item | STOP — the item awaits the user's ready-mark. Show its title and `success` criteria and ask whether to mark it ready; on yes, set `status: todo` + `ready_marked:` date and it is the plan → 1c. Do NOT re-grill it — that writes a duplicate. |
| `$ARGUMENTS` matches a **done** item | STOP — report that it already landed, with the item's `success` criteria as evidence. Offer the next READY item. Do NOT re-grill it; that writes a duplicate. |
| `$ARGUMENTS` matches an **active** (in-progress) item | STOP and confirm — another session may hold it. Step 2 marks items `in-progress` before the first edit precisely so two runs cannot claim one item. |
| `$ARGUMENTS` matches nothing, or is empty | Print the readiness view and ask: pick a READY item, or grill this as new work → 1d |
| `$ARGUMENTS` matches more than one READY item | Ask which one. Never guess. |

For an issue ID with a Linear MCP configured, fetch it for the fuller context:

```
mcp__linear-server__get_issue with id: ISSUE_ID
mcp__linear-server__list_comments with issueId: ISSUE_ID
```

If no Linear MCP is configured or the ID does not resolve, say so and fall back to treating `$ARGUMENTS` as a plain description.

#### 1c: Verify the item is still outstanding

**A `todo` item is a claim, not a fact.** Nothing marks items `done` automatically when work lands out-of-band — a teammate's PR, a previous session, or the user doing it by hand. Implementing already-finished work is worse than a wasted run: it produces a confusing empty-or-conflicting diff that the later pipeline steps will happily push.

Before implementing, check the item's `success` criteria and its `Verification` section against reality:

1. **Read the criteria** — they state observable behavior. Go observe it: read the files the item names, run the command it names.
2. **Search history** for the work having already landed. Check each command's status — an empty result from a command that *failed* is not evidence of absence:

   `ITEM_SLUG` is the resolved item's filename slug from 1b (`007-add-oauth.md` → `add-oauth`). Set it there; without it the guard below is the default path, not an edge case.

   ```bash
   EVIDENCE_OK=true   # must be initialized: the classify table reads it as
                      # "false", and an unset var is neither, plus a hard
                      # error under set -u.

   # `--grep ""` matches EVERY commit, which reads as "it already landed" and
   # stops a run that should have proceeded. Skip the searches entirely rather
   # than merely flagging — a bare flag still let the next line run.
   if [ -z "${ITEM_SLUG:-}" ]; then
     echo "1c: no slug to search — cannot verify from history"
     EVIDENCE_OK=false
   else
     git log --all --oneline --grep "$ITEM_SLUG" -i | head || EVIDENCE_OK=false

   # No 2>/dev/null: a swallowed gh failure yields an empty list that reads
   # exactly like "no merged PR", which is the answer that says "go build it".
     gh pr list --state merged --search "$ITEM_SLUG" --limit 5 \
       --json number,title,mergedAt || EVIDENCE_OK=false
   fi
   ```

   Note this is only as good as the repo's conventions: a repo that doesn't put slugs in commit subjects, or a shallow clone, yields zero hits for a reason unrelated to whether the work landed. Weigh the criteria check in step 1 more heavily than history when the two disagree.

3. **Classify** and act:

| Finding | Action |
|---|---|
| No evidence of the work → genuinely outstanding | Continue to Step 2 |
| Criteria already hold; history shows it landed | STOP the pipeline. Report the evidence, offer to mark the item `done`, and offer the next READY item. Do NOT implement. |
| Partially done (some criteria hold, some don't) | Report exactly which criteria still fail. Ask whether to scope this run to the remainder or re-grill the item via `hero-skills:think-it-through`. Never silently implement the delta. |
| **Could not evaluate** — `EVIDENCE_OK=false`, `gh` unauthenticated, a criteria command that errored for an unrelated reason, or criteria too vague to check | **STOP and ask.** Do not treat an unevaluable criterion as a failing one. Say which check could not run and let the user decide whether to build. |

The last row exists because every other uncertain path here resolves toward implementing — which is the outcome this step exists to prevent. An empty result must never stand in for a negative one.

State the verdict explicitly before advancing — "verified outstanding: SUCCESS_CRITERION does not hold" — so a wrong resolution is visible rather than assumed.

#### 1d: Grill it (only when nothing resolved)

Invoke `hero-skills:think-it-through` via the Skill tool, passing `$ARGUMENTS`. It grills the idea one question at a time and emits dependency-aware work-items into `.plans/`. It gates on the user confirming shared understanding — one-shot does not bypass that gate.

Skip the grill and plan inline only when the task is one think-it-through itself calls out as not worth grilling (`think-it-through`'s "When to Use": a typo, a copy tweak, a dependency bump). Say which exemption applied. For anything else, grill.

When think-it-through returns, re-run the readiness query and pick the item to implement.

#### 1e: Scope check

one-shot drives **one work-item to one PR**. After 1b–1d:

- **Exactly one READY item** to implement → continue to Step 2.
- **think-it-through emitted more than one item** → STOP. This is the scope guard firing: the work decomposed into a stack, which is the signal it is too large for unattended automation. Print the readiness view and tell the user to run one-shot per item, starting with the READY one(s).
- **The single item is flagged `one_way_door: true`** → STOP and confirm with the user before proceeding. One-way doors (schema, public API, data model, money) do not belong in an unattended pipeline without an explicit go-ahead.

The item's own `Non-goals` and `success` fields replace the old file-count heuristics — think-it-through sizes items to "the smallest units that each deliver something testable and can be reviewed on their own", which is exactly one-shot's contract.

### Step 2: implement

Render DAG with `implement` active. Implement the work-item resolved in Step 1, working from its `Approach` section and holding its `success` criteria as the target. Mark the item `status: in-progress` in `.plans/` before the first edit, so a session that dies mid-flight leaves an honest store behind. Follow these rules:

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

Render DAG with `await-review` active. If `HERO.md` declares a Code Review Agent (CodeRabbit, Greptile, Copilot review, etc.), poll the PR comments for the bot's first comment for **up to 60 seconds total, polling every 15 seconds**. If the bot has not posted by then, render `(–) await-review` (the gate behavior is delegated to Step 9's auto-approve, which will refuse on unresolved threads) and skip Step 8 with `(–)` too, going straight to Step 9.

Advance to Step 8 **only if this step's own poll found a comment** — i.e. `BOT_COMMENT` is non-empty. Do not gate on `BOT_REPLIED`: that is set by `resume-state.sh` at Step 0.5, in a different shell, and on a fresh run it was evaluated before any PR existed, so it is permanently `false`. Gating on it means `respond-to-comments` never runs and bot feedback is silently skipped.

```bash
# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
BOT_USER=$(hero_field bot-username || true)
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

Render DAG with `ship` active. Run `hero-skills:ship-pr`. It owns the auto-approve gates, the verdict wait, the merge confirmation, and the branch cleanup — see its SKILL.md for what those are.

**Contract — what one-shot needs back:** a merged SHA, or a STOP reason.

- **STOP** (REQUEST_CHANGES, WORKFLOW_FAILED, declined merge) → render `(✗)`, report the reason, leave the work-item `in-progress`. Never mark an unmerged PR's item `done`.
- **Merged** → run Step 9a.

#### Step 9a: Close out the work-item

The only place the store is marked `done`. one-shot is its sole consumer, so skipping this is what makes a later run re-resolve finished work (Step 1c catches it, but catching it late wastes the resolution):

1. Set `status: done` in the item's `.plans/NNN-slug.md`.
2. Close any cross-linked tracker issue — `gh issue close ISSUE_NUMBER --repo TARGET_REPO --comment "Merged in PR_URL"`, or the Linear MCP equivalent. Use the item's **recorded** repo; for a `handoff --repo` item that is not this one.
3. Run `hero_ready_items` and report what the merge unblocked — items whose `depends_on` just went green are the natural next run.

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
- **one-shot consumes work-items; it does not author them.** `think-it-through`, `handoff`, `harden`, and `wayfare` are the producers into `.plans/`. Step 1 resolves against that store (and the tracker) before it will grill anything new, and Step 9 is what marks an item `done` — one-shot is the store's only consumer, so if it skips the close-out nothing else will do it.
- **Trust the criteria, not the status field.** `status: todo` means a human marked the item ready but says nothing about whether the work has since landed — work lands out-of-band all the time. Step 1c re-verifies against the codebase before implementing.
- This skill **does not retry** on judgment-call failures (test design, large bot feedback). Retrying without human input is how small PRs become broken merges.
- Step 0.4's `git checkout -b` is unconfirmed by design — one-shot never works on the default branch and assumes the auto-derived name is acceptable. To rename later, use `git branch -m`. The sibling skill `push-pr` prompts for the name because it's invoked deliberately on an existing branch; one-shot's auto-mode contract precludes that prompt.
- For larger work, run the same skills individually so you can pause between them.
- Run `hero-skills:abandon` separately if you abandon mid-pipeline — ship-pr's reset only fires after a successful merge.
