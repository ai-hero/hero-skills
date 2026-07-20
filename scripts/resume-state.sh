#!/usr/bin/env bash
# resume-state.sh — gather the git/PR state one-shot needs to pick a resume point.
#
# Prints shell-eval-able KEY=VALUE lines describing where the current branch
# sits in the pipeline. one-shot's Step 0.5 maps these onto a resume step; this
# script makes no routing decision itself, so the decision table stays in
# SKILL.md where a reader can see it.
#
# Usage:
#   eval "$(scripts/resume-state.sh)"
#
# Emits:
#   DEFAULT_BRANCH, CURRENT_BRANCH   branch context
#   UNCOMMITTED                      count of dirty files
#   AHEAD                            commits past origin/DEFAULT_BRANCH
#   UNPUSHED                         commits past the branch's own upstream
#   PR_EXISTS PR_NUMBER PR_STATE PR_IS_DRAFT PR_REVIEW
#   SELF_REVIEW_DONE BOT_REPLIED
#   FETCH_OK GH_OK COMMENTS_OK       false when the underlying call failed
#
# The *_OK flags exist because a failed fetch or API call silently produces
# values indistinguishable from a legitimate clean state — AHEAD=0 reads as
# "nothing to push" whether the fetch succeeded or not. Callers must refuse to
# route on a false flag rather than trusting the derived values.
#
# Read-only. Never edits files, branches, or remote state. Always exits 0; the
# caller inspects the flags.

set -uo pipefail

HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel 2>/dev/null)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB" 2>/dev/null || { echo "echo 'ERROR: cannot source hero-lib.sh'"; exit 0; }

emit() { printf '%s=%s\n' "$1" "$(printf '%q' "$2")"; }

DEFAULT_BRANCH=$(hero_default_branch)
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)

FETCH_OK=true
git fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || FETCH_OK=false

UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

# AHEAD: commits past origin/DEFAULT_BRANCH on the current branch.
AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)

# UNPUSHED: commits past this branch's own upstream (the PR's head ref) —
# distinct from AHEAD. Someone who pushed once then committed again locally has
# AHEAD>0 AND UNPUSHED>0, and those follow-ups must reach the PR before any
# review/respond/ship step runs.
#
# With no upstream configured (normal before the first push) `git rev-list
# @{u}..HEAD` fails silently and would yield 0 — which routes the user past the
# push step and skips the initial push entirely. Fall back to AHEAD instead.
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  UNPUSHED=$(git rev-list --count '@{u}..HEAD' 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
else
  UNPUSHED=$AHEAD
fi

# `gh pr list` prints "[]" both when no PR exists and when the call fails —
# check the exit status separately so an API blip can't masquerade as "no PR".
GH_OK=true
if ! PR_LIST=$(gh pr list --head "$CURRENT_BRANCH" \
  --json number,url,isDraft,reviewDecision,state 2>/dev/null); then
  GH_OK=false
  PR_LIST="[]"
fi

PR_JSON=$(printf '%s' "$PR_LIST" | jq -r '.[0] // empty' 2>/dev/null)
PR_NUMBER=$(printf '%s' "$PR_JSON" | jq -r '.number // empty' 2>/dev/null)
PR_STATE=$(printf '%s' "$PR_JSON" | jq -r '.state // empty' 2>/dev/null)
PR_IS_DRAFT=$(printf '%s' "$PR_JSON" | jq -r '.isDraft // empty' 2>/dev/null)
PR_REVIEW=$(printf '%s' "$PR_JSON" | jq -r '.reviewDecision // empty' 2>/dev/null)

PR_EXISTS=false
[ -n "$PR_NUMBER" ] && PR_EXISTS=true

# Durable self-review marker, plus whether the configured review bot replied.
SELF_REVIEW_DONE=0
BOT_REPLIED=false
COMMENTS_OK=true
if [ "$PR_EXISTS" = "true" ]; then
  if ! COMMENTS=$(gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" 2>/dev/null); then
    COMMENTS_OK=false
  else
    SELF_REVIEW_DONE=$(printf '%s' "$COMMENTS" \
      | jq '[.[] | select(.body | test("ai-hero:self-review"))] | length' 2>/dev/null || echo 0)
    BOT_USER=$(hero_field bot-username || true)
    if [ -n "$BOT_USER" ]; then
      BOT_COUNT=$(printf '%s' "$COMMENTS" \
        | jq --arg u "$BOT_USER" '[.[] | select(.user.login == $u)] | length' 2>/dev/null || echo 0)
      [ "${BOT_COUNT:-0}" -gt 0 ] && BOT_REPLIED=true
    fi
  fi
fi

emit DEFAULT_BRANCH   "$DEFAULT_BRANCH"
emit CURRENT_BRANCH   "$CURRENT_BRANCH"
emit UNCOMMITTED      "$UNCOMMITTED"
emit AHEAD            "$AHEAD"
emit UNPUSHED         "$UNPUSHED"
emit PR_EXISTS        "$PR_EXISTS"
emit PR_NUMBER        "$PR_NUMBER"
emit PR_STATE         "$PR_STATE"
emit PR_IS_DRAFT      "$PR_IS_DRAFT"
emit PR_REVIEW        "$PR_REVIEW"
emit SELF_REVIEW_DONE "$SELF_REVIEW_DONE"
emit BOT_REPLIED      "$BOT_REPLIED"
emit FETCH_OK         "$FETCH_OK"
emit GH_OK            "$GH_OK"
emit COMMENTS_OK      "$COMMENTS_OK"
