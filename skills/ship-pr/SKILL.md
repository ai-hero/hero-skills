---
name: ship-pr
# prettier-ignore
description: Trigger auto-approve on a PR, wait for the verdict, merge if it passes, and reset to the default branch. Use after hero-skills:review-pr and any bot review when the PR is ready to ship.
argument-hint: [pr-number]
---

# Ship — Trigger Auto-Approve, Merge, Reset Local Branch

This skill posts `@auto-approve` on the PR, waits for the workflow run to finish, reads the verdict, and — if APPROVE — asks whether to merge. If REQUEST_CHANGES, it shows what to fix and offers to re-trigger after fixes land. After a successful merge, it switches to the default branch, pulls latest, deletes the merged head branch (remote + local), and offers cleanup of other stale merged branches (the merged-branch counterpart to `hero-skills:abandon`). It then runs an advisory post-merge deployment-health check (Kubernetes, VM, PaaS, or serverless, per HERO.md).

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

The workflow lives at `.github/workflows/auto-approve.yaml` (or `.yml` — both are honoured). **GitHub only honors `issue_comment`-triggered workflows that already exist on the default branch**, so the workflow file must be merged to `main` (or your default branch) before this skill can do anything useful. This skill checks that first.

## Arguments

- `$ARGUMENTS` - PR number or URL (optional)
  - If omitted: auto-detect from current branch

## Prerequisites

- `gh` CLI installed and authenticated with `repo` scope
- `.github/workflows/auto-approve.yaml` (or `.yml`) present on the default branch — run `hero-skills:init-hero --update` to install it
- The repo has an `ANTHROPIC_API_KEY` secret configured (used by the workflow)
- `kubectl`/`argocd` (k8s deploys) or `curl`-reachable health endpoints (VM/PaaS) — only needed if HERO.md declares a deployment platform

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
[ -f "$PWD/FLEET.md" ] && [ ! -f "$PWD/HERO.md" ] && echo "FLEET_ROOT" || true
```

If `FLEET_ROOT` printed, this folder is a fleet, not a repo: stop and follow **At the fleet root** in `docs/FLEET-MD.md`.

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
| --- | --- |
| No PR found | STOP. Tell the user to run `hero-skills:push-pr` first. |
| Draft PR | STOP. Auto-approve only runs on ready PRs — tell the user to run `hero-skills:review-pr` to mark ready. |
| `.state=="MERGED"`, `PR_BRANCH` still local | Skip to Step 7b to retry (re-derives `MERGED`, independent of Steps 2-6 — see its `$OWNER`/`$REPO` note). |
| `.state=="CLOSED"`, or `MERGED` with `PR_BRANCH` already gone | STOP. Report status. |
| Open, ready | Continue. |

### Step 2: Verify Auto-Approve Workflow Is on the Default Branch

GitHub only triggers `issue_comment` workflows that already exist on the default branch. If the file is only on the PR branch, the comment will be a no-op.

Probe **both** YAML spellings. GitHub honours `.yml` and `.yaml` equally, so a
fleet assembled over time carries some of each — treating one as canonical
reports MISSING for a workflow that is present and active, and stops the ship
on a filename rather than on anything real.

```bash
DEFAULT_BRANCH=$(gh api "/repos/{owner}/{repo}" --jq '.default_branch')
WF_PATH=""
for ext in yaml yml; do
  if gh api "/repos/{owner}/{repo}/contents/.github/workflows/auto-approve.$ext?ref=$DEFAULT_BRANCH" \
       --jq '.path' >/dev/null 2>&1; then
    WF_PATH=".github/workflows/auto-approve.$ext"
    break
  fi
done
[ -n "$WF_PATH" ] && echo "$WF_PATH" || echo "MISSING"
```

**If MISSING:** STOP and show:

```
No .github/workflows/auto-approve.yaml (or .yml) on the default branch (DEFAULT_BRANCH).

GitHub only honors issue_comment workflows that already exist on the default branch.
Posting @auto-approve here will silently do nothing.

