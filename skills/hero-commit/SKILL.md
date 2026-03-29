---
name: hero-commit
# prettier-ignore
description: Smart commit - reviews changes, groups logical changesets, and creates conventional commits. Runs pre-commit hooks if available.
disable-model-invocation: true
---

# Hero Commit - Smart Review & Commit

Reviews your changes, groups them into logical changesets, and creates clean conventional commits.

## Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters, formatters
- **Repository** → commit convention (conventional, angular, none)
- **Project Management** → issue prefix for `Fixes:` / `Relates to:` trailers

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

## Step 1: Verify Branch

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"
```

**If on main/master:** Warn the user. Ask if they want to:

1. Create a new branch first (ask for branch name)
2. Proceed on main anyway

Do NOT continue until the user responds. If they choose to create a branch, run `git checkout -b $BRANCH_NAME` before proceeding.

## Step 2: Run Pre-commit (if available)

```bash
which pre-commit && pre-commit run --all-files || echo "NO_PRECOMMIT"
```

If pre-commit is installed and checks fail: report errors, offer to auto-fix, do not proceed until passing.
If pre-commit is not installed: skip and continue.

## Step 3: Analyze Changes

```bash
git status --porcelain
git diff
git diff --cached
git diff --stat
```

For each changed file: read the diff, understand purpose, assess quality.

## Step 4: Ruthless Code Review

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

## Step 5: Fix Issues

Fix any CRITICAL or WARNING issues found. Re-run pre-commit after fixes (if available).

## Step 6: Group into Changesets

Group logically related changes:

- Same feature/component together
- Same type of change together
- Dependency updates separate
- Documentation separate

## Step 7: Commit Each Changeset

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

## Step 8: Post-Commit Validation

```bash
which pre-commit && pre-commit run --hook-stage pre-push --all-files || echo "NO_PRECOMMIT"
```

## Step 9: Summary

```
Hero Commit Summary
======================
Branch: {branch-name}
Commits Created: N

1. {type}({scope}): {description}
   Files: file1, file2 (+X -Y)

Pre-commit: PASSED (or SKIPPED)

Ready to push with /hero-push
```

---

## Philosophy

- Do not sugarcoat - if something is wrong, say why
- Ask before making significant changes
- Prefer simplicity over over-engineering
- Every commit should be a logical, coherent unit of work

## Important Notes

- **DO NOT PUSH** - Let user decide with `/hero-push`
- Never use `--no-verify` to skip hooks
- Never amend previous commits without explicit request
- Always include `Co-Authored-By` for AI-assisted commits
