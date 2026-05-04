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

- **Plan and implement from tickets** — Fetch from Linear/Jira/GitHub Issues, create branches, draft implementation plans in Plan Mode, then implement on approval
- **Verify changes** — Auto-detect project type (API, frontend, CLI, MCP) and run lint, typecheck, unit tests, and smoke tests
- **Ship with confidence** — Pre-commit checks, conventional commits, draft PRs by default, automated self-review before requesting human review
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

# 2. Plan work from a ticket — Plan Mode drafts the approach,
#    approve it, and Claude implements in the same conversation
/hero-plan PROJ-123

# 3. Verify, commit, push as draft, self-review
/hero-test
/hero-commit
/hero-push                 # opens a DRAFT PR
/hero-self-review          # runs review-pr, fixes findings, asks to mark ready

# 4. Once reviewers (human or bot) sign off, gate the merge with /hero-auto-approve
/hero-auto-approve         # @auto-approves only if reviewed + all threads resolved, then offers to merge
```

That's it. Each command reads your `HERO.md` config and adapts to your stack automatically.

## Commands

### Setup

| Command | What it does |
|---------|-------------|
| `/hero-init` | Investigate your repo, auto-detect stack, create `HERO.md` config |
| `/hero-setup` | Set up a developer's local environment (tools, auth, dependencies) |
| `/hero-new-project` | Scaffold a new project (Python, full-stack, Node.js) in any repo structure |
| `/hero-new-skill` | Create new Claude Code skills, rules, or hooks |

### Development Cycle

| Command | What it does |
|---------|-------------|
| `/hero-plan` | Fetch a ticket, create a branch, draft a plan in Plan Mode, then implement on approval |
| `/hero-test` | Verify changes (lint, typecheck, unit tests) and run smoke tests for any project type |
| `/hero-commit` | Code review, pre-commit checks, grouped conventional commits — never on main |
| `/hero-push` | Push and open a **draft PR** by default, or merge into a target branch |

### Code Review

| Command | What it does |
|---------|-------------|
| `/hero-self-review` | Run automated review on your draft PR, post findings, apply fixes, ask before marking ready |
| `/hero-review-pr` | Review someone else's PR and leave inline comments |
| `/hero-respond-to-pr` | Fix PR review comments, resolve threads, optionally loop with external review agent |
| `/hero-auto-approve` | Trigger gated `@auto-approve` on a ready PR, wait for the verdict, and offer to merge if it passes |

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
| `/hero-meta` | Audit the hero-skills plugin itself for quality and consistency |

## HERO.md

Every skill reads `HERO.md` from your repo root. It declares your stack so skills don't have to guess. **HERO.md is committed to the repo** — it's team-shared, so every developer and every hero skill works from the same config.

To keep it in sync automatically, wire `/hero-init --update` into your pre-commit hooks. A fast bash gate script checks staged files first — most commits skip Claude entirely and finish in milliseconds. Only when you change dependencies, CI config, or project structure does it invoke Claude to sync HERO.md.

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
- **Code Review Agent** — Greptile, CodeRabbit, Copilot (trigger, poll method, bot username)
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