Fix:
  1. Run hero-skills:init-hero --update to install the workflow
  2. Open a PR for that workflow file alone, get it reviewed and merged to DEFAULT_BRANCH
  3. Re-run hero-skills:ship-pr
```

Do not proceed.

### Step 3: Hard Gate — All Comments and Reviews Must Be Answered

Do not even post `@auto-approve` until every reviewer signal has been addressed. The local checks here mirror the workflow's gates so the user gets an immediate, actionable answer instead of waiting on a CI run that will fail anyway.

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB" || { echo "ERROR: cannot source hero-lib.sh — reinstall the plugin."; exit 1; }
OWNER_REPO=$(gh repo view --json owner,name --jq '"\(.owner.login) \(.name)"')
OWNER=$(echo "$OWNER_REPO" | awk '{print $1}')
REPO=$(echo "$OWNER_REPO" | awk '{print $2}')
PR_AUTHOR=$(gh api "/repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '.user.login')

# 3a — Prior review present (self-review OR reviewer review OR bot inline)
# Branch on the rc: an empty count summed below reads as 0, "no review".
SELF_REVIEW=$(hero_self_review_count "$PR_NUMBER") \
  || { echo "ship-pr: cannot read PR comments — the prior-review gate cannot be evaluated"; exit 1; }

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

# 3e — CI green on the head commit. The workflow's own CI gate fails CLOSED
# on a pending check rather than polling (polling would burn the runner
# minutes the gate exists to save), so wait here, locally and for free.
# Buckets: pass / fail / pending / skipping / cancel. The name filter mirrors
# the workflow's: a consumer that also calls auto-approve from a
# pull_request trigger would have its own check on the head.
#
# `gh pr checks` exits 1 with EMPTY stdout when the head has no checks yet,
# and 8 while any check is pending. Left unhandled, the empty case made both
# counts empty strings, `[ "" -gt 0 ]` errored instead of breaking, and the
# loop spun the full 30 minutes. Empty stdout is "no checks registered yet":
# keep polling for two minutes (registration lag after a push), then treat
# as no CI. Any other gh failure is a hard stop, not a pass.
CI_DEADLINE=$(( $(date +%s) + 1800 ))
CI_EMPTY_UNTIL=$(( $(date +%s) + 120 ))
CI_FAILED=0; CI_PENDING=0
while :; do
  CI_ERR=""
  CI_JSON=$(gh pr checks "$PR_NUMBER" --json name,bucket \
    --jq '[.[] | select(.name | test("(^| / )claude-approve$") | not)]' 2>/tmp/ci_err) || CI_ERR=$(cat /tmp/ci_err)
  if [ -z "$CI_JSON" ]; then
    if grep -qi "no checks reported" <<<"$CI_ERR"; then
      [ "$(date +%s)" -ge "$CI_EMPTY_UNTIL" ] && { CI_FAILED=0; CI_PENDING=0; break; }
      echo "CI: no checks registered on the head yet — waiting…"; sleep 15; continue
    fi
    echo "gh pr checks failed: $CI_ERR" >&2
    CI_FAILED=1; CI_PENDING=0; break
  fi
  CI_FAILED=$(jq -r '[.[] | select(.bucket == "fail" or .bucket == "cancel")] | length' <<<"$CI_JSON")
  CI_PENDING=$(jq -r '[.[] | select(.bucket == "pending")] | length' <<<"$CI_JSON")
  case "$CI_FAILED$CI_PENDING" in *[!0-9]*) echo "unexpected gh pr checks output" >&2; CI_FAILED=1; CI_PENDING=0; break ;; esac
  [ "$CI_FAILED" -gt 0 ] && break
  [ "$CI_PENDING" -eq 0 ] && break
  [ "$(date +%s)" -ge "$CI_DEADLINE" ] && break
  echo "CI: $CI_PENDING check(s) still running — waiting…"
  sleep 30
done
```

Show the user the gate result:

```
Pre-flight gates for PR #PR_NUMBER:
  Prior review present:       SELF_REVIEW self-review + OTHER_REVIEWS reviewer + BOT_INLINE bot
  Unresolved threads:         UNRESOLVED   (must be 0)
  Active CHANGES_REQUESTED:   ACTIVE_CHANGES (must be 0 — re-request review or push fixes)
  Unanswered reviewer Qs:     UNANSWERED_QUESTIONS (must be 0 — reply to each)
  CI on head commit:          CI_FAILED failed, CI_PENDING pending (both must be 0)
```

**This is a hard gate, not a warning.** Stop and refuse to post `@auto-approve` if any of the following:

- `(SELF_REVIEW + OTHER_REVIEWS + BOT_INLINE) == 0` — no prior review at all. Run `hero-skills:review-pr`.
- `UNRESOLVED > 0` — inline review threads still open. Run `hero-skills:respond-to-comments` to address them and resolve the threads.
- `ACTIVE_CHANGES > 0` — a reviewer's latest review still says CHANGES_REQUESTED. Address the change request, push fixes, then ask the reviewer to dismiss it or submit a fresh review (a subsequent APPROVED review supersedes it in `latestReviews`).
- `UNANSWERED_QUESTIONS > 0` — top-level questions from human reviewers with no author reply. List each one (`gh api .../issues/$PR_NUMBER/comments --jq '.[] | select(.id > LAST_AUTHOR_COMMENT_ID) | {user: .user.login, body: .body[0:200], url: .html_url}'`) and tell the user to reply to each before re-running.
- `CI_FAILED > 0` — a check on the head commit failed. List them (`gh pr checks $PR_NUMBER`), fix, push, and re-run. The workflow's CI gate would REQUEST_CHANGES on this anyway; failing here saves the run.
- `CI_PENDING > 0` after the 30-minute wait — a check is hung or queued behind a full runner pool. Report it; do not post `@auto-approve` into a pending build.

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

Only when **all five gates pass** continue to Step 4.

### Step 3b: Rebase onto the Base — Before the Trigger, Never After the Verdict

**Rebase onto the base before judging anything.** Work is concurrent — other
branches merge while this PR waits — so the head on the branch is routinely
behind the base, and a review of a stale head reviews code that is not what
will merge.

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB"
BASE_BRANCH=${BASE_BRANCH:-$(hero_default_branch)}
hero_rebase_on_base "$BASE_BRANCH"; echo "REBASE_RC=$?"
```

`REBASE_RC=0` continues (up to date, or rebased and pushed — say which).
`1` is a conflict: the rebase was aborted and the branch is unchanged; STOP,
list the conflicting files it printed, and hand back to the user — never
resolve a conflict on someone's behalf. `2` cannot proceed (dirty tree,
detached HEAD, fetch or lease failure): STOP with its message.

This runs **before** `@auto-approve`, not after: branch protection dismisses
approvals on push, so a rebase after the verdict would throw the verdict
away. Between the verdict and the merge, Step 7 only *re-reads*
`mergeStateStatus`; if the base moved again (`BEHIND`) or the merge became
`DIRTY`, come back here once — rebase, re-trigger, re-wait — and if it is
still not clean after that, STOP and say what keeps moving underneath it.

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
  # Exclude conclusion == "skipped". EVERY comment on the PR creates an
  # issue_comment run, and the shared workflow's trigger is anchored — it
  # fires only when the body STARTS with the command — so an ordinary comment
  # produces a run that is immediately `skipped`. review-pr posts its
  # self-review comment moments before this step runs, and any bot or human
  # comment lands in the same window. Taking .[0] unfiltered latches onto that
  # skipped run, polls it to "completed", finds no verdict comment, and
  # reports WORKFLOW_FAILED for a run in which nothing executed.
  # A queued or in-progress run has conclusion null, so it survives this
  # filter; only genuinely skipped ones are dropped.
  # Fetch RAW, then filter — never `gh api --jq` on this endpoint. An
  # issue_comment run carries the comment body in `display_title`, so a PR
  # comment containing a control character (U+0000–U+001F) puts one inside a
  # JSON string, and the whole poll dies with
  #   jq: parse error: Invalid string: control characters ... must be escaped
  # for a run that is otherwise perfectly healthy. Stripping C0 is safe on
  # both sides of the problem: between tokens they were only whitespace, and
  # inside a string they were illegal anyway.
  #
  # Capture before filtering, and check gh's own status. `gh api | jq` would
  # swallow it — a 404 or a rate-limit would read as "no run yet" and poll to
  # the timeout with a misleading error.
  RUNS_ERR=$(mktemp)
  if ! RAW=$(gh api "/repos/{owner}/{repo}/actions/workflows/$WF_ID/runs?event=issue_comment&per_page=10" 2>"$RUNS_ERR"); then
    echo "WARN: could not read workflow runs:"; cat "$RUNS_ERR"; rm -f "$RUNS_ERR"
    sleep 5; continue
  fi
  rm -f "$RUNS_ERR"
  # jq is checked too: an unchecked parse failure reads as "no run yet" and
  # burns all ten polls before printing a "Common causes" list that does not
  # contain the cause.
  RUN_JSON=$(printf '%s' "$RAW" | tr -d '\000-\037' \
    | jq -c "[.workflow_runs[]
             | select(.created_at > \"$TRIGGERED_AT\")
             | select(.conclusion != \"skipped\")] | .[0]") \
    || { echo "jq could not parse the runs payload:"; printf '%s' "$RAW" | head -c 400; echo; exit 1; }
  if [ -n "$RUN_JSON" ] && [ "$RUN_JSON" != "null" ]; then
    RUN_ID=$(echo "$RUN_JSON" | jq -r '.id')
    break
  fi
  sleep 5
done
```

