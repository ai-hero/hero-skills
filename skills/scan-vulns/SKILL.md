---
name: scan-vulns
# prettier-ignore
description: Scan and fix security vulnerabilities. Processes Dependabot alerts and PRs, applies dependency updates, scans Docker images with Scout and Trivy, and commits security fixes.
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

Every dependency bump gets tested **together**, in one PR, in one e2e run — two individually-passing bumps can still break once combined (e.g. a version bump plus a config change that only conflicts together), and that's exactly the interaction bug a single combined run is meant to catch. So collect every fix onto one branch before pushing anything.

Branch **fresh off the default branch on every scan-vulns run** rather than maintaining a long-lived security-fix branch across runs. This is what avoids stale security PRs piling up across successive runs, each needing its own catch-up against an ever-moving default branch: a fresh branch off today's default branch never has a stale base to reconcile against.

```bash
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
git checkout "$DEFAULT_BRANCH" && git pull

# Supersede any still-open PR(s) from a prior scan-vulns run — close them
# directly here, before opening the new one, rather than deferring to a
# later skill that has no mechanism to carry this obligation forward.
# Reuses A2's $OPEN_PRS payload rather than a second `gh pr list` call.
STALE_PR_NUMBERS=$(echo "$OPEN_PRS" | jq -r '.[] | select(.headRefName | startswith("fix/security-updates-")) | .number')
for STALE_PR in $STALE_PR_NUMBERS; do
  gh pr close "$STALE_PR" --comment "Superseded by a fresh security-fix run."
done

# Guard against a same-day rerun colliding on the branch name.
BRANCH_NAME="fix/security-updates-$(date +%Y%m%d)"
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" || git ls-remote --exit-code --heads origin "$BRANCH_NAME" >/dev/null 2>&1; then
  BRANCH_NAME="fix/security-updates-$(date +%Y%m%d)-$(date +%H%M%S)"
fi
git checkout -b "$BRANCH_NAME"
```

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

Scan the base of the **final/runtime stage** — builder stages never ship.

```bash
find . -name "Dockerfile*" -type f
docker scout cves IMAGE_NAME:TAG --only-fixed
```

**Scan with a second scanner too.** Scout and Trivy have different advisory
databases and each misses what the other catches. Report the union, not
whichever ran first.

```bash
trivy image --severity HIGH,CRITICAL --scanners vuln IMAGE_NAME:TAG
```

Observed 2026-07-14 on one image: Trivy reported only the Debian `libssl3` CVEs
and had no advisory for the Node runtime CVEs; Scout caught the Node CVEs plus
`glibc`. Trivy alone would have concluded OpenSSL was the whole story.

### B2: Get Recommendations and Apply Fixes

```bash
docker scout recommendations IMAGE_NAME:TAG
```

Update base images and system packages in Dockerfiles as recommended.

**`scout recommendations` is unreliable for non-Docker-Hub bases.** For
`gcr.io/distroless/*` (and other registries outside Hub's tag graph) it
auto-detects the base as `:latest` and reports a false all-clear:

```text
Base image is :latest
Refresh base image  -> This image version is up to date.
Change base image   -> There are no tag recommendations at this time.
```

It printed exactly that for an image carrying 14 HIGH (1 CRITICAL). **Never
treat "no tag recommendations" as "no fix exists"** — for these bases the tool
is blind, not reassuring. Enumerate the upgrade axes by hand.

### B2a: Enumerate every upgrade axis before deferring a CVE

Before writing "upstream has not published a fix" or "clears on the next base
bump", check **all** of these — a fix on any one axis resolves it today:

1. **Tag refresh** — repull; compare against upstream `IMAGE:TAG` directly.
2. **Runtime major** — e.g. `nodejs22` -> `nodejs24`.
3. **OS generation** — e.g. `-debian12` -> `-debian13`. **Most often missed.**
   A newer OS generation frequently ships both a newer runtime and patched
   system libs, and Scout never suggests it for distroless.
4. **Variant** — `:nonroot` / `:debug` / `-static`.

Verify by scanning the candidate directly rather than reasoning about it:

```bash
# Substitute the actual base; compare candidates side by side.
for base in nodejs24-debian12 nodejs24-debian13; do
  echo "== $base"
  docker scout cves --only-severity critical,high \
    "gcr.io/distroless/$base:nonroot" 2>&1 \
    | grep -E "vulnerabilities found|No vulnerable"
done
```

**Real miss this guards against:** a prior run bumped `nodejs22-debian12` ->
`nodejs24-debian12` and deferred 2 HIGH, reasoning that Node 24.14.1 was "not
yet published to distroless". It *was* published — on `nodejs24-debian13` (Node
24.18.0), which also cleared the `libssl3` + `glibc` CVEs. Only axis 3 was
skipped, and the finding was written off as unfixable.

