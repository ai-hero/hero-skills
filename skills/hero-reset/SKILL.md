---
name: hero-reset
# prettier-ignore
description: Reset to main branch, pull latest, and clear conversation context. Use when starting fresh or switching tasks.
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
git stash list
```

**If uncommitted changes exist:**

```
Warning: You have uncommitted changes.

Options:
1. Stash changes before resetting
2. Discard changes and reset (destructive)
3. Cancel
```

Stop and let user decide. Do NOT discard changes without explicit confirmation.

### Step 2: Switch to Default Branch

```bash
DEFAULT_BRANCH=main  # or from HERO.md
CURRENT=$(git branch --show-current)

if [ "$CURRENT" != "$DEFAULT_BRANCH" ]; then
  git checkout $DEFAULT_BRANCH
fi
```

### Step 3: Pull Latest

```bash
git pull origin $DEFAULT_BRANCH
```

**If pull fails due to conflicts:** Report and let user resolve.

### Step 4: Clean Up Merged Branches (Optional)

List local branches that have been merged and could be cleaned:

```bash
git branch --merged $DEFAULT_BRANCH | grep -v "^\*\|$DEFAULT_BRANCH"
```

If there are merged branches, suggest cleanup but don't delete without confirmation.

### Step 5: Clear Context

Run `/clear` to reset the conversation context.

### Step 6: Report

```
Hero Reset Summary
==================
Branch: <default-branch>
Status: Up to date with origin

Pulled: N new commits
Stashed: [yes/no]
Context: Cleared
```
