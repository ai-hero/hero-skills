---
name: hero-secure
# prettier-ignore
description: Scan and fix security vulnerabilities. Processes Dependabot alerts and PRs, applies dependency updates, scans Docker images with Scout, and commits security fixes. Works with any repository.
argument-hint: [dependabot|docker|all]
disable-model-invocation: true
---

# Hero Secure - Security Vulnerability Scanner and Fixer

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

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

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

```bash
gh pr list --author "app/dependabot" --state open --json number,title,headRefName,url
```

For each PR, view the diff and extract: package name, version change, file affected.

### A3: Apply Updates to Current Branch

**npm/pnpm:**

```bash
npm install <package>@<version>
```

**Python (uv):**

```bash
# Update in pyproject.toml, then
uv lock && uv sync
```

**GitHub Actions:**

Manually update `.github/workflows/*.yml` version pins.

### A4: Verify and Commit

Run tests to ensure updates don't break anything. Skip updates that cause failures.

```bash
git add package*.json pnpm-lock.yaml pyproject.toml uv.lock .github/workflows/*.yml
git commit -m "$(cat <<'EOF'
fix(deps): update dependencies for security vulnerabilities

Updates applied:
- <package1>: <old> -> <new>

Addresses:
- CVE-XXXX-XXXXX: <brief description>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Part B: Docker Scout CVE Fixes

### B1: Identify and Scan Images

```bash
find . -name "Dockerfile*" -type f
docker scout cves <image-name>:<tag> --only-fixed
```

### B2: Get Recommendations and Apply Fixes

```bash
docker scout recommendations <image-name>:<tag>
```

Update base images and system packages in Dockerfiles as recommended.

### B3: Rebuild, Rescan, and Commit

```bash
docker build -t <image-name>:<tag> -f <dockerfile-path> .
docker scout cves <image-name>:<tag>  # Verify fixes

git add Dockerfile*
git commit -m "$(cat <<'EOF'
fix(docker): update container base images for security

Scout scan results:
- Before: X critical, Y high
- After:  A critical, B high

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Summary Format

```
Hero Secure Summary
===================
Dependabot: 5 alerts (2 critical, 2 high, 1 medium)
  Applied: 4 updates
  Skipped: 1 (breaking changes)

Docker Scout: 3 images scanned
  Fixed: 3 critical, 7 high CVEs
  Remaining: 2 medium (no fix available)
```

## Safety Notes

- Run tests after applying dependency updates
- Skip major version updates by default (may have breaking changes)
- Always rescan after applying Docker fixes
- Dependabot PRs auto-close when fixes reach main
