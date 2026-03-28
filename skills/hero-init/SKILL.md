---
name: hero-init
# prettier-ignore
description: Initialize Hero configuration for a project. Investigates the repo deeply, auto-detects everything it can, then confirms findings with smart questions. Creates or updates HERO.md that all /hero-* skills use.
argument-hint: [--update]
disable-model-invocation: true
---

# Hero Init - Investigate & Configure

Deeply investigate the repository, auto-detect project settings, then confirm findings with the user through smart, evidence-based questions. Creates or updates `HERO.md` at the repo root.

## Arguments

- `$ARGUMENTS`:
  - (none) - Investigate repo and create `HERO.md`
  - `--update` - Re-investigate and update existing `HERO.md`

## Why This Matters

Each `/hero-*` skill needs specific information to work well. This skill figures out what's needed by examining the repo rather than asking generic questions.

**What each skill needs from HERO.md:**

| Skill | Needs |
|-------|-------|
| `/hero-commit` | Commit convention, linters/formatters, issue prefix |
| `/hero-push` | Default branch, branch convention, CI platform, issue prefix |
| `/hero-plan` | PM tool + MCP server, branch naming, project list |
| `/hero-implement` | Linters, formatters, type-checkers, test commands, framework |
| `/hero-test` | Language, framework, test/dev commands, ports |
| `/hero-cicd` | CI platform, workflow names, registry |
| `/hero-health` | Deployment platform, namespaces, ArgoCD |
| `/hero-secure` | Registry, language/framework, dependency files |
| `/hero-architect` | Repo type, project list, deployment platform |
| `/hero-setup` | Required tools, recommended tools, MCP servers |

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
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for the full tech stack configuration detected by `/hero-init`.

## Best Practices
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for project conventions, code quality tools, and CI/CD configuration.

## Coding Conventions
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
See [HERO.md](./HERO.md) for coding conventions detected from the codebase.
```

**If `CLAUDE.md` DOES exist:**
- Read it and check whether it already has `## Tech Stack`, `## Best Practices`, and `## Coding Conventions` sections.
- If either section is **missing**, append it to the end of the file.
- If a section exists but does **not** reference `HERO.md`, add a reference line:
  `See [HERO.md](./HERO.md) for details managed by /hero-init.`
- **Do not** remove or overwrite any existing content the user has written in these sections — only add the HERO.md pointer if absent.

**Why this matters:** CLAUDE.md is loaded into Claude's context at conversation start. Without a reference to HERO.md here, Claude won't know to consult HERO.md for tech stack decisions (e.g., using OpenTofu instead of Terraform, or a specific framework) or coding conventions (e.g., snake_case, structured logging, no DB mocks in tests). The pointer ensures Claude always reads HERO.md for authoritative project configuration.

### Step 2: Check for Existing HERO.md Configuration

```bash
ls "$ROOT/HERO.md" 2>/dev/null && echo "EXISTS" || echo "NEW"
```

If `HERO.md` exists and `--update` was not passed, show current config and ask if user wants to update it. If `--update`, read the existing file to compare against new findings.

### Step 3: Deep Investigation

Launch a thorough investigation of the repository. Use an Explore subagent or do it yourself — the goal is to gather **evidence** for every configuration decision.