If every run after `TRIGGERED_AT` is `skipped`, the command comment itself did
not match the trigger. On a public repo that is the `github.event.repository.private`
gate; otherwise check that the comment body *starts with* `@auto-approve` — a
body that merely contains it no longer fires.

If no run appears within ~50 seconds, surface a clear error:

```
Could not find an Auto Approve workflow run for the @auto-approve comment.

Common causes:
  - auto-approve.yaml/.yml is not on the default branch (re-check Step 2)
  - The ANTHROPIC_API_KEY repo secret is missing
  - GitHub Actions is disabled for this repo
  - This repo is PUBLIC — the caller is gated on the repo being private,
    so the job is skipped and never posts anything

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
  # `skipped` is not a failure and has no failing step to look at — sending
  # someone to "the logs" for a run where nothing executed is a dead end. The
  # caller is gated on `github.event.repository.private`, so a public repo
  # skips forever with no error anywhere: the file is on the default branch,
  # so preflight passes too.
  if [ "$CONCLUSION" = "skipped" ]; then
    echo ""
    echo "The run was SKIPPED — no step failed, the job's \`if:\` did not match."
    echo "Most likely this repo is public: auto-approve is gated on the repo"
    echo "being private, because the shared workflow uploads changed-file"
    echo "contents to a model and public repos take PRs from untrusted forks."
    echo "Check: gh repo view --json visibility"
  else
    echo "Treating as WORKFLOW_FAILED — see logs for the failing step."
  fi
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
# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
MERGE_METHOD_RAW=$(hero_field merge-method || true)
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
# mergeStateStatus BEHIND or DIRTY here → Step 3b once (rebase, re-trigger,
# re-wait), then STOP. Never merge a head that is behind the base.
```

**Then check for stacked PRs — before the merge, not after.** Any open PR
whose base is this PR's head branch is a *dependent*, and merging this PR
destroys it:

```bash
# Every step here is checked, because the failure mode of an UNCHECKED gate
# is the exact loss the gate exists to prevent: on a gh hiccup STACKED_COUNT
# would be "", `[ "" -gt 0 ]` is false, and the merge proceeds. Likewise an
# empty PR_BRANCH makes `--base ""` match EVERY open PR (verified), and `r`
# would then retarget all of them.
[ -n "$PR_BRANCH" ] && [ -n "$BASE_BRANCH" ] \
  || { echo "PR_BRANCH/BASE_BRANCH not set from Step 1 — refusing to merge."; exit 1; }
if ! STACKED=$(gh pr list --state open --base "$PR_BRANCH" --json number,url,title,headRefName); then
  echo "Could not list PRs based on $PR_BRANCH — refusing to merge until the stacked-PR check can run."; exit 1
fi
STACKED_COUNT=$(printf '%s' "$STACKED" | jq 'length') || exit 1
case "$STACKED_COUNT" in ''|*[!0-9]*)
  echo "Unparsable stacked-PR count '$STACKED_COUNT' — refusing to merge."; exit 1 ;;
esac
```

`STACKED_COUNT > 0` is a **stop-and-ask**, not a warning to print past:

```
PR #104 has 1 open PR stacked on its branch:
  #105  Add the retry path        (base: feat/parent, head: feat/child)

Merging #104 deletes feat/parent, which AUTO-CLOSES #105. A closed PR whose
base branch is gone cannot be reopened or retargeted — #105 would have to be
recreated from scratch under a new number, losing its review history.

  r -> retarget #105 onto main, then merge #104   (recommended)
  m -> merge anyway and accept that #105 is lost
  n -> stop here
```

On `r`, retarget every dependent **before** merging, then re-check — a
retarget that failed (permissions, a locked PR) followed by the merge is the
unrecoverable loss this gate exists to prevent, and a flag set inside a
`| while` loop is lost to the subshell, so the re-list is the only reliable
check:

```bash
printf '%s' "$STACKED" | jq -r '.[].number' | while read -r N; do
  gh pr edit "$N" --base "$BASE_BRANCH" || echo "WARN: could not retarget #$N"
done
REMAINING=$(gh pr list --state open --base "$PR_BRANCH" --json number --jq 'length') || exit 1
[ "$REMAINING" = 0 ] \
  || { echo "$REMAINING PR(s) still based on $PR_BRANCH — not merging. Retarget them by hand and re-run."; exit 1; }
```

Three reasons the order matters:

- **Retarget before the merge, not after.** With repo setting
  `deleteBranchOnMerge=true` the branch is gone the instant the merge lands,
  so there is no "after" — the dependents are already closed. Waiting until
  Step 7b's cleanup is too late even when the repo does not auto-delete.
- **The damage is not reversible.** GitHub refuses `Cannot change the base
  branch of a closed pull request`, and reopening requires the base ref to
  exist. Recreating the PR loses its review threads, its approvals, and its
  number.
- **Retargeting onto the base is correct, not a workaround.** Once the parent
  merges, its commits are in `$BASE_BRANCH`, so the dependent's diff collapses
  to exactly its own work. Do it before the merge and the diff is briefly
  wrong; that resolves itself the moment the parent lands.

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

Worth telling the user when they are staring at a failed merge, because "don't use `--admin`" reads like a policy they could choose to break: **under `enforce_admins: true` it does not work at all.** Branch protection with admin enforcement on applies to admins too, so `gh pr merge --admin` returns an error rather than overriding anything. It is not a lever being withheld — there is no lever. The real options are to satisfy the failing requirement, or to have someone with repo-settings access change the protection rule.

#### Step 7b: Reset to the Default Branch (the merged-branch counterpart to `hero-skills:abandon`)

After a successful merge, leave the user on the default branch, pulled, with the merged PR branch cleaned up — we're usually still on the just-merged head. `abandon` mirrors this for the never-merged case; not shared logic.

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
5. Delete the local head branch with `-d` (refuses unmerged history — that is a feature). If `-d` refuses, fall back to `-D` only when the local branch tip is confirmed to be exactly the PR's merged head (via `headRefOid`) — never on `MERGED=true` alone, since that only proves the PR merged, not that the local branch has no commits beyond it.
6. Offer to clean up other stale merged local branches.
7. Suggest `/clear` so the next task starts on a fresh context.

