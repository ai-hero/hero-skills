---
name: hero-pr-respond
# prettier-ignore
description: Read PR review comments, fix the code issues they raise, and resolve the conversations on GitHub. Handles the full respond-to-feedback cycle.
argument-hint: [pr-number]
disable-model-invocation: true
---

# Hero PR Respond - Fix Issues and Resolve PR Comments

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
1. Stash changes (saved as "hero-pr-respond: WIP on $CURRENT") — will NOT auto-restore since you're moving to a different branch
2. Cancel — go back and commit or handle changes first
```

**STOP and wait for user to choose.** Do NOT switch branches without explicit confirmation.

**If user chooses option 1 (stash):**

```bash
git stash push -m "hero-pr-respond: WIP on $CURRENT"
```

Report: `Stashed as: stash@{0} — "hero-pr-respond: WIP on $CURRENT". Restore later with: git checkout $CURRENT && git stash pop`

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
git add <changed-files>
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
Hero PR Respond Summary
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

## Notes

- Always ask the user before making changes — don't blindly follow every review comment
- Some comments may conflict with each other; flag these to the user
- If a reviewer's suggestion would introduce a bug or regression, explain why to the user
- Never force-push unless the user explicitly requests it
- Reply to comments before resolving them so reviewers see what changed
- If the PR has many comments, work through them file-by-file for efficiency
