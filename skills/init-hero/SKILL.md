---
name: init-hero
# prettier-ignore
description: Initialize Hero for a project. Investigates the repo, auto-detects the stack, confirms findings with smart questions, and creates HERO.md that all skills use.
argument-hint: [--update]
disable-model-invocation: true
---

# Init — Investigate & Configure

Deeply investigate the repository, auto-detect project settings, then confirm findings with the user through smart, evidence-based questions. Creates or updates `HERO.md` at the repo root.

## Pipeline DAG

This skill owns Pipeline 3 from `PIPELINES.md`:

```
investigate → confirm → write → commit
```

Print the DAG line at the start of each step. Substep groups in this skill map to pipeline nodes as:

- Step 3 (Deep Investigation) → `investigate`
- Step 4 (Synthesize Findings into Smart Questions) → `confirm`
- Steps 5, 6, and 6a (write HERO.md, validate with the user, optionally install auto-approve workflow) → `write`
- Step 7 (Commit HERO.md) → `commit`

Format:

```
[N/4] (✓) investigate → (▶) confirm → ( ) write → ( ) commit

Now running: confirm
```

## Arguments

- `$ARGUMENTS`:
  - (none) - Investigate repo and create `HERO.md`
  - `--update` - Re-investigate and update existing `HERO.md`

## Why This Matters

Each skill needs specific information to work well. This skill figures out what's needed by examining the repo rather than asking generic questions.

**What each skill needs from HERO.md:**

| Skill | Needs |
|-------|-------|
| `hero-skills:push-pr` | Default branch, branch convention, hosting platform (`gh`/`glab`), issue prefix, commit convention, pre-commit run command, CI platform, workflow names, registry, required status checks |
| `hero-skills:one-shot` | PM tool + MCP server name, branch template, issue prefix, project list |
| `hero-skills:push-pr` (test phase) | Language, framework, lint/format/typecheck commands, test/dev/install commands, ports, dependency file |
| `hero-skills:review-pr` | Code Quality (pre-commit), Code Review Agent (bot username — to dedupe its comments) |
| `hero-skills:harden` | Registry, language/framework, dependency files per project |
| `hero-skills:think-it-through` (arch mode) | Repo type, project list, deployment platform |
| `hero-skills:create-project` | Repo type, coding conventions, code quality tools, project scaffold patterns |
| `hero-skills:setup-dev` | Required tools, recommended tools, MCP servers |
| `hero-skills:respond-to-comments` | Code Review Agent (agent, trigger, poll-method, bot-username) |
| `hero-skills:ship-pr` | CI/CD (auto-approve workflow installed on default branch), Repository (default branch), deployment platform, namespaces, ArgoCD, health check endpoints |
| `hero-skills:init-hero --update` | All sections — re-investigates and refreshes HERO.md on demand |
| `hero-skills:audit-plugin` | (internal) Plugin structure validation |

## Instructions

### Step 1: Ensure Claude Code is Initialized

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls "$ROOT/CLAUDE.md" 2>/dev/null && echo "CLAUDE_EXISTS" || echo "CLAUDE_NEW"
```

**If `CLAUDE.md` does NOT exist:**

- Create `CLAUDE.md` at the repo root with a scaffold that includes Tech Stack and Best Practices sections (content will be filled in Step 5 after investigation).
- For now, create the file with placeholder sections:

```markdown
# CLAUDE.md

## Tech Stack
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for the full tech stack configuration detected by `hero-skills:init-hero`.

## Best Practices
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for project conventions, code quality tools, and CI/CD configuration.

## Coding Conventions
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for coding conventions detected from the codebase.
```

**If `CLAUDE.md` DOES exist:**

- Read it and check whether it already has `## Tech Stack`, `## Best Practices`, and `## Coding Conventions` sections.
- If either section is **missing**, append it to the end of the file.
- If a section exists but does **not** reference `HERO.md`, add a reference line:
  `See [HERO.md](./HERO.md) for details managed by hero-skills:init-hero.`
- **Do not** remove or overwrite any existing content the user has written in these sections — only add the HERO.md pointer if absent.

**Why this matters:** CLAUDE.md is loaded into Claude's context at conversation start. Without a reference to HERO.md here, Claude won't know to consult HERO.md for tech stack decisions (e.g., using OpenTofu instead of Terraform, or a specific framework) or coding conventions (e.g., snake_case, structured logging, no DB mocks in tests). The pointer ensures Claude always reads HERO.md for authoritative project configuration.

### Step 2: Check for Existing HERO.md Configuration

```bash
ls "$ROOT/HERO.md" 2>/dev/null && echo "EXISTS" || echo "NEW"
```

If `HERO.md` exists and `--update` was not passed, show current config and ask if user wants to update it. If `--update`, read the existing file to compare against new findings.

### Step 3: Deep Investigation

Launch a thorough investigation of the repository. Use an Explore subagent or do it yourself — the goal is to gather **evidence** for every configuration decision.

#### 3a: Coding Agent & AI Tooling

Detect which AI coding agent(s) the team uses. This must come first — it determines what hooks, configs, and integrations are possible.

```bash
# Claude Code
ls .claude/ .claude-plugin/ CLAUDE.md .claude/settings.json 2>/dev/null
ls .claude/hooks/ 2>/dev/null
cat .claude/settings.json 2>/dev/null

# Cursor
ls .cursor/ .cursorrules .cursor/rules/ 2>/dev/null
cat .cursorrules 2>/dev/null | head -20

# Windsurf
ls .windsurf/ .windsurfrules 2>/dev/null

# Copilot
ls .github/copilot-instructions.md .copilot/ 2>/dev/null

# Aider
ls .aider* 2>/dev/null

# Other signals
ls .ai/ .llm/ 2>/dev/null
grep -r "claude\|cursor\|copilot\|windsurf\|aider" .pre-commit-config.yaml 2>/dev/null | head -5
```

**What to look for:**

