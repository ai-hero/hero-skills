---
name: review-pr
# prettier-ignore
description: Review a PR. No argument reviews your own draft PR and applies fixes. A PR number reviews the author's code and posts inline comments without editing their code.
argument-hint: [#PR] [--no-mark-ready]
disable-model-invocation: true
---

# Review — PR Review

Context-aware PR review. Auto-detects whether you're reviewing your own draft or someone else's PR and runs the right mode.

## Arguments

- `$ARGUMENTS` — Optional PR number or URL, plus optional flags
  - (none) — Auto-detect from current branch → your draft PR → self-review mode
  - `#123` or URL — Your PR: self-review mode. Someone else's PR: review mode (no edits).
  - `--no-mark-ready` — Self-review mode only: run Steps 1–8 (post review, apply fixes, push, post improvements summary, update PR description) but skip Step 9 (the mark-ready prompt + `gh pr ready`). Used by `hero-skills:one-shot` so its DAG can render `self-review` (Step 8) and `mark-ready` (Step 9) as distinct nodes without double-prompting. Combine with a PR number/URL as needed (`#42 --no-mark-ready`).

Parse `$ARGUMENTS` for the flag once at the top of Step 0:

```bash
NO_MARK_READY=false
ARGS_FILTERED=""
for tok in $ARGUMENTS; do
  case "$tok" in
    --no-mark-ready) NO_MARK_READY=true ;;
    *) ARGS_FILTERED="$ARGS_FILTERED $tok" ;;
  esac
done
ARGS_FILTERED=$(printf '%s' "$ARGS_FILTERED" | sed 's/^ //')
# Use $ARGS_FILTERED wherever the existing skill body references $ARGUMENTS
# for the PR identifier (Step 0's `PR_ARG=...awk '{print $1}'` lookup, etc.).
```

## Prerequisites

- `gh` CLI installed and authenticated
- The `pr-review-toolkit` plugin available

## Instructions

### Step 0: Load Configuration and Detect Mode

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` for:

- **Code Quality** → pre-commit (re-run after fixes in self-review mode)
- **Code Review Agent** → bot username (to avoid duplicating its comments)

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with defaults.

Detect the PR and mode:

```bash
BRANCH=$(git branch --show-current)
ME=$(gh api user --jq '.login' 2>/dev/null)

if [ -n "$ARGUMENTS" ]; then
  PR_ARG=$(printf '%s' "$ARGUMENTS" | awk '{print $1}')
  PR_JSON=$(gh pr view "$PR_ARG" --json number,url,headRefName,baseRefName,state,isDraft,author)
else
  PR_JSON=$(gh pr list --head "$BRANCH" --json number,url,headRefName,baseRefName,state,isDraft,author --jq '.[0]')
fi

# When no PR is found, gh pr list --jq '.[0]' returns the literal string "null".
# A subsequent `jq -r '.number'` on that yields "null" too, which would slip past
# the "No PR found" mode-selection check below. Stop explicitly here instead.
if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "null" ]; then
  echo "No PR found for branch '$BRANCH'. Run hero-skills:push-pr first."
  exit 1
fi

