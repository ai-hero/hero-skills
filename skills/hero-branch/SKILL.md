---
name: hero-branch
# prettier-ignore
description: Create a feature branch from a short description of what you'll do. Names the branch using the repo's branch convention from HERO.md.
argument-hint: <description-of-work>
disable-model-invocation: true
---

# Hero Branch - Create Feature Branch from Description

Describe what you're going to work on and this skill creates a properly named feature branch based on the repository's branch convention.

## Arguments

- `$ARGUMENTS` - A short description of the work (required)
  - e.g., `add user authentication`
  - e.g., `fix login page crash on mobile`
  - e.g., `refactor database connection pooling`

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default-branch (branch from here), branch-convention
- **Project Management** → issue-prefix (for linking to issues)

If `HERO.md` is missing, suggest `/hero-init` but proceed with `github-standard` convention.

### Step 1: Check Current State

```bash
git status --porcelain
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"
```

**If uncommitted changes exist, STOP and show:**

```
⚠ You have uncommitted changes on '$BRANCH':

  <list changed files from git status>

These changes will be affected by switching branches.

Options:
1. Stash changes (saved as "hero-branch: WIP on $BRANCH") — will auto-restore when done
2. Carry changes to the new branch (default git behavior — changes stay unstaged)
3. Cancel — go back and commit or handle changes first
```

**STOP and wait for user to choose.** Do NOT proceed without explicit confirmation.

**If user chooses option 1 (stash):**

```bash
git stash push -m "hero-branch: WIP on $BRANCH"
```

Report the stash ref so the user can find it later:

```
Stashed as: stash@{0} — "hero-branch: WIP on $BRANCH"
Will auto-restore after branch creation.
```

Track that a stash was created (for Step 5 restore).

### Step 2: Ensure on Default Branch

```bash
DEFAULT_BRANCH=main  # or from HERO.md
CURRENT=$(git branch --show-current)

if [ "$CURRENT" != "$DEFAULT_BRANCH" ]; then
  echo "Currently on $CURRENT, not $DEFAULT_BRANCH"
fi
```

If not on the default branch, ask:

```
You're on '$CURRENT', not '$DEFAULT_BRANCH'.

Options:
1. Switch to $DEFAULT_BRANCH first, then branch (recommended)
2. Branch from $CURRENT instead
```

**If option 1 (switch to default branch):**

```bash
git checkout "$DEFAULT_BRANCH"
git pull origin "$DEFAULT_BRANCH"
```

**If option 2 (branch from current):** Skip the pull — branch from `$CURRENT` as-is.

### Step 3: Generate Branch Name

Based on the branch-convention from HERO.md:

**github-standard** (default):

```
{type}/{short-description}
```

**Examples by work type:**

| Description | Branch Name |
|-------------|-------------|
| add user authentication | feat/add-user-authentication |
| fix login page crash | fix/login-page-crash |
| refactor database pooling | refactor/database-pooling |
| update CI pipeline | chore/update-ci-pipeline |

**Rules:**

- Infer type from description: `add/create/implement` → `feat/`, `fix/repair/resolve` → `fix/`, `refactor/clean/restructure` → `refactor/`, `update/bump/upgrade` → `chore/`
- Lowercase, hyphens instead of spaces
- Max 50 characters for the description part
- Strip filler words (the, a, an, for, to, in)
- If issue-prefix is set and user mentions an issue number, include it: `feat/PROJ-123-add-auth`

**If branch-convention is `custom` or has a branch-template in HERO.md**, follow that template instead.

Present the proposed branch name and let the user confirm or modify:

```
Proposed branch: feat/add-user-authentication

Enter to confirm, or type a different name:
```

### Step 4: Validate Branch Name Against Pre-commit

If `.pre-commit-config.yaml` exists, check for a `no-commit-to-branch` hook:

```bash
if [ -f .pre-commit-config.yaml ]; then
  grep -A5 "no-commit-to-branch" .pre-commit-config.yaml
fi
```

If a branch pattern is enforced (e.g., `feature/*`, `fix/*`, etc.), verify the proposed branch name matches. If it doesn't, warn the user and suggest a compliant name before creating the branch. This prevents frustrating commit rejections later.

### Step 5: Create Branch

```bash
# Check that the branch does not already exist (local or remote)
if git branch --list "$BRANCH_NAME" | grep -q .; then
  echo "Branch '$BRANCH_NAME' already exists locally. Please choose a different name."
  # Ask user to rename or append a number
fi

git checkout -b $BRANCH_NAME
```

### Step 6: Restore Stash (if applicable)

If changes were stashed in Step 1:

```bash
git stash pop
```

Report the restore:

```
Restored stashed changes from "hero-branch: WIP on $ORIGINAL_BRANCH"
```

If the stash pop has conflicts, report them clearly and let the user resolve.

### Step 7: Report

```
Hero Branch Summary
===================
Created: {branch-name}
From: {default-branch} (up to date)
Stash: [restored / carried over / n/a]

Ready to work. When done:
  /hero-commit  - review and commit changes
  /hero-push    - push and create PR
```

## Notes

- Always pulls latest default branch before branching
- Never creates a branch that already exists — check first with `git branch --list`
- If branch name already exists, suggest appending a number or ask user to rename
