---
name: hero-auto-approve
# prettier-ignore
description: Trigger the auto-approve GitHub Action on a PR, wait for the verdict, and offer to merge if it passes. Use after /hero-self-review and any external bot review when the PR is ready to ship.
argument-hint: [pr-number]
disable-model-invocation: true
---

# Hero Auto-Approve - Trigger and Act on the Auto-Approve Workflow

The last step before merge in the hero workflow:

```
/hero-self-review (mark ready) -> external review bot -> /hero-respond-to-pr -> /hero-auto-approve -> merge
```

This skill posts `@auto-approve` on the PR, waits for the workflow run to finish, reads the verdict, and — if the verdict is APPROVE — asks whether to merge. If the verdict is REQUEST_CHANGES, it shows what to fix and offers to re-trigger after fixes land.

The workflow lives at `.github/workflows/auto-approve.yml`. **GitHub only honors `issue_comment`-triggered workflows that already exist on the default branch**, so the workflow file must be merged to `main` (or your default branch) before this skill can do anything useful. This skill checks that first.

## Arguments

- `$ARGUMENTS` - PR number or URL (optional)
  - If omitted: auto-detect from current branch

## Prerequisites

- `gh` CLI installed and authenticated with `repo` scope
- `.github/workflows/auto-approve.yml` present on the default branch — run `/hero-init --update` to install it
- The repo has an `ANTHROPIC_API_KEY` secret configured (used by the workflow)

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** -> default branch (to confirm the workflow is on it)
- **CI/CD** -> workflow names (to identify the auto-approve run)

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Identify the PR

If `$ARGUMENTS` provided:

```bash
gh pr view "$ARGUMENTS" --json number,url,headRefName,baseRefName,state,isDraft,mergeable,mergeStateStatus
```

Otherwise auto-detect from the current branch:

```bash
BRANCH=$(git branch --show-current)
gh pr list --head "$BRANCH" --json number,url,headRefName,baseRefName,state,isDraft,mergeable,mergeStateStatus --jq '.[0]'
```

Record `PR_NUMBER`, `PR_URL`, `PR_BRANCH`, `BASE_BRANCH`, `IS_DRAFT`.

**Decide what to do based on PR state:**

| State | Action |
|-------|--------|
| No PR found | STOP. Tell the user to run `/hero-push` first. |
| Draft PR | STOP. Auto-approve only runs on ready PRs — tell the user to run `/hero-self-review` to mark ready. |
| Closed/merged | STOP. Report status. |
| Open, ready | Continue. |

### Step 2: Verify Auto-Approve Workflow Is on the Default Branch

GitHub only triggers `issue_comment` workflows that already exist on the default branch. If the file is only on the PR branch, the comment will be a no-op.

```bash
DEFAULT_BRANCH=$(gh api "/repos/{owner}/{repo}" --jq '.default_branch')
gh api "/repos/{owner}/{repo}/contents/.github/workflows/auto-approve.yml?ref=$DEFAULT_BRANCH" --jq '.path' 2>/dev/null \
  || echo "MISSING"
```

**If MISSING:** STOP and show:

```
auto-approve.yml is not on the default branch (DEFAULT_BRANCH).

GitHub only honors issue_comment workflows that already exist on the default branch.
Posting @auto-approve here will silently do nothing.

Fix:
  1. Run /hero-init --update to install .github/workflows/auto-approve.yml
  2. Open a PR for that workflow file alone, get it reviewed and merged to DEFAULT_BRANCH
  3. Re-run /hero-auto-approve
```

Do not proceed.

### Step 3: Confirm Prerequisite Reviews Are Present

Before posting the comment, sanity-check what the workflow's gates require so the user is not surprised by an immediate REQUEST_CHANGES.

