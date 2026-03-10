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

## Instructions

### Step 1: Check for Existing Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls "$ROOT/HERO.md" 2>/dev/null && echo "EXISTS" || echo "NEW"
```

If `HERO.md` exists and `--update` was not passed, show current config and ask if user wants to update it. If `--update`, read the existing file to compare against new findings.

### Step 2: Deep Investigation

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

#### 2d: Deployment & Infrastructure

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

#### 2e: Code Quality & Developer Tooling

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

#### 2f: Project Structure & Tech Stack

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

### Step 3: Synthesize Findings into Smart Questions

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

Please confirm or correct the [??] items, and fill in the [--] items.
Everything marked [OK] will be used as-is unless you say otherwise.
```

### Step 4: Incorporate Answers & Generate HERO.md

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

### Step 5: Validate & Confirm

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

### Step 6: Git Decision

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