Wrap the whole block in an `if` so an early return cannot kill the wrapping shell, and surface real errors instead of speculating about their cause.

```bash
sleep 3
# `--json merged` isn't a valid gh CLI field (gh 2.86.0 rejects unknown
# --json names locally, before any API call) — derive from `state`. Also
# check gh's own exit status: an auth/network failure here must not read
# as "not merged yet" (both would otherwise leave MERGED empty).
if ! MERGED=$(gh pr view $PR_NUMBER --json state --jq 'if .state == "MERGED" then "true" else "false" end' 2>/tmp/ship_pr_merge_check_err.log); then
  echo "WARN: could not check merge status via 'gh pr view' — see error below."
  cat /tmp/ship_pr_merge_check_err.log
  echo "Resolve (check 'gh auth status' / network) and re-run 'hero-skills:ship-pr' to retry."
  MERGED=false
fi
rm -f /tmp/ship_pr_merge_check_err.log
RESET_OK=true   # cleared if any sync step (checkout/pull/fetch) fails. Gates
                # the cleanup steps below — never delete branches based on a
                # stale local view of $BASE_BRANCH.

# shellcheck source=/dev/null
. "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
if [ "$MERGED" != "true" ]; then
  echo "Merge not yet recorded — skipping branch reset."
elif hero_in_worktree; then
  # A linked worktree cannot check out the default branch — it is checked out
  # in the primary — and its branch is deleted by whoever removes the worktree
  # (wayfare's goal turn, or the user with `git worktree remove`).
  RESET_OK=true
  echo "Linked worktree: merge landed; leaving $PR_BRANCH checked out here. Remove the worktree to finish: git worktree remove $(pwd)"
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

  HERO_AUTO_DELETE=$(hero_field auto-delete-branches 2>/dev/null | tr '[:upper:]' '[:lower:]')
  HERO_AUTO_DELETE=${HERO_AUTO_DELETE:-true}

  if [ "$AUTO_DELETE" = "true" ]; then
    # By the time we reach this branch the merge has already happened and
    # GitHub has already deleted the remote ref. Past-tense, not future.
    echo "GitHub auto-deleted $PR_BRANCH on merge (repo deleteBranchOnMerge=true)."
  elif [ "$HERO_AUTO_DELETE" != "true" ]; then
    echo "Skipping remote branch cleanup (HERO.md auto-delete-branches=$HERO_AUTO_DELETE)."
  else
    # Backstop for the stacked-PR gate in Step 7a. That gate only runs on the
    # merge path; a ship-pr resumed against an ALREADY-merged PR reaches this
    # line having never checked, and deleting the ref here auto-closes every
    # dependent just as surely. Retarget first, then delete.
    # A check that cannot run must NOT default to "zero stacked" — deleting on
    # a gh failure auto-closes the dependents just as surely as deleting on a
    # real zero would not.
    if ! STILL_STACKED=$(gh pr list --state open --base "$PR_BRANCH" --json number --jq 'length') \
       || ! printf '%s' "$STILL_STACKED" | grep -qE '^[0-9]+$'; then
      echo "Could not verify stacked PRs on $PR_BRANCH — NOT deleting it. Delete by hand once verified."
    elif [ "$STILL_STACKED" -gt 0 ]; then
      echo "NOT deleting $PR_BRANCH — $STILL_STACKED open PR(s) are still based on it."
      echo "Deleting it would auto-close them, and a closed PR whose base is gone"
      echo "cannot be reopened or retargeted. Retarget them first:"
      gh pr list --state open --base "$PR_BRANCH" --json number,title \
        --jq '.[] | "  gh pr edit \(.number) --base '"$BASE_BRANCH"'   # \(.title)"'
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
  fi

  # 4. Local head-branch cleanup. We're on BASE_BRANCH now. Check the actual
  #    exit status, not stderr emptiness — `git branch -d` can print a
  #    non-fatal "not yet merged to HEAD" warning on a *successful* delete
  #    (squash/rebase merges break linear ancestry, but an upstream-tracking
  #    ref still shows it merged) — stderr-emptiness would misreport that as
  #    a failure.
  CURRENT=$(git branch --show-current)
  if [ "$CURRENT" = "$PR_BRANCH" ]; then
    # Should not happen — checkout above handled it. Skip defensively.
    echo "Still on $PR_BRANCH after checkout attempt. Skipping local delete."
  elif git show-ref --verify --quiet "refs/heads/$PR_BRANCH"; then
    if git branch -d "$PR_BRANCH" 2>&1; then
      echo "Deleted local branch: $PR_BRANCH"
    else
      # MERGED=true only proves the PR merged, not that the local tip has no
      # commits beyond it (a forgotten local commit, an amend). Verify the
      # local tip IS the merged PR head before force-deleting.
      PR_HEAD_SHA=$(gh pr view $PR_NUMBER --json headRefOid --jq '.headRefOid' 2>/dev/null)
      LOCAL_SHA=$(git rev-parse "$PR_BRANCH" 2>/dev/null)
      if [ -n "$PR_HEAD_SHA" ] && [ "$LOCAL_SHA" = "$PR_HEAD_SHA" ]; then
        if git branch -D "$PR_BRANCH" 2>&1; then
          echo "Deleted local branch: $PR_BRANCH (forced — local tip matched the merged PR head $PR_HEAD_SHA)"
        else
          echo "WARN: could not delete local $PR_BRANCH even with -D. Investigate manually."
        fi
      else
        echo "WARN: local $PR_BRANCH ($LOCAL_SHA) does not match the merged PR head ($PR_HEAD_SHA)."
        echo "  It may have local-only commits that were never part of the merged PR — not force-deleting."
        echo "  Investigate; delete manually with 'git branch -D $PR_BRANCH' only if you're sure."
      fi
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
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB" || { echo "ERROR: cannot source hero-lib.sh — reinstall the plugin."; exit 1; }
DEPLOY_CAVEAT=""
if [ "$MERGED" != "true" ]; then
  DEPLOY_STATUS="skipped"
else
  # BLOCK-scoped: an unscoped read returns CI/CD's platform. rc 2 is a value
  # the security gate rejected, not an absent key — say so instead of `none`.
  DEPLOY_PLATFORM=$(hero_md_field "$ROOT/HERO.md" platform '## Deployment' | tr '[:upper:]' '[:lower:]'); HF_RC=$?
  [ "$HF_RC" -eq 2 ] && { DEPLOY_PLATFORM=none; DEPLOY_CAVEAT="Deployment platform value rejected as unsafe — treat the result as UNKNOWN"; }
  DEPLOY_PLATFORM=${DEPLOY_PLATFORM:-none}

  # A probe taken while the merge commit's own workflow runs are still going
  # measures the PREVIOUS deploy — healthy, and not the one this PR produced.
  # Wait for them (ten-minute cap), then probe. Only Actions-driven deploys
  # are visible here: a platform that deploys off its own git hook or a
  # polling CD (ArgoCD) has no run to wait on, and the probe can still read
  # the previous deploy.
  if [ "$DEPLOY_PLATFORM" != "none" ]; then
    MERGE_COMMIT=$(gh pr view "$PR_NUMBER" --json mergeCommit --jq '.mergeCommit.oid // empty') \
      || { MERGE_COMMIT=""; DEPLOY_CAVEAT="could not read the merge commit — the health result may be the previous deploy's"; }
  fi
  if [ -n "${MERGE_COMMIT:-}" ]; then
    # Runs take seconds to register after a merge, so an empty list is "not
    # yet", not "all finished" — same grace as Step 3e's CI wait.
    WAITED=0; RUNS_EMPTY_UNTIL=120
    while [ "$WAITED" -lt 600 ]; do
      if ! RUNS=$(gh run list --commit "$MERGE_COMMIT" --json status 2>&1); then
        # Advisory step: a gh that cannot list runs will not start listing
        # them in ten minutes — probe now rather than sleep out the cap.
        echo "deploy: could not read runs on $MERGE_COMMIT ($RUNS) — probing now"
        DEPLOY_CAVEAT="workflow runs unreadable — the health result may be the previous deploy's"
        break
      fi
      TOTAL=$(printf '%s' "$RUNS" | jq 'length')
      IN_FLIGHT=$(printf '%s' "$RUNS" | jq '[.[] | select(.status != "completed")] | length')
      if [ "$TOTAL" -eq 0 ]; then
        [ "$WAITED" -ge "$RUNS_EMPTY_UNTIL" ] && { echo "deploy: no workflow runs on $MERGE_COMMIT after ${RUNS_EMPTY_UNTIL}s — probing; a HEALTHY result may be the previous deploy's"; break; }
      elif [ "$IN_FLIGHT" -eq 0 ]; then
        break
      fi
      echo "deploy: ${IN_FLIGHT:-0}/${TOTAL} run(s) still in flight on $MERGE_COMMIT — waiting…"
      sleep 30; WAITED=$((WAITED + 30))
    done
    [ "$WAITED" -ge 600 ] && echo "deploy: runs on $MERGE_COMMIT still in flight after 10 minutes — probing anyway; treat a HEALTHY result as the previous deploy's"
  fi
fi
```

