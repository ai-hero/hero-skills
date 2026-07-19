---
name: ship-pr
# prettier-ignore
description: Trigger auto-approve on a PR, wait for the verdict, merge if it passes, and reset to the default branch. Use after hero-skills:review-pr and any bot review when the PR is ready to ship.
argument-hint: [pr-number]
---

# Ship — Trigger Auto-Approve, Merge, Reset Local Branch

This skill posts `@auto-approve` on the PR, waits for the workflow run to finish, reads the verdict, and — if APPROVE — asks whether to merge. If REQUEST_CHANGES, it shows what to fix and offers to re-trigger after fixes land. After a successful merge, it switches to the default branch, pulls latest, deletes the merged head branch (remote + local), and offers cleanup of other stale merged branches (the merged-branch counterpart to `hero-skills:abandon-branch`). It then runs an advisory post-merge deployment-health check (Kubernetes, VM, PaaS, or serverless, per HERO.md).

## Pipeline DAG

This skill is the final step of Pipeline 2 (one-shot) from `PIPELINES.md`, but it also runs standalone. Its internal DAG is:

```
gates → trigger → verdict → merge → reset → verify-deploy
```

Print at each step transition:

```
[N/6] (✓) gates → (✓) trigger → (▶) verdict → ( ) merge → ( ) reset → ( ) verify-deploy

Now running: verdict
```