#### 2a: Repository & Collaboration Model

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
```

**What to look for:**
- Multiple contributors in git log → team project with shared conventions
- LICENSE + CONTRIBUTING.md → open-source, may need DCO sign-off
- CODEOWNERS → enforced code review ownership
- PR templates → structured PR process
- Branch naming patterns in `git branch -r` (e.g., `feature/PROJ-123-*`, `fix/*`)
- Commit message patterns in `git log` (e.g., `feat:`, `fix:`, `PROJ-123:`)

#### 2b: Project Management & Issue Tracking

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

#### 2c: CI/CD Platform & Workflows

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

#### 2d: Required CLI Tools & Developer Toolchain

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
- These go into HERO.md `## Developer Setup` as team-shared requirements — individual installation/auth is handled by `/hero-setup`

#### 2e: Deployment & Infrastructure

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

#### 2f: Code Quality & Developer Tooling

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

#### 2g: Project Structure & Tech Stack

```bash
# Root project files
ls pyproject.toml package.json go.mod Cargo.toml build.gradle pom.xml 2>/dev/null

# Monorepo indicators
ls pnpm-workspace.yaml lerna.json nx.json turbo.json 2>/dev/null
grep -l "workspaces" package.json 2>/dev/null

# Subproject detection
ls */pyproject.toml */package.json 2>/dev/null | head -20
ls apps/*/package.json packages/*/package.json services/*/pyproject.toml 2>/dev/null | head -20

# Framework detection (read the actual deps)
grep -E "fastapi|django|flask|starlette" pyproject.toml 2>/dev/null
grep -E "next|vite|remix|astro|nuxt|svelte|express|nestjs|hono" package.json 2>/dev/null

# Test setup
ls pytest.ini conftest.py jest.config* vitest.config* playwright.config* cypress.config* 2>/dev/null
grep -E "test-command\|scripts.*test\|pytest\|jest\|vitest" pyproject.toml package.json 2>/dev/null

# Dev server
grep -E "dev.*command\|scripts.*dev\|scripts.*start\|uvicorn\|gunicorn" pyproject.toml package.json 2>/dev/null

# Ports
grep -E "port\|PORT\|:3000\|:8000\|:8080\|:5173\|:4000" pyproject.toml package.json .env.example docker-compose*.yml 2>/dev/null | head -10
```

**What to look for:**
- Language and framework from dependency files
- Monorepo structure (workspaces, nx, turborepo, multiple pyproject.toml)
- Test commands from scripts section or config files
- Dev server commands and default ports
- Entry points for CLIs

#### 2h: Coding Conventions & Team Patterns

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

**Format for each finding:**

```
[CONFIRMED] <setting>: <value>
  Evidence: <what you found>
  Used by: /hero-commit, /hero-push

[NEEDS CONFIRMATION] <setting>: <best guess>
  Evidence: <what you found, and why it's ambiguous>
  Question: <specific question based on the evidence>
  Used by: /hero-plan

[NOT DETECTED] <setting>
  Looked for: <what you checked>
  Question: <what to ask>
  Used by: /hero-health
```

**Group findings into these categories, presented in this order:**

#### Group 1: "For committing and pushing code" (`/hero-commit`, `/hero-push`)
- Commit convention (evidence from git log patterns)
- Branch naming convention (evidence from branch -r patterns)
- Default branch
- Pre-commit hooks and what they run
- Linters, formatters

#### Group 2: "For planning and tracking work" (`/hero-plan`)
- PM tool (evidence from templates, commit messages, integrations)
- Issue ID prefix (evidence from commit/branch patterns)
- MCP server name if applicable

#### Group 3: "For implementing and testing" (`/hero-implement`, `/hero-test`)
- Per-project: language, framework, test command, dev command, port
- Type checkers
- Monorepo vs single repo structure

#### Group 4: "For CI/CD and deployment" (`/hero-cicd`, `/hero-health`, `/hero-secure`)
- CI platform and workflow names
- Deployment platform
- Container registry
- ArgoCD / GitOps
- Namespaces / environments

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

FOR COMMITTING & PUSHING (/hero-commit, /hero-push)
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

FOR PLANNING & TRACKING (/hero-plan)
─────────────────────────────────────
[??] PM tool: likely Linear
     Evidence: Found "linear" in .github/workflows/sync.yml,
     commits reference LIN-XXX IDs
     → Is Linear your PM tool? What MCP server name?

[OK] Issue prefix: LIN
     Evidence: 8 commits reference LIN-### pattern

FOR IMPLEMENTING & TESTING (/hero-implement, /hero-test)
────────────────────────────────────────────────────────
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

FOR CI/CD & DEPLOYMENT (/hero-cicd, /hero-health)
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

CODING CONVENTIONS (/hero-implement, /hero-commit)
───────────────────────────────────────────────────
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
<!-- Generated by /hero-init. Re-run with /hero-init --update to refresh. -->

## Project Management
- tool: <detected-or-confirmed>
- mcp-server: <if applicable>
- issue-prefix: <detected-or-confirmed>

## Repository
- type: <single|monorepo>
- default-branch: <detected>
- branch-convention: <detected-or-confirmed>
- commit-convention: <detected-or-confirmed>

## CI/CD
- platform: <detected>
- workflows:
  - <workflow-1>
  - <workflow-2>

## Deployment
- platform: <detected-or-confirmed>
- registry: <detected-or-confirmed>
- argocd: <true|false>
- namespaces:
  - <namespace-1>

## Code Quality
- pre-commit: <true|false>
- linters: <detected>
- formatters: <detected>
- type-checkers: <detected>

## Developer Setup
<!-- What every developer needs installed to work on this project.
     This is team-shared — individual auth/config is handled by /hero-setup. -->

### Required Tools
<!-- Only tools the project won't build/run/test without -->
- <tool>: <minimum-version-if-known> — <what it's used for>
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
- linear (mcp__linear) — for /hero-plan issue management
- slack (mcp__slack) — for notifications
-->

## Coding Conventions
<!-- Detected patterns from the codebase. Adapt to the project's language/framework. -->
<!-- Rationale rules:
     - Standard/expected conventions: one-liner or omit rationale entirely
     - Non-obvious choices or exceptions to common defaults: explain WHY in a
       "reason:" line so Claude (and new team members) understand the intent -->

### Naming
- functions: <snake_case|camelCase>
- classes: <PascalCase>
- files: <snake_case|kebab-case|PascalCase>
- folders: <snake_case|kebab-case>

### Imports
- style: <absolute|relative|aliases>
- ordering: <stdlib, third-party, local>

### Error Handling
- pattern: <description of how errors are handled>
- custom-exceptions: <true|false, location if true>
- reason: <only if non-standard — e.g., "all exceptions inherit AppError so the global handler can map them to HTTP status codes">

### Logging
- library: <detected>
- style: <structured|unstructured>
- reason: <only if non-obvious — e.g., "structured JSON for Datadog ingestion">

### Tests
- location: <tests/|co-located|__tests__/>
- naming: <test_*|*.test.ts|*_test.go>
- fixtures: <description of fixture/mock approach>
- reason: <only if non-obvious — e.g., "no DB mocks — we hit a real test DB because mocked tests missed a migration bug in Q3">

### API Patterns
<!-- Only include if the project has APIs -->
- style: <REST|GraphQL|gRPC>
- response-format: <description if consistent pattern found>
- reason: <only if non-obvious — e.g., "envelope pattern with {data, error, meta} because the mobile team parses it that way">

### Documentation
- docstrings: <Google|NumPy|JSDoc|none>
- required-for: <public functions|all|none>

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

### <project-name>
- path: <detected>
- language: <detected>
- framework: <detected>
- test-command: <detected-or-confirmed>
- dev-command: <detected-or-confirmed>
- port: <detected-or-confirmed>
```

**Only include sections that are relevant.** If there's no CI/CD, no deployment, etc., omit those sections entirely rather than filling them with "none". Keep it clean.

**Also update CLAUDE.md Tech Stack and Best Practices sections** with a human-readable summary of the key findings. This ensures Claude has immediate context without needing to parse HERO.md. Example:

```markdown
## Tech Stack
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
- **Language:** Python 3.12
- **Framework:** FastAPI
- **Infrastructure:** OpenTofu (NOT Terraform), Kubernetes
- **Database:** PostgreSQL via SQLAlchemy
- **CI/CD:** GitHub Actions
See [HERO.md](./HERO.md) for the full tech stack configuration.

## Best Practices
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`)
- **Branches:** `feature/*`, `fix/*` off `main`
- **Code Quality:** ruff (linter), black (formatter), mypy (type checker)
- **Pre-commit:** Enabled — runs ruff, black, mypy
- **Tests:** `uv run pytest` — always run before pushing

## Coding Conventions
<!-- Auto-managed by /hero-init. See HERO.md for full configuration. -->
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
HERO.md written to <root>/HERO.md

How your hero skills will use this:
  /hero-commit  → conventional commits, ruff + black pre-commit
  /hero-push    → PRs against main, link LIN-### issues
  /hero-plan    → fetch from Linear (mcp__linear), branch as LIN-###-<desc>
  /hero-test    → uv run pytest on :8000
  /hero-cicd    → check GitHub Actions: ci, build, deploy
  /hero-health  → k8s namespaces: staging, production

Does this look right? [Y/n]
```

After confirmation, suggest:
```
Run /hero-setup to configure your local dev environment
(git config, CLI tools, authentication) based on this HERO.md.
```

### Step 7: Git Decision

```
Should HERO.md be committed to the repo?
1. Yes - shared with team (recommended for team projects)
2. No - add to .gitignore (personal config)
```

**Auto-suggest based on evidence:**
- If CONTRIBUTING.md or multiple contributors → suggest "Yes, shared"
- If solo project → suggest either is fine

## --update Mode

When `--update` is passed:

1. Read existing `HERO.md`
2. Re-run investigation (Step 2)
3. Compare findings against current config
4. Show only what changed or what's new
5. Ask user to confirm updates
6. Preserve any custom content or comments the user added
7. Write updated file

## Key Principles

- **Investigate first, ask second.** Never ask what you can detect.
- **Show your evidence.** Every finding should cite what file/pattern you found.
- **Ask smart questions.** "I see X, does that mean Y?" not "What is your Z?"
- **Be purpose-driven.** Frame everything as "skill X needs this to work."
- **Omit irrelevant sections.** If no deployment, don't include a Deployment section.
- **One round of questions.** Present all findings at once, get all answers at once.

## Examples

```
/hero-init              # Investigate and create HERO.md
/hero-init --update     # Re-investigate and update existing config
```