- `.claude/` directory or `CLAUDE.md` → Claude Code user — can use hooks, skills, MCP servers
- `.cursorrules` or `.cursor/rules/` → Cursor user — rules files, no hook system
- `.github/copilot-instructions.md` → Copilot user — instructions file
- `.windsurfrules` → Windsurf user — rules file
- Multiple signals → team uses different agents — note all of them
- Pre-commit hooks referencing AI tools → existing self-review or lint integration

**If no coding agent detected**, ask:
*"What AI coding agent does your team use? (Claude Code, Cursor, Windsurf, Copilot, other)"*
This determines what hooks and integrations hero skills can set up (e.g., pre-commit self-review, agent-specific rules files).

#### 3b: Code Review Agent

Detect which external code review bot the team uses for automated PR reviews.

```bash
# Config files for known review agents
ls .greptile/ .greptile.yaml .greptile.yml 2>/dev/null
ls .coderabbit.yaml .coderabbit.yml 2>/dev/null
ls .github/copilot-review.yml 2>/dev/null

# Check recent PR comments for bot activity (last 5 PRs)
gh pr list --state merged --limit 5 --json number --jq '.[].number' 2>/dev/null | while read pr; do
  gh api "repos/{owner}/{repo}/pulls/$pr/comments" --jq '.[].user.login' 2>/dev/null
done | sort | uniq -c | sort -rn | head -5

# Check the repository's GitHub App installation (look for review bots)
gh api "/repos/{owner}/{repo}/installation" --jq '{app_slug, app_name}' 2>/dev/null
```

**What to look for:**

- `.coderabbit.yaml` → CodeRabbit — trigger: auto on push, poll-method: comments, bot-username: `coderabbitai`
- `.greptile/` or `.greptile.yaml` → Greptile — trigger: `@greptile review` comment, poll-method: check-runs, bot-username: `greptile-bot`
- Bot usernames in recent PR comments → identifies active review agent
- GitHub Copilot code review enabled → trigger: auto on push, poll-method: comments, bot-username: `copilot`

**If no review agent detected**, set `agent: none`. Optionally ask:
*"Does your team use an automated code review bot (Greptile, CodeRabbit, Copilot review, etc.)?"*

#### 3c: Repository & Collaboration Model

```bash
# Basic structure
git rev-parse --show-toplevel
git remote -v
git branch -r | head -20
git log --oneline -20
git shortlog -sn --all | head -10

# Default branch
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null || echo "UNKNOWN"

# Collaboration signals
ls LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md CODEOWNERS .github/PULL_REQUEST_TEMPLATE* .github/ISSUE_TEMPLATE* 2>/dev/null

# Allowed merge methods on the GitHub remote — the team's PR merge
# button is constrained by these flags. We surface the allowed set so
# Step 4 can ask the user to pick one (preferring squash when allowed).
# Also fetch deleteBranchOnMerge — when false, hero-skills:ship-pr will
# delete merged branches itself.
gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge 2>/dev/null
```

**What to look for:**

- Remote URL → hosting platform: `github.com` → GitHub (`gh`), `gitlab.com` → GitLab (`glab`), `bitbucket.org` → Bitbucket
- Multiple contributors in git log → team project with shared conventions
- LICENSE + CONTRIBUTING.md → open-source, may need DCO sign-off
- CODEOWNERS → enforced code review ownership
- PR templates → structured PR process
- Branch naming patterns in `git branch -r` → extract the **branch template** (e.g., `feature/PROJ-123-DESC`, `fix/DESC`, `PREFIX/ISSUE_ID-DESC`)
- Commit message patterns in `git log` (e.g., `feat:`, `fix:`, `PROJ-123:`)
- Allowed merge methods → `merge-method` field. Prefer `squash` when allowed; otherwise `rebase`; otherwise `merge`. If multiple are allowed, ask the user once to pin the team's choice.
- `deleteBranchOnMerge` → `auto-delete-branches` field. If true, GitHub already deletes merged branches and `hero-skills:ship-pr` will skip cleanup. If false, the skill will delete the remote and local branch after a successful merge unless `auto-delete-branches: false` overrides it in HERO.md.

#### 3d: Project Management & Issue Tracking

```bash
# Issue templates often reveal the PM tool
ls .github/ISSUE_TEMPLATE/*.yml .github/ISSUE_TEMPLATE/*.md 2>/dev/null
cat .github/ISSUE_TEMPLATE/*.yml 2>/dev/null | head -40

# Check commit messages for ticket IDs
git log --oneline -30 | grep -oE '[A-Z]+-[0-9]+' | sort -u | head -5

# Check branch names for ticket IDs
git branch -r | grep -oE '[A-Z]+-[0-9]+' | sort -u | head -5

# Linear, Jira, etc. references in config
grep -r "linear\|jira\|asana\|shortcut" .github/ 2>/dev/null | head -5
```

**What to look for:**

- Ticket IDs like `PROJ-123` in commits/branches → extract the prefix
- Linear/Jira mentions in templates → identifies PM tool
- GitHub issue references (`#123`, `Fixes #123`) → GitHub Issues

#### 3e: CI/CD Platform & Workflows

```bash
# GitHub Actions
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null

# Read workflow names and triggers
for f in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$f" ] && echo "=== $f ===" && head -20 "$f"
done 2>/dev/null

# Other CI platforms
ls .gitlab-ci.yml Jenkinsfile .circleci/config.yml .travis.yml buildkite.yml 2>/dev/null

# What the CI does (test, lint, build, deploy, release)
grep -l "test\|lint\|build\|deploy\|release" .github/workflows/*.yml 2>/dev/null
```

**What to look for:**

- Which workflows exist and what they do (test, lint, build images, deploy)
- Whether CI runs on PR, push to main, or both
- Required status checks (signals what must pass before merge)
- Whether `.github/workflows/auto-approve.yml` already exists — needed by `hero-skills:ship-pr`

