---
name: hero-review-pr
# prettier-ignore
description: Review someone else's PR. Runs pr-review-toolkit:review-pr, posts findings as inline comments, submits an overall review (comment/approve/request-changes). Same engine as /hero-self-review, no edits.
argument-hint: PR_NUMBER_OR_URL
disable-model-invocation: true
---

# Hero Review PR - Review Someone Else's PR

Same engine as `/hero-self-review`, different output:

| Skill | Used for | After review |
|-------|----------|--------------|
| `/hero-self-review` | Your own draft PR | Apply fixes, push, then mark ready |
| `/hero-review-pr` | Someone else's PR | Post inline comments and submit a review (comment / approve / request-changes). **Never edits their code.** |

## Arguments

- `$ARGUMENTS` - PR number, URL, or branch name
  - `123` - PR number
  - `https://github.com/owner/repo/pull/123` - PR URL
  - If omitted: list open PRs and ask the user to pick one

## Prerequisites

- `gh` CLI installed and authenticated
- Read access to the repository
- The `pr-review-toolkit` plugin available (provides `/pr-review-toolkit:review-pr`)

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Code Quality** → linters/formatters in CI, so the review doesn't duplicate them
- **Code Review Agent** → bot username, to avoid duplicating that bot's existing PR comments

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Identify the PR

Resolve `PR_ARG` from `$ARGUMENTS`. If empty, list open PRs and **stop** until the user picks one — do not silently fall through with `PR_ARG=""`, which would make every later `gh pr view` call ambiguous:

```bash
PR_ARG=$(printf '%s' "$ARGUMENTS" | awk '{print $1}')

if [ -z "$PR_ARG" ]; then
  echo "No PR specified. Open PRs:"
  gh pr list --state open --json number,title,author,headRefName,additions,deletions --limit 20
  echo ""
  echo "Re-run with /hero-review-pr <number|url|branch>"
  exit 1
fi
```

Resolve the argument and capture all derived identifiers in one block. `OWNER`/`REPO`/`HEAD_SHA` are needed by Step 2's `gh api` calls and by the inline-comment APIs in Step 6, so capture them here once:

```bash
PR_JSON=$(gh pr view "$PR_ARG" --json number,title,body,author,headRefName,baseRefName,additions,deletions,files,url,reviewDecision,state,isDraft,headRepository,headRepositoryOwner)
PR_NUMBER=$(echo "$PR_JSON" | jq -r '.number')
PR_URL=$(echo "$PR_JSON" | jq -r '.url')
PR_STATE=$(echo "$PR_JSON" | jq -r '.state')

# OWNER/REPO of the *base* repo (where the PR lives) — comments and
# reviews go here, even for cross-fork PRs. Derive from the URL so
# this works for forked-PR reviews too.
OWNER=$(echo "$PR_URL" | awk -F/ '{print $4}')
REPO=$(echo "$PR_URL" | awk -F/ '{print $5}')

HEAD_SHA=$(gh pr view "$PR_NUMBER" --json commits --jq '.commits[-1].oid')
```

**If `PR_STATE` is `MERGED` or `CLOSED`:** Report status and stop.

### Step 2: Get PR Context

Read the PR description carefully — it often explains design decisions you'd otherwise flag.

`OWNER`, `REPO`, `PR_NUMBER`, `HEAD_SHA` were captured in Step 1 — reuse them rather than re-querying.

```bash
gh pr diff $PR_NUMBER

# Existing review comments (avoid duplicating)
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --jq '.[] | {path: .path, line: .line, body: .body, user: .user.login}'

# Commit messages for intent
gh pr view $PR_NUMBER --json commits --jq '.commits[].messageHeadline'
```

#### Large PR check

```bash
ADDITIONS=$(gh pr view $PR_NUMBER --json additions --jq '.additions')
FILES=$(gh pr view $PR_NUMBER --json files --jq '.files | length')
```

If the diff exceeds 1500 lines or 50 files, warn the user and ask whether to review everything, focus on specific paths, or skip generated/test files.

### Step 3: Run the pr-review-toolkit Review

