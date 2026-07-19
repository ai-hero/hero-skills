---
name: push-pr
# prettier-ignore
description: Commit your work and push it — smart conventional commit, branch off the default branch if needed, then open a draft PR and report CI. Pass `ready` for a non-draft PR, or a branch name to merge into a target.
argument-hint: [ready|target-branch]
---

# Push — Commit, Push, Draft PR, and Merge Workflow

Commit any outstanding work with a smart conventional commit, branch off the default branch first if you're still on it, push to the remote repository, and open a **draft PR by default**. Drafts are the default because the author should run `hero-skills:review-pr` (which calls all pr-review-toolkit agents, applies fixes, and asks for confirmation) before promoting the PR to ready-for-review. After a successful push, this skill also prints a brief CI status summary.

## Arguments

- `$ARGUMENTS` - Optional modifier or target branch:
  - (none, default) - Commit if dirty, push, and create a **draft** PR
  - `ready` - Commit if dirty, push, and create a non-draft PR (ready for review immediately) — only use when you have already self-reviewed or for trivial changes
  - If a branch name (e.g., `main`, `develop`): Commit if dirty, push, then merge into that target branch (no PR)

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Stale-HERO check — fast subset of the plugin's check-hero-staleness.sh.
# Keep aligned with the copies in test-changes/one-shot.
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

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default branch (for branching and PR base), branch convention, commit convention
- **Code Quality** → linters, formatters (for the pre-commit steps)
- **CI/CD** → platform name for PR description context and CI status reporting
- **Project Management** → issue prefix for branch names, `Fixes:`/`Relates to:` trailers, and linking PRs to issues

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with defaults. If the stale-HERO hint fired, mention it once to the user but do not block.

### Step 1: Branch if on Default Branch

Never commit or push directly to the default branch.

```bash
BRANCH=$(git branch --show-current)
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
echo "Current branch: $BRANCH (default: $DEFAULT_BRANCH)"
```

**If `$BRANCH` is not `$DEFAULT_BRANCH`, skip this step entirely** and proceed to Step 2 on the current branch.