A base-OS generation bump is low-risk when the payload doesn't link the base
libs — a `CGO_ENABLED=0` Go binary and a static tini don't. Confirm each copied
binary still executes after the bump (see B3).

### B3: Rebuild, Rescan, Smoke-Test, and Commit

A base bump can scan clean and still not boot. Rescan **and** prove it runs.

```bash
docker build -t IMAGE_NAME:TAG -f DOCKERFILE_PATH .

# Rescan with BOTH scanners (see B1).
docker scout cves IMAGE_NAME:TAG
trivy image --severity HIGH,CRITICAL --scanners vuln IMAGE_NAME:TAG

# Every binary COPY'd in from another stage — a base-OS bump changes the
# runtime linker/libc, and a static binary assumption may not hold.
docker run --rm --entrypoint BINARY_PATH IMAGE_NAME:TAG --version

# Then drive the real thing: bring up the project's smoke stack, wait for
# the healthcheck, and hit a route that exercises each process.
docker compose -f docker-compose.prod.yml up --build -d
docker inspect --format='{{.State.Health.Status}}' CONTAINER   # want: healthy
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:PORT/health
docker compose -f docker-compose.prod.yml down -v
```

Report what was actually verified. Do not claim an image works on a scan alone.

```bash
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

Docker images: 3 scanned (Scout + Trivy)
  Fixed: 3 critical, 7 high CVEs
  Remaining: 2 medium
    CVE-XXXX-XXXXX: axes checked — tag refresh (same), runtime major (same),
                     OS generation debian13 (same), variant (n/a) -> no fix upstream

Automated scanning: NONE (no dependabot config, no CI scan)
  -> clean as of now; pinned tags rot unwatched. Offer a scheduled CI gate.

Original Dependabot PRs covered: #123, #124, #126, #128
  These are NOT closed by this skill. Expect GitHub to auto-close each one
  once this consolidated fix reaches the default branch and Dependabot next
  scans it (timing depends on this repo's dependabot.yml schedule interval
  — could be immediate or up to that interval's length). If one is still
  open well past that, comment `@dependabot recreate` on it to trigger a
  recheck.

Next step: hero-skills:push-pr — commit and push the fixes, opens a draft PR (offer to auto-run: ask "Run it now? [y/N]", invoke via Skill tool on yes)
```

Don't also print `hero-skills:ship-pr`; `push-pr`'s own next-steps chain (review-pr → ship-pr) already leads there once this PR exists.

## Safety Notes

- Run tests after applying dependency updates
- Skip major version updates by default (may have breaking changes)
- Always rescan after applying Docker fixes — with **both** Scout and Trivy
- Never close the original Dependabot PRs directly — GitHub closes each one automatically on its next scan of the default branch after the fix lands (timing follows this repo's `dependabot.yml` schedule interval, not a fixed delay; nudge with `@dependabot recreate` if one is still open well past that). Report this expectation to the user rather than acting on their PRs.
- Branch fresh off the default branch on every run (A3) — never accumulate fixes on a persistent branch across runs. The one exception is this skill's *own* prior-run PR (branch prefix `fix/security-updates-`), which is fine to close/supersede since it's this skill's own artifact, not a Dependabot PR

### Before writing "no fix available"

That phrase is a claim about upstream, and it has been wrong. Earn it:

- Walk **every** axis in B2a (tag / runtime major / **OS generation** / variant)
  and scan the candidate — don't infer availability from a version number.
- "`scout recommendations` had nothing" is **not** evidence, especially for
  `gcr.io/distroless/*`, where it is blind and reports a false all-clear.
- If a CVE is genuinely deferred, record **which axes were checked** and what
  each returned, so the next run can refute it instead of inheriting it.

### This skill is manual — pinned base tags rot between runs

`disable-model-invocation: true`, so it runs only when a user invokes it, and it
is typically wired into neither CI nor pre-commit. A pinned base tag accrues new
CVEs with nothing watching: one image went from "0 CRITICAL, 2 HIGH" at commit
time to 1 CRITICAL / 14 HIGH shortly after, with no code change.

So a clean scan means "clean **as of now**", never "clean going forward". When a
repo has no automated scanning, say so in the summary and offer a scheduled CI
gate (`trivy image --exit-code 1 --severity HIGH,CRITICAL`) on a `schedule:`
trigger — a push-only gate cannot catch rot, because rot happens without pushes.
