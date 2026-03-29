---
name: hero-push
# prettier-ignore
description: Push current work to remote, create PRs, or merge to target branches. Handles the complete push/PR/merge workflow for any repository.
argument-hint: [target-branch]
disable-model-invocation: true
---

# Hero Push - Push, PR, and Merge Workflow

Push your current work to the remote repository. Handles pushing, PR creation, and optional merging to target branches.

## Arguments

- `$ARGUMENTS` - Optional target branch to merge into (e.g., `main`, `develop`)
  - If not provided: Push current branch and create PR if needed
  - If provided: Push, then merge into the target branch

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Repository** → default branch (for PR base), branch convention
- **CI/CD** → platform name for PR description context
- **Project Management** → issue prefix for linking PRs to issues

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Assess Current State

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"

git status --porcelain
git rev-list --count origin/$BRANCH..$BRANCH 2>/dev/null || echo "NEW_BRANCH"
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "NO_UPSTREAM"
```

**If uncommitted changes exist:**

```
Warning: You have uncommitted changes.

Options:
1. Run /hero-commit review first
2. Stash changes and proceed
3. Cancel
```

Stop and let user decide.

### Step 2: Determine Workflow

| Target | Workflow |
|--------|----------|
| (none) | Push + PR |
| `main`/`master` | Push + Merge to main |
| Other branch | Push + Merge to target |

---

## Workflow A: Push and Create PR (No Target)

### A1: Push to Remote

```bash
git push -u origin $(git branch --show-current)
```

**Handle push failures:**

| Error | Action |
|-------|--------|
| `rejected` (non-fast-forward) | Suggest `git pull --rebase` |
| `permission denied` | Suggest `gh auth login` |
| `remote not found` | Check remote configuration |

### A2: Check for Existing PR

```bash
gh pr list --head $(git branch --show-current) --json number,url,title,state
```

**If PR exists:** Report it and done.

### A3: Create Pull Request

```bash
git log origin/main..HEAD --pretty=format:"%s%n%b" --reverse
git diff origin/main..HEAD --stat
git diff origin/main..HEAD --name-only
```

**Generate PR content by listing each commit as a changeset with its files and description:**

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
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
[Link issues if mentioned in commits]

---
Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

### A4: Report Success

```
Hero Push Summary
=================
Branch: <branch-name>
Action: Push + Create PR

Commits pushed: N
PR created: #42
URL: <pr-url>
```

---

## Workflow B: Merge to Target Branch

### B1: Push Feature Branch

```bash
git push -u origin $(git branch --show-current)
```

### B2: Switch to Target and Pull

```bash
FEATURE_BRANCH=$(git branch --show-current)
git checkout <target>
git pull origin <target>
```

### B3: Merge Feature Branch

```bash
git merge $FEATURE_BRANCH --no-ff -m "Merge branch '$FEATURE_BRANCH' into <target>"
```

**If merge conflicts:** Stop and let user resolve.

### B4: Push Target

```bash
git push origin <target>
```

### B5: Report and Suggest Cleanup

```
Hero Push Summary
=================
Source: <feature-branch>
Target: <target>

Merged successfully!

Suggestion: Delete the feature branch?
  git branch -d <feature-branch>
  git push origin --delete <feature-branch>
```

---

## Safety Checks

- [ ] Pre-push hooks pass before any push
- [ ] No uncommitted changes (or user acknowledged)
- [ ] Not force pushing
- [ ] Merge commits (not fast-forward) for traceability

### Never Do

- Force push to main/master without explicit confirmation
- Auto-resolve merge conflicts
- Skip hooks with `--no-verify`
- Push secrets or sensitive files

## Large PR Warning

If diff >1000 lines or >50 files, warn and suggest breaking into smaller PRs.

## Notes

- Uses GitHub CLI (`gh`) for PR operations
- Respects repository PR templates if they exist
- Always creates merge commits for traceability