A non-empty `DEPLOY_CAVEAT` downgrades a `HEALTHY` result to `UNKNOWN` in the report below, with the caveat as the reason: the probe ran, but not against a deploy this merge is known to have produced.

Dispatch on `$DEPLOY_PLATFORM`:

**`kubernetes`** — read-only cluster health (nodes, pods, deployments, optional ArgoCD):

```bash
kubectl config current-context
kubectl cluster-info --request-timeout=5s
```

If the connection fails, report `Deployment: UNKNOWN (kubectl unreachable)` and stop here — an unreachable cluster is not DEGRADED, and it is not `skipped` either: `skipped` means nothing was configured to check, and wayfare's security items accept that as done.

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
# hero_field returns only the FIRST match; health-endpoint legitimately repeats,
# so this list is read directly.
HEALTH_ENDPOINTS=$(awk -F': ' '/^- health-endpoint:/ {print $2}' "$ROOT/HERO.md" 2>/dev/null `# hero-lint: allow-inline` \
  | tr -d '"' | tr -d "'")

if [ -z "$HEALTH_ENDPOINTS" ]; then
  # A platform declared with nothing to probe is a config gap, not a
  # no-platform repo: report UNKNOWN so it cannot tick a "deployed" DoD line.
  echo "No health endpoint configured for $DEPLOY_PLATFORM — cannot verify."
  DEPLOY_STATUS="UNKNOWN"
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

