---
name: scan-vulns
# prettier-ignore
description: Scan and fix security vulnerabilities. Processes Dependabot alerts and PRs, applies dependency updates, scans Docker images with Scout, and commits security fixes.
argument-hint: [dependabot|docker|all]
disable-model-invocation: true
---

# Scan — Security Vulnerability Scanner and Fixer

Comprehensive security scanning and remediation for dependencies and container images.

## Arguments

- `$ARGUMENTS` - What to scan (default: `all`)
  - `dependabot` - Only process Dependabot alerts and PRs
  - `docker` - Only scan Docker images with Scout
  - `all` - Both Dependabot and Docker Scout

## Prerequisites

- `gh` CLI installed and authenticated
- `docker` CLI installed (for Docker Scout)
- Write access to the repository

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Deployment** → registry for Docker Scout image scanning
- **Projects** → language/framework to know which dependency files to check
- **Code Quality** → linters/tools context

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with auto-detection.

### Step 1: Detect Repository Context

```bash
gh repo view --json nameWithOwner,url
cat .github/dependabot.yml 2>/dev/null || echo "NO_DEPENDABOT_CONFIG"
find . -name "Dockerfile*" -type f 2>/dev/null | head -10
```

---

## Part A: Dependabot Vulnerability Fixes

### A1: Get Dependabot Alerts

```bash
gh api repos/{owner}/{repo}/dependabot/alerts \
  --jq '.[] | select(.state=="open") | {
    number, package: .dependency.package.name,
    severity: .security_advisory.severity,
    summary: .security_advisory.summary
  }'
```

Prioritize by severity: **critical > high > medium > low**

### A2: List and Process Open Dependabot PRs

Fetch all open PRs once — A3 reuses this same payload to check for a stale prior-run PR, instead of a second `gh pr list` round-trip:

```bash
OPEN_PRS=$(gh pr list --state open --json number,title,headRefName,url,author)
echo "$OPEN_PRS" | jq '.[] | select(.author.login == "app/dependabot")'
```

For each Dependabot PR, view the diff and extract: package name, version change, file affected.

### A3: Branch Fresh and Collect All Fixes

Every dependency bump gets tested **together**, in one PR, in one e2e run — a major-version bump can pass CI in isolation and still break once combined with another simultaneous update, and that's exactly the interaction bug a single combined run is meant to catch. So collect every fix onto one branch before pushing anything.

Branch **fresh off the default branch on every scan-vulns run** rather than maintaining a long-lived security-fix branch across runs. This is what avoids the classic "N branches all need rebasing against each other" trap: a fresh branch off today's default branch never has a stale base to reconcile against, so there is nothing to rebase.

```bash
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
git checkout "$DEFAULT_BRANCH" && git pull

# Supersede any still-open PR from a prior scan-vulns run — don't let stale
# security PRs pile up alongside the fresh one this run is about to open.
# Reuses A2's $OPEN_PRS payload rather than a second `gh pr list` call.
echo "$OPEN_PRS" | jq '.[] | select(.headRefName | startswith("fix/security-updates-"))'

BRANCH_NAME="fix/security-updates-$(date +%Y%m%d)"
git checkout -b "$BRANCH_NAME"
```

If a stale PR was found above, close it once the new PR exists in A4/push-pr: `gh pr close STALE_PR_NUMBER --comment "Superseded by a fresh security-fix run — see #NEW_PR_NUMBER."`

For each open Dependabot alert/PR (severity order, from A1/A2), edit the target file **directly** to the fixed version — do not shell out to `npm install PACKAGE@VERSION` or `uv add` per package. Each of those calls regenerates the lockfile on its own, which stacks up N separate (and sometimes conflicting) lockfile diffs for what should be one coherent update. Collect every version-bump edit first:

**npm/pnpm** — bump the version in `package.json` for each affected package.

**Python (uv)** — bump the version in `pyproject.toml` for each affected package.

**GitHub Actions** — update `.github/workflows/*.yml` version pins.

### A4: One Lockfile Regen, One Verify, One Commit

Once every version bump from A3 is edited in, regenerate the lockfile **once**, covering all of them:

```bash
npm install   # or: uv lock && uv sync
```

Run the project's test suite once against the combined change. If a specific package bump breaks tests, revert just that edit, note it as skipped, and keep the rest — don't let one bad update block the whole batch.

```bash
git add package*.json pnpm-lock.yaml pyproject.toml uv.lock .github/workflows/*.yml
git commit -m "$(cat <<'EOF'
fix(deps): update dependencies for security vulnerabilities

Updates applied:
- PACKAGE: OLD_VERSION -> NEW_VERSION
- PACKAGE: OLD_VERSION -> NEW_VERSION

Addresses:
- CVE-XXXX-XXXXX: BRIEF_DESCRIPTION
- CVE-XXXX-XXXXX: BRIEF_DESCRIPTION

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Part B: Docker Scout CVE Fixes

### B1: Identify and Scan Images

```bash
find . -name "Dockerfile*" -type f
docker scout cves IMAGE_NAME:TAG --only-fixed
```

### B2: Get Recommendations and Apply Fixes

```bash
docker scout recommendations IMAGE_NAME:TAG
```

Update base images and system packages in Dockerfiles as recommended.

### B3: Rebuild, Rescan, and Commit

```bash
docker build -t IMAGE_NAME:TAG -f DOCKERFILE_PATH .
docker scout cves IMAGE_NAME:TAG  # Verify fixes

git add Dockerfile*
git commit -m "$(cat <<'EOF'
fix(docker): update container base images for security

Scout scan results:
- Before: X critical, Y high
- After:  A critical, B high

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Summary Format

```
Scan Summary
===================
Dependabot: 5 alerts (2 critical, 2 high, 1 medium)
  Applied: 4 updates
  Skipped: 1 (breaking changes)

Docker Scout: 3 images scanned
  Fixed: 3 critical, 7 high CVEs
  Remaining: 2 medium (no fix available)

Original Dependabot PRs covered: #123, #124, #126, #128
  These are NOT closed by this skill. Expect GitHub to auto-close each one
  once this consolidated fix reaches the default branch — GitHub does this
  automatically once it detects the same version bump on the default branch.
  If one doesn't close within a day or so, comment `@dependabot recreate`
  on it to trigger a recheck.

Next step: hero-skills:push-pr — commit and push the fixes, opens a draft PR (offer to auto-run: ask "Run it now? [y/N]", invoke via Skill tool on yes)
```

Don't also print `hero-skills:ship-pr`; `push-pr`'s own next-steps chain (review-pr → ship-pr) already leads there once this PR exists.

## Safety Notes

- Run tests after applying dependency updates
- Skip major version updates by default (may have breaking changes)
- Always rescan after applying Docker fixes
- Never close the original Dependabot PRs directly — GitHub closes each one automatically once it detects the same fix on the default branch (this can occasionally lag; nudge it with `@dependabot recreate` if a PR is still open after a day). Report this expectation to the user rather than acting on their PRs.
- Branch fresh off the default branch on every run (A3) — never accumulate fixes on a persistent branch across runs. The one exception is this skill's *own* prior-run PR (branch prefix `fix/security-updates-`), which is fine to close/supersede since it's this skill's own artifact, not a Dependabot PR
