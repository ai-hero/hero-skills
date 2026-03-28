<p align="center">
  <img src="https://img.shields.io/badge/Hero_Skills-Claude_Code_Plugin-7C3AED?style=for-the-badge&logoColor=white" alt="Hero Skills" />
</p>

<h3 align="center">Your dev workflow, automated end to end.</h3>

<p align="center">
  An opinionated development workflow for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> — customizable to <em>your</em> opinions.
</p>

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#commands">Commands</a> &bull;
  <a href="#heromd">Config</a> &bull;
  <a href="#extending">Extending</a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/ai-hero/hero-skills?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/claude_code-plugin-blue?style=flat-square" alt="Claude Code Plugin" />
</p>

---

## Why Hero Skills?

Most dev work follows the same loop: grab a ticket, plan, implement, test, review, commit, push, monitor. But every team does it slightly differently — different PM tools, different CI, different deploy targets.

Hero Skills gives you **slash commands for the entire dev lifecycle** that adapt to your stack. Configure once with `HERO.md`, then every skill knows your conventions, your tools, and your preferences.

- **Plan from tickets** — Fetch from Linear/Jira/GitHub Issues, create branches, draft implementation plans
- **Implement with guardrails** — Execute plans step by step with per-step verification
- **Test anything** — Auto-detect project type (API, frontend, CLI, MCP) and run the right smoke tests
- **Ship with confidence** — Self-review, pre-commit checks, conventional commits, PR creation
- **Stay informed** — CI/CD status, cluster health, security scans

## Install

```bash
git clone https://github.com/ai-hero/hero-skills.git ~/.claude/plugins/hero-skills
```

Skills are immediately available in any Claude Code session. No restart needed.

## Quick Start

```
# 1. Configure your project (run once per repo)
/hero-init

# 2. Plan work from a ticket
/hero-plan PROJ-123

# 3. Implement the approved plan
/hero-implement

# 4. Test, review, commit, push
/hero-test
/hero-commit
/hero-push
```

That's it. Each command reads your `HERO.md` config and adapts to your stack automatically.

## Commands

### Setup

| Command | What it does |
|---------|-------------|
| `/hero-init` | Investigate your repo, auto-detect stack, create `HERO.md` config |
| `/hero-setup` | Set up a developer's local environment (tools, auth, dependencies) |
| `/hero-new` | Scaffold a new project (Python, full-stack, Node.js) in any repo structure |

### Development Cycle

| Command | What it does |
|---------|-------------|
| `/hero-plan` | Fetch a ticket, create a branch, draft an implementation plan |
| `/hero-implement` | Execute an approved plan step by step with verification |
| `/hero-test` | Auto-detect project type and run smoke tests |
| `/hero-commit` | Self-review, pre-commit checks, grouped conventional commits |
| `/hero-push` | Push, create PR with generated description, or merge |
| `/hero-update` | Sync HERO.md with codebase changes (wire into pre-commit) |

### Operations

| Command | What it does |
|---------|-------------|
| `/hero-cicd` | Check CI/CD pipeline status, build logs, image publish status |
| `/hero-health` | Kubernetes cluster health (nodes, pods, deployments, ArgoCD) |
| `/hero-secure` | Scan dependencies (Dependabot) and containers (Docker Scout) for CVEs |

### Architecture & Meta

| Command | What it does |
|---------|-------------|
| `/hero-architect` | Generate architecture specs with Mermaid diagrams |
| `/hero-new-skill` | Create new Claude Code skills, rules, or hooks |
| `/hero-meta` | Audit the hero-skills plugin itself for quality and consistency |

## HERO.md

Every skill reads `HERO.md` from your repo root. It declares your stack so skills don't have to guess. **HERO.md is committed to the repo** — it's team-shared, so every developer and every hero skill works from the same config.

To keep it in sync automatically, wire `/hero-update` into your pre-commit hooks. A fast bash gate script checks staged files first — most commits skip Claude entirely and finish in milliseconds. Only when you change dependencies, CI config, or project structure does it invoke Claude to sync HERO.md.

Here's what a minimal config looks like:

```markdown
# HERO Configuration

## Project Management
- Tool: Linear
- Project: PROJ

## CI/CD
- Platform: GitHub Actions

## Code Quality
- Pre-commit: true
- Formatter: ruff format
- Linter: ruff check

## Projects
### api
- Language: Python
- Framework: FastAPI
- Test command: pytest
- Dev command: uvicorn main:app --reload
```

No `HERO.md`? Skills fall back to auto-detection. Run `/hero-init` to generate one — it investigates your repo and asks smart questions to fill in what it can't detect.

<details>
<summary><strong>Full config reference</strong></summary>

`HERO.md` supports these sections:

- **Project Management** — Linear, Jira, Asana, GitHub Issues
- **CI/CD** — GitHub Actions, GitLab CI, Jenkins, CircleCI
- **Deployment** — Kubernetes, Vercel, ECS, Fly.io, container registries
- **Code Quality** — pre-commit, linters, formatters, type checkers
- **Projects** — per-subproject language, framework, test/dev commands, ports

</details>

## Extending

Hero Skills is built to be extended. Use `/hero-new-skill` to create new skills that plug into the same workflow and read the same `HERO.md` config.

Skills are markdown files that live in the `skills/` directory. Each skill is a structured prompt with instructions Claude follows when you invoke it. No code to compile, no APIs to wire up.

## License

MIT — built by [AI Hero](https://aihero.studio).