```bash
# Check whether the hero-skills auto-approve workflow is installed
ls .github/workflows/auto-approve.yml 2>/dev/null && \
  grep -q '@auto-approve' .github/workflows/auto-approve.yml 2>/dev/null && \
  echo "AUTO_APPROVE_INSTALLED" || echo "AUTO_APPROVE_MISSING"

# And whether it has been merged to the default branch — issue_comment
# workflows only trigger from the default branch, so a PR-branch-only
# install does nothing.
DEFAULT_BRANCH=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
# Refresh before checking — a stale origin/$DEFAULT_BRANCH would report
# AUTO_APPROVE_NOT_ON_DEFAULT for a workflow that was actually just merged.
# On fetch failure, report the result as unknown rather than letting a
# possibly-stale ref produce a silent false AUTO_APPROVE_ON_DEFAULT that
# suppresses the "will be a no-op" warning the user actually needs.
if git fetch origin "$DEFAULT_BRANCH" 2>/dev/null; then
  git cat-file -e "origin/$DEFAULT_BRANCH:.github/workflows/auto-approve.yml" 2>/dev/null \
    && echo "AUTO_APPROVE_ON_DEFAULT" || echo "AUTO_APPROVE_NOT_ON_DEFAULT"
else
  echo "AUTO_APPROVE_ON_DEFAULT_UNKNOWN (fetch failed — verify manually before trusting this check)"
fi
```

#### 3f: Required CLI Tools & Developer Toolchain

```bash
# Version control & hosting
which gh 2>/dev/null && gh --version
which git 2>/dev/null && git --version

# Project management CLIs
which linear 2>/dev/null && linear --version 2>/dev/null
which jira 2>/dev/null && jira --version 2>/dev/null

# Language runtimes & package managers
which node 2>/dev/null && node --version
which python 2>/dev/null && python --version
which python3 2>/dev/null && python3 --version
which go 2>/dev/null && go version
which rustc 2>/dev/null && rustc --version
which uv 2>/dev/null && uv --version
which pnpm 2>/dev/null && pnpm --version
which yarn 2>/dev/null && yarn --version
which bun 2>/dev/null && bun --version
which cargo 2>/dev/null && cargo --version

# Infrastructure tools
which docker 2>/dev/null && docker --version
which kubectl 2>/dev/null && kubectl version --client 2>/dev/null
which helm 2>/dev/null && helm version --short 2>/dev/null
which tofu 2>/dev/null && tofu --version 2>/dev/null
which terraform 2>/dev/null && terraform --version 2>/dev/null
which aws 2>/dev/null && aws --version 2>/dev/null
which gcloud 2>/dev/null && gcloud --version 2>/dev/null | head -1
which az 2>/dev/null && az --version 2>/dev/null | head -1

# Code quality
which pre-commit 2>/dev/null && pre-commit --version
```

**What to look for:**

