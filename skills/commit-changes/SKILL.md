---
name: commit-changes
# prettier-ignore
description: Smart commit - reviews changes, groups logical changesets, and creates conventional commits. Runs pre-commit hooks if available.
disable-model-invocation: true
---

# Commit — Smart Review & Commit

Reviews your changes, groups them into logical changesets, and creates clean conventional commits.

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters, formatters
- **Repository** → commit convention (conventional, angular, none)
- **Project Management** → issue prefix for `Fixes:` / `Relates to:` trailers

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with auto-detection.

### Step 1: Verify Branch — Never Commit to Main

```bash
BRANCH=$(git branch --show-current)
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
echo "Current branch: $BRANCH (default: $DEFAULT_BRANCH)"
```

**If on the default branch (main/master) or any protected branch:** STOP. Never commit directly to main. Show:

```
You are on '$BRANCH', which is the default branch. Hero Commit never commits to the default branch.

I will create a feature branch from your current changes. Suggested name: '{suggested-branch}'

Options:
1. Use suggested name '{suggested-branch}'
2. Provide your own branch name
3. Cancel
```

Generate `{suggested-branch}` from the diff:

- If commit-convention is `conventional`, infer the type from changed files (`docs/` → `docs/`, tests only → `test/`, source code → `feat/` or `fix/` based on heuristics) and append a 3-5 word slug derived from the diff summary, e.g. `feat/add-self-review`, `fix/null-handling-in-auth`.
- If branch-convention from HERO.md uses an issue prefix and one is mentioned in the diff or commit message draft, prefer `{issue-id}-{slug}`.

**Wait for user choice.** Then:

```bash
git checkout -b "$BRANCH_NAME"
```

The uncommitted changes follow the checkout into the new branch automatically — no stash needed. Confirm:

```bash
git branch --show-current
git status --porcelain
```

Proceed with the rest of the skill on the new branch.

### Step 2: Run Pre-commit (if available)

```bash
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --all-files
else
  echo "NO_PRECOMMIT"
fi
```

If pre-commit is installed and checks fail: report errors, offer to auto-fix, do not proceed until passing.
If pre-commit is not installed: skip and continue.

### Step 3: Analyze Changes

```bash
git status --porcelain
git diff
git diff --cached
git diff --stat
```

For each changed file: read the diff, understand purpose, assess quality.

### Step 4: Ruthless Code Review

Review every change:

**Naming Consistency**

- Same concepts use same names throughout
- Imports match exports

**Code Quality**

- [ ] No debug code (print, console.log, debugger)
- [ ] No commented-out code
- [ ] No TODO/FIXME without associated issue
- [ ] No obvious security issues

**Simplicity**

- [ ] No premature abstractions
- [ ] No over-engineering
- [ ] Could this be simpler?

**Completeness**

- [ ] All renames updated everywhere
- [ ] Imports correct
- [ ] Tests updated if behavior changed

**Report:**

```
Code Review Summary
===================
Files Changed: 5
Lines Added: 120, Removed: 45

Issues Found:
- CRITICAL: [file:line description]
- WARNING: [file:line description]

Suggestions:
- [improvements]
```

### Step 5: Fix Issues

Fix any CRITICAL or WARNING issues found. Re-run pre-commit after fixes (if available).

### Step 6: Group into Changesets

Group logically related changes:

- Same feature/component together
- Same type of change together
- Dependency updates separate
- Documentation separate

### Step 7: Commit Each Changeset

```bash
git add file1 file2 ...
git diff --cached --stat
git commit -m "$(cat <<'EOF'
{type}({scope}): {description}

{body if needed}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Types:** feat, fix, refactor, docs, style, test, chore, perf

**If issue ID in branch name:** Add `Fixes: PROJ-123` or `Relates to: PROJ-123`.

### Step 8: Post-Commit Validation

Dry-run any pre-push hooks now so failures surface before the user runs `hero-skills:push-pr`:

```bash
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --hook-stage pre-push --all-files
else
  echo "NO_PRECOMMIT"
fi
```

### Step 9: Summary

```
Commit Summary
======================
Branch: {branch-name}
Commits Created: N

1. {type}({scope}): {description}
   Files: file1, file2 (+X -Y)

Pre-commit: PASSED (or SKIPPED)

Ready to push with hero-skills:push-pr
```

---

## Philosophy

- Do not sugarcoat - if something is wrong, say why
- Ask before making significant changes
- Prefer simplicity over over-engineering
- Every commit should be a logical, coherent unit of work

## Important Notes

- **DO NOT PUSH** - Let user decide with `hero-skills:push-pr`
- Never use `--no-verify` to skip hooks
- Never amend previous commits without explicit request
- Always include `Co-Authored-By` for AI-assisted commits
