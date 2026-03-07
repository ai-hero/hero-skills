# Hero Skills

An opinionated development workflow for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — customizable to *your* opinions.

Hero skills give you a structured, end-to-end dev process: plan from tickets, implement with verification, test, review, commit, push PRs, and monitor deployments. They work across any project — Python, TypeScript, full-stack, monorepo or single repo.

**The opinions are yours.** Run `/hero-init` to create a `HERO.md` at your repo root that configures every skill to your PM tool, CI/CD platform, deployment target, and conventions. Without it, skills auto-detect and use sensible defaults.

## Install

```bash
git clone https://github.com/ai-hero/hero-skills.git ~/.claude/skills/hero-skills
```

Skills are immediately available in any Claude Code session. No restart needed.

## The Workflow

```
/hero-init       Configure HERO.md for your project (run once per repo)

/hero-new        Scaffold a new project
/hero-plan       Fetch a ticket → create branch → draft implementation plan
/hero-implement  Execute the plan step by step with verification
/hero-test       Smoke test backend, frontend, CLI, MCP — or all
/hero-commit     Code review + pre-commit checks + conventional commits
/hero-push       Push, create PR, or merge to target branch
/hero-cicd       Check CI/CD pipeline status
```

## All Commands

| Command | What it does |
|---------|-------------|
| `/hero-init` | Create/update `HERO.md` — your project config for all hero skills |
| `/hero-new` | Scaffold projects (Python, full-stack, Node.js) in single or monorepos |
| `/hero-plan` | Fetch issue from your PM tool, create branch, draft implementation plan |
| `/hero-implement` | Execute an approved plan end-to-end with per-step verification |
| `/hero-test` | Auto-detect project type and run smoke tests |
| `/hero-commit` | Ruthless self-review, pre-commit checks, grouped conventional commits |
| `/hero-push` | Push to remote, create PR with generated description, or merge |
| `/hero-cicd` | Check workflow runs, build logs, image publish status |
| `/hero-health` | Kubernetes cluster health check (nodes, pods, deployments, ArgoCD) |
| `/hero-secure` | Scan dependencies (Dependabot) and containers (Docker Scout) for CVEs |
| `/hero-architect` | Generate architecture specs with Mermaid diagrams in `specs/` |
| `/hero-skill` | Create new Claude Code skills, rules, or hooks |

## HERO.md

Every skill reads `HERO.md` from your repo root. It declares your stack so skills don't have to guess:

- **Project Management** — Linear, Jira, Asana, GitHub Issues
- **CI/CD** — GitHub Actions, GitLab CI, Jenkins, CircleCI
- **Deployment** — Kubernetes, Vercel, ECS, Fly.io, container registries
- **Code Quality** — pre-commit, linters, formatters, type checkers
- **Projects** — per-subproject language, framework, test/dev commands, ports

No `HERO.md`? Skills fall back to auto-detection. Run `/hero-init` to generate one interactively.

## License

MIT — built by [AI Hero](https://aihero.studio).
