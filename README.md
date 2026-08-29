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

- **Plan and implement from tickets** — Fetch from Linear/Jira/GitHub Issues, grill the work into dependency-aware work-items, create branches, then implement on approval
- **Verify changes** — Auto-detect project type (API, frontend, CLI, MCP) and run lint, typecheck, unit tests, and smoke tests
- **Ship with confidence** — Pre-commit checks, conventional commits, draft PRs by default, automated parallel review before requesting human review
- **Stay informed** — CI/CD status, cluster health, security scans

## Install

```bash
git clone https://github.com/ai-hero/hero-skills.git ~/.claude/plugins/hero-skills
```

Skills are immediately available in any Claude Code session. No restart needed.

### Companion installs (for full pipeline coverage)

Three pieces ride along with one-shot — install them so Steps 4 (`push`, tests included), 5 (`self-review`), 8 (`respond`), and 9 (`ship`) work out of the box:

**1. GitHub CLI (`gh`)** — required by `push-pr`, `review-pr`, `respond-to-comments`, and `ship-pr` for every PR / comment / workflow operation. Without it, every step from `push` onward fails immediately.

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

**2. `pr-review-toolkit` plugin** — provides five of the six review agents that `hero-skills:review-pr` runs in parallel (code-reviewer, silent-failure-hunter, pr-test-analyzer, comment-analyzer, type-design-analyzer; the sixth, a security pass, needs no install). From inside Claude Code:

```
/plugin install pr-review-toolkit
```

Or from the host shell:

```bash
claude plugins add pr-review-toolkit@claude-plugins-official
```

If you skip this, `hero-skills:review-pr` still runs but produces a much thinner review.

**3. Playwright MCP server** — drives the browser smoke test in `hero-skills:push-pr`'s test phase (frontend smoke). Requires Node.js 18+ (check with `node --version`):

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

Use `--scope user` to share the registration across every project on the machine, or `--scope project` to commit it to the repo. Without this, the frontend-smoke portion of the test phase renders `(–)` (skipped) and you lose the UI regression check before commits land.

## Quick Start

```
# 1. Configure your project (run once per repo)
hero-skills:init-hero

# 2. Plan and implement from a ticket — think-it-through grills the work into
#    work-items, you confirm, and Claude implements one in the same conversation
#                                              # Steps 1–2: plan, implement

# 3. Simplify, then test + push as draft, then review your own PR
/simplify                                   # Step 3: tidy the dirty diff
hero-skills:push-pr                         # Step 4: test (lint/typecheck/unit + UI smoke), commit + push, DRAFT PR
hero-skills:review-pr                       # Steps 5–6: parallel review agents + security pass, fixes, then mark-ready gate

# 4. Wait for the review bot, address its feedback, then ship
#    (the wait in Step 7 is implicit — respond-to-comments only runs once the bot replies)
hero-skills:respond-to-comments             # Step 8: address Copilot/CodeRabbit/Greptile inline comments
hero-skills:ship-pr                         # Step 9: @auto-approve, merge, reset to default branch
```

That's it. Each command reads your `HERO.md` config and adapts to your stack automatically.

### Or: one-shot the whole thing

For genuinely small, low-risk PRs:

```
hero-skills:one-shot PROJ-123   # start a new ticket (or a plain-text description)
hero-skills:one-shot            # resume the current goal to merged + reset branch
```

This chains all nine steps end-to-end — `plan → implement → simplify → push → self-review → mark-ready → await-review → respond → ship` — with explicit user gates at plan-approval, mark-ready, and merge. `plan` resolves what you asked for against your `.plans/` store and this repo's tracker before it plans anything new, delegating to `hero-skills:think-it-through` only when nothing matches — and it re-checks a matched item against the codebase first, so already-finished work is reported rather than rebuilt. `simplify` runs the `/simplify` skill on the dirty diff so the commit lands clean. `push` tests first (lint/typecheck/unit tests plus a UI smoke check via Playwright MCP for routes affected by the diff, skipped automatically on backend-only PRs), then commits and opens the draft PR. `self-review` runs the review agents plus a security pass. `mark-ready` is the explicit draft → ready gate; `await-review` polls for your configured Code Review Agent (Copilot, CodeRabbit, Greptile, …) before `respond` addresses its feedback.

