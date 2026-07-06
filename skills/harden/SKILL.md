---
name: harden
# prettier-ignore
description: Audit the codebase for hardening opportunities — dependency CVEs, container CVEs, code-level robustness — read-only, and emit execution-ready plans as plan-work items. Never edits source.
argument-hint: "[deps|docker|code|all]"
disable-model-invocation: true
---

# Harden — Audit Read-Only, Emit Execution-Ready Hardening Plans

Deeply audit the codebase for security and robustness hardening opportunities, then write plans precise enough that a downstream executor — a cheaper model, a fresh session, or `hero-skills:one-shot` — can apply, test, and verify them with **zero context from this session**.

Inspired by [shadcn/improve](https://github.com/shadcn/improve): the expensive, high-ceiling model does the part where intelligence compounds (understanding, judging, specifying); cheaper models do the execution. **The plan is the product.** This skill absorbed the former `hero-skills:scan-vulns` — its Dependabot and Docker Scout scanning mechanics live in Parts A and B, but the *apply-and-commit* half now lands in the plan's execution recipe instead of this session's working tree.

## The Hard Rule

**This skill never edits source code, dependency files, Dockerfiles, or workflows. Read-only, always.** Its only writes are plan items under the git-ignored `plan-work/` store. If you catch yourself about to run `npm install`, edit a Dockerfile, or `git commit` — stop; that command belongs *inside* a plan item's execution recipe.

## Arguments

- `$ARGUMENTS` - What to audit (default: `all`)
  - `deps` - Dependency CVEs only (Dependabot alerts + open Dependabot PRs)
  - `docker` - Container image CVEs only (Docker Scout)
  - `code` - Code-level hardening audit only
  - `all` - Everything

## Prerequisites

- `gh` CLI installed and authenticated (for Dependabot alerts)
- `docker` CLI installed (for Docker Scout; the `docker` part degrades to skipped without it)

## Instructions

### Step 0: Load Hero Configuration and the plan-work Store

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Same store think-it-through emits into — one plate per repo, git-ignored
# via .git/info/exclude so no tracked file is ever dirtied.
mkdir -p "$ROOT/plan-work"
EXCLUDE_FILE=$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)
case "$EXCLUDE_FILE" in
  /*) ;;
  *)  EXCLUDE_FILE="$ROOT/$EXCLUDE_FILE" ;;
esac
mkdir -p "$(dirname "$EXCLUDE_FILE")"
grep -qxF 'plan-work/' "$EXCLUDE_FILE" 2>/dev/null \
  || printf '\nplan-work/\n' >> "$EXCLUDE_FILE"
ls "$ROOT/plan-work"/*.md 2>/dev/null || echo "plan-work/ is empty"
```

Read `HERO.md` for **Deployment** (registry for Docker Scout), **Projects** (languages/frameworks → which dependency files and which code-audit angles apply), and **Code Quality** (existing tooling so plans don't re-propose what a linter already enforces). Read existing plan-work items so new plans reference or supersede rather than duplicate.

### Step 1: Detect Repository Context

```bash
gh repo view --json nameWithOwner,url
cat .github/dependabot.yml 2>/dev/null || echo "NO_DEPENDABOT_CONFIG"
find . -name "Dockerfile*" -type f 2>/dev/null | head -10
```

---

## Part A: Dependency CVE Audit (`deps` / `all`)

### A1: Get Dependabot Alerts

```bash
gh api repos/{owner}/{repo}/dependabot/alerts \
  --jq '.[] | select(.state=="open") | {
    number, package: .dependency.package.name,
    severity: .security_advisory.severity,
    summary: .security_advisory.summary
  }'
```

Prioritize by severity: **critical > high > medium > low**.

### A2: List Open Dependabot PRs

```bash
gh pr list --author "app/dependabot" --state open --json number,title,headRefName,url
```

For each PR, view the diff and extract: package name, version change, file affected. An open Dependabot PR is *evidence for the plan* — note whether the plan item should say "merge Dependabot PR #N" or "apply the update manually" (e.g., when the PR is stale or conflicts).

### A3: Judge Each Alert

For each open alert, read enough of the codebase to judge (this is the expensive-model work):

- Is the vulnerable code path actually reachable from this repo's usage?
- Is the fix a patch/minor bump (low risk) or a major bump (breaking-change risk — flag it)?
- What is the correct update command for this ecosystem (`npm install PACKAGE@VERSION`, `uv lock && uv sync` after a `pyproject.toml` edit, a version pin bump in `.github/workflows/*.yml`)?
- What test/verification proves the update didn't break anything?

---

## Part B: Container CVE Audit (`docker` / `all`)

```bash
find . -name "Dockerfile*" -type f
docker scout cves IMAGE_NAME:TAG --only-fixed
docker scout recommendations IMAGE_NAME:TAG
```

Read-only: record the recommended base-image bumps and system-package updates. The rebuild-and-rescan loop (`docker build …` then `docker scout cves …` again) goes in the plan item's verification section — the executor runs it, not this session.

If `docker` is unavailable or the daemon is down, report `Docker Scout: skipped (docker unavailable)` and continue — do not fail the whole audit.

---

## Part C: Code-Level Hardening Audit (`code` / `all`)

Sweep the codebase for robustness gaps that scanning tools can't see. Audit angles — apply the ones the stack makes relevant:

- **Boundary validation** — unvalidated input at API routes, CLI args, file/env parsing
- **Silent failures** — swallowed exceptions, bare `except`/empty `catch`, error paths that return defaults
- **Secrets hygiene** — credentials in code/config/logs, tokens in URLs, missing redaction
- **AuthN/AuthZ seams** — endpoints missing checks that sibling endpoints have
- **Unsafe defaults** — debug modes, permissive CORS, `verify=False`, world-readable artifacts
- **Missing timeouts/retries** — outbound calls that can hang forever, retry loops without backoff or caps
- **Injection surfaces** — string-built SQL/shell/HTML where a parameterized/escaped form exists

High signal only: every finding needs a concrete failure or exploit scenario and a specific fix. Skip theoretical issues, DoS/rate-limiting noise, and anything the repo's linters already enforce. For a large codebase, fan the angles out as parallel read-only agents and aggregate.

---

## Step 2: Prioritize

Rank everything found by `severity × blast radius ÷ effort`. Cluster related findings into plan-sized units (one dependency-update batch per ecosystem; one code-hardening item per subsystem or mechanism — not per line). Cap the emitted plans at the top **10** items per run; note what was cut so nothing is silently dropped.

## Step 3: Emit Plan Items

Write each unit as a work-item in `plan-work/` using think-it-through's format (id numbering continues from the highest existing id; filename `NNN-slug.md`; `depends_on` when one plan must land first), with two extra sections the executor needs:

```markdown
---
id: 12
title: Update lodash + minimist for critical CVEs
status: ready
depends_on: []
one_way_door: false
success: "gh api dependabot/alerts shows 0 open critical/high; test suite green"
---

## Context

Which alerts/CVEs/findings this addresses and why they matter here (reachability, blast radius).

## Approach

The chosen fix and why (e.g., merge Dependabot PR #41 rather than manual bump — it is current and CI-green).

## Execution recipe

Exact commands and edits, in order, assuming zero context:
1. `npm install lodash@4.17.21`
2. ...

## Verification

How the executor proves it worked (tests to run, rescan commands, endpoints to probe).

## Failure modes

What can break, and the rollback (e.g., major-bump risk: pin back and mark blocked).
```

A plan an executor cannot follow without asking questions is not done — rewrite it, don't hand it off vague.

## Step 4: Summary

```
Harden Audit Summary
====================
Dependabot:   5 alerts (2 critical, 2 high, 1 medium) → 2 plan items
Docker Scout: 3 images scanned, 10 fixable CVEs        → 1 plan item
Code audit:   4 findings (2 important)                 → 2 plan items

Plans emitted: plan-work/012-*.md … 016-*.md (5 items, 0 cut)
Source files modified: NONE (read-only by contract)

Next steps:
  hero-skills:one-shot         # execute a READY plan item ticket-to-merge
  hero-skills:think-it-through # re-grill a plan that needs a human decision
```

## Safety Notes

- Never edit source, dependency files, Dockerfiles, or workflows — the plan is the product.
- Flag major version updates as breaking-change risks in the plan; default the recipe to the non-breaking path.
- Dependabot PRs auto-close when their fixes reach the default branch — prefer "merge PR #N" recipes when the PR is current.
- `plan-work/` is private and git-ignored; never commit or push it.