- Which tools the project actually requires (cross-reference with deps, CI, Dockerfiles, Makefiles)
- Distinguish between **required** (project won't build/run without it) vs. **recommended** (nice to have)
- Note minimum versions if the project depends on specific features
- These go into HERO.md `## Developer Setup` as team-shared requirements — individual installation/auth is handled by `hero-skills:setup-dev`

#### 3g: Deployment & Infrastructure

```bash
# Container
ls Dockerfile* docker-compose*.yml docker-compose*.yaml 2>/dev/null

# Kubernetes
ls -d k8s/ kubernetes/ charts/ helm/ kustomize/ 2>/dev/null
ls k8s/*.yml k8s/*.yaml kubernetes/*.yml kubernetes/*.yaml 2>/dev/null | head -10

# Serverless / PaaS
ls vercel.json netlify.toml fly.toml render.yaml app.yaml Procfile serverless.yml 2>/dev/null

# ArgoCD
ls -d argocd/ 2>/dev/null
grep -r "argocd\|argo-cd" .github/ k8s/ 2>/dev/null | head -5

# Container registry references
grep -r "ghcr.io\|ecr\.\|docker.io\|dockerhub\|acr\.\|gcr.io\|artifact-registry" .github/workflows/ Dockerfile* 2>/dev/null | head -10

# Namespace / environment references
grep -r "namespace\|environment\|staging\|production" k8s/ .github/workflows/ 2>/dev/null | head -10
```

**What to look for:**

- Dockerfile → containerized app, look for registry in CI
- K8s manifests → Kubernetes deployment, look for namespaces
- vercel.json / netlify.toml → serverless/static deployment
- ArgoCD references → GitOps workflow
- Environment names → staging, production, etc.

#### 3h: Code Quality & Developer Tooling

```bash
# Pre-commit
ls .pre-commit-config.yaml 2>/dev/null && cat .pre-commit-config.yaml

# Python quality tools
ls ruff.toml pyproject.toml setup.cfg mypy.ini .flake8 .pylintrc 2>/dev/null
grep -A5 "\[tool.ruff\]\|\[tool.black\]\|\[tool.mypy\]\|\[tool.pytest\]\|\[tool.isort\]" pyproject.toml 2>/dev/null

# JavaScript/TypeScript quality tools
ls .eslintrc* .prettierrc* tsconfig.json biome.json .stylelintrc* 2>/dev/null

# Editor config
ls .editorconfig 2>/dev/null
```

**What to look for:**

- Pre-commit config → which hooks run (linters, formatters, type checks)
- ruff/eslint → linter
- black/prettier/biome → formatter
- mypy/pyright/tsc strict → type checker
- What's enforced in CI vs. just local

#### 3i: Project Structure & Tech Stack

```bash
# Root project files (dependency files)
ls pyproject.toml package.json go.mod Cargo.toml build.gradle pom.xml requirements.txt 2>/dev/null

# Monorepo indicators
ls pnpm-workspace.yaml lerna.json nx.json turbo.json 2>/dev/null
grep -l "workspaces" package.json 2>/dev/null

# Subproject detection
ls */pyproject.toml */package.json 2>/dev/null | head -20
ls apps/*/package.json packages/*/package.json services/*/pyproject.toml 2>/dev/null | head -20

# Framework detection (read the actual deps)
grep -E "fastapi|django|flask|starlette" pyproject.toml 2>/dev/null
grep -E "next|vite|remix|astro|nuxt|svelte|express|nestjs|hono" package.json 2>/dev/null

# Task runners / command wrappers (these define canonical commands)
ls Makefile justfile Taskfile.yml 2>/dev/null
cat Makefile 2>/dev/null | grep -E "^[a-zA-Z_-]+:" | head -20
cat justfile 2>/dev/null | grep -E "^[a-zA-Z_-]+:" | head -20

# Package scripts (canonical command source for JS/TS)
grep -A30 '"scripts"' package.json 2>/dev/null

# Python scripts (canonical command source)
grep -A10 "\[project.scripts\]\|\[tool.poetry.scripts\]" pyproject.toml 2>/dev/null

# Install commands
# Python: look for uv, pip, poetry, conda
grep -E "uv sync|pip install|poetry install|conda" Makefile justfile README.md 2>/dev/null | head -5
# JS: look for which package manager
ls pnpm-lock.yaml yarn.lock package-lock.json bun.lockb 2>/dev/null

# Test setup
ls pytest.ini conftest.py jest.config* vitest.config* playwright.config* cypress.config* 2>/dev/null
grep -E "test-command\|scripts.*test\|pytest\|jest\|vitest" pyproject.toml package.json 2>/dev/null

# Lint / format / typecheck commands
grep -E "lint|format|check|typecheck|mypy|ruff|eslint|prettier|biome" Makefile justfile 2>/dev/null | head -10
grep -E '"lint"|"format"|"check"|"typecheck"' package.json 2>/dev/null

# Dev server
grep -E "dev.*command\|scripts.*dev\|scripts.*start\|uvicorn\|gunicorn" pyproject.toml package.json 2>/dev/null

# Ports
grep -E "port\|PORT\|:3000\|:8000\|:8080\|:5173\|:4000" pyproject.toml package.json .env.example docker-compose*.yml 2>/dev/null | head -10
```

**What to look for:**

- Language and framework from dependency files
- Monorepo structure (workspaces, nx, turborepo, multiple pyproject.toml)
- **Dependency file** per project (pyproject.toml, package.json, go.mod, etc.) — needed by `hero-skills:harden` and `hero-skills:push-pr`'s test phase
- **Lock file** → identifies the package manager (pnpm-lock.yaml → pnpm, yarn.lock → yarn, etc.)
- **Install command** (e.g., `uv sync`, `pnpm install`) — needed by `hero-skills:push-pr`'s test phase before running
- **Task runner** (Makefile, justfile, Taskfile) — if present, prefer its targets as canonical commands (e.g., `make test` over `uv run pytest`)
- **Exact lint/format/typecheck commands** — not just tool names; `hero-skills:push-pr`'s test phase needs runnable commands for verification
- Test commands from scripts section or config files
- Dev server commands and default ports
- Entry points for CLIs

#### 3j: Coding Conventions & Team Patterns

Investigate the codebase for established conventions the team follows. These are critical — Claude must follow the same patterns the team uses.

```bash
# Existing style guides or contributing docs
ls CONTRIBUTING.md STYLE_GUIDE.md docs/CONVENTIONS.md docs/STYLE*.md 2>/dev/null
cat CONTRIBUTING.md 2>/dev/null | head -80

# Existing CLAUDE.md for conventions already documented
cat CLAUDE.md 2>/dev/null

# Import style — relative vs absolute, aliased paths
# (sample 5-10 source files from different directories)
head -20 src/**/*.{ts,tsx,py,go,rs} 2>/dev/null | head -60
grep -r "from \.\|from src\|from @/\|from ~/\|import \.\|import src" --include="*.py" --include="*.ts" --include="*.tsx" -l 2>/dev/null | head -5

# Naming conventions — sample function/class/variable names
grep -rE "^(def |class |function |const |export (const|function|class))" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -20

# Error handling patterns
grep -rE "(try:|except |catch\(|\.catch\(|Result<|anyhow::|thiserror)" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -10

# Logging patterns
grep -rE "(logger\.|logging\.|console\.(log|error|warn)|log\.(info|error|warn|debug)|slog\.|tracing::)" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -10

# Test patterns — naming, structure, fixtures vs mocks
ls tests/ test/ __tests__/ spec/ 2>/dev/null
grep -rE "(describe\(|it\(|test\(|def test_|func Test|#\[test\]|#\[cfg\(test\)\])" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -10

# Dependency injection / configuration patterns
grep -rE "(Depends\(|@inject|@Inject|providers\.|Container)" --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | head -5

# API patterns — REST conventions, response shapes
grep -rE "(router\.|@app\.(get|post|put|delete|patch)|app\.(get|post|put|delete|patch)|@(Get|Post|Put|Delete|Patch))" --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | head -10

# Database / ORM patterns
grep -rE "(Base\.metadata|declarative_base|mapped_column|Column\(|prisma\.|drizzle|knex|sqlx|diesel)" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -10

# Documentation patterns — docstrings, JSDoc, etc.
grep -rE '("""|\/\*\*|/// |//!)' --include="*.py" --include="*.ts" --include="*.tsx" --include="*.go" --include="*.rs" 2>/dev/null | head -10
```

**What to look for — adapt to detected tech stack:**

For **Python** projects:

- snake_case vs camelCase for functions/variables
- Import style: absolute (`from app.models`) vs relative (`from .models`)
- Docstring format: Google, NumPy, or Sphinx style
- Async patterns: `async def` usage, asyncio vs trio
- Error handling: custom exception classes, bare except usage
- Type hints: inline vs stub files, Optional vs `| None`

For **TypeScript/JavaScript** projects:

- Named exports vs default exports
- Path aliases (`@/`, `~/`) vs relative imports
- Interface vs Type for object shapes
- Barrel files (`index.ts` re-exports) usage
- `async/await` vs `.then()` chains
- Error handling: custom error classes, error boundaries

For **Go** projects:

- Package naming and layout (standard vs flat)
- Error wrapping style: `fmt.Errorf("...: %w", err)` vs custom
- Interface placement: consumer-side vs provider-side
- Context propagation patterns

For **Rust** projects:

- Error handling: `anyhow` vs `thiserror` vs custom
- Module structure: `mod.rs` vs file-based
- Trait patterns and generics usage

**Cross-language patterns to detect:**

- File/folder naming: kebab-case, snake_case, PascalCase
- API response shape conventions (envelope pattern, error format)
- Logging approach: structured vs unstructured, which library
- Config management: env vars, config files, secrets handling
- Test organization: co-located vs separate directory, naming patterns (`test_*`, `*.test.ts`, `*_test.go`)

**Rationale detection — when to ask "why":**

Most conventions are self-evident (snake_case in Python, PascalCase classes) — don't ask why for those. But flag and ask about anything that is:

- **An exception to the language/framework default** (e.g., no default exports in TS, relative imports in a flat Python project)
- **A deliberate avoidance** (e.g., no ORM, no mocks, no barrel files)
- **A tool choice that has a common alternative** (e.g., OpenTofu over Terraform, pnpm over npm, Bun over Node)
- **A pattern that would surprise a new team member or Claude**

For these, ask the user: *"I noticed you use X instead of Y — is there a specific reason? This helps Claude avoid suggesting Y in the future."*

Keep rationale brief for mild preferences, elaborate for hard-won lessons (e.g., "mocks hid a migration bug").

### Step 4: Synthesize Findings into Smart Questions

Based on your investigation, present findings grouped by **what the hero skills need**. Do NOT ask generic questionnaire questions. Instead, present evidence-based confirmations.

**IMPORTANT: When asking clarifying questions, switch to plan mode or present ALL questions in a single numbered list (1. 2. 3. ...) so the user can answer them efficiently in one go. Never ask questions in freeform prose scattered across the output.**

**Format for each finding:**

```
[CONFIRMED] SETTING: VALUE
  Evidence: EVIDENCE
  Used by: hero-skills:push-pr

[NEEDS CONFIRMATION] SETTING: BEST_GUESS
  Evidence: EVIDENCE (and why ambiguous)
  Question: QUESTION
  Used by: hero-skills:one-shot

[NOT DETECTED] SETTING
  Looked for: WHAT_WAS_CHECKED
  Question: QUESTION
  Used by: hero-skills:ship-pr
```

**Group findings into these categories, presented in this order:**

#### Group 0: "Your coding agent" (`hero-skills:init-hero --update`, `hero-skills:setup-dev`)

- Coding agent (Claude Code, Cursor, Windsurf, etc.)
- Whether hooks/pre-commit integration is possible

Do NOT offer to install a pre-commit hook for `hero-skills:init-hero --update`. Skills surface a stale-HERO.md hint on demand instead — see `scripts/check-hero-staleness.sh`.

#### Group 1: "For committing and pushing code" (`hero-skills:push-pr`, `hero-skills:ship-pr`)

- Hosting platform (GitHub, GitLab, Bitbucket — from remote URL)
- Commit convention (evidence from git log patterns)
- Branch naming convention and branch template (evidence from branch -r patterns)
- Default branch
- Merge method for PRs — squash, rebase, or merge. Detect with `gh repo view --json squashMergeAllowed,rebaseMergeAllowed,mergeCommitAllowed`; pick the **first allowed in this preference order: squash → rebase → merge**. If multiple are allowed, confirm with the user once and write the choice to `merge-method` in HERO.md.
- Whether GitHub auto-deletes merged head branches — `gh repo view --json deleteBranchOnMerge`. If false, `hero-skills:ship-pr` will clean up the remote + local branch after merge. Record as `auto-delete-branches` in HERO.md.
- Pre-commit hooks and what they run
- Linters, formatters
- Task runner (if Makefile/justfile provides commit/push/lint targets)

#### Group 2: "For planning and tracking work" (`hero-skills:one-shot`)

- PM tool (evidence from templates, commit messages, integrations)
- Issue ID prefix (evidence from commit/branch patterns)
- MCP server name if applicable

#### Group 3: "For testing and verification" (`hero-skills:push-pr` test phase)

- Per-project: language, framework, dependency file, install command
- Per-project: test, lint, format, typecheck commands (prefer task runner targets if available)
- Per-project: dev command, port
- Type checkers
- Task runner (Makefile, justfile, etc.) and its available targets
- Monorepo vs single repo structure

#### Group 4: "For CI/CD and deployment" (`hero-skills:push-pr`, `hero-skills:ship-pr`, `hero-skills:harden`)

- CI platform and workflow names
- Deployment platform
- Container registry
- ArgoCD / GitOps
- Namespaces / environments
- Whether to install `.github/workflows/auto-approve.yml` for `hero-skills:ship-pr` — if absent, ask:
  *"`hero-skills:ship-pr` lets you comment `@auto-approve` on a PR to get a Claude-verified approval (gated by self-review, no unresolved threads, and PR-metadata checks). Install `.github/workflows/auto-approve.yml`? It also requires an `ANTHROPIC_API_KEY` repo secret."*
  - If the user says yes, run the install in Step 6a below.
  - If the workflow exists locally but is not on the default branch yet, remind the user that `@auto-approve` will be a no-op until that file lands on the default branch.

#### Group 5: "Coding conventions for consistent code" (all skills that write code)

- Naming conventions (functions, files, folders)
- Import style and organization
- Error handling patterns
- Logging approach
- Test structure and naming
- API patterns (if applicable)
- Any other strong patterns detected in the codebase

Present ALL findings at once, clearly marking what's confirmed vs. what needs input. Ask the user to confirm or correct.

**Example output:**

```
Hero Init - Investigation Results
=================================

I analyzed the repo and here's what I found:

FOR COMMITTING & PUSHING (hero-skills:push-pr)
────────────────────────────────────────────────────
[OK] Commit convention: conventional
     Evidence: 18/20 recent commits use "feat:", "fix:", "chore:" format

[OK] Default branch: main
     Evidence: origin/HEAD → origin/main

[OK] Pre-commit: enabled (ruff, black, mypy)
     Evidence: .pre-commit-config.yaml with 3 hooks

[??] Branch convention: unclear
     Evidence: Branches show mixed patterns:
       - feature/add-auth, feature/fix-login (feature/* pattern)
       - PROJ-45-update-deps (ticket-first pattern)
     → Which pattern do you prefer?

FOR PLANNING & TRACKING (hero-skills:one-shot)
─────────────────────────────────────
[??] PM tool: likely Linear
     Evidence: Found "linear" in .github/workflows/sync.yml,
     commits reference LIN-XXX IDs
     → Is Linear your PM tool? What MCP server name?

[OK] Issue prefix: LIN
     Evidence: 8 commits reference LIN-### pattern

FOR TESTING & VERIFICATION (hero-skills:push-pr test phase)
────────────────────────────────────────
[OK] Single repo, Python + FastAPI
     Evidence: pyproject.toml with fastapi dependency, no subprojects

[OK] Test command: uv run pytest
     Evidence: [tool.pytest.ini_options] in pyproject.toml, tests/ dir

[??] Dev command: probably "uv run uvicorn app.main:app --reload"
     Evidence: uvicorn in deps, app/main.py exists, but no
     scripts section defined
     → Is this the right dev command?

[OK] Port: 8000
     Evidence: Found in docker-compose.yml port mapping

FOR CI/CD & DEPLOYMENT (hero-skills:push-pr, hero-skills:ship-pr)
──────────────────────────────────────────────────
[OK] CI: GitHub Actions
     Evidence: 3 workflows: ci.yml (test+lint), build.yml (docker),
     deploy.yml (k8s)

[OK] Deployment: Kubernetes
     Evidence: k8s/ directory with deployment.yml, service.yml

[OK] Registry: ghcr.io
     Evidence: build.yml pushes to ghcr.io/org/repo

[??] ArgoCD: possibly
     Evidence: Found argocd/ directory but no sync config
     → Do you use ArgoCD for deployment?

[--] Namespaces: not detected
     → What k8s namespaces do you deploy to?

CODING CONVENTIONS (hero-skills:one-shot, hero-skills:push-pr)
──────────────────────────────────────────────
[OK] Naming: snake_case functions, PascalCase classes
     Evidence: 40+ function defs follow snake_case, all classes PascalCase

[OK] Imports: absolute (from app.models import ...), grouped stdlib/third-party/local
     Evidence: consistent across 15 source files sampled

[OK] Error handling: custom exceptions in app/exceptions.py, no bare except
     Evidence: AppError, NotFoundError, ValidationError classes found
     → All exceptions inherit AppError — is there a reason? (e.g., global handler mapping)

[OK] Logging: structlog with bound loggers
     Evidence: structlog in deps, logger = structlog.get_logger() in 8 files
     → Using structured logging — is this for a specific observability stack? (Datadog, ELK, etc.)

[OK] Tests: tests/ mirror src/, test_*.py naming, pytest fixtures (no mocks for DB)
     Evidence: tests/test_users.py, tests/test_auth.py, conftest.py with DB fixtures
     → I notice no DB mocks anywhere — is this intentional? If so, why?

[??] Docstrings: mixed — some Google-style, some missing
     Evidence: 6/15 public functions have docstrings, all Google format
     → Should all public functions have Google-style docstrings?

EXCEPTIONS & GOTCHAS
─────────────────────
[??] OpenTofu instead of Terraform
     Evidence: Found opentofu in deps, no terraform references
     → Is this a licensing decision? Claude would default to suggesting Terraform otherwise.

Please confirm or correct the [??] items, and fill in the [--] items.
Everything marked [OK] will be used as-is unless you say otherwise.
```

### Step 5: Incorporate Answers & Generate HERO.md

After the user responds, merge confirmed findings + user answers and write `HERO.md`:

```markdown
# Hero Configuration
<!-- Generated by hero-skills:init-hero. Re-run with hero-skills:init-hero --update to refresh. -->

## Coding Agent
- primary: claude-code # or cursor, windsurf, copilot, aider
- agents: AGENT_LIST # list all if team uses multiple
- hooks: true # or false — whether the agent supports pre-commit/hook integration
- rules-file: CLAUDE.md # or .cursorrules, .windsurfrules, copilot-instructions.md, none
<!-- HERO.md is refreshed on demand by `hero-skills:init-hero --update`.
     Skills detect when HERO.md is stale (project config newer than HERO.md)
     and prompt the user to run the refresh themselves. There is no
     pre-commit hook for this — it was too slow.
-->

## Code Review Agent
<!-- External code review bot that reviews PRs automatically.
     Used by hero-skills:respond-to-comments --loop to trigger, poll, and fix feedback iteratively. -->
- agent: AGENT_TYPE (greptile|coderabbit|copilot|none)
- trigger: TRIGGER_METHOD (e.g., "@greptile review" comment, auto on push, label)
- poll-method: POLL_METHOD (check-runs|comments|pipeline-status)
- bot-username: BOT_USERNAME (GitHub username of the bot, for filtering comments)

## Project Management
- tool: Linear # or Jira, GitHub Issues
- mcp-server:
- issue-prefix: PROJ

## Repository
- type: single # or monorepo
- hosting: github # or gitlab, bitbucket, other
- default-branch: main
- branch-convention: github-standard # or custom
- branch-template: "feat/ISSUE_ID-desc" # or "fix/desc"
- commit-convention: conventional # or angular, none
- merge-method: squash # or rebase, merge
<!-- Preferred PR merge method. Default: squash. Used by hero-skills:ship-pr
     when calling `gh pr merge`. Must be one of the methods allowed by the
     remote (gh repo view --json squashMergeAllowed,...). -->
- auto-delete-branches: true # or false
<!-- Whether GitHub auto-deletes merged head branches (deleteBranchOnMerge).
     If false, hero-skills:ship-pr deletes the remote + local branch after
     a successful merge. Override to false in HERO.md to keep merged
     branches around (e.g. for downstream tooling). -->
- task-runner: make # or just, taskfile, npm-scripts, none

## CI/CD
- platform: DETECTED
- workflows:
  - WORKFLOW_NAME

- required-checks: LIST_OF_REQUIRED_CHECKS

## Deployment
- platform: kubernetes # or vercel, ecs, fly
- registry: ghcr.io
- argocd: true # or false
- namespaces:
  - NAMESPACE

## Code Quality
- pre-commit: true # or false
- linters: [ruff, eslint]
- formatters: DETECTED
- type-checkers: [mypy, tsc]

## Developer Setup
<!-- What every developer needs installed to work on this project.
     This is team-shared — individual auth/config is handled by hero-skills:setup-dev. -->

### Required Tools
<!-- Only tools the project won't build/run/test without -->
- TOOL_NAME: MIN_VERSION — WHAT_IT_IS_USED_FOR
<!-- Examples:
- node: >=20 — runtime
- pnpm: >=9 — package manager (NOT npm)
- uv: >=0.4 — Python package manager
- docker: any — local dev containers
- gh: any — PR workflows, CI checks
- tofu: >=1.6 — infrastructure (NOT terraform)
- kubectl: any — deployment
-->

### Recommended Tools
<!-- Nice to have, but project works without them -->
<!-- Examples:
- pre-commit: auto-runs linters on commit
- linear: CLI for issue management
-->

### MCP Servers
<!-- MCP servers that hero skills or Claude need to interact with external tools -->
<!-- Examples:
- linear (mcp__linear) — for hero-skills:one-shot issue planning
- slack (mcp__slack) — for notifications
-->

## Coding Conventions
<!-- Detected patterns from the codebase. Adapt to the project's language/framework. -->
<!-- Rationale rules:
     - Standard/expected conventions: one-liner or omit rationale entirely
     - Non-obvious choices or exceptions to common defaults: explain WHY in a
       "reason:" line so Claude (and new team members) understand the intent -->

### Naming
- functions: snake_case # or camelCase
- classes: PascalCase
- files: snake_case # or kebab-case, PascalCase
- folders: snake_case # or kebab-case

### Imports
- style: absolute # or relative, aliases
- ordering: stdlib, third-party, local

### Error Handling
- pattern: DESCRIPTION
- custom-exceptions: true # or false; path to exceptions file if true
- reason: "all exceptions inherit AppError so the global handler can map them to HTTP status codes"

### Logging
- library: structlog # or logging, console
- style: structured # or unstructured
- reason: REASON_IF_NON_OBVIOUS

### Tests
- location: tests/ # or co-located, __tests__/
- naming: test_* # or *.test.ts, *_test.go
- fixtures: FIXTURE_DESCRIPTION
- reason: REASON_IF_NON_OBVIOUS

### API Patterns
<!-- Only include if the project has APIs -->
- style: REST # or GraphQL, gRPC
- response-format: RESPONSE_SHAPE_DESCRIPTION
- reason: REASON_IF_NON_OBVIOUS

### Documentation
- docstrings: Google # or NumPy, JSDoc, none
- required-for: public-functions # or all, none

### Exceptions & Gotchas
<!-- List anything that deviates from what Claude or a new developer would assume.
     These MUST have a reason. Keep the list short — only genuine exceptions. -->
<!-- Examples:
- Use OpenTofu, NOT Terraform — reason: licensing; the team migrated after the BSL change
- Use pnpm, NOT npm or yarn — reason: strict dependency resolution required for monorepo
- No default exports — reason: refactoring tools can't track default exports across the codebase
- DB tests hit real Postgres, never mock — reason: mocked tests passed but prod migration failed in Q3
-->

## Projects

### PROJECT_NAME
- path: PATH
- language: python # or typescript, go
- framework: fastapi # or next, express
- dependency-file: pyproject.toml # or package.json, go.mod, Cargo.toml
- install-command: "uv sync" # or "pnpm install", "go mod download"
- test-command: DETECTED_OR_CONFIRMED
- lint-command: "ruff check ." # or "pnpm lint", "make lint"
- format-command: "ruff format ." # or "pnpm format", "make format"
- typecheck-command: "mypy ." # or "pnpm typecheck", "make check"
- dev-command: DETECTED_OR_CONFIRMED
- port: DETECTED_OR_CONFIRMED
```

**Only include sections that are relevant.** If there's no CI/CD, no deployment, etc., omit those sections entirely rather than filling them with "none". Keep it clean.

**Also update CLAUDE.md Tech Stack and Best Practices sections** with a human-readable summary of the key findings. This ensures Claude has immediate context without needing to parse HERO.md. Example:

```markdown
## Tech Stack
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
- **Language:** Python 3.12
- **Framework:** FastAPI
- **Infrastructure:** OpenTofu (NOT Terraform), Kubernetes
- **Database:** PostgreSQL via SQLAlchemy
- **CI/CD:** GitHub Actions
See [HERO.md](./HERO.md) for the full tech stack configuration.

## Best Practices
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`)
- **Branches:** `feature/*`, `fix/*` off `main`
- **Code Quality:** ruff (linter), black (formatter), mypy (type checker)
- **Pre-commit:** Enabled — runs ruff, black, mypy
- **Tests:** `uv run pytest` — always run before pushing