```bash
# Self-review marker
gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" \
  --jq '[.[] | select(.body | test("Hero Self-Review"; "i"))] | length'

# Reviews from anyone other than the author (filter PENDING)
PR_AUTHOR=$(gh api "/repos/{owner}/{repo}/pulls/$PR_NUMBER" --jq '.user.login')
gh api "/repos/{owner}/{repo}/pulls/$PR_NUMBER/reviews" \
  --jq "[.[] | select(.user.login != \"$PR_AUTHOR\") | select(.state != \"PENDING\")] | length"

# Bot inline review comments (Copilot/CodeRabbit/Greptile/etc.)
gh api "/repos/{owner}/{repo}/pulls/$PR_NUMBER/comments" \
  --jq "[.[] | select(.user.login != \"$PR_AUTHOR\") | select((.user.type == \"Bot\") or (.user.login | test(\"(coderabbit|greptile|copilot|sonarcloud|codeball)\"; \"i\")))] | length"

# Unresolved review threads
OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login) \(.name)"')
OWNER=$(echo "$OWNER_REPO" | awk '{print $1}')
REPO=$(echo "$OWNER_REPO" | awk '{print $2}')
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes { isResolved isOutdated }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | select(.isOutdated == false)] | length'
```

Show the user a short summary:

```
Pre-flight check for PR #PR_NUMBER:
  Self-review:        N (need >= 1, or another reviewer)
  Other reviews:      N
  Bot inline reviews: N
  Unresolved threads: N (must be 0)
```

If both review counters are 0 OR unresolved threads > 0, warn the user the workflow will REQUEST_CHANGES and ask whether to proceed anyway. Default: do not proceed; suggest `/hero-self-review` or `/hero-respond-to-pr` first.

### Step 4: Post the @auto-approve Trigger Comment

Record the timestamp first so we can find the workflow run we just triggered without confusing it with prior runs.

```bash
TRIGGERED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gh pr comment $PR_NUMBER --body "@auto-approve"
```

Capture the head SHA — `Submit verdict` is keyed off the PR, but the workflow run is keyed off the comment event, not a SHA. We use the comment timestamp instead.

### Step 5: Wait for the Workflow Run

Poll for the most recent `Auto Approve` workflow run that started after `TRIGGERED_AT`:

```bash
# Find the run id
for i in 1 2 3 4 5 6 7 8 9 10; do
  RUN_JSON=$(gh api "/repos/{owner}/{repo}/actions/workflows" \
    --jq '.workflows[] | select(.name == "Auto Approve") | .id' \
    | head -1 \
    | xargs -I{} gh api "/repos/{owner}/{repo}/actions/workflows/{}/runs?event=issue_comment&per_page=10" \
    --jq "[.workflow_runs[] | select(.created_at > \"$TRIGGERED_AT\")] | .[0]")
  if [ -n "$RUN_JSON" ] && [ "$RUN_JSON" != "null" ]; then
    RUN_ID=$(echo "$RUN_JSON" | jq -r '.id')
    break
  fi
  sleep 5
done
```

If no run appears within ~50 seconds, surface a clear error:

```
Could not find an Auto Approve workflow run for the @auto-approve comment.

Common causes:
  - auto-approve.yml is not on the default branch (re-check Step 2)
  - The ANTHROPIC_API_KEY repo secret is missing
  - GitHub Actions is disabled for this repo

Visit PR_URL/checks to investigate.
```

Stop here.

Once `RUN_ID` is found, poll until the run completes:

```bash
while true; do
  STATUS=$(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.status')
  CONCLUSION=$(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.conclusion')
  [ "$STATUS" = "completed" ] && break
  sleep 10
done
```

Time-box the wait at ~5 minutes. If it does not complete by then, ask the user whether to keep waiting or stop.

### Step 6: Read the Verdict

The workflow posts a single PR comment marked with `<!-- claude-approve -->` and submits a review. Either is enough to read the verdict.

