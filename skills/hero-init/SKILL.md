---
name: hero-init
# prettier-ignore
description: Initialize Hero configuration for a project. Creates HERO.md at the repo root with project management, CI/CD, deployment, code quality, and tech stack settings that all /hero-* skills use. Run once per repo.
argument-hint: [--update]
disable-model-invocation: true
---

# Hero Init - Initialize Hero Configuration

Create or update `HERO.md` at the repository root. This file configures all `/hero-*` skills with project-specific settings: what PM tool you use, how you deploy, your tech stack, and your conventions.

## Arguments

- `$ARGUMENTS`:
  - (none) - Interactive wizard to create `HERO.md`
  - `--update` - Re-detect and update existing `HERO.md`

## Instructions

### Step 1: Check for Existing Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls "$ROOT/HERO.md" 2>/dev/null && echo "EXISTS" || echo "NEW"
```

If `HERO.md` exists and `--update` was not passed, show current config and ask if user wants to update it.

### Step 2: Detect Repository Structure

```bash
# Repo type
ls */pyproject.toml */package.json 2>/dev/null | head -10

# CI/CD
ls .github/workflows/*.yml .gitlab-ci.yml Jenkinsfile .circleci/config.yml 2>/dev/null

# Deployment
ls k8s/ kubernetes/ Dockerfile* docker-compose*.yml 2>/dev/null
ls vercel.json netlify.toml fly.toml render.yaml 2>/dev/null

# Code quality
ls .pre-commit-config.yaml .eslintrc* .prettierrc* ruff.toml 2>/dev/null
```

Use detection results as defaults, but always confirm with user.

### Step 3: Interactive Configuration

Ask the user about each section. Present detected defaults where available.

#### 3a: Project Management

```
Which project management tool do you use?
1. Linear (MCP: mcp__linear-server)
2. Jira (MCP or CLI)
3. Asana (MCP or CLI)
4. GitHub Issues (gh CLI)
5. Shortcut
6. None / other

Issue ID prefix (e.g., PROJ, ENG): ___
```

#### 3b: Repository & Conventions

```
Repository type: [auto-detected: single | monorepo]
Default branch: [auto-detected: main | master]
Branch naming: {issue-id}-{short-desc} | custom
Commit convention: conventional | angular | none
```

#### 3c: CI/CD

```
CI/CD platform: [auto-detected]
1. GitHub Actions
2. GitLab CI
3. Jenkins
4. CircleCI
5. None

Key workflow names (comma-separated, or leave blank):
```

#### 3d: Deployment

```
Deployment platform:
1. Kubernetes
2. AWS ECS
3. Vercel
4. Netlify
5. Fly.io
6. Heroku
7. Azure App Service
8. None / manual

Container registry (if applicable):
1. GitHub Container Registry (ghcr.io)
2. AWS ECR
3. Docker Hub
4. Azure ACR
5. Google Artifact Registry
6. None

ArgoCD for GitOps? [y/n]
```

#### 3e: Code Quality

```
Pre-commit hooks: [auto-detected: yes/no]
Linters: [auto-detected, e.g., ruff, eslint]
Formatters: [auto-detected, e.g., black, prettier]
Type checkers: [auto-detected, e.g., mypy, tsc]
```

#### 3f: Projects (for monorepos, or single project)

For each detected project (or the root project):

```
Project: <name>
  Path: <path>
  Language: python | typescript | javascript
  Framework: fastapi | django | flask | nextjs | vite | express | none
  Test command: <e.g., uv run pytest, npm test>
  Dev command: <e.g., uv run uvicorn app.main:app --reload, npm run dev>
  Port: <default port>
```

### Step 4: Generate HERO.md

Write the file to the repository root:

```markdown
# Hero Configuration
<!-- This file configures /hero-* skills. See /hero-init to update. -->

## Project Management
- tool: <linear|jira|asana|github-issues|shortcut|none>
- mcp-server: <mcp server name, if applicable>
- issue-prefix: <e.g., PROJ>

## Repository
- type: <single|monorepo>
- default-branch: <main|master>
- branch-convention: <{issue-id}-{short-desc}>
- commit-convention: <conventional|angular|none>

## CI/CD
- platform: <github-actions|gitlab-ci|jenkins|circleci|none>
- workflows:
  - <workflow-name-1>
  - <workflow-name-2>

## Deployment
- platform: <kubernetes|ecs|vercel|netlify|fly|heroku|azure|none>
- registry: <ghcr|ecr|docker-hub|acr|gar|none>
- argocd: <true|false>
- namespaces:
  - <namespace-1>
  - <namespace-2>

## Code Quality
- pre-commit: <true|false>
- linters: <ruff, eslint>
- formatters: <black, prettier>
- type-checkers: <mypy, tsc>

## Projects

### <project-name>
- path: <./ or subdir/>
- language: <python|typescript|javascript>
- framework: <fastapi|nextjs|vite|express|none>
- test-command: <uv run pytest>
- dev-command: <uv run uvicorn app.main:app --reload>
- port: <8000>
```

### Step 5: Validate

Read back the generated file and confirm with the user:

```
HERO.md created at <root>/HERO.md

Configuration Summary:
  PM: Linear (PROJ-*)
  CI/CD: GitHub Actions
  Deploy: Kubernetes + ArgoCD (ghcr.io)
  Projects: 3 (backend, frontend, worker)

All /hero-* skills will now use this configuration.
Does this look correct? [Y/n]
```

### Step 6: Git Ignore Decision

Ask whether to commit `HERO.md` or keep it local:

```
Should HERO.md be committed to the repo?
1. Yes - Team-shared configuration (recommended)
2. No - Add to .gitignore (personal config only)
```

## --update Mode

When `--update` is passed:

1. Read existing `HERO.md`
2. Re-run detection (Step 2)
3. Show diff between current config and detected state
4. Ask user which sections to update
5. Preserve any custom content or comments
6. Write updated file

## Examples

```
/hero-init              # Interactive wizard
/hero-init --update     # Re-detect and update existing config
```

## Notes

- Run once per repo, update as your stack changes
- All `/hero-*` skills read `HERO.md` — if missing, they auto-detect and suggest `/hero-init`
- `HERO.md` uses simple `key: value` format under markdown headers for easy parsing
- Custom comments and extra sections are preserved during `--update`