## Coding Conventions
<!-- Auto-managed by hero-skills:init-hero. See HERO.md for full configuration. -->
- **Naming:** snake_case functions, PascalCase classes, kebab-case files
- **Imports:** Absolute (`from app.models import ...`), grouped stdlib → third-party → local
- **Error handling:** Custom exceptions in `app/exceptions.py`, no bare `except`
- **Logging:** structlog with bound loggers
- **Tests:** `tests/` mirrors `src/`, pytest fixtures, no DB mocks
- **Docstrings:** Google-style for all public functions
See [HERO.md](./HERO.md) for full coding conventions.
```

Tailor the bullet points to what was actually detected. Include anything that Claude might otherwise get wrong (e.g., "OpenTofu NOT Terraform", "pnpm NOT npm", "Bun NOT Node").

### Step 6: Validate & Confirm

Show the generated file and a one-line-per-skill summary:

```
HERO.md written to REPO_ROOT/HERO.md

How your hero skills will use this:
  hero-skills:push-pr       → conventional commits, pre-commit runs ruff + black + mypy,
                               PRs via gh against main, link LIN-### issues,
                               check GitHub Actions: ci, build, deploy
  hero-skills:one-shot      → fetch from Linear (mcp__linear), branch as feature/LIN-###-DESC
  hero-skills:push-pr (test)    → uv sync, then ruff check + mypy + pytest, smoke at :8000
  hero-skills:ship-pr       → k8s namespaces: staging, production
  hero-skills:harden        → audit pyproject.toml deps, check ghcr.io registry
  hero-skills:think-it-through arch → single repo, Python + FastAPI, k8s deployment
  hero-skills:setup-dev     → require node, uv, gh, docker; recommend pre-commit, linear CLI
  hero-skills:init-hero --update → re-investigate and refresh HERO.md on demand (run when project config changes)