```bash
# Latest auto-approve comment body
gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" \
  --jq '[.[] | select(.body | startswith("<!-- claude-approve -->"))] | last | .body'

# Most recent review submitted by github-actions[bot]
gh api "/repos/{owner}/{repo}/pulls/$PR_NUMBER/reviews" \
  --jq '[.[] | select(.user.login == "github-actions[bot]")] | last | {state, submitted_at, body}'
```

Parse the verdict:

- Review `state == "APPROVED"` -> **APPROVE**
- Review `state == "CHANGES_REQUESTED"` -> **REQUEST_CHANGES**
- Workflow run `conclusion != "success"` -> **WORKFLOW_FAILED** (treat as REQUEST_CHANGES, surface the run logs URL)

Show the comment body to the user verbatim — it contains the gate results and Claude's per-check reasoning the user needs to act on.

### Step 7a: APPROVE Path — Offer to Merge

Check mergeability before asking:

```bash
gh pr view $PR_NUMBER --json mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
```

Then ask:

```
Auto-approve PASSED on PR #PR_NUMBER.

Mergeable:        MERGEABLE_VALUE
Merge state:      MERGE_STATE_STATUS
Review decision:  REVIEW_DECISION
Required checks:  SUMMARY (e.g. 5 passing, 0 failing)

Merge now? [y/N]
  y -> merge with the repo's default merge method
  n -> stop here, I will merge manually
```

**Wait for explicit confirmation.** If the user says yes:

```bash
gh pr merge $PR_NUMBER --auto
```

Use `--auto` so any pending required checks are respected; if `auto-merge` is not enabled on the repo, fall back to the explicit method (`--squash`, `--merge`, or `--rebase`) the team prefers — read it from `HERO.md` if specified, otherwise ask.

**Never force-merge or override branch protection.** If the merge is blocked, report which check is blocking and stop.

### Step 7b: REQUEST_CHANGES Path — Surface and Offer Next Steps

Show the verdict comment, then ask:

```
Auto-approve REQUESTED CHANGES on PR #PR_NUMBER.

(reasons from the verdict comment)

What would you like to do?
  1. /hero-respond-to-pr  -> address the unresolved comments and re-run
  2. Re-trigger @auto-approve once I have addressed the items above
  3. Stop here
```

If the user picks 2, return to Step 3 (re-check pre-flight, then post a fresh `@auto-approve` comment). The workflow updates its prior `<!-- claude-approve -->` comment in place, so re-running does not spam the PR.

### Step 7c: WORKFLOW_FAILED Path

Surface the run URL and the failing step:

```bash
gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.html_url'
gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID/jobs" \
  --jq '.jobs[].steps[] | select(.conclusion == "failure") | {name, conclusion, number}'
```

Suggest the most likely fixes (missing `ANTHROPIC_API_KEY`, GitHub token permissions, repo secrets disabled). Do not retry automatically.

### Step 8: Summary

```
Hero Auto-Approve Summary
=========================
PR:        #PR_NUMBER - PR_TITLE
Branch:    PR_BRANCH -> BASE_BRANCH

Verdict:   APPROVE | REQUEST_CHANGES | WORKFLOW_FAILED
Run:       RUN_URL

Action taken:
  - Merged with METHOD (sha SHORT_SHA)        # APPROVE + user said yes
  - Left for manual merge                       # APPROVE + user said no
  - Suggested /hero-respond-to-pr               # REQUEST_CHANGES
  - Stopped, action failure surfaced            # WORKFLOW_FAILED
```

## Notes

- The workflow's gates (prior review present, all threads resolved) run **before** Claude is invoked. A failed gate is the cheap path; do not assume Claude is wrong if the verdict comes back fast.
- Auto-approve is one signal among many. Branch protection, CODEOWNERS, and required status checks still apply — `gh pr merge` will fail loudly if any of those block the merge, and that is the correct behavior.
- Re-running `@auto-approve` is safe. The workflow updates the same comment and submits a fresh review, so the PR history shows the latest verdict without duplicates.
- Never use `--admin` to bypass branch protection during merge, even if the user asks. Stop and let them merge manually if protection blocks.
