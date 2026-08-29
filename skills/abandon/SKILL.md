---
name: abandon
# prettier-ignore
description: Abandon or pause work on a branch that hasn't merged — stash uncommitted changes, switch to the default branch, and clear conversation context.
disable-model-invocation: true
---

# Abandon Branch — Stash and Walk Away

Abandon or pause work on a branch that never merged: stash any uncommitted changes, switch back to the default branch, pull latest, and clear conversation context.

> **Note:** Merged branches are already cleaned up by `hero-skills:ship-pr`'s final step (switch to default, pull, delete merged head, offer cleanup) — this skill is for the opposite case, when you're stepping away from a branch that did **not** go through `ship-pr`.

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
[ -f "$PWD/FLEET.md" ] && [ ! -f "$PWD/HERO.md" ] && echo "FLEET_ROOT" || true
```

If `FLEET_ROOT` printed, this folder is a fleet, not a repo: stop and follow **At the fleet root** in `docs/FLEET-MD.md`.

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default-branch (to know which branch to switch back to)

If `HERO.md` is missing, default to `main`.

### Step 1: Check for Uncommitted Work

```bash
git status --porcelain
CURRENT=$(git branch --show-current)
git stash list
```

**If uncommitted changes exist, STOP and show:**

```
You have uncommitted changes on '$CURRENT':

  (list changed files from git status)

Options:
1. Stash changes (saved as "abandon: WIP on $CURRENT") — you can restore later with `git stash pop`
2. Cancel — go back and commit or handle changes first
```

**STOP and wait for user to choose.** Do NOT proceed without explicit confirmation. Do NOT offer a "discard" option — if the user truly wants to discard, they can do that themselves before running this skill.

**If user chooses option 1 (stash):**

```bash
git stash push -m "abandon: WIP on $CURRENT"
```

Report the stash ref:

```
Stashed as: stash@{0} — "abandon: WIP on $CURRENT"
You can restore later with: git stash pop
```

Note: this does NOT auto-pop the stash since the purpose is to switch away from the current branch. The user must manually restore if needed.

### Step 2: Confirm the Branch Is Actually Unmerged, Then Switch Away

```bash
# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
# _verbose, not the silent variant: this value gates a force-delete. On a repo
# whose real default is `master`, a silent fallback to `main` makes
# `gh pr list --base main` return 0, the branch reads as never-merged, and
# Delete is offered on work that was merged.
DEFAULT_BRANCH=$(hero_default_branch_verbose)
if ! git fetch origin "$DEFAULT_BRANCH"; then
  echo "WARN: 'git fetch origin $DEFAULT_BRANCH' failed — the merged-check below may be unreliable. Resolve network/auth before trusting its result."
fi
```

If already on the default branch, skip to Step 3.

Otherwise, check whether the current branch has secretly already been merged (handles squash-and-merge) — if so, this isn't an abandon at all, point the user at `ship-pr`'s cleanup instead of duplicating it here. Check remotely first, but fall back to a local check if the API call fails — a network hiccup must not silently read as "unmerged" when a real merge-status query would have said otherwise, especially since this now gates a destructive Delete option below:

```bash
MERGED_COUNT=$(gh pr list --head "$CURRENT" --base "$DEFAULT_BRANCH" --state merged --json number --jq 'length' 2>/dev/null)
if [ -z "$MERGED_COUNT" ]; then
  echo "WARN: could not query merged-PR status via gh — falling back to a local check."
  if git branch --merged "origin/$DEFAULT_BRANCH" 2>/dev/null | grep -Eq "^[[:space:]]*\*?[[:space:]]*${CURRENT}$"; then
    MERGED_COUNT=1
  else
    MERGED_COUNT=0
  fi
fi
```

**If `$MERGED_COUNT >= 1` (already merged):** stop and say `'$CURRENT' already has a merged PR — this isn't an abandon. Run hero-skills:ship-pr's cleanup flow (or delete '$CURRENT' manually) instead.` If Step 1 stashed anything, say so explicitly here too — the user is being redirected away without a reminder otherwise: `Note: your uncommitted changes are stashed (stash@{0}) — restore with 'git stash pop' after switching branches.` Do not proceed with this skill.

**Otherwise (genuinely unmerged):**

```
Warning: Branch '$CURRENT' has NOT been merged into '$DEFAULT_BRANCH'.

Options:
1. Pause — switch away, keep '$CURRENT' locally to come back to later
2. Delete — abandon for good: force-delete '$CURRENT' locally (and its remote
   branch / open PR, if any) after switching away
3. Cancel — stay on '$CURRENT' and handle it first
```

**STOP and wait for user to choose.** Never delete without this explicit confirmation — an unmerged branch is unrecoverable work once its local ref and reflog expire.

**If the user chose option 3 (Cancel): stop here.** Do not run the checkout below.

For options 1 (Pause) and 2 (Delete), switch to the default branch first:

```bash
if [ "$CURRENT" != "$DEFAULT_BRANCH" ]; then
  git checkout $DEFAULT_BRANCH
fi
```

**If the user chose option 2 (Delete):** force-delete the local branch, then check for a remote branch and/or open PR and offer to remove those too — don't delete them silently:

```bash
git branch -D "$CURRENT"

PR_INFO=$(gh pr list --head "$CURRENT" --state open --json number,url --jq '.[0]' 2>/dev/null)
REMOTE_EXISTS=$(git ls-remote --heads origin "$CURRENT" 2>/dev/null)
```

If `$PR_INFO` is non-empty, ask: `Open PR #{number} ({url}) still points at '$CURRENT'. Close it too? [y/N]` — on yes, `gh pr close {number} --delete-branch` (this closes the PR and deletes the remote branch in one call). On no, leave the PR and remote branch alone and say so explicitly.

If there's no open PR but `$REMOTE_EXISTS` is non-empty, ask: `Remote branch 'origin/$CURRENT' still exists. Delete it too? [y/N]` — on yes, `git push origin --delete "$CURRENT"`.

### Step 3: Pull Latest

```bash
git pull origin $DEFAULT_BRANCH
```

**If pull fails due to conflicts:** Report and let user resolve.

### Step 4: Clear Context

Run `/clear` to reset the conversation context.

### Step 5: Report

```
Abandon Summary
==================
Branch: {default-branch}
Status: Up to date with origin

Previous branch: {previous-branch} [paused, kept locally / deleted (local + remote/PR, if confirmed) / was already on default]
Pulled: N new commits
Stashed: [yes — "abandon: WIP on {branch}" (restore with `git stash pop`) / no]
Context: Cleared

Next step: hero-skills:one-shot — start the next task (print only — launch it on the user's word, never spontaneously)
```