Does this look right? [Y/n]
```

After confirmation, suggest:

```
Run hero-skills:setup-dev to configure your local dev environment
(git config, CLI tools, authentication) based on this HERO.md.
```

### Step 6a: Optionally Install Auto-Approve Workflow

If the user agreed to install `.github/workflows/auto-approve.yml` (Group 4 confirmation), copy it into their repo using the bundled installer. The installer's exit code is the contract — capture it and branch on it explicitly so an existing customized workflow is never silently overwritten or treated as "installed":

```bash
# Locate this plugin's installed root. Tries the two standard locations;
# bails out if neither matches.
PLUGIN_ROOT=""
for candidate in \
  "$HOME/.claude/plugins/hero-skills" \
  "$HOME/.config/claude/plugins/hero-skills"; do
  if [ -x "$candidate/scripts/install-auto-approve.sh" ]; then
    PLUGIN_ROOT="$candidate"
    break
  fi
done

INSTALL_RC=255
INSTALL_OK=false           # workflow file is in the right state to be staged
INSTALL_FRESH_WRITE=false  # the installer actually created or refreshed the file this run

# Capture pre-existence so we can tell "freshly installed" apart from
# "already up to date" — both produce exit 0, but the user-facing
# reminder text below should only fire on a fresh write.
WF_EXISTED_BEFORE=false
[ -f "$ROOT/.github/workflows/auto-approve.yml" ] && WF_EXISTED_BEFORE=true