At each step transition, one-shot prints a progress line so you always know where you are:

```
[5/9] (✓) plan → (✓) implement → (✓) simplify → (✓) push → (▶) self-review → ( ) mark-ready → ( ) await-review → ( ) respond → ( ) ship

Now running: self-review
```

Each step maps to a skill you can run on its own when you don't want the whole pipeline:

| # | Step | Skill to run standalone |
|---|------|-------------------------|
| 1 | `plan` | `hero-skills:think-it-through` (only when nothing resolves from `.plans/` or the tracker) |
| 2 | `implement` | inline (executes the resolved work-item) |
| 3 | `simplify` | `/simplify` (external skill) |
| 4 | `push` | `hero-skills:push-pr` (tests — verification + UI smoke — then commits + pushes a draft PR) |
| 5 | `self-review` | `hero-skills:review-pr --no-mark-ready` |
| 6 | `mark-ready` | `hero-skills:review-pr`'s own Step 9 gate, or `gh pr ready` |
| 7 | `await-review` | inline poll (no separate skill) |
| 8 | `respond` | `hero-skills:respond-to-comments` |
| 9 | `ship` | `hero-skills:ship-pr` |

Re-running `hero-skills:one-shot` mid-flow is safe: it inspects git + the open PR for that branch and resumes from the inferred step deterministically — no confirmation prompt. With no arguments, that resume behavior is the whole point. On the default branch with work to preserve, one-shot auto-branches off (no prompt) before resuming. It exits cleanly with a hand-off hint only when there's nothing left to do (e.g., after the PR has merged) or when state can't be inferred safely (e.g., a failed `git fetch`).

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
| `hero-skills:push-pr` | Test (lint, typecheck, unit tests + smoke incl. UI via Playwright MCP), commit + push + draft PR + CI status — or `test` for a test-only run, or a target branch to merge into |

### Code Review

| Command | What it does |
|---------|-------------|
| `hero-skills:review-pr` | Review a PR with the review agents plus a security pass: your draft → applies fixes, asks before marking ready. Others' PR → inline comments only. |
| `hero-skills:respond-to-comments` | Fix PR review comments, resolve threads, optionally loop with external review agent |
| `hero-skills:ship-pr` | Trigger gated `@auto-approve`, wait for the verdict, merge if it passes, reset to the default branch, and run a post-merge deploy-health check |

### Pipelines (orchestrators)

| Command | What it does |
|---------|-------------|
| `hero-skills:one-shot` | Drives a small task end-to-end: plan → implement → simplify → push (tests included) → self-review → mark-ready → await-review → respond → ship. Detects a resume point on re-invocation; with no arguments, drives the current goal to merged + reset branch. Explicit user gates at each destructive step. |
| `hero-skills:create-project` | Scaffolds a new project, then chains into setup-dev → init-hero → first-commit. |

### Operations

