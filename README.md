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
- **Ship with confidence** — Pre-commit checks, conventional commits, draft PRs by default, automated parallel review before requesting human review
- **Stay informed** — CI/CD status, cluster health, security scans

## Install

```bash
git clone https://github.com/ai-hero/hero-skills.git ~/.claude/plugins/hero-skills
```

Skills are immediately available in any Claude Code session. No restart needed.

### Companion installs (for full pipeline coverage)

Three pieces ride along with one-shot — install them so Steps 3 (`test`), 5 (`push`), 6 (`self-review`), 9 (`respond`), and 10 (`ship`) work out of the box:

**1. GitHub CLI (`gh`)** — required by `push-pr`, `review-pr`, `respond-to-comments`, and `ship-pr` for every PR / comment / workflow operation. Without it, every step from `push-draft` onward fails immediately.

```bash
# macOS (Homebrew)
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh

# Other platforms: https://cli.github.com/
```

Then authenticate with the `repo` scope (required for PR creation, merge, and `gh secret set`):

```bash
gh auth login -s repo
```

`hero-skills:preflight` verifies both presence and the `repo` scope.

**2. `pr-review-toolkit` plugin** — provides the five review agents that `hero-skills:review-pr` runs in parallel (code-reviewer, silent-failure-hunter, pr-test-analyzer, comment-analyzer, type-design-analyzer). From inside Claude Code:

```
/plugin install pr-review-toolkit
```

Or from the host shell:

```bash
claude plugins add pr-review-toolkit@claude-plugins-official
```

If you skip this, `hero-skills:review-pr` still runs but produces a much thinner review.

**3. Playwright MCP server** — drives the browser smoke test in `hero-skills:test-changes` (frontend smoke). Requires Node.js 18+ (check with `node --version`):

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

Use `--scope user` to share the registration across every project on the machine, or `--scope project` to commit it to the repo. Without this, the frontend-smoke portion of the `test` step renders `(–)` (skipped) and you lose the UI regression check before commits land.

## Quick Start

```
# 1. Configure your project (run once per repo)
hero-skills:init-hero

# 2. Plan and implement from a ticket — Plan Mode drafts the approach,
#    approve it, and Claude implements in the same conversation (inline, no skill)
#                                              # Steps 1–2: plan, implement

# 3. Verify, simplify, push as draft, then review your own PR
hero-skills:test-changes                    # Step 3: lint/typecheck/unit tests + UI smoke
/simplify                                   # Step 4: tidy the dirty diff
hero-skills:push-pr                         # Step 5: commit + push, opens a DRAFT PR
hero-skills:review-pr                       # Steps 6–7: parallel review agents, fixes, then mark-ready gate

# 4. Wait for the review bot, address its feedback, then ship
#    (the wait in Step 8 is implicit — respond-to-comments only runs once the bot replies)
hero-skills:respond-to-comments             # Step 9: address Copilot/CodeRabbit/Greptile inline comments
hero-skills:ship-pr                         # Step 10: @auto-approve, merge, reset to default branch
```

That's it. Each command reads your `HERO.md` config and adapts to your stack automatically.

### Or: one-shot the whole thing

For genuinely small, low-risk PRs:

```
hero-skills:one-shot PROJ-123
```

This chains all ten steps end-to-end — `plan → implement → test → simplify → push → self-review → mark-ready → await-review → respond → ship` — with explicit user gates at plan-approval, mark-ready, and merge. `test` includes a UI smoke check via Playwright MCP for routes affected by the diff and is skipped automatically on backend-only PRs. `simplify` runs the `/simplify` skill on the dirty diff so the commit lands clean. `push` commits and opens the draft PR in one step. `mark-ready` is the explicit draft → ready gate; `await-review` polls for your configured Code Review Agent (Copilot, CodeRabbit, Greptile, …) before `respond` addresses its feedback.

At each step transition, one-shot prints a progress line so you always know where you are:

```
[6/10] (✓) plan → (✓) implement → (✓) test → (✓) simplify → (✓) push → (▶) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship

Now running: self-review
```

Each step maps to a skill you can run on its own when you don't want the whole pipeline:

| # | Step | Skill to run standalone |
|---|------|-------------------------|
| 1 | `plan` | inline (Plan Mode; fetches a Linear issue if given an issue ID) |
| 2 | `implement` | inline (Plan Mode → edits) |
| 3 | `test` | `hero-skills:test-changes` (includes UI smoke) |
| 4 | `simplify` | `/simplify` (external skill) |
| 5 | `push` | `hero-skills:push-pr` (commits + pushes a draft PR) |
| 6 | `self-review` | `hero-skills:review-pr --no-mark-ready` |
| 7 | `mark-ready` | `hero-skills:review-pr`'s own Step 9 gate, or `gh pr ready` |
| 8 | `await-review` | inline poll (no separate skill) |
| 9 | `respond` | `hero-skills:respond-to-comments` |
| 10 | `ship` | `hero-skills:ship-pr` |

Re-running `hero-skills:one-shot` mid-flow is safe: it inspects git + the open PR for that branch and resumes from the inferred step deterministically — no confirmation prompt. On the default branch with work to preserve, one-shot auto-branches off (no prompt) before resuming. It exits cleanly with a hand-off hint only when there's nothing left to do (e.g., after the PR has merged) or when state can't be inferred safely (e.g., a failed `git fetch`).

See [`PIPELINES.md`](./PIPELINES.md) for the full DAG and stop conditions.

## Commands

### Setup

| Command | What it does |
|---------|-------------|
| `hero-skills:init-hero` | Investigate your repo, auto-detect stack, create `HERO.md` config |
| `hero-skills:preflight` | Catch missing tooling, stale `HERO.md`, env mismatches, and busy ports before a pipeline step does destructive work |
| `hero-skills:setup-dev` | Set up a developer's local environment (tools, auth, dependencies) |
| `hero-skills:create-project` | Scaffold a new project (Python, full-stack, Node.js) |
| `hero-skills:create-skill` | Create a new Claude Code skill, subagent, rule, or hook |

### Development Cycle

| Command | What it does |
|---------|-------------|
| `hero-skills:test-changes` | Verify changes (lint, typecheck, unit tests) and run smoke tests — including UI smoke via Playwright MCP — for any project type |
| `hero-skills:push-pr` | Commit + push + draft PR + CI status — smart conventional commit, then opens a **draft PR** by default, or merges into a target branch |

### Code Review

| Command | What it does |
|---------|-------------|
| `hero-skills:review-pr` | Review a PR: your draft → runs all agents in parallel, applies fixes, asks before marking ready. Others' PR → inline comments only. |
| `hero-skills:respond-to-comments` | Fix PR review comments, resolve threads, optionally loop with external review agent |
| `hero-skills:ship-pr` | Trigger gated `@auto-approve`, wait for the verdict, merge if it passes, reset to the default branch, and run a post-merge deploy-health check |

### Pipelines (orchestrators)

| Command | What it does |
|---------|-------------|
| `hero-skills:one-shot` | Drives a small task end-to-end: plan → implement → test → simplify → push → self-review → mark-ready → await-review → respond → ship. Detects a resume point on re-invocation. Explicit user gates at each destructive step. |
| `hero-skills:create-project` | Scaffolds a new project, then chains into setup-dev → init-hero → first-commit. |

### Operations

| Command | What it does |
|---------|-------------|
| `hero-skills:scan-vulns` | Scan dependencies (Dependabot) and containers (Docker Scout) for CVEs |
| `hero-skills:document-arch` | Create and update architecture specs with Mermaid diagrams |

### Utilities

| Command | What it does |
|---------|-------------|
| `hero-skills:reset-branch` | Reset to default branch, pull latest, clear conversation context |
| `hero-skills:audit-plugin` | Audit the hero-skills plugin itself for quality and consistency |

## HERO.md

Every skill reads `HERO.md` from your repo root. It declares your stack so skills don't have to guess. **HERO.md is committed to the repo** — it's team-shared, so every developer and every skill works from the same config.

When project config drifts (new deps, CI changes, switched task runner), skills detect the staleness and remind you to run `hero-skills:init-hero --update` to refresh. There is no auto-pre-commit hook for this — it was too slow. Run the refresh on demand.

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

No `HERO.md`? Skills fall back to auto-detection. Run `hero-skills:init-hero` to generate one — it investigates your repo and asks smart questions to fill in what it can't detect.

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

Use `hero-skills:create-skill` to create new skills that plug into the same workflow and read the same `HERO.md` config.

Skills are markdown files in the `skills/` directory. Each is a structured prompt with instructions Claude follows when you invoke it. No code to compile, no APIs to wire up.

## License

MIT — built by [AI Hero](https://aihero.studio).