PR_NUMBER=$(echo "$PR_JSON" | jq -r '.number')
PR_AUTHOR=$(echo "$PR_JSON" | jq -r '.author.login')
IS_DRAFT=$(echo "$PR_JSON" | jq -r '.isDraft')
PR_BRANCH=$(echo "$PR_JSON" | jq -r '.headRefName')
PR_URL=$(echo "$PR_JSON" | jq -r '.url')
PR_STATE=$(echo "$PR_JSON" | jq -r '.state')
```

**Mode selection:**

| Condition | Mode |
|-----------|------|
| No PR found | STOP — "No PR for '$BRANCH'. Run `hero-skills:push-pr` first." |
| Closed/merged | STOP — Report status. |
| PR author is you AND draft | Self-review mode |
| PR author is you AND not draft | Warn "PR is already ready-for-review — continue self-review? [y/N]" |
| PR author is someone else | Review mode (no edits) |

---

## Self-Review Mode

### Step 1: Ensure on Correct Branch

```bash
CURRENT=$(git branch --show-current)
```

If `CURRENT != PR_BRANCH`, check for uncommitted changes:

```bash
git status --porcelain
```

If uncommitted changes exist, STOP — show what's uncommitted and tell the user to commit or cancel. Never silently stash.

When working tree is clean, switch:

```bash
git fetch origin "$PR_BRANCH"
git checkout "$PR_BRANCH"
git pull origin "$PR_BRANCH"
```

### Step 2: Run All Review Agents in Parallel

Launch all pr-review-toolkit agents simultaneously in a single message:

```
Agent(subagent_type="pr-review-toolkit:code-reviewer", ...)
Agent(subagent_type="pr-review-toolkit:silent-failure-hunter", ...)
Agent(subagent_type="pr-review-toolkit:pr-test-analyzer", ...)
Agent(subagent_type="pr-review-toolkit:comment-analyzer", ...)
Agent(subagent_type="pr-review-toolkit:type-design-analyzer", ...)
```

Wait for all agents to complete, then aggregate findings into: **Critical** (bugs, security, data loss), **Important** (quality, correctness), **Suggestions** (style, polish), **Strengths**.

### Step 3: Post Review Comment

```bash
gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
## Hero Self-Review

### Critical ({N})
- [agent] {file:line} — {finding}

### Important ({N})
- [agent] {file:line} — {finding}

### Suggestions ({N})
- [agent] {file:line} — {finding}

### Strengths
- {what's well-done}

---
Self-review by [Claude Code](https://claude.ai/code)
EOF
)"
```

Omit empty sections.

### Step 4: Ask Permission to Apply Fixes

Show the findings summary and ask:

```
Apply fixes? [Default: all]
1. All (critical + important + suggestions) ← default
2. Only critical + important
3. Only critical
4. Pick individually
5. Skip — leave the comment only
```

Wait for the user's choice. If "individually", walk through each finding yes/no.

### Step 5: Apply Fixes

For each accepted finding:

1. Read the file and surrounding context.
2. Apply the minimal fix — don't refactor surrounding code.
3. Track changed files.
4. If a finding is ambiguous or conflicts with another, stop and ask.

After all fixes:

```bash
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --files "${CHANGED_FILES[@]}"
else
  echo "NO_PRECOMMIT"
fi
```

Fix any pre-commit failures before continuing.

### Step 6: Commit and Push Fixes

```bash
git add "${CHANGED_FILES[@]}"
git commit -m "$(cat <<'EOF'
fix: address self-review findings

- {summary of fix 1}
- {summary of fix 2}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push origin "$PR_BRANCH"
```

Commit logically distinct fixes separately if they touch unrelated areas.

### Step 7: Post Improvements Summary

**Always post this, even when no fixes were applied.** This is the durable record that the review ran.

Render the template with real values — never post literal placeholders. Omit sections whose count is zero.

```bash
gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
## Hero Self-Review Improvements

**Critical (A / X fixed):**
- FILE:LINE — FINDING — FIX_DESCRIPTION

**Important (B / Y fixed):**
- FILE:LINE — FINDING — FIX_DESCRIPTION

**Suggestions (C / Z fixed):**
- FILE:LINE — FINDING — FIX_DESCRIPTION

**Skipped:**
- FILE:LINE — FINDING — REASON

Commits: SHA1, SHA2

---
Applied by [Claude Code](https://claude.ai/code)
EOF
)"
```

If the post fails, surface the rendered body for manual paste — do NOT swallow the error.

### Step 8: Update PR Description if Scope Changed

Update when:

- New files added by fixes weren't in the original description
- Critical fixes changed observable behavior (security, data-loss, correctness)
- Features were removed or defaults changed

Leave unchanged for: style/typo/comment fixes only. Default to update when uncertain.

```bash
gh pr view $PR_NUMBER --json title,body --jq '{title, body}'
```

Draft the full new body preserving structure (Summary, Changesets, Test Plan), then apply:

```bash
gh pr edit $PR_NUMBER --title "NEW_TITLE_UNDER_70_CHARS" --body "$(cat <<'EOF'
DRAFTED_FULL_BODY_HERE
EOF
)"
```

Substitute `DRAFTED_FULL_BODY_HERE` with actual Markdown before running.

### Step 9: Ask to Mark Ready

**Skip this step entirely when `$NO_MARK_READY` is `true`** (caller passed `--no-mark-ready`, typically `hero-skills:one-shot` whose own Step 9 owns the mark-ready gate). In that case, jump straight to Step 10 — the summary will show `PR state: Draft (mark-ready deferred to caller)`.

Otherwise, ask the user:

```
Self-review complete.