| Command | What it does |
|---------|-------------|
| `hero-skills:harden` | Audit read-only for hardening — dependency CVEs (Dependabot), container CVEs (Docker Scout, Trivy), code robustness — and emit execution-ready plans as `.plans/` items |
| `hero-skills:think-it-through` | Brainstorm + grill an idea one question at a time into shared understanding and dependency-aware work-items |
| `hero-skills:my-humanizer` | Strip AI-writing patterns from prose (Wikipedia's "Signs of AI writing"). Runs inline inside the pipeline on everything a person reads: code comments, docs, commit bodies, and the PR body in `push-pr`, review comments in `review-pr`, thread replies in `respond-to-comments`; standalone on any text |
| `hero-skills:architecture` | Create + converge a single root `DESIGN.md` — tech stack, boundaries, dependency rules, invariants, users, flows, interaction standards, append-only decisions; never restates what the code says. `sync` converges, `review` reports drift read-only |
| `hero-skills:fleet` | Create + converge `FLEET.md` — the local, unversioned map of the repos checked out beside each other (group, port). `sync` scans the folder and proposes rows, `review` reports drift read-only. Every repo skill run from the fleet root fans out to the repos you pick (see `docs/FLEET-MD.md`) |
| `hero-skills:wayfare` | Feature roadmap from source to the claude.ai/design project (HERO.md-configured, read via DesignSync or a manual snapshot drop), four verbs: `sync` reads both ends, converges the `.plans/` roadmap, then plans the set as its postflight (think-it-through per feature, your ready-mark); `do N` builds one planned feature via one-shot; `goal` runs a multi-feature goal under `/goal`, building up to `concurrency` dep-free features at once, each in its own git worktree; `deps [N]` takes one Dependabot PR — review, local tests, `@auto-approve`, merge, deployment check — without ever committing on the bot's branch. Features are SLC vertical slices (user stories, never layers) carrying subtasks, a definition of done, comments, design feedback back to the design team, and staleness flags |
| `hero-skills:handoff` | Distill the current conversation into one self-contained work-item for a downstream agent (optionally filed to the tracker, or to **another repo** with `--repo OWNER/NAME`) |

### Utilities

| Command | What it does |
|---------|-------------|
| `hero-skills:abandon` | Abandon or pause an unmerged branch — stash uncommitted work, switch to default, clear context |
| `hero-skills:audit-plugin` | Audit the hero-skills plugin itself for quality and consistency |

## Updating vendored assets in a downstream repo

`scripts/install-design-system.sh` and `scripts/install-auto-approve.sh` copy
files *into* consuming repos (`.claude/rules/`, `.claude/hooks/`). Those copies
are vendored, not authored: fix bugs here, then re-vendor.

To refresh a consuming repo after a fix lands upstream:

```bash
"$PLUGIN_ROOT/scripts/install-design-system.sh" /path/to/repo
```

The installer **never overwrites a file that differs**. On drift it writes
`<file>.new` beside the original and exits 2, leaving you to reconcile:

```bash
diff .claude/hooks/check-design-tokens.sh{,.new}
```

**Read that diff in both directions before taking `.new`.** Drift is not always
upstream-is-newer. A consuming repo can carry a genuine improvement that was
never back-ported, and blindly accepting `.new` silently reverts it — for a
*check*, that reads as "still installed" while no longer catching what it used
to. Back-port the downstream improvement here first, then re-vendor, so both
sides converge on one version instead of alternating.

Exit 2 means "you have a decision to make", not "it failed".

**Auto-approve is the exception: always take `.new`, never merge it.** The two
files are not two versions of one thing. The existing file is the old inline
copy of the review *logic*; `.new` is a ~40-line caller into the shared
workflow. Reconciling them the way you would a design-system hook — keeping the
local improvement — is exactly how the fleet ended up with a private copy per
repo, several of them missing security fixes made here. A job holding both
`uses:` and `steps:` is also an invalid workflow file, and because the trigger
is `issue_comment` nothing surfaces that until someone tries to ship.

## `main` is the distribution mechanism

Consumers call `ai-hero/hero-skills/.github/workflows/auto-approve.yaml@main`, so
**merging a change to `auto-approve.yaml` publishes it to every consuming repo
the moment it lands.** There is no release step, no tag to move, and no per-repo
PR to open.

Three consequences worth internalising:

- That file has a blast radius no other file here has. Review it accordingly.
- **`main`'s branch protection is the only gate.** Not a formality: approval
  required, stale approvals dismissed on push, and last-push approval required
  — without that last pair, an approval collected on a benign diff survives a
  force-push and ships fleet-wide seconds later.
- Roll back by reverting on `main`. That is the whole procedure.

This replaced a moving `v1` tag. The tag needed a release workflow to move it,
an App to be allowed to move it past a ruleset, and a carve-out in the fleet's
pin rule — and its one distinctive feature, a manual lever to point the tag at
an arbitrary commit, turned out to be a way around the very branch protection
the design depended on. A branch ref cannot be aimed anywhere; there is nothing
to aim.

`assets/auto-approve/caller.yaml` is what gets installed into consumers. It is
not the logic and should stay small; `scripts/install-auto-approve.test.sh`
asserts it stays a caller and that its secrets and permissions still line up
with what `auto-approve.yaml` declares.

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
