---
name: hero-review-pr
# prettier-ignore
description: Review a pull request and leave inline comments. Analyzes code changes for quality, bugs, security, and style issues. Works with any GitHub repository.
argument-hint: PR_NUMBER_OR_URL
disable-model-invocation: true
---

# Hero Review PR - Review and Comment on Pull Requests

Review someone else's pull request thoroughly and leave constructive inline comments on GitHub.

## Arguments

- `$ARGUMENTS` - PR number, URL, or branch name (required)
  - `123` - PR number
  - `https://github.com/owner/repo/pull/123` - PR URL
  - If omitted: list open PRs and ask user to pick one

## Prerequisites

- `gh` CLI installed and authenticated
- Read access to the repository

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:

- **Repository** → default branch, commit convention
- **Code Quality** → linters, formatters, pre-commit context
- **Code Review Agent** → external review bot info (for context on existing bot reviews)
- **Projects** → language, framework for language-specific review guidance

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults.

### Step 1: Identify the PR

```bash
# If no argument, list open PRs
gh pr list --state open --json number,title,author,headRefName,additions,deletions --limit 20
```

If argument provided, resolve it:

```bash
gh pr view $PR_ARG --json number,title,body,author,headRefName,baseRefName,additions,deletions,files,url,reviewDecision,state
```

**If PR is already merged or closed:** Report status and stop.

### Step 2: Get PR Context

```bash
# Get the full diff
gh pr diff $PR_NUMBER

# Get existing review comments to avoid duplicates
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments --jq '.[] | {path: .path, line: .line, body: .body, user: .user.login}'

# Get commit messages for intent
gh pr view $PR_NUMBER --json commits --jq '.commits[].messageHeadline'
```

Also read the PR description carefully — it often explains design decisions.

### Step 3: Analyze the Diff

Review every changed file in the diff. For each file, assess:

**Correctness**

- Logic errors, off-by-one, null/undefined handling
- Race conditions or concurrency issues
- Edge cases not handled
- API contract mismatches

**Security**

- Injection vulnerabilities (SQL, XSS, command)
- Hardcoded secrets or credentials
- Improper input validation at system boundaries
- Insecure defaults

**Code Quality**

- Naming clarity and consistency
- Dead code, commented-out code, leftover debug statements
- Unnecessary complexity or premature abstraction
- Missing error handling where it matters

**Design**

- Does the approach fit the codebase patterns?
- Are there simpler alternatives?
- Will this be maintainable?

**Tests**

- Are new behaviors covered by tests?
- Do test names describe what they verify?
- Are edge cases tested?

### Step 4: Prepare Comments

For each issue found, classify its severity:

| Severity | Prefix | When to use |
|----------|--------|-------------|
| Critical | `🔴` | Bugs, security issues, data loss risks — must fix |
| Suggestion | `🟡` | Improvements that would meaningfully help — should fix |
| Nit | `🔵 nit:` | Style, naming, minor preferences — take it or leave it |
| Question | `❓` | Clarification needed — not necessarily wrong |
| Praise | `👍` | Good pattern worth calling out — use sparingly |

**Comment guidelines:**

- Be specific: reference the exact code and explain why it's an issue
- Be constructive: suggest a fix or alternative, not just "this is wrong"
- Be respectful: assume the author made reasonable choices given their context
- Avoid duplicating comments already left by others
- Group related issues into a single comment when they affect the same lines
- Don't comment on things that linters/formatters should catch (unless there's no CI)

### Step 5: Submit Review Comments

For each inline comment:

```bash
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  -f body="$COMMENT_BODY" \
  -f commit_id="$COMMIT_SHA" \
  -f path="$FILE_PATH" \
  -f line=$LINE_NUMBER \
  -f side="RIGHT"
```

To get the latest commit SHA:

```bash
gh pr view $PR_NUMBER --json commits --jq '.commits[-1].oid'
```

**Important:** Use `line` (not `original_line`) to comment on the new version of the file. Use `side=RIGHT` for additions/modifications.

For multi-line comments, also include `start_line` and `start_side`:

```bash
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  -f body="$COMMENT_BODY" \
  -f commit_id="$COMMIT_SHA" \
  -f path="$FILE_PATH" \
  -F line=$END_LINE \
  -f side="RIGHT" \
  -F start_line=$START_LINE \
  -f start_side="RIGHT"
```

### Step 6: Submit Overall Review

After all inline comments, submit an overall review:

```bash
gh pr review $PR_NUMBER --comment --body "$(cat <<'EOF'
## Review Summary

**Files reviewed:** N
**Comments:** X critical, Y suggestions, Z nits

### Overall Assessment

[1-3 sentence summary of the PR quality and main concerns]

### Key Findings

- [Most important issue or pattern]
- [Second most important]

### What's Good

- [Positive observations — acknowledge good work]

---
Review by [Claude Code](https://claude.ai/code)
EOF
)"
```

**Review decision guidance:**

- Use `--approve` only if there are no critical or suggestion-level issues
- Use `--request-changes` if there are critical issues that must be fixed
- Use `--comment` (default) for suggestions and nits that don't block merging

### Step 7: Report

```
Hero PR Review Summary
======================
PR: #123 - PR_TITLE
Author: @username
Files: N changed (+A -D)

Comments Left:
  🔴 Critical: X
  🟡 Suggestions: Y
  🔵 Nits: Z
  ❓ Questions: W

Decision: [Comment / Approve / Request Changes]
URL: PR_URL
```

## Large PR Warning

If the diff exceeds 1500 lines or 50 files, warn the user:

```
⚠ This PR is large (N files, +A -D lines).
A thorough review may take a while. Options:
1. Review everything (recommended for critical PRs)
2. Focus on specific files or directories
3. Skip test/generated files
```

## Notes

- Never approve a PR with known critical issues just to be nice
- Don't nitpick style if the project has formatters/linters in CI
- If unsure about a design choice, ask a question rather than asserting it's wrong
- Praise genuinely good patterns — reviews shouldn't be only negative
- Use `gh api` for inline comments (not `gh pr review` which only does top-level)