Critical fixed: A/X | Important fixed: B/Y | Suggestions fixed: C/Z

Convert draft PR #{number} to ready-for-review? [y/N]
```

Wait for the user's confirmation. Never mark ready without it.

```bash
gh pr ready $PR_NUMBER
```

### Step 10: Summary

```
Self-Review Summary
===================
PR: #{number} - {title}
Branch: {branch}

Findings:
  Critical: X (Y fixed, Z skipped)
  Important: A (B fixed, C skipped)
  Suggestions: D (E fixed, F skipped)

Commits: N pushed
PR description: {updated | left as-is} ({reason})
PR state: {Draft / Ready for review}
URL: {pr-url}

Next steps:
  # If you marked ready: your Code Review Agent (Copilot / CodeRabbit / Greptile)
  # auto-reviews the ready PR — no skill to run, just wait for its first comment.
  # Skipped entirely if HERO.md has agent: none.
  hero-skills:respond-to-comments   # address the bot's inline comments
  hero-skills:ship-pr               # @auto-approve, merge, reset (jump here directly if `agent: none`)
  # If you declined mark-ready, address findings and re-run hero-skills:review-pr.
```

---

## Review Mode (Someone Else's PR)

### Step 1: Get PR Context

`OWNER`, `REPO`, `PR_NUMBER`, `HEAD_SHA` from Step 0 detection.

```bash
gh pr diff $PR_NUMBER
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --jq '.[] | {path: .path, line: .line, body: .body, user: .user.login}'
gh pr view $PR_NUMBER --json commits --jq '.commits[].messageHeadline'
```

Read the PR description carefully — it explains design decisions.

If diff exceeds 1500 lines or 50 files, warn and ask to focus on specific paths.

### Step 2: Run All Review Agents in Parallel

Same as self-review Step 2: launch all five pr-review-toolkit agents simultaneously and aggregate findings.

### Step 3: Post Inline Comments

Map severity to prefix:

| Category | Prefix |
|----------|--------|
| Critical | `🔴` |
| Important | `🟡` |
| Suggestion | `🔵 nit:` |
| Question | `❓` |
| Strength | `👍` |

Comment guidelines: be specific, constructive, respectful. Skip findings already raised by others. Skip nits the linter catches.

```bash
OWNER=$(echo "$PR_URL" | awk -F/ '{print $4}')
REPO=$(echo "$PR_URL" | awk -F/ '{print $5}')
HEAD_SHA=$(gh pr view "$PR_NUMBER" --json commits --jq '.commits[-1].oid')

gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  -f body="$COMMENT_BODY" \
  -f commit_id="$HEAD_SHA" \
  -f path="$FILE_PATH" \
  -F line=$LINE_NUMBER \
  -f side="RIGHT"
```

For multi-line: also pass `-F start_line=$START_LINE -f start_side="RIGHT"`.

### Step 4: Submit Overall Review

| Has criticals? | Has importants? | Decision |
|----------------|-----------------|----------|
| Yes | — | `--request-changes` |
| No | Yes | `--comment` |
| No | No | `--approve` (unless questions remain) |

```bash
gh pr review $PR_NUMBER {DECISION_FLAG} --body "$(cat <<'EOF'
## Review Summary

**Findings:** {X} critical, {Y} important, {Z} suggestions

### Overall Assessment
{1-3 sentence summary}

### Key Findings
- {most important issue}
- {second most important}

### What's Good
- {positive observations}

---
Review by [Claude Code](https://claude.ai/code)
EOF
)"
```

### Step 5: Report

```
Review Summary
==============
PR: #{number} - {title}
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

- Never edit code in review mode — only post comments.
- Never mark a PR ready without explicit user confirmation.
- Do not auto-resolve other reviewers' comments.
