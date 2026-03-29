---
name: hero-implement
# prettier-ignore
description: Implement a plan end to end. Takes an approved implementation plan (from /hero-plan or user-provided) and executes each step, writing code, running checks, and verifying as it goes. Works with any project structure.
argument-hint: [step-number-to-resume-from]
disable-model-invocation: true
---

# Hero Implement - Execute an Implementation Plan

Takes an approved implementation plan and implements it step by step, writing code, running checks, and verifying along the way.

## Arguments

- `$ARGUMENTS` - Optional step number to resume from (e.g., `3` to start at step 3)

## Prerequisites

- An approved implementation plan (from `/hero-plan` or provided by the user)
- On the correct feature branch
- Dependencies installed

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters, formatters, type-checkers for verification commands
- **Projects** → test commands, framework-specific patterns
- **Repository** → commit convention for any intermediate commits

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

### Step 1: Locate the Plan

Look for the plan in this priority order:

1. **Recent conversation** - If `/hero-plan` was just run, use that plan
2. **User-provided plan** - If the user pasted or described a plan
3. **Ask the user** - "What should I implement? Provide a plan or describe the feature."

Confirm the plan with the user:

```
Implementation Plan Found
=========================
Summary: [1-line summary]
Steps: N
Files to modify: X
Files to create: Y

Starting from step: [1 or $ARGUMENTS]

Proceed? [Y/n]
```

### Step 2: Verify Workspace

```bash
git branch --show-current
git status --porcelain
```

- Confirm on a feature branch (not main/master)
- Confirm working tree is clean (or warn about existing changes)
- If dependencies need installing, do it now

### Step 3: Execute Each Step

For each step in the plan:

#### 3a: Announce the Step

```
Step N/Total: [step description]
──────────────────────────────
```

#### 3b: Implement

- Read existing files before modifying them
- Follow existing patterns and conventions in the codebase
- Write clean, production-quality code
- Match the project's style (naming, formatting, structure)

#### 3c: Verify the Step

After each step, verify:

- **Syntax**: Files parse without errors
- **Imports**: All imports resolve
- **Types** (if applicable): Run type checker on changed files

```bash
# Python
uv run python -m py_compile <file>

# TypeScript
npx tsc --noEmit
```

- **Lint**: Run linter on changed files

```bash
# Python
uv run ruff check <files>

# TypeScript/JavaScript
npx eslint <files>
```

#### 3d: Report Progress

```
Step N/Total: DONE
  Modified: file1.py, file2.py
  Created: file3.py
  Verified: syntax OK, imports OK
```

### Step 4: Integration Verification

After all steps complete:

```bash
# Run pre-commit on all changed files
pre-commit run --all-files

# Run relevant tests if they exist
uv run pytest <test-files> 2>/dev/null || npm test 2>/dev/null
```

Fix any issues that arise. If a fix is non-trivial, report it and ask for guidance.

### Step 5: Final Review

Do a quick self-review of all changes:

```bash
git diff --stat
git diff
```

Check for:

- Debug code left in
- Commented-out code
- Missing error handling at system boundaries
- Incomplete implementations (TODO markers)
- Consistency across all changed files

### Step 6: Summary

```
Hero Implement Summary
======================
Plan: [summary]
Steps completed: N/N
Branch: <branch-name>

Files Modified:
  - path/to/file1.py
  - path/to/file2.ts

Files Created:
  - path/to/new_file.py

Pre-commit: PASSED
Tests: PASSED (or N/A)

Changes are ready. Next steps:
  /hero-commit review   # Review and commit
  /hero-push               # Push and create PR
```

## Handling Issues

### Step fails verification

1. Report what failed and why
2. Attempt to fix
3. Re-verify
4. If still failing, ask user for guidance before continuing

### Plan is ambiguous

1. Stop at the ambiguous step
2. Ask a specific clarifying question
3. Resume after getting an answer

### Unexpected codebase state

1. Report what was expected vs. what was found
2. Suggest how to adapt the plan
3. Wait for user approval before deviating from the plan

## Examples

```
/hero-implement              # Implement the current plan from step 1
/hero-implement 3            # Resume from step 3
```

## Notes

- Always read files before modifying them
- Follow existing patterns - don't introduce new conventions
- Verify after each step, not just at the end
- Stop and ask rather than guess on ambiguity
- Do NOT commit or push - that's for `/hero-commit` and `/hero-push`
