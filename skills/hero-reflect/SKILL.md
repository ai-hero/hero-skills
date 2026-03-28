---
name: hero-reflect
# prettier-ignore
description: Review uncommitted code changes against HERO.md conventions and best practices. Use before committing, or wire into pre-commit as `claude -p "/hero-reflect"`. Catches convention drift, missing tests, and gotcha violations.
argument-hint: [--staged-only]
---

# Hero Reflect - Self-Review Uncommitted Code

Review the current uncommitted changes against the project's conventions, best practices, and gotchas defined in `HERO.md` and `CLAUDE.md`. This is the "did I follow the rules?" check before committing.

## Arguments

- `$ARGUMENTS`:
  - (none) — Review all uncommitted changes (staged + unstaged)
  - `--staged-only` — Only review staged changes (for pre-commit hook use)

## Pre-commit Integration

To wire this into pre-commit so it runs automatically before every commit, add to `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: hero-reflect
        name: "Hero Reflect: AI self-review"
        entry: claude -p "/hero-reflect --staged-only"
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
        verbose: true
```

**Requires:** Claude Code CLI installed and authenticated. Only works with Claude Code as the coding agent. Check `HERO.md → ## Coding Agent → primary` to confirm.

## Instructions

### Step 1: Load Project Context

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
```

Read these files (all optional — degrade gracefully if missing):
1. `HERO.md` — coding conventions, gotchas, code quality tools, project structure
2. `CLAUDE.md` — tech stack, best practices, coding conventions summary

If neither exists, still review the diff but warn:
```
No HERO.md or CLAUDE.md found. Reviewing against general best practices only.
Run /hero-init to configure project-specific conventions.
```

### Step 2: Get the Diff

```bash
# If --staged-only
git diff --cached --stat
git diff --cached

# Otherwise (all uncommitted)
git diff HEAD --stat
git diff HEAD
```

If the diff is empty, report "Nothing to review" and exit.

### Step 3: Review Against Conventions

Check the diff against every relevant section of HERO.md. Only flag things that are actually violated — do not lecture about rules that are followed correctly.

**Check each of these, in order:**

#### 3a: Coding Conventions (from HERO.md `## Coding Conventions`)
- **Naming**: Do new functions/classes/files follow the convention?
- **Imports**: Are new imports in the right style and order?
- **Error handling**: Do new try/catch blocks follow the pattern? Any bare except?
- **Logging**: Are new log statements using the right library and style?
- **Documentation**: Do new public functions have the expected docstrings?

#### 3b: Exceptions & Gotchas (from HERO.md `### Exceptions & Gotchas`)
This is the most critical check. These are hard-won lessons. Examples:
- If gotcha says "Use OpenTofu, NOT Terraform" → flag any `terraform` references in the diff
- If gotcha says "no DB mocks" → flag any new mock.patch on DB calls
- If gotcha says "pnpm NOT npm" → flag any `npm install` or `package-lock.json`

#### 3c: Code Quality (from HERO.md `## Code Quality`)
- If pre-commit is enabled, remind that it will run linters — don't duplicate that work
- If type-checkers are listed, check for obvious type issues (missing annotations on new public APIs)
- If formatters are listed, check for obvious formatting issues

#### 3d: Test Coverage
- If new functions/endpoints/handlers are added, check if corresponding tests exist
- Use HERO.md `### Tests` for location and naming conventions
- Don't demand tests for trivial changes (config, comments, imports)

#### 3e: Security Quick-Check
- New environment variable usage without validation
- Hardcoded secrets, tokens, API keys
- SQL string concatenation
- Unescaped user input in templates/HTML

### Step 4: Report

Output a concise, actionable report. Group by severity.

**Format:**

```
HERO REFLECT — Self-Review
══════════════════════════
Files changed: 5 (+120, -30)

MUST FIX (blocks commit)
─────────────────────────
1. app/infra.py:23 — Uses `terraform` command
   Convention: Use OpenTofu, NOT Terraform (HERO.md → Exceptions & Gotchas)
   Fix: Change to `tofu` command

2. tests/test_api.py:45 — Mocks database connection
   Convention: No DB mocks (HERO.md → Tests → reason)
   Fix: Use the test DB fixture from conftest.py

SHOULD FIX (before merge)
──────────────────────────
3. app/handlers.py:67 — New public function `process_order` has no docstring
   Convention: Google-style docstrings required for public functions

4. app/services.py:12 — Import ordering: local import before third-party
   Convention: stdlib → third-party → local

LOOKS GOOD
──────────
- Naming conventions: ✓ all snake_case
- Error handling: ✓ uses AppError pattern
- Logging: ✓ structlog with bound logger
- Tests: ✓ test_orders.py added for new handler
- Security: ✓ no issues detected

Verdict: 2 must-fix, 2 should-fix
```

**Rules for the report:**
- **MUST FIX**: Violations of Exceptions & Gotchas (these exist for a reason), security issues, broken conventions the team explicitly marked as important
- **SHOULD FIX**: Style/convention violations, missing docs, import ordering
- **LOOKS GOOD**: Briefly confirm what's correct — builds confidence
- If everything passes: `All clear — changes follow project conventions.`
- Be specific: file, line number, what's wrong, what the convention says, how to fix
- Reference the exact HERO.md section so the developer can look it up
- Never be vague ("looks off") — cite the rule or don't flag it

### Step 5: Exit Code (for pre-commit)

When running in `--staged-only` mode (pre-commit):
- If there are MUST FIX items → exit with a non-zero message so the commit is blocked
- If only SHOULD FIX or all clear → allow the commit to proceed (exit cleanly)
- Always show the report regardless

## Key Principles

- **Convention-driven, not opinion-driven.** Only flag what HERO.md defines. Don't invent rules.
- **Specific and actionable.** File, line, rule, fix. No vague suggestions.
- **Fast.** This runs on every commit. Review only the diff, not the whole codebase.
- **Non-blocking by default.** Only Exceptions & Gotchas and security issues are MUST FIX.
- **Graceful degradation.** Works without HERO.md (general review), better with it.
