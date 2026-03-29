---
name: hero-pr-create
# prettier-ignore
description: Create a pull request from the current branch. Supports draft PRs. Pushes if needed, generates title and description from commits.
argument-hint: [draft]
disable-model-invocation: true
---

# Hero PR - Create Pull Request

Push the current branch and create a pull request. Supports draft mode.

## Arguments

- `$ARGUMENTS` - Optional modifiers:
  - `draft` - Create as a draft PR
  - If omitted: Create a regular PR

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Repository** → default-branch (PR base), branch-convention
- **Project Management** → issue-prefix for linking PRs to issues

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Verify Branch

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"
```

**If on main/master:** Stop — cannot create a PR from the default branch to itself. Suggest creating a feature branch first.

### Step 2: Check for Uncommitted Changes

```bash
git status --porcelain
```

**If uncommitted changes exist:**

```
Warning: You have uncommitted changes.

Options:
1. Run /hero-commit first
2. Proceed without committing (changes won't be in the PR)
3. Cancel
```

Stop and let user decide.

### Step 3: Push to Remote

```bash
git push -u origin $(git branch --show-current)
```

**Handle push failures:**

| Error | Action |
|-------|--------|
| `rejected` (non-fast-forward) | Suggest `git pull --rebase` |
| `permission denied` | Suggest `gh auth login` |
| `remote not found` | Check remote configuration |

### Step 4: Check for Existing PR

```bash
gh pr list --head $(git branch --show-current) --json number,url,title,state,isDraft
```

**If PR already exists:** Report it and stop. If it's a draft and user didn't request draft, ask if they want to mark it ready.

### Step 5: Gather PR Content

```bash
DEFAULT_BRANCH=main  # or from HERO.md

# Commits on this branch
git log origin/$DEFAULT_BRANCH..HEAD --pretty=format:"%s%n%b" --reverse

# Changed files
git diff origin/$DEFAULT_BRANCH..HEAD --stat
git diff origin/$DEFAULT_BRANCH..HEAD --name-only
```

Also check for a PR template:

```bash
cat .github/pull_request_template.md 2>/dev/null || cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "NO_TEMPLATE"
```

If a template exists, fill it in. Otherwise use the default format below.

### Step 6: Create Pull Request

Determine the draft flag:

```bash
DRAFT_FLAG=""
if [ "$ARGUMENTS" = "draft" ]; then
  DRAFT_FLAG="--draft"
fi
```

Generate a title from commits — keep under 70 characters. Generate the body by listing each commit as a changeset with its files and a one-line description:

```bash
gh pr create $DRAFT_FLAG --title "<title>" --body "$(cat <<'EOF'
## Summary
[1-3 sentence overview of what this PR accomplishes]

## Changesets

### 1. `<commit-type>(<scope>): <commit-message>`
**Files:** `file1.ts`, `file2.ts` (+A -D)
<Brief description of what this commit does and why>

### 2. `<commit-type>(<scope>): <commit-message>`
**Files:** `file3.py` (+A -D)
<Brief description of what this commit does and why>

[...repeat for each commit on the branch]

## Test Plan
- [ ] [Test step 1]
- [ ] [Test step 2]

## Related Issues
[Link issues if mentioned in commits or branch name]

---
Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

### Step 7: Report

```
Hero PR Summary
===============
Branch: <branch-name> → <default-branch>
Type: [Draft PR | PR]

Title: <pr-title>
PR: #<number>
URL: <pr-url>

Files: N changed (+A -D)
Commits: M
```

## Large PR Warning

If diff >1000 lines or >50 files, warn and suggest breaking into smaller PRs.

## Notes

- Uses GitHub CLI (`gh`) for PR operations
- Respects repository PR templates if they exist
- If issue ID found in branch name, links it in the PR body
- Does NOT merge — use `/hero-push <target>` for that
