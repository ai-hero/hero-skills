---
name: hero-respond-to-pr
# prettier-ignore
description: Read PR review comments, fix the code issues they raise, and resolve the conversations on GitHub. Handles the full respond-to-feedback cycle.
argument-hint: [pr-number]
disable-model-invocation: true
---

# Hero Respond to PR - Fix Issues and Resolve PR Comments

Read review comments on your pull request, update the code to address them, and resolve the conversations on GitHub.

## Arguments

- `$ARGUMENTS` - PR number or URL (optional)
  - If omitted: auto-detect from current branch

## Prerequisites

- `gh` CLI installed and authenticated
- Write access to the repository
- On the PR's feature branch (or will checkout)

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → commit convention
- **Code Quality** → linters, formatters, pre-commit
- **Code Review Agent** → agent name, trigger method, poll method, bot username (for review loop)

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Identify the PR

If no argument provided, detect from current branch:

```bash
BRANCH=$(git branch --show-current)
gh pr list --head "$BRANCH" --json number,title,url,headRefName --jq '.[0]'
```

If argument provided:

```bash
gh pr view $PR_ARG --json number,title,url,headRefName,baseRefName,state
```

**If PR is merged or closed:** Report status and stop.

### Step 2: Ensure on Correct Branch

```bash
CURRENT=$(git branch --show-current)
PR_BRANCH=$(gh pr view $PR_NUMBER --json headRefName --jq '.headRefName')
```

If not on the PR branch, first check for uncommitted changes:

```bash
git status --porcelain
```

**If uncommitted changes exist, STOP and show:**

```
You have uncommitted changes on '$CURRENT':

  (list changed files from git status)

Need to switch to '$PR_BRANCH' to address PR comments.

Options:
1. Stash changes (saved as "hero-respond-to-pr: WIP on $CURRENT") — will NOT auto-restore since you're moving to a different branch
2. Cancel — go back and commit or handle changes first
```

**STOP and wait for user to choose.** Do NOT switch branches without explicit confirmation.

**If user chooses option 1 (stash):**

```bash
git stash push -m "hero-respond-to-pr: WIP on $CURRENT"
```

Report: `Stashed as: stash@{0} — "hero-respond-to-pr: WIP on $CURRENT". Restore later with: git checkout $CURRENT && git stash pop`

Note: Since the user is switching to a different branch to do PR work, do NOT auto-pop the stash. Remind the user in the final summary how to restore.

**Then switch to the PR branch:**

```bash
git fetch origin $PR_BRANCH
git checkout $PR_BRANCH
git pull origin $PR_BRANCH
```

### Step 3: Fetch All Review Comments

```bash
# Get pending (unresolved) review comments
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  --jq '.[] | {
    id: .id,
    node_id: .node_id,
    path: .path,
    line: .line,
    original_line: .original_line,
    body: .body,
    user: .user.login,
    in_reply_to_id: .in_reply_to_id,
    created_at: .created_at
  }'

# Get review threads to check which are resolved
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 10) {
              nodes {
                id
                databaseId
                body
                path
                line
                author { login }
              }
            }
          }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER
```

### Step 4: Categorize Comments

Group comments into:

1. **Actionable** — code changes requested (bugs, improvements, missing handling)
2. **Questions** — clarification needed, may or may not need code changes
3. **Acknowledged** — nits, praise, or FYI comments that need no code change
4. **Already resolved** — threads already marked resolved

**Skip already-resolved threads.** Focus on unresolved ones.

Present the categorized list to the user:

```
PR #123 Review Comments
=======================
Unresolved: N comments in M threads

Actionable (will fix):
  1. [file.ts:42] @reviewer - "Handle the null case here"
  2. [api.ts:15] @reviewer - "This should validate input before..."

Questions (need your input):
  3. [utils.ts:88] @reviewer - "Why not use the existing helper?"

Acknowledged (no code change needed):
  4. [README.md:5] @reviewer - "Nice docs 👍"

Already resolved: K threads
```

Ask the user to confirm the plan before proceeding. The user may:

- Agree with all actionable items
- Disagree with specific comments (skip those)
- Provide answers to questions
- Reclassify comments

### Step 5: Fix Code Issues

For each confirmed actionable comment:

1. Read the relevant file and surrounding context
2. Understand what the reviewer is asking for
3. Make the code change

```bash
# Read the file context around the commented line
# (Use Read tool for the file, centered on the line number)
```

Apply fixes one at a time. After each fix, verify the change makes sense in context.

**If a comment is ambiguous:** Ask the user for clarification rather than guessing.

### Step 6: Run Quality Checks

After all fixes are applied:

```bash
# Run pre-commit if available
which pre-commit && pre-commit run --all-files || echo "NO_PRECOMMIT"

# Run tests if configured in HERO.md
# Use the test command from HERO.md projects section
```

If checks fail, fix the issues before committing.

### Step 7: Commit the Fixes

```bash
git add CHANGED_FILES
git commit -m "$(cat <<'EOF'
fix: address PR review feedback

- [Summary of fix 1]
- [Summary of fix 2]

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Group related fixes into a single commit. If fixes are logically independent and touch different areas, use separate commits.

### Step 8: Push Changes

```bash
git push origin $(git branch --show-current)
```

### Step 9: Reply to and Resolve Comments

For each addressed comment, reply with what was done and resolve the thread:

```bash
# Reply to the comment explaining the fix
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  -f body="Fixed — [brief description of what changed]" \
  -F in_reply_to=$COMMENT_ID

