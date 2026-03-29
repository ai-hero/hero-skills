---
name: hero-update
# prettier-ignore
description: Sync HERO.md with the current codebase. Detects drift in dependencies, tools, projects, and conventions, then updates HERO.md and CLAUDE.md. Wire into pre-commit to keep config always up to date.
argument-hint: [--staged-only|--dry-run]
disable-model-invocation: true
---

# Hero Update - Keep HERO.md in Sync

Investigate the current codebase and update `HERO.md` so it always reflects the actual tech stack, dependencies, tools, and conventions. This ensures every `/hero-*` skill works with accurate configuration.

`HERO.md` is committed to the repo — it's team-shared. This skill keeps it from drifting out of date.

## Arguments

- `$ARGUMENTS`:
  - (none) — Full sync: investigate repo and update HERO.md
  - `--staged-only` — Only check staged files for changes (for pre-commit hook use)
  - `--dry-run` — Show what would change without writing

## Pre-commit Integration

For fast pre-commit, use the gate script that checks staged files first and only invokes Claude when something HERO.md-relevant changed. Most commits skip Claude entirely and finish in milliseconds.

```yaml
  - repo: local
    hooks:
      - id: hero-update
        name: "Hero Update: sync HERO.md"
        entry: ./scripts/hero-update-precommit.sh
        language: script
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
        verbose: true
```

The gate script (`scripts/hero-update-precommit.sh`) pattern-matches staged file names against HERO.md-relevant patterns (dependency files, CI configs, Dockerfiles, linter configs, coding agent configs, task runners). If nothing matches, it exits 0 instantly. If something matches, it runs `claude -p "/hero-update --staged-only"`.

**Requires:** Claude Code CLI installed and authenticated. Only works with Claude Code as the coding agent.

## Instructions

### Step 1: Load Current HERO.md

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

If `HERO.md` does not exist:

```
No HERO.md found. Run /hero-init to create one.
```

Exit — this skill updates, it does not create from scratch.

Parse the existing `HERO.md` into sections. Track every field and its current value.

### Step 2: Determine Scope

**If `--staged-only` (pre-commit mode):**

```bash
git diff --cached --name-only
```

Only investigate changes relevant to staged files:

- Dependency file changed (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`) → re-detect dependencies, tools, versions
- New directory with its own dependency file → potential new project/subproject
- CI config changed (`.github/workflows/`, `.gitlab-ci.yml`) → re-detect CI/CD
- Dockerfile changed → re-detect deployment/registry
- Pre-commit config changed → re-detect code quality tools
- New coding agent config (`.cursorrules`, `CLAUDE.md`, etc.) → re-detect coding agent
- Linter/formatter config changed (`ruff.toml`, `.eslintrc`, `tsconfig.json`) → re-detect code quality

If no staged files are relevant to HERO.md, report "HERO.md is up to date" and exit cleanly.

**If no flag (full sync):**

Investigate everything — same scope as `/hero-init` Step 3, but compare against existing values instead of starting from scratch.

### Step 3: Investigate Changes

For each relevant area, run targeted detection. Compare findings against current HERO.md values.

#### 3a: Projects & Dependencies

```bash
# Find all dependency files
find "$ROOT" -maxdepth 3 -name "pyproject.toml" -o -name "package.json" -o -name "go.mod" -o -name "Cargo.toml" -o -name "Gemfile" | grep -v node_modules | grep -v .venv | sort
```

For each project in HERO.md `## Projects`:

- Verify the path still exists
- Check if dependency file changed (new dependencies, removed dependencies)
- Detect if language/framework changed (e.g., added FastAPI to a plain Python project)
- Check test/lint/format/dev commands still work with current config

For new dependency files not in HERO.md → flag as potential new project.

#### 3b: Code Quality Tools

```bash
cat "$ROOT/.pre-commit-config.yaml" 2>/dev/null
cat "$ROOT/ruff.toml" "$ROOT/pyproject.toml" 2>/dev/null | head -50
cat "$ROOT/.eslintrc*" "$ROOT/eslint.config.*" 2>/dev/null | head -30
cat "$ROOT/tsconfig.json" 2>/dev/null | head -20
```

Compare detected linters, formatters, and type-checkers against HERO.md `## Code Quality`.

#### 3c: CI/CD & Deployment

```bash
ls "$ROOT/.github/workflows/" 2>/dev/null
ls "$ROOT/.gitlab-ci.yml" "$ROOT/Jenkinsfile" "$ROOT/.circleci/" 2>/dev/null
```

Compare against HERO.md `## CI/CD` and `## Deployment`.

#### 3d: Repository Settings

```bash
git remote get-url origin 2>/dev/null
git branch --show-current
cat "$ROOT/Makefile" "$ROOT/justfile" "$ROOT/Taskfile.yml" 2>/dev/null | head -30
```

Compare against HERO.md `## Repository`.

#### 3e: Coding Agent

```bash
ls "$ROOT/.claude/" "$ROOT/CLAUDE.md" "$ROOT/.cursorrules" "$ROOT/.cursor/rules/" "$ROOT/.windsurfrules" "$ROOT/.github/copilot-instructions.md" 2>/dev/null
```

Compare against HERO.md `## Coding Agent`.

### Step 4: Build Change Set

Collect all differences between current HERO.md and detected state. Categorize each:

- **Auto-update**: Safe to change without asking — version bumps, new dependencies added to existing projects, new CI workflows detected, new linter configs
- **Needs confirmation**: Structural changes — new projects, removed projects, changed framework, changed coding agent

### Step 5: Apply Updates

**If `--dry-run`:**

Show the diff of what would change and exit.

**If `--staged-only` (pre-commit mode):**

- Apply all auto-updates silently
- For changes that need confirmation, add a `<!-- TODO: confirm -->` comment next to the line
- Stage the updated HERO.md: `git add HERO.md`
- If CLAUDE.md was also updated, stage it too: `git add CLAUDE.md`

**If full sync (no flags):**

- Apply auto-updates
- Ask the user about structural changes before applying
- Stage nothing — let the user review and commit

### Step 6: Update CLAUDE.md

If HERO.md changed, also update the corresponding sections in CLAUDE.md:

- `## Tech Stack` — human-readable summary of language, framework, infra
- `## Best Practices` — commits, branches, code quality, testing
- `## Coding Conventions` — naming, imports, error handling, etc.

Only update sections marked with `<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->`. Never touch user-written sections.

### Step 7: Report

**Full sync report:**

```
HERO UPDATE — Sync Report
==========================

Updated:
  ## Projects → api: added fastapi-cache to dependencies
  ## Code Quality: added biome to formatters
  ## CI/CD → workflows: added deploy-staging.yml

No changes:
  ## Repository, ## Deployment, ## Coding Agent

HERO.md updated. Review with: git diff HERO.md
```

**Pre-commit report (keep brief):**

```
HERO.md synced: updated Code Quality (added biome), Projects → api (new deps)
```

If nothing changed:

```
HERO.md is up to date.
```

## Key Principles

- **Update, never create.** If no HERO.md exists, point to `/hero-init`. This skill only syncs.
- **Auto-update safe changes.** Version bumps, new deps, new workflows are safe. Don't ask about every small change.
- **Ask about structural changes.** New/removed projects, framework changes, agent changes need confirmation.
- **Always stage in pre-commit mode.** The whole point is HERO.md gets committed alongside the code that changed it.
- **Fast in pre-commit mode.** Only investigate what the staged files tell you changed. Don't scan the whole repo.
- **HERO.md is team-shared.** It's committed to the repo. Every developer and every hero skill reads it.
