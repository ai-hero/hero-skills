---
name: push-pr
# prettier-ignore
description: Push current work to remote and open a draft PR by default, so the author can run hero-skills:review-pr before human review. Pass `ready` for a non-draft PR, or a branch name to merge into a target.
argument-hint: [ready|target-branch]
disable-model-invocation: true
---

# Push — Push, Draft PR, and Merge Workflow

Push your current work to the remote repository and open a **draft PR by default**. Drafts are the default because the author should run `hero-skills:review-pr` (which calls all pr-review-toolkit agents, applies fixes, and asks for confirmation) before promoting the PR to ready-for-review.

## Arguments

- `$ARGUMENTS` - Optional modifier or target branch:
  - (none, default) - Push and create a **draft** PR
  - `ready` - Push and create a non-draft PR (ready for review immediately) — only use when you have already self-reviewed or for trivial changes
  - If a branch name (e.g., `main`, `develop`): Push, then merge into that target branch (no PR)

## Instructions

### Step 0: Load Hero Configuration

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

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default branch (for PR base), branch convention
- **CI/CD** → platform name for PR description context
- **Project Management** → issue prefix for linking PRs to issues

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with defaults. If the stale-HERO hint fired, mention it once to the user but do not block.

### Step 1: Assess Current State

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"

git status --porcelain
git rev-list --count origin/$BRANCH..$BRANCH 2>/dev/null || echo "NEW_BRANCH"
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "NO_UPSTREAM"
```

**If uncommitted changes exist, STOP and show:**

```
You have uncommitted changes:

  (list changed files from git status)

Options:
1. Run hero-skills:commit-changes to review and commit first (recommended)
2. Cancel — go back and handle changes first
```

**STOP and wait for user to choose.** Do NOT offer to stash here — pushing with uncommitted changes is almost always a mistake. The user should commit or explicitly handle their changes first.

### Step 2: Determine Workflow

| Argument | Workflow |
|----------|----------|
| (none, default) | Push + **Draft** PR |
| `ready` | Push + non-draft PR |
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
DEFAULT_BRANCH=main  # or from HERO.md
git log origin/$DEFAULT_BRANCH..HEAD --pretty=format:"%s%n%b" --reverse
git diff origin/$DEFAULT_BRANCH..HEAD --stat
git diff origin/$DEFAULT_BRANCH..HEAD --name-only
```

Determine the draft flag (drafts are the default). Parse the first whitespace-separated token of `$ARGUMENTS` so trailing whitespace or extra arguments don't silently fall through:

```bash
# Draft is the default; pass `ready` to opt into a non-draft PR
FIRST_ARG=$(printf '%s' "$ARGUMENTS" | awk '{print $1}')
DRAFT_FLAG="--draft"
if [ "$FIRST_ARG" = "ready" ]; then
  DRAFT_FLAG=""
fi
```

**Generate the PR title from commit history** (use the most descriptive commit, or summarize if multiple):

```bash
# Default to first commit subject; override with a better summary if needed
PR_TITLE="$(git log origin/$DEFAULT_BRANCH..HEAD --pretty=%s | head -1)"
```

**Generate PR content by listing each commit as a changeset with its files and description:**

```bash
gh pr create $DRAFT_FLAG --base "$DEFAULT_BRANCH" --title "$PR_TITLE" --body "$(cat <<'EOF'
## Summary
[1-3 sentence overview of what this PR accomplishes]

## Changesets

### 1. `commit-type(scope): commit-message`
**Files:** `file1.ts`, `file2.ts` (+A -D)
Brief description of what this commit does and why

### 2. `commit-type(scope): commit-message`
**Files:** `file3.py` (+A -D)
Brief description of what this commit does and why

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
Push Summary
=================
Branch: {branch-name}
Action: Push + Create Draft PR

Commits pushed: N
Draft PR created: #{number}
URL: {pr-url}

Next steps:
  hero-skills:review-pr   # Run automated review and fix findings before marking ready
```

If the PR was created with `ready` (non-draft), report `PR created` instead of `Draft PR created` and skip the self-review hint.

---

## Workflow B: Merge to Target Branch

### B1: Push Feature Branch

```bash
git push -u origin $(git branch --show-current)
```

### B2: Switch to Target and Pull

Before switching, verify the working tree is clean (Step 1 should have caught this, but double-check):

```bash
FEATURE_BRANCH=$(git branch --show-current)
git status --porcelain
```

**If uncommitted changes exist at this point, STOP.** Do not switch branches. Ask the user to commit or cancel.

```bash
git checkout $TARGET_BRANCH
git pull origin $TARGET_BRANCH
```

### B3: Merge Feature Branch

```bash
git merge $FEATURE_BRANCH --no-ff -m "Merge branch '$FEATURE_BRANCH' into $TARGET_BRANCH"
```

**If merge conflicts:** Stop and let user resolve.

### B4: Push Target

```bash
git push origin $TARGET_BRANCH
```

### B5: Report and Suggest Cleanup

```
Push Summary
=================
Source: {feature-branch}
Target: {target-branch}

Merged successfully!

Suggestion: Delete the feature branch?
  git branch -d {feature-branch}
  git push origin --delete {feature-branch}
```

---

## Safety Checks

- [ ] Pre-push hooks pass before any push
- [ ] No uncommitted changes (or user acknowledged)
- [ ] Not force pushing
- [ ] Merge commits (not fast-forward) for traceability

### Pre-push Hook Awareness

If `.pre-commit-config.yaml` exists, check for `pre-push` stage hooks:

```bash
if [ -f .pre-commit-config.yaml ]; then
  grep -B2 "pre-push" .pre-commit-config.yaml
fi
```

Pre-push hooks often run tests, builds, and security scans which can take minutes. If heavy hooks are detected, warn the user before pushing:

```
Note: Pre-push hooks will run before push completes.
Detected: [pytest, eslint, build, semgrep, trivy, etc.]
This may take a few minutes.
```

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
