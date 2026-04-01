---
name: hero-reset
# prettier-ignore
description: Reset to the default branch, pull latest, and clear conversation context. Use when starting fresh or switching tasks.
disable-model-invocation: true
---

# Hero Reset - Clean Slate

Reset to the default branch, pull latest changes, and clear conversation context for a fresh start.

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default-branch (to know which branch to reset to)

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
1. Stash changes (saved as "hero-reset: WIP on $CURRENT") — you can restore later with `git stash pop`
2. Cancel — go back and commit or handle changes first
```

**STOP and wait for user to choose.** Do NOT proceed without explicit confirmation. Do NOT offer a "discard" option — if the user truly wants to discard, they can do that themselves before running this skill.

**If user chooses option 1 (stash):**

```bash
git stash push -m "hero-reset: WIP on $CURRENT"
```

Report the stash ref:

```
Stashed as: stash@{0} — "hero-reset: WIP on $CURRENT"
You can restore later with: git stash pop
```

Note: hero-reset does NOT auto-pop the stash since the purpose is to switch away from the current branch. The user must manually restore if needed.

### Step 2: Check if Current Branch is Merged

```bash
DEFAULT_BRANCH=main  # or from HERO.md
```

**First, always update the local default branch from remote:**

```bash
git fetch origin $DEFAULT_BRANCH
```

If already on the default branch, skip to Step 3.

Otherwise, check whether the current branch has been merged:

```bash
git branch --merged origin/$DEFAULT_BRANCH | grep -Eq "^[[:space:]]*$CURRENT$" && echo "MERGED" || echo "NOT_MERGED"
```

**If the current branch is merged into the default branch:**

The branch work is safely in the default branch. Auto-clean it after switching:

```
Branch '$CURRENT' has been merged into '$DEFAULT_BRANCH'. Will clean it up.
```

```bash
git checkout $DEFAULT_BRANCH
git branch -d $CURRENT
```

If the branch also exists on the remote and was already deleted there (e.g., via PR merge), clean the tracking ref:

```bash
git fetch --prune
```

**If the current branch is NOT merged:**

```
Warning: Branch '$CURRENT' has NOT been merged into '$DEFAULT_BRANCH'.
Switching away means leaving unmerged work behind.

Options:
1. Switch anyway — the branch will remain locally for you to come back to
2. Cancel — stay on '$CURRENT' and handle it first
```

**STOP and wait for user to choose.** Do NOT delete an unmerged branch.

```bash
if [ "$CURRENT" != "$DEFAULT_BRANCH" ]; then
  git checkout $DEFAULT_BRANCH
fi
```

### Step 3: Pull Latest

```bash
git pull origin $DEFAULT_BRANCH
```

**If pull fails due to conflicts:** Report and let user resolve.

### Step 4: Clean Up Other Merged Branches (Optional)

List any other local branches that have been merged and could be cleaned:

```bash
git branch --merged "origin/$DEFAULT_BRANCH" | grep -vE '^\*' | grep -vE "^[[:space:]]*${DEFAULT_BRANCH}$"
```

If there are merged branches, suggest cleanup but don't delete without confirmation.

### Step 5: Clear Context

Run `/clear` to reset the conversation context.

### Step 6: Report

```
Hero Reset Summary
==================
Branch: {default-branch}
Status: Up to date with origin

Previous branch: {previous-branch} [merged — deleted / not merged — kept / was already on default]
Pulled: N new commits
Stashed: [yes — "hero-reset: WIP on {branch}" (restore with `git stash pop`) / no]
Cleaned up: [list of deleted merged branches, if any]
Context: Cleared
```