if [ -z "$PLUGIN_ROOT" ]; then
  echo "Could not locate hero-skills plugin root in standard locations."
  echo "Install /hero-skills under ~/.claude/plugins/hero-skills, or copy"
  echo ".github/workflows/auto-approve.yml from the plugin into this repo manually."
else
  set +e
  "$PLUGIN_ROOT/scripts/install-auto-approve.sh" "$ROOT"
  INSTALL_RC=$?
  set -e
fi

case "$INSTALL_RC" in
  0)
    # Workflow file is in sync with the plugin — safe to stage.
    INSTALL_OK=true
    if [ "$WF_EXISTED_BEFORE" = "false" ]; then
      INSTALL_FRESH_WRITE=true
    fi
    ;;
  2)
    echo ""
    echo "An existing .github/workflows/auto-approve.yml differs from the plugin's."
    echo "The plugin's version was written to .github/workflows/auto-approve.yml.new."
    echo "Diff and decide before committing:"
    echo "  diff -u .github/workflows/auto-approve.yml .github/workflows/auto-approve.yml.new"
    echo "  # to apply the plugin's version:  mv .github/workflows/auto-approve.yml{.new,}"
    echo "Skipping auto-stage of the workflow file."
    ;;
  255)
    # Plugin not found — already explained above.
    ;;
  *)
    echo "Installer failed with exit code $INSTALL_RC. Investigate before committing."
    ;;