The review skill analyzes the diff fetched in Step 2 — no local checkout is required for review-only mode. Skip the checkout block below if you only need the diff.

If you do need a local checkout (e.g., to run the project's tests against the PR), first verify the working tree is clean:

```bash
git status --porcelain
```

**If uncommitted changes exist, STOP** and ask the user to commit or cancel — never silently switch branches.

```bash
gh pr checkout $PR_NUMBER
```

Invoke the `pr-review-toolkit` review skill:

```
Skill(skill="pr-review-toolkit:review-pr", args="all")
```

The skill returns findings categorized as:

- **Critical** — must fix before merge (bugs, security, data loss)
- **Important** — should fix (significant quality, design, or correctness concerns)
- **Suggestions** — nice to have (style, polish, alternatives)
- **Strengths** — what's well-done

If the skill is unavailable, fall back to running the equivalent agents directly:

```
Agent(subagent_type="pr-review-toolkit:code-reviewer", ...)
Agent(subagent_type="pr-review-toolkit:silent-failure-hunter", ...)
Agent(subagent_type="pr-review-toolkit:pr-test-analyzer", ...)
```

Aggregate the findings.

### Step 4: Post Inline Review Comments

Map each finding to a severity prefix the author can scan quickly:

| Finding category | Prefix | When |
|------------------|--------|------|
| Critical | `🔴` | Bugs, security, data loss — must fix |
| Important | `🟡` | Should fix — meaningfully helps quality or correctness |
| Suggestion | `🔵 nit:` | Style, naming, minor preferences — optional |
| Question | `❓` | Clarification needed |
| Strength | `👍` | Worth calling out — use sparingly |

Comment guidelines:

- Be specific: reference the exact code and explain why.
- Be constructive: suggest a fix, not just "this is wrong."
- Be respectful: assume the author made reasonable choices.
- Skip findings already raised by other reviewers (Step 2 fetched them).
- Skip nits the linter/formatter would catch if CI is configured.
- Group related issues into a single comment when they share lines.

For each finding, post an inline comment via the GitHub API. Use `line` (not `original_line`) to comment on the new version of the file, and `side=RIGHT` for additions/modifications:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  -f body="$COMMENT_BODY" \
  -f commit_id="$HEAD_SHA" \
  -f path="$FILE_PATH" \
  -F line=$LINE_NUMBER \
  -f side="RIGHT"
```

For multi-line comments, also pass `-F start_line=$START_LINE -f start_side="RIGHT"`.

### Step 5: Submit the Overall Review

Decide the review type based on the findings:

| Has criticals? | Has importants? | Decision |
|----------------|-----------------|----------|
| Yes | — | `--request-changes` |
| No | Yes | `--comment` |
| No | No | `--approve` (only if no question/clarification needed) |

```bash
gh pr review $PR_NUMBER {DECISION_FLAG} --body "$(cat <<'EOF'
## Review Summary

Generated by `/hero-review-pr` using the `pr-review-toolkit` review skill.

**Findings:** {X} critical, {Y} important, {Z} suggestions

### Overall Assessment

{1-3 sentence summary of the PR quality and main concerns}

### Key Findings

- {Most important issue or pattern}
- {Second most important}

### What's Good

- {Positive observations}

---
Review by [Claude Code](https://claude.ai/code)
EOF
)"
```

Where `{DECISION_FLAG}` is `--comment`, `--approve`, or `--request-changes` per the table above.

### Step 6: Report

```
Hero PR Review Summary
======================
PR: #{number} - {pr-title}
Author: @{username}
Files: {N} changed (+A -D)

Findings:
  🔴 Critical: {X}
  🟡 Important: {Y}
  🔵 Suggestions: {Z}
  ❓ Questions: {W}

Inline comments posted: {N}
Decision: {Comment / Approve / Request Changes}
URL: {pr-url}
```

## Notes

- This skill is for **someone else's** PR — to self-review your own draft PR, use `/hero-self-review`.
- Never edit the author's code — this skill only posts review comments.
- Use `gh api .../pulls/.../comments` for inline comments (`gh pr review` only posts top-level).
