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

**If uncommitted changes exist:**

```
Warning: You have uncommitted changes on $BRANCH.

Options:
1. Stash changes, create branch, then pop stash
2. Carry changes to the new branch (default git behavior)
3. Cancel
```

Stop and let user decide.

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
<type>/<short-description>
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

### Step 4: Create Branch

```bash
# Check that the branch does not already exist (local or remote)
if git branch --list "<branch-name>" | grep -q .; then
  echo "Branch '<branch-name>' already exists locally. Please choose a different name."
  # Ask user to rename or append a number
fi

git checkout -b <branch-name>
```

### Step 5: Report

```
Hero Branch Summary
===================
Created: <branch-name>
From: <default-branch> (up to date)

Ready to work. When done:
  /hero-commit  - review and commit changes
  /hero-push    - push and create PR
```

## Notes

- Always pulls latest default branch before branching
- Never creates a branch that already exists — check first with `git branch --list`
- If branch name already exists, suggest appending a number or ask user to rename