**If `$BRANCH` equals `$DEFAULT_BRANCH`:** pull it fresh before branching off it — a stale local default branch means the new feature branch (and later, the PR's base diff) silently misses recent commits.

```bash
if ! git pull --ff-only origin "$DEFAULT_BRANCH"; then
  echo "WARN: 'git pull --ff-only origin $DEFAULT_BRANCH' failed — local $DEFAULT_BRANCH may be divergent or dirty."
  echo "Resolve manually (check 'git status'), then re-run."
fi
```

Then derive a feature-branch name from the diff and check out a new branch. Uncommitted changes follow the checkout automatically — do **not** stash.

Generate `BRANCH_NAME` as `{type}/{slug}`:

- Infer `{type}` from the changed files and diff content: `docs/` for docs-only changes, `test/` for test-only changes, `feat/` for new functionality, `fix/` for bug fixes, `refactor/` for restructuring, `chore/` for tooling/CI/dependency bumps.
- Derive a 3-5 word `{slug}` from the diff summary — lowercase, hyphens instead of spaces, strip filler words (the, a, an, for, to, in), max 50 characters.
- If an issue prefix is configured in HERO.md and an issue ID appears in the diff or a commit message draft, prefer `{issue-id}-{slug}`.

Present the proposed name and let the user confirm or modify:

```
You are on '$BRANCH', which is the default branch. push-pr never commits or pushes directly to the default branch.

Proposed branch: BRANCH_NAME

Options:
1. Use the proposed name
2. Provide your own branch name
3. Cancel
```

**Wait for confirmation**, then:

```bash
git checkout -b "$BRANCH_NAME"
git branch --show-current
git status --porcelain
```

### Step 2: Commit Dirty Changes (Smart Commit)

```bash
git status --porcelain
```

**If the tree is clean (no output):** the work is already committed — skip straight to Step 3.

**If the tree is dirty**, run the following before pushing.

#### 2a: Run Pre-commit (if available)

```bash
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --all-files
else
  echo "NO_PRECOMMIT"
fi
```

If pre-commit is installed and checks fail: report errors, offer to auto-fix, do not proceed until passing. If not installed, skip and continue.

#### 2b: Analyze Changes

```bash
git status --porcelain
git diff
git diff --cached
git diff --stat
```

For each changed file: read the diff, understand its purpose, assess quality.

#### 2c: Simplify Code

Invoke the `simplify` skill via the Skill tool. `simplify` is **not** part of this plugin — it ships separately (see the user-invocable skills list in the current session). It reviews the current diff for reuse, quality, and efficiency and fixes any issues found before the commit lands. Step 2g below handles the post-fix pre-push dry-run.

If the `simplify` skill is unavailable in this environment, report `NO_SIMPLIFY_SKILL — falling back to inline checklist` and apply this check before continuing:

- [ ] No premature abstractions
- [ ] No over-engineering
- [ ] Could this be simpler?

#### 2d: Ruthless Code Review

Additional checks beyond simplify:

**Naming Consistency**

- Same concepts use same names throughout
- Imports match exports

**Code Quality**

- [ ] No debug code (print, console.log, debugger)
- [ ] No commented-out code
- [ ] No TODO/FIXME without associated issue
- [ ] No obvious security issues

**Completeness**

- [ ] All renames updated everywhere
- [ ] Imports correct
- [ ] Tests updated if behavior changed

**Report:**

```
Code Review Summary
===================
Files Changed: N
Lines Added: A, Removed: D

Issues Found:
- CRITICAL: FILE:LINE — description
- WARNING: FILE:LINE — description

Suggestions:
- IMPROVEMENT
```

Fix any CRITICAL or WARNING issues found. Re-run pre-commit after fixes (if available).

#### 2e: Group into Changesets

Group logically related changes:

- Same feature/component together
- Same type of change together
- Dependency updates separate
- Documentation separate

#### 2f: Commit Each Changeset

```bash
git add file1 file2 ...
git diff --cached --stat
git commit -m "$(cat <<'EOF'
{type}({scope}): {description}

{body if needed}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

**Types:** feat, fix, refactor, docs, style, test, chore, perf

**If issue ID in branch name:** Add `Fixes: PROJ-123` or `Relates to: PROJ-123`.

#### 2g: Post-Commit Pre-Push Dry-Run

Dry-run any pre-push hooks now so failures surface before the actual push (Workflow A1 / B1):

```bash
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --hook-stage pre-push --all-files
else
  echo "NO_PRECOMMIT"
fi
```

#### 2h: Commit Summary

```
Commit Summary
======================
Branch: {branch-name}
Commits Created: N

1. {type}({scope}): {description}
   Files: file1, file2 (+X -Y)

Pre-commit: PASSED (or SKIPPED)
```

Proceed to Step 3.

### Step 3: Determine Workflow

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

**If PR exists:** Report it and skip to A5 (CI status).

### A3: Create Pull Request

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RAW_DEFAULT=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${RAW_DEFAULT:-main}
# Surface the resolved base and whether it came from HERO.md or the fallback,
# so a missing/mistyped default-branch key can't silently open the PR against
# the wrong base (e.g. `main` on a repo whose real default is `master`).
if [ -z "$RAW_DEFAULT" ]; then
  echo "PR base: $DEFAULT_BRANCH (fallback — HERO.md default-branch not found)"
else
  echo "PR base: $DEFAULT_BRANCH (from HERO.md)"
fi
# Refresh the remote-tracking ref before diffing against it — Step 1 only
# fetches when this branch came from the default branch; a branch that
# existed before this run may never have fetched at all this session.
git fetch origin "$DEFAULT_BRANCH" || echo "WARN: fetch failed — origin/$DEFAULT_BRANCH may be stale for this diff."
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

**Generate PR content by listing each commit as a changeset with its files and description.** Keep the title unbranded (no "Hero"/"hero-skills"). End the body with exactly one attribution line, `_Generated using hero-skills._`:

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

_Generated using hero-skills._
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

Next step: hero-skills:review-pr — self-review, runs pr-review-toolkit agents, applies fixes, marks ready (offer to auto-run: ask "Run it now? [y/N]", invoke via Skill tool on yes)
```

If the PR was created with `ready` (non-draft), report `PR created` instead of `Draft PR created`, skip the self-review hint, and pick exactly one next step instead:

- **This PR touched dependency files** (`package.json`, `pyproject.toml`, lockfiles, `.github/workflows/*.yml` version pins): `Next step: hero-skills:scan-vulns` (print only — model-invocation-restricted, cannot auto-run).
- **Otherwise**: `Next step: hero-skills:ship-pr — once green, @auto-approve, merge, verify deploy, reset` (offer to auto-run).

### A5: Report CI Status

Give a brief, non-blocking CI summary after the push. Skip this step entirely if `gh` is unavailable.

```bash
BRANCH=$(git branch --show-current)
# Distinguish three outcomes explicitly so an errored gh call is never mistaken
# for "no runs yet" (which would otherwise read as a clean/absent CI state):
if ! gh repo view --json nameWithOwner -q .nameWithOwner >/dev/null 2>&1; then
  echo "CI status unavailable (gh not authenticated or no remote) — skipping CI block."
else
  RUNS_JSON=$(gh run list --branch "$BRANCH" --limit 5 \
    --json databaseId,name,status,conclusion,headBranch,createdAt,url 2>&1)
  if [ $? -ne 0 ]; then
    echo "CI status unavailable (gh run list failed) — skipping CI block: $RUNS_JSON"
  elif [ "$(printf '%s' "$RUNS_JSON" | tr -d '[:space:]')" = "[]" ]; then
    echo "Overall: NO RUNS YET"
  else
    printf '%s\n' "$RUNS_JSON"   # classify PASSING / FAILING / IN PROGRESS from these
  fi
fi
```

For each run, report: workflow name, status (queued/in_progress/completed), conclusion (success/failure/cancelled/skipped).

If any run failed, surface the failing job/step:

```bash
gh run view RUN_ID --json jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | {name, steps: [.steps[] | select(.conclusion=="failure") | .name]}'
```

**Do not poll or block on long-running CI.** If runs are still `queued`/`in_progress`, say so once and note that re-running this command later will show updated status.

Print a compact summary:

```
CI Status
=========
Branch: {branch-name}

Workflow Runs (latest 5):
  1. Build & Test   SUCCESS   2m 15s
  2. Lint           SUCCESS   45s
  3. Docker Build   FAILURE   1m 48s

Overall: PASSING | FAILING | IN PROGRESS | NO RUNS YET
```

If `gh` is unavailable, or `gh run list` errors (no workflows, no auth, etc.), skip this step silently and omit the CI Status block from the report.

---

## Workflow B: Merge to Target Branch

### B1: Push Feature Branch

```bash
git push -u origin $(git branch --show-current)
```

### B2: Switch to Target and Pull

Before switching, verify the working tree is clean (Step 2 should have committed everything, but double-check):

```bash
FEATURE_BRANCH=$(git branch --show-current)
git status --porcelain
```

**If uncommitted changes exist at this point, STOP.** Do not switch branches — go back and commit them (re-run Step 2) before continuing.

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
- [ ] Working tree clean before push (Step 2 committed any dirty changes)
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
- Stash changes to work around a dirty tree — commit them instead (Step 2)

## Large PR Warning

If diff >1000 lines or >50 files, warn and suggest breaking into smaller PRs.

## Notes

- Uses GitHub CLI (`gh`) for PR, branch, and CI operations
- Respects repository PR templates if they exist
- Always creates merge commits for traceability
- Never commits or pushes directly to the default branch — Step 1 branches off first