# Resolve the thread via GraphQL
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId="$THREAD_NODE_ID"
```

For question comments where the user provided an answer:

```bash
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  -f body="[User's explanation or rationale]" \
  -F in_reply_to=$COMMENT_ID
```

For acknowledged comments (praise, FYI):

```bash
# Just resolve, no reply needed unless user wants to respond
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId="$THREAD_NODE_ID"
```

### Step 10: Summary

```
Hero Respond to PR Summary
=======================
PR: #{number} - {pr-title}
Branch: {pr-branch}

Comments Addressed:
  Fixed: X (code changes made)
  Replied: Y (questions answered)
  Acknowledged: Z (resolved without changes)
  Skipped: W (user chose to skip)

Commits: N new commits pushed
Threads Resolved: M of T

Remaining unresolved: [list any, if applicable]

URL: {pr-url}
```

**If changes were stashed in Step 2, remind the user:**

```
Note: You have stashed changes from {original-branch}.
To restore: git checkout {original-branch} && git stash pop
```

### Step 11: Review Loop (when Code Review Agent is configured)

After completing the initial respond cycle (Steps 3-10), check if `HERO.md` has a **Code Review Agent** configured (agent is not `none`). If so, and the user passed `--loop` or confirms they want to loop, enter the iterative review loop.

**Skip this step entirely if:**

- No Code Review Agent is configured in HERO.md
- The user explicitly declines the loop

#### Loop Setup

```bash
ITERATION=1
MAX_ITERATIONS=5
REVIEW_AGENT=$(grep '^\- agent:' "$ROOT/HERO.md" | sed 's/- agent: //' | head -1)
TRIGGER=$(grep '^\- trigger:' "$ROOT/HERO.md" | sed 's/- trigger: //' | head -1)
POLL_METHOD=$(grep '^\- poll-method:' "$ROOT/HERO.md" | sed 's/- poll-method: //' | head -1)
```

Report to user:

```
Review Loop enabled (agent: REVIEW_AGENT, max iterations: 5)
Starting iteration 1...
```

#### Loop Body (repeat until exit condition)

**11a. Trigger external review**

Trigger depends on the configured method:

- **Comment trigger** (e.g., Greptile): Post a comment on the PR

  ```bash
  gh pr comment $PR_NUMBER --body "TRIGGER_TEXT"
  ```

- **Label trigger** (e.g., some CodeRabbit setups): Add a label

  ```bash
  gh pr edit $PR_NUMBER --add-label "TRIGGER_LABEL"
  ```

- **Auto on push**: No action needed — the push from Step 8 already triggers it

**11b. Poll for review completion**

Poll every 30 seconds based on configured `poll-method`:

- **check-runs**: Wait for the review agent's check run to complete

  ```bash
  gh api repos/OWNER/REPO/commits/HEAD_SHA/check-runs \
    --jq '.check_runs[] | select(.app.slug == "AGENT_SLUG") | {status: .status, conclusion: .conclusion}'
  ```

- **comments**: Wait for a new comment from the review agent bot

  ```bash
  gh api repos/OWNER/REPO/pulls/$PR_NUMBER/comments \
    --jq '[.[] | select(.user.login == "AGENT_BOT_USERNAME")] | last | {id: .id, created_at: .created_at, body: .body}'
  ```

- **pipeline-status**: Wait for pipeline job to finish

  ```bash
  gh api repos/OWNER/REPO/actions/runs?head_sha=HEAD_SHA \
    --jq '.workflow_runs[] | select(.name | contains("AGENT_NAME")) | {status: .status, conclusion: .conclusion}'
  ```

**Timeout:** If no result after 5 minutes of polling, report timeout and ask user whether to retry or exit the loop.

**11c. Parse results**

After the external review completes:

```bash
# Count unresolved review threads from the agent
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 10) {
              nodes {
                body
                author { login }
              }
            }
          }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER
```

Filter for threads authored by the review agent bot that are unresolved. Count them.

If the agent provides a confidence score (e.g., `5/5` in PR description or comment), extract it.

**11d. Check exit conditions**

Exit the loop if ANY of these are true:

- Zero unresolved comments from the review agent
- Confidence score is perfect (e.g., `5/5`)
- Iteration count >= MAX_ITERATIONS (5)

If exiting due to max iterations with remaining issues, warn the user:

```
Review loop reached maximum iterations (5).
Remaining unresolved comments: N
Manual review may be needed for the remaining items.
```

**11e. Fix, commit, push, resolve**

If not exiting, repeat the respond cycle for the new comments:

1. Categorize the agent's new comments (same as Step 4)
2. Present to user for confirmation
3. Fix actionable items (same as Step 5)
4. Run quality checks (same as Step 6)
5. Commit fixes (same as Step 7)
6. Push (same as Step 8)
7. Reply to and resolve addressed threads (same as Step 9)

Increment iteration counter and loop back to 11a.

**11f. Loop summary**

After exiting the loop, report:

```
Review Loop Complete
====================
Agent: REVIEW_AGENT
Iterations: N of MAX_ITERATIONS
Total comments addressed: X
Total commits: Y

Per-iteration breakdown:
  Iteration 1: A comments fixed, B resolved
  Iteration 2: C comments fixed, D resolved
  ...

Final status: [Clean / N unresolved comments remain]
URL: PR_URL
```

## Notes

- Always ask the user before making changes — don't blindly follow every review comment
- Some comments may conflict with each other; flag these to the user
- If a reviewer's suggestion would introduce a bug or regression, explain why to the user
- Never force-push unless the user explicitly requests it
- Reply to comments before resolving them so reviewers see what changed
- If the PR has many comments, work through them file-by-file for efficiency