esac
```

Reminders shown only when the workflow was newly created this run (`INSTALL_FRESH_WRITE=true`). For an already-up-to-date repo (`INSTALL_OK=true` but `INSTALL_FRESH_WRITE=false`), skip the "installed at..." text — it would be misleading.

1. **Merge the workflow to the default branch.** GitHub only honors `issue_comment` workflows that already exist on the default branch.
2. **Add an `ANTHROPIC_API_KEY` repo secret.** The workflow uses it for Claude verification.

```
Auto-approve installed at .github/workflows/auto-approve.yml.

Next steps before hero-skills:ship-pr will work:
  1. git add .github/workflows/auto-approve.yml
  2. Commit, open a PR, and merge to DEFAULT_BRANCH
  3. Add ANTHROPIC_API_KEY in repo settings -> Secrets and variables -> Actions
```

### Step 7: Commit HERO.md

Always commit `HERO.md` to the repo. Do NOT ask whether to commit or whether to add it to `.gitignore`. Stage and commit it immediately after user confirmation in Step 6 (and Step 6a if the workflow was installed).

Only stage the workflow file when Step 6a reported the file is in sync with the plugin (`INSTALL_OK=true`, covering both the fresh-install and already-up-to-date paths). When the installer returned exit 2 (`EXISTS`, drift detected), the working file is still the user's original — committing it now would falsely claim `hero-skills:init-hero` installed the new version.

```bash
FILES_TO_ADD=("HERO.md" "CLAUDE.md")
if [ "${INSTALL_OK:-false}" = "true" ] && [ -f .github/workflows/auto-approve.yml ]; then
  FILES_TO_ADD+=(".github/workflows/auto-approve.yml")
fi
git add "${FILES_TO_ADD[@]}"
git commit -m "chore: initialize HERO.md and update CLAUDE.md via hero-skills:init-hero"
```

## --update Mode

When `--update` is passed:

1. Read existing `HERO.md` and `CLAUDE.md`
2. Re-run full investigation (Step 3, all sub-steps)
3. Compare findings against current config — flag what changed, what's new, and what was removed
4. Show only deltas: `[CHANGED]`, `[NEW]`, `[REMOVED]` markers
5. Ask user to confirm updates
6. Preserve any custom content or comments the user added to both files
7. Write updated `HERO.md` and refresh `CLAUDE.md` summary sections

## Key Principles

- **Investigate first, ask second.** Never ask what you can detect.
- **Show your evidence.** Every finding should cite what file/pattern you found.
- **Ask smart questions.** "I see X, does that mean Y?" not "What is your Z?"
- **Be purpose-driven.** Frame everything as "skill X needs this to work."
- **Omit irrelevant sections.** If no deployment, don't include a Deployment section.
- **One round of questions.** Present all findings at once with a single numbered list of questions (1. 2. 3. ...), get all answers at once. Use plan mode or numbered format — never freeform prose questions.

## Examples

```
hero-skills:init-hero              # Investigate and create HERO.md
hero-skills:init-hero --update     # Re-investigate and update existing config
```