A platform with no endpoint list is UNKNOWN, not DEGRADED and not skipped — the platform is declared, so something should have been checkable. Otherwise the loop above sets `HEALTHY` (every endpoint returns 2xx) vs `DEGRADED` (any non-2xx response or timeout).

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
- Abandoning mid-flight → `hero-skills:abandon` — restricted, print only.

Skip `hero-skills:one-shot`; it's not the deterministic next action.

## Notes

- The workflow's gates (prior review present, all threads resolved) run **before** Claude is invoked. A failed gate is the cheap path; do not assume Claude is wrong if the verdict comes back fast.
- Auto-approve is one signal among many. Branch protection, CODEOWNERS, and required status checks still apply — `gh pr merge` will fail loudly if any of those block the merge, and that is the correct behavior.
- Re-running `@auto-approve` is safe. The workflow updates the same comment and submits a fresh review, so the PR history shows the latest verdict without duplicates.
- Never use `--admin` to bypass branch protection during merge, even if the user asks. Stop and let them merge manually if protection blocks. And say the useful half out loud: under `enforce_admins: true` the flag does not work anyway, so someone staring at a failed merge is not being denied a shortcut that exists.
- Never merge a PR that has open PRs stacked on its branch without retargeting them first (Step 7a). The failure is silent at merge time and unrecoverable afterward.
