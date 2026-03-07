---
name: hero-cicd
# prettier-ignore
description: Check CI/CD pipeline status. Inspects GitHub Actions workflow runs, build logs, image publish status, and deployment triggers. Use after pushing to verify builds pass, or to debug failing pipelines.
argument-hint: [branch|pr-number|run-id]
disable-model-invocation: true
---

# Hero CICD - CI/CD Pipeline Status Check

Check the status of CI/CD pipelines for the current repository. Inspects workflow runs, build results, and image publish status.

## Arguments

- `$ARGUMENTS` - Optional scope:
  - (none) - Check latest runs for current branch
  - `<branch>` - Check runs for a specific branch
  - `#<pr-number>` - Check runs for a specific PR
  - `<run-id>` - Check a specific workflow run

## Prerequisites

- CI CLI installed and authenticated (e.g., `gh` for GitHub Actions, `glab` for GitLab)
- Repository has CI/CD workflows configured

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **CI/CD** → platform (github-actions, gitlab-ci, jenkins, circleci) and workflow names
- **Deployment** → registry and platform for image/deploy status checks

If `HERO.md` is missing, suggest `/hero-init` but proceed assuming GitHub Actions.

## Instructions

### Step 1: Identify Context

```bash
# Current repo
gh repo view --json nameWithOwner -q .nameWithOwner

# Current branch
git branch --show-current

# List available workflows
gh workflow list
```

### Step 2: Check Workflow Runs

**Latest runs for current branch (default):**

```bash
BRANCH=$(git branch --show-current)
gh run list --branch "$BRANCH" --limit 5 --json databaseId,name,status,conclusion,headBranch,createdAt,url
```

**For a specific PR:**

```bash
gh pr checks <pr-number>
```

**For a specific run:**

```bash
gh run view <run-id>
```

### Step 3: Analyze Results

For each run, report:

| Field | Source |
|-------|--------|
| Workflow name | Run metadata |
| Status | queued / in_progress / completed |
| Conclusion | success / failure / cancelled / skipped |
| Duration | createdAt → completedAt |
| Branch | headBranch |

**If any runs failed:**

```bash
# Get failed job details
gh run view <run-id> --json jobs --jq '.jobs[] | select(.conclusion=="failure") | {name, conclusion, steps: [.steps[] | select(.conclusion=="failure") | .name]}'
```

**Get logs for failed steps:**

```bash
gh run view <run-id> --log-failed
```

### Step 4: Check Image Build Status (if applicable)

```bash
# Check for container registry workflows
gh run list --workflow "build" --limit 3 --json databaseId,name,status,conclusion,headBranch

# Check if images were published (GitHub Container Registry)
gh api repos/{owner}/{repo}/packages?package_type=container --jq '.[].name' 2>/dev/null

# Check latest image tags
gh api repos/{owner}/{repo}/packages/container/{package}/versions --jq '.[0] | {tags: .metadata.container.tags, created: .created_at}' 2>/dev/null
```

### Step 5: Check Deployment Status (if applicable)

```bash
# GitHub deployments
gh api repos/{owner}/{repo}/deployments --jq '.[:3] | .[] | {environment: .environment, ref: .ref, created: .created_at, status: .statuses_url}' 2>/dev/null

# Deployment statuses
gh api repos/{owner}/{repo}/deployments/latest/statuses --jq '.[0] | {state, description, created_at}' 2>/dev/null
```

### Step 6: Wait for In-Progress Runs (optional)

If runs are `in_progress`, offer to watch:

```bash
gh run watch <run-id>
```

Use `run_in_background: true` and report when it completes.

### Step 7: Summary

```
Hero CICD Summary
=================
Repo: owner/repo
Branch: feature/my-change

Workflow Runs (latest 5):
  1. Build & Test     SUCCESS   2m 15s   (run #1234)
  2. Lint             SUCCESS   45s      (run #1233)
  3. Docker Build     SUCCESS   3m 22s   (run #1232)
  4. Deploy Staging   SUCCESS   1m 05s   (run #1231)
  5. Build & Test     FAILURE   1m 48s   (run #1228)

Failed Run Details (#1228):
  Job: test-backend
  Step: Run pytest
  Error: AssertionError in test_auth.py:45

Images:
  ghcr.io/owner/repo:main - pushed 2h ago
  ghcr.io/owner/repo:sha-abc123 - pushed 2h ago

Overall: PASSING | FAILING | IN PROGRESS
```

**Status classification:**

| Status | Condition |
|--------|-----------|
| PASSING | All latest runs succeeded |
| FAILING | Any run failed |
| IN PROGRESS | Runs still executing |
| STALE | No runs in last 24h for this branch |

## Examples

```
/hero-cicd                  # Check current branch
/hero-cicd main             # Check main branch pipelines
/hero-cicd #42              # Check PR #42 checks
/hero-cicd 12345678         # Check specific run ID
```

## Notes

- Uses `gh` CLI exclusively - no direct GitHub API tokens needed
- Log output can be large - only fetches failed logs by default
- For ArgoCD deployment sync status, use `/hero-health --argocd`
- Read-only operation - does not trigger or modify any workflows
