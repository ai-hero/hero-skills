---
name: hero-commit
# prettier-ignore
description: Review and commit code changes, plus manage pre-commit hooks. Use "review" (default when changes exist) for ruthless self-review, pre-commit checks, changeset grouping, and conventional commits. Use "init|update|status" to manage hook configuration. Works with any project structure.
argument-hint: [review|init|update|status] [focus-area]
disable-model-invocation: true
---

# Hero Commit - Pre-commit Management + Code Review & Commit

Two modes in one skill: manage pre-commit hook configuration, or review and commit your changes.

## Arguments

- `$ARGUMENTS` - Command to run:
  - `init` - Initialize pre-commit config for the project
  - `update` - Update config based on current project structure
  - `add-project <name>` - Add hooks for a specific subproject
  - `status` - Show pre-commit status and detected projects
  - `review [focus]` - Ruthless code review + commit (default if uncommitted changes exist)

## Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Code Quality** → pre-commit, linters, formatters for hook configuration
- **Repository** → commit convention (conventional, angular, none)
- **Projects** → which subprojects to configure hooks for
- **Project Management** → issue prefix for `Fixes:` / `Relates to:` trailers

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

---

**Auto-detection:** If no argument given, check for uncommitted changes. If changes exist, run `review`. Otherwise, run `status`.

---

## Mode A: Hook Management (init | update | status | add-project)

### init

1. **Check installation:**

```bash
which pre-commit || echo "NOT_INSTALLED"
ls -la .pre-commit-config.yaml 2>/dev/null || echo "NO_CONFIG"
```

If not installed: `brew install pre-commit` / `pip install pre-commit` / `uv tool install pre-commit`

2. **Detect projects** in repo (and immediate subdirectories for monorepos):

| Indicator | Project Type |
|-----------|--------------|
| `pyproject.toml` | Python (uv) |
| `pyproject.toml` + `app/` folder | Python FastAPI |
| `package.json` + `next.config.*` | Next.js |
| `package.json` + `vite.config.*` | Vite |
| `Dockerfile*` | Docker |
| `*.yaml` in k8s/ or kubernetes/ | Kubernetes |

3. **Generate `.pre-commit-config.yaml`** with sections per detected project:

```yaml
default_install_hook_types:
  - pre-commit
  - pre-push
  - commit-msg

repos:
  # General: trailing whitespace, end-of-file, large files, secrets
  # Python: ruff (lint + format), mypy, pytest (pre-push)
  # Frontend: prettier, eslint, tsc
  # Markdown: markdownlint
  # Commit messages: conventional commits
```

4. **Install hooks:**

```bash
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

5. **Validate:** `pre-commit run --all-files --show-diff-on-failure`

### update

Re-detect projects, update config preserving `# CUSTOM:` sections, reinstall.

### add-project \<name\>

Detect type at `<name>/`, add hooks, reinstall.

### status

Show installation status, detected projects, configured hooks.

---

## Mode B: Review & Commit (review)

### Philosophy

- Do not sugarcoat - if something is wrong, say why
- Ask before making significant changes
- Prefer simplicity over over-engineering
- Every commit should be a logical, coherent unit of work

### Step 1: Verify Branch

```bash
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"
```

**If on main/master:** Warn and stop. Let user create a feature branch or explicitly continue.

### Step 2: Run Pre-commit

```bash
pre-commit run --all-files
```

If checks fail: report errors, offer to auto-fix, do not proceed until passing.

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

Fix any CRITICAL or WARNING issues found. Re-run pre-commit after fixes.

### Step 6: Group into Changesets

Group logically related changes:

- Same feature/component together
- Same type of change together
- Dependency updates separate
- Documentation separate

### Step 7: Commit Each Changeset

```bash
git add <file1> <file2> ...
git diff --cached --stat
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<body if needed>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Types:** feat, fix, refactor, docs, style, test, chore, perf

**If issue ID in branch name:** Add `Fixes: PROJ-123` or `Relates to: PROJ-123`.

### Step 8: Post-Commit Validation

```bash
pre-commit run --hook-stage pre-push --all-files
```

### Step 9: Summary

```
Hero Commit Summary
======================
Branch: <branch-name>
Commits Created: N

1. <type>(<scope>): <description>
   Files: file1, file2 (+X -Y)

Pre-commit: PASSED
Pre-push: PASSED

Ready to push with /hero-push
```

---

## Important Notes

- **DO NOT PUSH** - Let user decide with `/hero-push`
- Never use `--no-verify` to skip hooks
- Never amend previous commits without explicit request
- Always include `Co-Authored-By` for AI-assisted commits
- Custom hooks in config preserved via `# CUSTOM:` comments