Mapping to the steps below: Step 3 = `gates`, Step 4 = `trigger`, Steps 5-6 = `verdict`, Step 7a = `merge`, Step 7b = `reset` (merged-branch cleanup — see Step 7b's own note), Step 7e = `verify-deploy` (platform-agnostic post-merge deployment-health check). Steps 1-2 are pre-flight (PR identification, workflow-on-default-branch check) and Step 8 is the summary — neither appears in the DAG. Steps 7c (REQUEST_CHANGES) and 7d (WORKFLOW_FAILED) are alternative end states that *replace* `merge`, `reset`, and `verify-deploy` — there is no merge to verify deployment health for. On those paths render `(✗) merge → ( ) reset → ( ) verify-deploy` and stop, never `(✓) merge → (✓) reset → (✓) verify-deploy`.

The workflow lives at `.github/workflows/auto-approve.yml`. **GitHub only honors `issue_comment`-triggered workflows that already exist on the default branch**, so the workflow file must be merged to `main` (or your default branch) before this skill can do anything useful. This skill checks that first.

## Arguments

- `$ARGUMENTS` - PR number or URL (optional)
  - If omitted: auto-detect from current branch

## Prerequisites

- `gh` CLI installed and authenticated with `repo` scope
- `.github/workflows/auto-approve.yml` present on the default branch — run `hero-skills:init-hero --update` to install it
- The repo has an `ANTHROPIC_API_KEY` secret configured (used by the workflow)
- `kubectl`/`argocd` (k8s deploys) or `curl`-reachable health endpoints (VM/PaaS) — only needed if HERO.md declares a deployment platform

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** -> default branch (to confirm the workflow is on it)
- **CI/CD** -> workflow names (to identify the auto-approve run)
- **Deployment** -> platform (kubernetes | vm | serverless | paas | none), namespaces/hosts, health endpoints

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with defaults.

### Step 1: Identify the PR

If `$ARGUMENTS` provided:

```bash
gh pr view "$ARGUMENTS" --json number,url,headRefName,baseRefName,state,isDraft,mergeable,mergeStateStatus
```

Otherwise auto-detect from the current branch:

```bash
BRANCH=$(git branch --show-current)
# --state all: gh defaults to open-only, which would hide the merged-PR row below.
gh pr list --head "$BRANCH" --state all --json number,url,headRefName,baseRefName,state,isDraft,mergeable,mergeStateStatus --jq '.[0]'
```

Record `PR_NUMBER`, `PR_URL`, `PR_BRANCH`, `BASE_BRANCH`, `IS_DRAFT`.

**Decide what to do based on PR state:**

| State | Action |
|-------|--------|
| No PR found | STOP. Tell the user to run `hero-skills:push-pr` first. |
| Draft PR | STOP. Auto-approve only runs on ready PRs — tell the user to run `hero-skills:review-pr` to mark ready. |
| `.state=="MERGED"`, `PR_BRANCH` still local | Skip to Step 7b to retry (re-derives `MERGED`, independent of Steps 2-6 — see its `$OWNER`/`$REPO` note). |
| `.state=="CLOSED"`, or `MERGED` with `PR_BRANCH` already gone | STOP. Report status. |
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
  1. Run hero-skills:init-hero --update to install .github/workflows/auto-approve.yml
  2. Open a PR for that workflow file alone, get it reviewed and merged to DEFAULT_BRANCH
  3. Re-run hero-skills:ship-pr
```

Do not proceed.

### Step 3: Hard Gate — All Comments and Reviews Must Be Answered

Do not even post `@auto-approve` until every reviewer signal has been addressed. The local checks here mirror the workflow's gates so the user gets an immediate, actionable answer instead of waiting on a CI run that will fail anyway.

```bash
OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login) \(.name)"')
OWNER=$(echo "$OWNER_REPO" | awk '{print $1}')
REPO=$(echo "$OWNER_REPO" | awk '{print $2}')
PR_AUTHOR=$(gh api "/repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '.user.login')

# 3a — Prior review present (self-review OR reviewer review OR bot inline)
SELF_REVIEW=$(gh api "/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
  --jq '[.[] | select(.body | test("ai-hero:self-review"))] | length')

OTHER_REVIEWS=$(gh api "/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" \
  --jq "[.[] | select(.user.login != \"$PR_AUTHOR\") | select(.state != \"PENDING\")] | length")

BOT_INLINE=$(gh api "/repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --jq "[.[] | select(.user.login != \"$PR_AUTHOR\") | select((.user.type == \"Bot\") or (.user.login | test(\"(coderabbit|greptile|copilot|sonarcloud|codeball)\"; \"i\")))] | length")

# 3b — No unresolved review threads (inline conversations)
UNRESOLVED=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            isResolved
            isOutdated
            comments(first: 1) { nodes { path author { login } body } }
          }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | select(.isOutdated == false)] | length')

# 3c — No active CHANGES_REQUESTED review left standing. A
# CHANGES_REQUESTED is "active" if it is the latest review from that
# reviewer and has not been dismissed. Use the GraphQL latestReviews
# field which returns the most recent review per author.
ACTIVE_CHANGES=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        latestReviews(first: 50) {
          nodes { state author { login } }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER \
  --jq '[.data.repository.pullRequest.latestReviews.nodes[] | select(.state == "CHANGES_REQUESTED")] | length')

# 3d — No unanswered top-level reviewer questions. A top-level issue
# comment from a non-author with no later comment from the author is a
# question the author has not answered. We flag any such comment whose
# id is greater than the author's most recent comment id.
LAST_AUTHOR_COMMENT_ID=$(gh api "/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
  --jq "[.[] | select(.user.login == \"$PR_AUTHOR\")] | (last // {id: 0}) | .id")
UNANSWERED_QUESTIONS=$(gh api "/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
  --jq "[.[]
    | select(.user.login != \"$PR_AUTHOR\")
    | select((.user.type != \"Bot\") and ((.user.login | test(\"(coderabbit|greptile|copilot|sonarcloud|codeball|github-actions)\"; \"i\")) | not))
    | select(.id > ${LAST_AUTHOR_COMMENT_ID:-0})
  ] | length")
```

Show the user the gate result:

```
Pre-flight gates for PR #PR_NUMBER:
  Prior review present:       SELF_REVIEW self-review + OTHER_REVIEWS reviewer + BOT_INLINE bot
  Unresolved threads:         UNRESOLVED   (must be 0)
  Active CHANGES_REQUESTED:   ACTIVE_CHANGES (must be 0 — re-request review or push fixes)
  Unanswered reviewer Qs:     UNANSWERED_QUESTIONS (must be 0 — reply to each)
```

**This is a hard gate, not a warning.** Stop and refuse to post `@auto-approve` if any of the following:

- `(SELF_REVIEW + OTHER_REVIEWS + BOT_INLINE) == 0` — no prior review at all. Run `hero-skills:review-pr`.
- `UNRESOLVED > 0` — inline review threads still open. Run `hero-skills:respond-to-comments` to address them and resolve the threads.
- `ACTIVE_CHANGES > 0` — a reviewer's latest review still says CHANGES_REQUESTED. Address the change request, push fixes, then ask the reviewer to dismiss it or submit a fresh review (a subsequent APPROVED review supersedes it in `latestReviews`).
- `UNANSWERED_QUESTIONS > 0` — top-level questions from human reviewers with no author reply. List each one (`gh api .../issues/$PR_NUMBER/comments --jq '.[] | select(.id > LAST_AUTHOR_COMMENT_ID) | {user: .user.login, body: .body[0:200], url: .html_url}'`) and tell the user to reply to each before re-running.

Show the offending items inline so the user can act:

```
Cannot run hero-skills:ship-pr yet. Address these first:

  Unresolved threads (3):
    - api/users.ts:42 — @reviewer: "Handle the null case here"
    - ...

  Active CHANGES_REQUESTED reviews (1):
    - @reviewer1 — push fixes and ask them to re-review or dismiss

  Unanswered reviewer questions (1):
    - @reviewer (PR_URL#issuecomment-12345): "Why not use the existing helper?"

Recommended next step: hero-skills:respond-to-comments
```

Do not proceed. Do not post `@auto-approve`.

Only when **all four gates pass** continue to Step 4.

### Step 4: Post the @auto-approve Trigger Comment

Record the timestamp first so we can find the workflow run we just triggered without confusing it with prior runs.

```bash
TRIGGERED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gh pr comment $PR_NUMBER --body "@auto-approve"
```

The workflow run is keyed off the `issue_comment` event, not a commit SHA. We capture `TRIGGERED_AT` so Step 5 can disambiguate this run from prior `Auto Approve` runs on the same PR.

### Step 5: Wait for the Workflow Run

Poll for the most recent `Auto Approve` workflow run that started after `TRIGGERED_AT`. Implement the lookup as two explicit calls — **not** a piped `xargs -I{}`. Empty-input behavior of `xargs` differs between GNU and BSD/macOS: BSD will run the command with `{}` substituted as the empty string, producing a malformed URL silently. Capture the workflow ID first, bail out loudly if it is empty, then poll the runs endpoint directly:

```bash
WF_ID=$(gh api "/repos/{owner}/{repo}/actions/workflows" \
  --jq '.workflows[] | select(.name == "Auto Approve") | .id' | head -1)

if [ -z "$WF_ID" ]; then
  echo "Auto Approve workflow not found in this repo. Did the workflow file land on the default branch yet?"
  exit 1
fi

RUN_ID=""
for i in 1 2 3 4 5 6 7 8 9 10; do
  RUN_JSON=$(gh api "/repos/{owner}/{repo}/actions/workflows/$WF_ID/runs?event=issue_comment&per_page=10" \
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

Once `RUN_ID` is found, poll until the run completes. The loop has a hard 5-minute timeout — without it, a hung workflow blocks indefinitely with no surfaced error:

```bash
WAIT_START=$SECONDS
while true; do
  if (( SECONDS - WAIT_START > 300 )); then
    RUN_URL=$(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.html_url')
    echo "Timed out waiting for run $RUN_ID after 5 minutes."
    echo "Visit $RUN_URL to check status manually, then ask the user whether to keep waiting or stop."
    break
  fi
  STATUS=$(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.status')
  CONCLUSION=$(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.conclusion')
  [ "$STATUS" = "completed" ] && break
  sleep 10
done
```

### Step 6: Read the Verdict

The workflow posts a single PR comment marked with `<!-- claude-approve -->` and submits a review. Either is enough to read the verdict — but if **both** are missing the run aborted before posting anything, and we treat it as WORKFLOW_FAILED rather than parsing a `null` value as success.

```bash
# Latest auto-approve comment body — `// empty` collapses missing/null
# to an empty string instead of the literal "null".
COMMENT_BODY=$(gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" \
  --jq '[.[] | select(.body | startswith("<!-- claude-approve -->"))] | (last // {}) | (.body // empty)')

# Most recent review submitted by github-actions[bot] (state only).
REVIEW_STATE=$(gh api "/repos/{owner}/{repo}/pulls/$PR_NUMBER/reviews" \
  --jq '[.[] | select(.user.login == "github-actions[bot]")] | (last // {}) | (.state // empty)')

if [ -z "$COMMENT_BODY" ] && [ -z "$REVIEW_STATE" ]; then
  echo "Workflow completed but posted neither a verdict comment nor a review."
  echo "Run conclusion: $CONCLUSION"
  echo "Run URL:        $(gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.html_url')"
  echo "Treating as WORKFLOW_FAILED — see logs for the failing step."
  VERDICT="WORKFLOW_FAILED"
elif [ "$REVIEW_STATE" = "APPROVED" ]; then
  VERDICT="APPROVE"
elif [ "$REVIEW_STATE" = "CHANGES_REQUESTED" ]; then
  VERDICT="REQUEST_CHANGES"
elif [ "$CONCLUSION" != "success" ]; then
  VERDICT="WORKFLOW_FAILED"
else
  # Comment exists but review state was unexpected — fail closed.
  VERDICT="REQUEST_CHANGES"
fi
```

Show the comment body to the user verbatim — it contains the gate results and Claude's per-check reasoning the user needs to act on.

### Step 7: Act on the Verdict

#### Step 7a: APPROVE Path — Offer to Merge

Resolve the merge method from HERO.md (default `squash`), normalize the value (lowercase, strip quotes/whitespace) so `Squash`, `"squash"`, ` squash ` all resolve to `squash`, and reject anything else loudly:

```bash
MERGE_METHOD_RAW=$(awk -F': ' '/^- merge-method:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null)
MERGE_METHOD=$(printf '%s' "${MERGE_METHOD_RAW:-squash}" \
  | tr -d '[:space:]' | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')

case "$MERGE_METHOD" in
  squash|rebase|merge) ;;
  *)
    echo "ERROR: HERO.md merge-method='$MERGE_METHOD_RAW' is not one of squash|rebase|merge."
    echo "Fix HERO.md or pass the method explicitly when merging. Aborting."
    exit 1
    ;;
esac
MERGE_FLAG="--$MERGE_METHOD"

gh pr view $PR_NUMBER --json mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,headRefName
```

Then ask:

```
Auto-approve PASSED on PR #PR_NUMBER.

Mergeable:        MERGEABLE_VALUE
Merge state:      MERGE_STATE_STATUS
Review decision:  REVIEW_DECISION
Required checks:  SUMMARY (e.g. 5 passing, 0 failing)
Merge method:     MERGE_METHOD (from HERO.md)

Merge now? [y/N]
  y -> merge with MERGE_METHOD
  n -> stop here, I will merge manually
```

**Wait for explicit confirmation.** If the user says yes, attempt `--auto` first. If that fails, **inspect the failure reason** before deciding whether to retry without `--auto`:

```bash
gh pr merge $PR_NUMBER $MERGE_FLAG --auto 2> merge_err.log
RC=$?

if [ $RC -ne 0 ]; then
  if grep -qi "auto.merge.*not.*enabled\|auto-merge is not allowed" merge_err.log; then
    # Repo has auto-merge disabled — fall back to immediate merge with
    # the same method. This is safe: branch protection still applies.
    gh pr merge $PR_NUMBER $MERGE_FLAG
  else
    # Branch protection, missing checks, conflicts, permissions — surface
    # the error and stop. Do NOT retry without --auto, because that path
    # bypasses the wait-for-checks safety net.
    cat merge_err.log
    echo "Merge failed. Resolve the underlying issue and re-run hero-skills:ship-pr, or merge manually."
    exit 1
  fi
fi
```

**Never force-merge or override branch protection.** Never pass `--admin`. The fallback above is *only* for the specific "auto-merge not enabled on this repo" case; every other failure is surfaced and stops the skill.

#### Step 7b: Reset to the Default Branch (the merged-branch counterpart to `hero-skills:abandon-branch`)

After a successful merge, leave the user on the default branch, pulled, with the merged PR branch cleaned up — we're usually still on the just-merged head. `abandon-branch` mirrors this for the never-merged case; not shared logic.

If Step 1 skipped straight here, `$OWNER`/`$REPO` were never set (only Step 3 sets them):

```bash
if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login) \(.name)"')
  OWNER=$(echo "$OWNER_REPO" | awk '{print $1}')
  REPO=$(echo "$OWNER_REPO" | awk '{print $2}')
fi
```

Order matters:

1. Confirm the merge actually landed.
2. Switch to `BASE_BRANCH` *before* deleting the head branch locally — `git branch -d` fails if you are on the branch you want to delete.
3. Pull `BASE_BRANCH` so the local copy includes the squash/merge commit.
4. Delete the remote head branch (unless GitHub auto-delete or HERO.md disables it).
5. Delete the local head branch with `-d` (refuses unmerged history — that is a feature).
6. Offer to clean up other stale merged local branches.
7. Suggest `/clear` so the next task starts on a fresh context.

Wrap the whole block in an `if` so an early return cannot kill the wrapping shell, and surface real errors instead of speculating about their cause.

```bash
sleep 3
MERGED=$(gh pr view $PR_NUMBER --json merged --jq '.merged')
RESET_OK=true   # cleared if any sync step (checkout/pull/fetch) fails. Gates
                # the cleanup steps below — never delete branches based on a
                # stale local view of $BASE_BRANCH.

if [ "$MERGED" != "true" ]; then
  echo "Merge not yet recorded — skipping branch reset."
else
  # 1. Switch to BASE_BRANCH first if we are still on the merged head.
  #    Hard-failing checkout post-merge would leave the user stuck on the
  #    merged head with no recovery path. Instead, surface the state, set
  #    RESET_OK=false, and let the user finish the reset manually.
  CURRENT=$(git branch --show-current)
  if [ "$CURRENT" = "$PR_BRANCH" ]; then
    echo "Switching from $PR_BRANCH to $BASE_BRANCH..."
    if ! git checkout "$BASE_BRANCH"; then
      RESET_OK=false
      echo ""
      echo "Could not checkout $BASE_BRANCH. The merge already landed remotely,"
      echo "but you are still on $PR_BRANCH locally."
      echo ""
      echo "Likely causes:"
      echo "  - Uncommitted local edits — check 'git status'"
      echo "  - The local $BASE_BRANCH ref is divergent or missing"
      echo ""
      echo "Resolve manually, then re-run 'hero-skills:ship-pr' to retry."
      echo "Skipping branch deletion + stale-cleanup so we do not act on a"
      echo "stale local view of $BASE_BRANCH."
    fi
  elif [ "$CURRENT" != "$BASE_BRANCH" ]; then
    # User happens to be on a third branch. Leave them there, but flag
    # that this skill is NOT refreshing $BASE_BRANCH locally — otherwise the
    # next task starts from a stale base.
    echo "You are on '$CURRENT', neither '$PR_BRANCH' nor '$BASE_BRANCH'."
    echo "Leaving you here. Note: this skill is NOT pulling $BASE_BRANCH —"
    echo "run 'git fetch origin $BASE_BRANCH' yourself before branching off it."
    RESET_OK=false   # cannot safely run cleanup against a possibly-stale ref
  fi

  # 2. Pull latest into BASE_BRANCH (only if we ended up on it AND the
  #    checkout above succeeded). A non-fast-forward pull means the local
  #    BASE_BRANCH is divergent from origin — a subsequent
  #    "git branch --merged origin/BASE_BRANCH" would judge against a stale
  #    ref, so we fail closed and skip the deletion + cleanup steps.
  CURRENT=$(git branch --show-current)
  if [ "$RESET_OK" = "true" ] && [ "$CURRENT" = "$BASE_BRANCH" ]; then
    if ! git pull --ff-only origin "$BASE_BRANCH"; then
      RESET_OK=false
      echo ""
      echo "WARN: 'git pull --ff-only origin $BASE_BRANCH' failed."
      echo "      The local $BASE_BRANCH is divergent from origin. Skipping"
      echo "      branch deletion and stale-branch cleanup to avoid acting"
      echo "      on a stale reference. Resolve with:"
      echo "        git status; git fetch origin $BASE_BRANCH"
      echo "      then re-run 'hero-skills:ship-pr' to retry."
    fi
  fi
fi

# 3. Remote head-branch cleanup — only when sync succeeded.
if [ "$RESET_OK" = "true" ] && [ "$MERGED" = "true" ]; then
  # Treat null/empty deleteBranchOnMerge as unknown and defer to HERO.md.
  # Non-admins may not see this field.
  AUTO_DELETE=$(gh repo view --json deleteBranchOnMerge --jq '.deleteBranchOnMerge // empty' 2>/dev/null)

  HERO_AUTO_DELETE=$(awk -F': ' '/^- auto-delete-branches:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null \
    | tr -d '[:space:]' | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
  HERO_AUTO_DELETE=${HERO_AUTO_DELETE:-true}

  if [ "$AUTO_DELETE" = "true" ]; then
    # By the time we reach this branch the merge has already happened and
    # GitHub has already deleted the remote ref. Past-tense, not future.
    echo "GitHub auto-deleted $PR_BRANCH on merge (repo deleteBranchOnMerge=true)."
  elif [ "$HERO_AUTO_DELETE" != "true" ]; then
    echo "Skipping remote branch cleanup (HERO.md auto-delete-branches=$HERO_AUTO_DELETE)."
  else
    # Distinguish 404/422 ("already gone — fine") from 401/403 ("permission
    # denied — surface, do not silently mask").
    DELETE_STATUS=$(gh api -X DELETE "/repos/$OWNER/$REPO/git/refs/heads/$PR_BRANCH" \
      -i 2>/dev/null | awk 'NR==1 {print $2; exit}')
    case "$DELETE_STATUS" in
      204|200)        echo "Deleted remote branch: $PR_BRANCH" ;;
      404|422)        echo "Remote branch $PR_BRANCH already gone." ;;
      401|403)        echo "WARN: cannot delete remote $PR_BRANCH — permission denied (HTTP $DELETE_STATUS). Delete it manually if needed." ;;
      *)              echo "WARN: remote delete returned HTTP ${DELETE_STATUS:-error}. Re-check $PR_URL and remove the branch manually if needed." ;;
    esac
  fi

  # 4. Local head-branch cleanup. We're on BASE_BRANCH now; -d (not -D) so
  #    git refuses on unmerged history.
  CURRENT=$(git branch --show-current)
  if [ "$CURRENT" = "$PR_BRANCH" ]; then
    # Should not happen — checkout above handled it. Skip defensively.
    echo "Still on $PR_BRANCH after checkout attempt. Skipping local delete."
  elif git show-ref --verify --quiet "refs/heads/$PR_BRANCH"; then
    LOCAL_ERR=$(git branch -d "$PR_BRANCH" 2>&1 1>/dev/null) || true
    if [ -z "$LOCAL_ERR" ]; then
      echo "Deleted local branch: $PR_BRANCH"
    else
      echo "WARN: could not delete local $PR_BRANCH:"
      echo "  $LOCAL_ERR"
      echo "  Investigate before deleting manually with git branch -D."
    fi
  fi

  # 5. Offer to clean up other merged-but-stale local branches. Distinguish
  #    "no stale branches" from "cannot check" — a missing
  #    refs/remotes/origin/$BASE_BRANCH means git branch --merged returns
  #    nothing, which would silently look identical to "all clean".
  if ! git show-ref --verify --quiet "refs/remotes/origin/$BASE_BRANCH"; then
    echo ""
    echo "Skipping stale-branch cleanup: refs/remotes/origin/$BASE_BRANCH is"
    echo "missing locally. Run 'git fetch origin' and re-check yourself."
  elif ! git fetch --prune origin >/dev/null 2>&1; then
    echo ""
    echo "Skipping stale-branch cleanup: 'git fetch --prune origin' failed."
    echo "Resolve manually before deleting any branches."
  else
    STALE=$(git branch --merged "origin/$BASE_BRANCH" \
      | grep -vE '^\*' \
      | grep -vE "^[[:space:]]*${BASE_BRANCH}$" \
      | sed 's/^[[:space:]]*//' \
      | grep -v '^$' \
      | grep -v "^$PR_BRANCH$" || true)

    if [ -n "$STALE" ]; then
      echo ""
      echo "Other local branches fully merged into $BASE_BRANCH (candidates for cleanup):"
      echo "$STALE" | sed 's/^/  - /'
      echo ""
      echo "Delete them now? [y/N]"
    fi
  fi
fi

# 6. Tidy up the merge-error tempfile from Step 7a regardless of success.
rm -f merge_err.log
```

If the user confirms the cleanup prompt above, run `git branch -d BRANCH_NAME` for each listed branch. Do NOT use `-D` — refuse to force-delete.

After the cleanup, suggest (do not auto-execute) running `/clear` to start the next task on a fresh conversation context. The orchestrating skill (e.g. `hero-skills:one-shot`) may want to print its own summary first, so do not clobber the conversation here.

#### Step 7c: REQUEST_CHANGES Path — Surface and Offer Next Steps

Show the verdict comment, then ask:

```
Auto-approve REQUESTED CHANGES on PR #PR_NUMBER.

(reasons from the verdict comment)

What would you like to do?
  1. hero-skills:respond-to-comments  -> address the unresolved comments and re-run
  2. Re-trigger @auto-approve once I have addressed the items above
  3. Stop here
```

If the user picks 2, return to Step 3 (re-check pre-flight, then post a fresh `@auto-approve` comment). The workflow updates its prior `<!-- claude-approve -->` comment in place, so re-running does not spam the PR.

#### Step 7d: WORKFLOW_FAILED Path

Surface the run URL and the failing step:

```bash
gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID" --jq '.html_url'
gh api "/repos/{owner}/{repo}/actions/runs/$RUN_ID/jobs" \
  --jq '.jobs[].steps[] | select(.conclusion == "failure") | {name, conclusion, number}'
```

Suggest the most likely fixes (missing `ANTHROPIC_API_KEY`, GitHub token permissions, repo secrets disabled). Do not retry automatically.

#### Step 7e: Verify Deployment Health (post-merge)

Runs only on the APPROVE + merged path, gated on `MERGED == "true"` from Step 7b. REQUEST_CHANGES (7c), WORKFLOW_FAILED (7d), and declined-merge paths have no merge to check the deployment health of, so this step does not run there — it is skipped entirely, not rendered as failed.

This check is **advisory only**. It surfaces a DEGRADED or unreachable deployment loudly so the user can act, but it never un-merges, reverts, or blocks anything that already landed in Step 7a.

```bash
if [ "$MERGED" != "true" ]; then
  DEPLOY_STATUS="skipped"
else
  DEPLOY_PLATFORM=$(awk -F': ' '/^- platform:/ {print $2; exit}' "$ROOT/HERO.md" 2>/dev/null \
    | tr -d '[:space:]' | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
  DEPLOY_PLATFORM=${DEPLOY_PLATFORM:-none}
fi
```

Dispatch on `$DEPLOY_PLATFORM`:

**`kubernetes`** — read-only cluster health (nodes, pods, deployments, optional ArgoCD):

```bash
kubectl config current-context
kubectl cluster-info --request-timeout=5s
```

If the connection fails, report `Deployment: skipped (kubectl unreachable)` and stop here — an unreachable cluster is not the same as a DEGRADED one.

```bash
# A failed query must never be mistaken for "all healthy": empty output means
# healthy ONLY when the query itself succeeded. Capture each command's exit
# status and set CHECK_FAILED on any failure. `set -o pipefail` so a kubectl
# failure piped into jq is not masked by jq's own exit code.
set -o pipefail
CHECK_FAILED=false

# Nodes — Ready/NotReady and pressure conditions
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.conditions[*]}{.type}={.status}{"\t"}{end}{"\n"}{end}' || CHECK_FAILED=true

# Pods — anything not Running/Succeeded, plus crashloops
PODS_OUT=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide 2>&1) \
  && printf '%s\n' "$PODS_OUT" \
  || { echo "WARN: pod-status query failed: $PODS_OUT"; CHECK_FAILED=true; }
kubectl get pods --all-namespaces -o json \
  | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | "\(.metadata.namespace)/\(.metadata.name) restarts=\(.status.containerStatuses[0].restartCount)"' \
  || CHECK_FAILED=true

# Deployments — ready vs desired replica counts
kubectl get deployments --all-namespaces -o json \
  | jq -r '.items[] | select(.status.readyReplicas != .status.replicas) | "\(.metadata.namespace)/\(.metadata.name) ready=\(.status.readyReplicas // 0)/\(.status.replicas)"' \
  || CHECK_FAILED=true
```

If HERO.md flags ArgoCD for this deployment, also check sync/health:

```bash
# Try the argocd CLI; fall back to kubectl. If BOTH fail, ArgoCD state is
# unknown — record that rather than treating empty output as "all Synced".
if ! argocd app list -o json 2>/dev/null \
     | jq -r '.[] | "\(.metadata.name)\t\(.status.sync.status)\t\(.status.health.status)"'; then
  if ! kubectl get applications -n argocd -o json 2>/dev/null \
       | jq -r '.items[] | "\(.metadata.name)\tsync=\(.status.sync.status)\thealth=\(.status.health.status)"'; then
    echo "WARN: could not query ArgoCD via the argocd CLI or kubectl."
    CHECK_FAILED=true
  fi
fi
```

Classify in this order:

- **`UNKNOWN` (could not verify)** when `CHECK_FAILED` is `true` — a health query itself failed (RBAC denial, missing `argocd` binary, apiserver error, expired token). This is **not** the same as healthy; report it as `could not verify deployment health` so the user investigates rather than trusting a false green.
- Otherwise `HEALTHY` (all nodes Ready, no crashlooping/pending pods, all deployments at desired replica count, ArgoCD Synced/Healthy where checked) vs `DEGRADED` (any NotReady node, any crashlooping/pending pod, any under-replica'd deployment, or ArgoCD OutOfSync/Degraded/Missing).

**`vm` / `paas` / `serverless`** — curl the HERO.md-configured health endpoint(s). HERO.md's Deployment section lists one or more, e.g. `- health-endpoint: https://api.example.com/healthz`; read them all first:

```bash
HEALTH_ENDPOINTS=$(awk -F': ' '/^- health-endpoint:/ {print $2}' "$ROOT/HERO.md" 2>/dev/null \
  | tr -d '"' | tr -d "'")

if [ -z "$HEALTH_ENDPOINTS" ]; then
  echo "No health endpoint configured for $DEPLOY_PLATFORM — skipping."
  DEPLOY_STATUS="skipped"
else
  DEPLOY_STATUS="HEALTHY"
  # Here-string (not `... | while`): a pipeline runs the loop in a subshell,
  # so DEPLOY_STATUS assignments inside it would be discarded. curl emits 000
  # on timeout/unreachable, which the non-2xx branch correctly treats as
  # DEGRADED.
  while read -r URL; do
    [ -z "$URL" ] && continue
    CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$URL")
    echo "$URL -> HTTP $CODE"
    case "$CODE" in
      2??) ;;                          # 2xx — healthy
      *)   DEPLOY_STATUS="DEGRADED" ;; # non-2xx or 000 (timeout/unreachable)
    esac
  done <<< "$HEALTH_ENDPOINTS"
fi
```

Treat a missing endpoint list as skipped, not DEGRADED — there is nothing configured to check. Otherwise the loop above sets `HEALTHY` (every endpoint returns 2xx) vs `DEGRADED` (any non-2xx response or timeout).

**`none` or missing** — skip silently; render `(–)` for this phase in the DAG and Summary.

Report the result as `HEALTHY`, `DEGRADED`, `UNKNOWN` (could not verify — a health query failed), or `skipped` (no platform configured), along with the raw evidence (offending node/pod/deployment names, the failing endpoint and status code, or the query that errored) so the user can act on it directly. Never suggest un-merging — end a DEGRADED result with a note like "Deployment looks DEGRADED — investigate, but the merge itself stands."

### Step 8: Summary

Render the Pipeline DAG line **conditionally on the verdict, whether the user merged, and the deployment-health result**. Use the marker semantics from `PIPELINES.md`:

- APPROVE + merged + reset succeeded + deploy healthy → `(✓) gates → (✓) trigger → (✓) verdict → (✓) merge → (✓) reset → (✓) verify-deploy`
- APPROVE + merged + reset succeeded + deploy DEGRADED → `(✓) gates → (✓) trigger → (✓) verdict → (✓) merge → (✓) reset → (✗) verify-deploy`
- APPROVE + merged + reset succeeded + deploy UNKNOWN (a health query failed) → `(✓) gates → (✓) trigger → (✓) verdict → (✓) merge → (✓) reset → (✗) verify-deploy` with a `could not verify deployment health` note (distinct from DEGRADED — the deployment may be fine; the check couldn't confirm it)
- APPROVE + merged + reset succeeded + no platform configured (skipped) → `(✓) gates → (✓) trigger → (✓) verdict → (✓) merge → (✓) reset → (–) verify-deploy`
- APPROVE + merged + reset partial (RESET_OK=false) → `(✓) gates → (✓) trigger → (✓) verdict → (✓) merge → (✗) reset → (✓|✗|–) verify-deploy` — verify-deploy still runs off `MERGED == true`, independent of the reset outcome
- APPROVE + user declined merge → `(✓) gates → (✓) trigger → (✓) verdict → (✗) merge → ( ) reset → ( ) verify-deploy` with `Stopped: user declined merge`
- REQUEST_CHANGES → `(✓) gates → (✓) trigger → (✓) verdict → (✗) merge → ( ) reset → ( ) verify-deploy` with `Stopped: REQUEST_CHANGES`
- WORKFLOW_FAILED → `(✓) gates → (✓) trigger → (✗) verdict → ( ) merge → ( ) reset → ( ) verify-deploy` with `Stopped: WORKFLOW_FAILED`

```
Ship Summary
=========================
PR:        #PR_NUMBER - PR_TITLE
Branch:    PR_BRANCH -> BASE_BRANCH

Pipeline:  (CONDITIONAL_DAG_LINE_FROM_ABOVE)

Verdict:   APPROVE | REQUEST_CHANGES | WORKFLOW_FAILED
Run:       RUN_URL

Deployment: HEALTHY | DEGRADED | UNKNOWN | skipped

Action taken:
  - Merged with MERGE_METHOD (sha SHORT_SHA)            # APPROVE + user said yes
  - Reset: switched to BASE_BRANCH, pulled, deleted PR_BRANCH (remote+local)
  - Stale-branch cleanup: deleted N | offered N | none found | skipped (sync failed)
  - Left for manual merge                                # APPROVE + user said no
  - Suggested hero-skills:respond-to-comments             # REQUEST_CHANGES
  - Stopped, action failure surfaced                     # WORKFLOW_FAILED

Next step: (one only — omit for REQUEST_CHANGES/WORKFLOW_FAILED, already covered by 7c/7d)
```

- Merged → `/clear` — plain suggestion, not Skill-tool invocable, no y/N offer.
- Abandoning mid-flight → `hero-skills:abandon-branch` — restricted, print only.

Skip `hero-skills:one-shot`; it's not the deterministic next action.

## Notes

- The workflow's gates (prior review present, all threads resolved) run **before** Claude is invoked. A failed gate is the cheap path; do not assume Claude is wrong if the verdict comes back fast.
- Auto-approve is one signal among many. Branch protection, CODEOWNERS, and required status checks still apply — `gh pr merge` will fail loudly if any of those block the merge, and that is the correct behavior.
- Re-running `@auto-approve` is safe. The workflow updates the same comment and submits a fresh review, so the PR history shows the latest verdict without duplicates.
- Never use `--admin` to bypass branch protection during merge, even if the user asks. Stop and let them merge manually if protection blocks.
