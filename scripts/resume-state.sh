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
#   STATE_OK STATE_ERRORS            aggregate health + which sources failed
#
# THE UNKNOWN/ZERO RULE
#
# A failed call produces values indistinguishable from a legitimate clean state:
# AHEAD=0 reads as "nothing to push" whether or not `git fetch` succeeded, and
# SELF_REVIEW_DONE=0 reads as "never reviewed" whether or not the comments call
# worked. Routing on either is how a pipeline skips a step it needed to run, or
# repeats one it didn't.
#
# So a value whose source failed is emitted as the literal string `unknown`,
# never as a number. This puts the uncertainty IN the value: a consumer doing
# `[ "$AHEAD" -eq 0 ]` fails loudly, and a decision table row written as
# `SELF_REVIEW_DONE == 0` cannot match. The guard is structural rather than a
# rule the reader has to remember.
#
# STATE_OK is false if ANY source failed, with STATE_ERRORS naming which. One
# row guarding STATE_OK covers every case, so adding a source later cannot
# silently bypass a guard that enumerated the old ones.
#
# Read-only apart from `git fetch`, which writes local remote-tracking refs.
# Never edits files, branches, or remote state. Always exits 0 — the caller
# inspects STATE_OK.

set -uo pipefail

STATE_ERRORS=""
fail_source() { STATE_ERRORS="${STATE_ERRORS:+$STATE_ERRORS,}$1"; }

emit() { printf '%s=%s\n' "$1" "$(printf '%q' "$2")"; }

HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel 2>/dev/null)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
if ! . "$HERO_LIB" 2>/dev/null; then
  # Emit a well-formed unhealthy state rather than nothing. Emitting nothing
  # left every variable unset in the caller — including STATE_OK, so the guard
  # row could not match and the run proceeded on garbage.
  echo "STATE_OK=false"
  echo "STATE_ERRORS=lib"
  echo "echo 'resume-state: cannot source hero-lib.sh — reinstall the plugin.' >&2"
  exit 0
fi

# ---------- branch context -------------------------------------------------

DEFAULT_BRANCH=$(hero_default_branch)
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)

# Detached HEAD yields an empty branch name, and `gh pr list --head ""` does not
# error — it returns an ARBITRARY open PR. Binding the pipeline to an unrelated
# PR and then routing it toward ship is the worst failure this script can cause.
if [ -z "$CURRENT_BRANCH" ]; then
  fail_source "detached-head"
fi

# jq is a hard dependency for every PR field below. Without it `gh` still
# succeeds, so a GH-only flag reads healthy while every parse yields empty —
# PR_EXISTS=false on a repo with a live PR, which routes to push and opens a
# duplicate.
# Probe that jq WORKS, not merely that it exists on PATH — a jq that is present
# but broken (wrong arch, missing lib, shim on a stripped PATH) passes a
# `command -v` check and then fails every parse, which is the same silent-empty
# outcome as jq being absent.
JQ_OK=true
printf '{}' | jq -e . >/dev/null 2>&1 || { JQ_OK=false; fail_source "jq"; }

FETCH_OK=true
git fetch origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || { FETCH_OK=false; fail_source "fetch"; }

# A successful fetch does NOT imply the ref resolves: in a --single-branch clone
# the refspec only covers the cloned branch, so `git fetch origin main` returns 0
# while origin/main does not exist. AHEAD would then be 0 on a branch carrying a
# full stack of commits.
REF_OK=true
git rev-parse --verify --quiet "origin/$DEFAULT_BRANCH" >/dev/null 2>&1 \
  || { REF_OK=false; fail_source "default-ref"; }

UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

if [ "$FETCH_OK" = true ] && [ "$REF_OK" = true ]; then
  AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
else
  AHEAD=unknown
fi

# UNPUSHED: commits past this branch's own upstream (the PR's head ref) —
# distinct from AHEAD. Someone who pushed once then committed again locally has
# both non-zero, and those follow-ups must reach the PR before any review step.
#
# With no upstream configured (normal before the first push) `git rev-list
# @{u}..HEAD` fails silently and would yield 0 — which routes the user past the
# push step and skips the initial push entirely. Fall back to AHEAD instead.
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  UNPUSHED=$(git rev-list --count '@{u}..HEAD' 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
else
  UNPUSHED=$AHEAD
fi

# ---------- PR state -------------------------------------------------------

PR_EXISTS=unknown
PR_NUMBER=""
PR_STATE=""
PR_IS_DRAFT=""
PR_REVIEW=""
SELF_REVIEW_DONE=unknown
BOT_REPLIED=unknown

if [ "$JQ_OK" = true ] && [ -n "$CURRENT_BRANCH" ]; then
  if PR_LIST=$(gh pr list --head "$CURRENT_BRANCH" \
      --json number,url,isDraft,reviewDecision,state 2>/dev/null); then
    PR_JSON=$(printf '%s' "$PR_LIST" | jq -r '.[0] // empty' 2>/dev/null)
    PR_NUMBER=$(printf '%s' "$PR_JSON" | jq -r '.number // empty' 2>/dev/null)
    PR_STATE=$(printf '%s' "$PR_JSON" | jq -r '.state // empty' 2>/dev/null)
    PR_IS_DRAFT=$(printf '%s' "$PR_JSON" | jq -r '.isDraft // empty' 2>/dev/null)
    PR_REVIEW=$(printf '%s' "$PR_JSON" | jq -r '.reviewDecision // empty' 2>/dev/null)
    if [ -n "$PR_NUMBER" ]; then PR_EXISTS=true; else PR_EXISTS=false; fi
  else
    fail_source "gh-pr-list"
  fi
fi

if [ "$PR_EXISTS" = "false" ]; then
  # No PR means these are genuinely zero, not unknown.
  SELF_REVIEW_DONE=0
  BOT_REPLIED=false
elif [ "$PR_EXISTS" = "true" ]; then
  if COMMENTS=$(gh api "/repos/{owner}/{repo}/issues/$PR_NUMBER/comments" 2>/dev/null); then
    SELF_REVIEW_DONE=$(printf '%s' "$COMMENTS" \
      | jq '[.[] | select(.body | test("ai-hero:self-review"))] | length' 2>/dev/null || echo unknown)

    # BOT_REPLIED is only meaningful if we know who the bot is. Without
    # bot-username configured, a `false` here is indistinguishable from "no
    # reply yet" and await-review waits forever for a reply already posted.
    if BOT_USER=$(hero_field bot-username 2>/dev/null); then
      BOT_COUNT=$(printf '%s' "$COMMENTS" \
        | jq --arg u "$BOT_USER" '[.[] | select(.user.login == $u)] | length' 2>/dev/null || echo 0)
      if [ "${BOT_COUNT:-0}" -gt 0 ]; then BOT_REPLIED=true; else BOT_REPLIED=false; fi
    else
      BOT_REPLIED=unknown
      fail_source "bot-username"
    fi
  else
    fail_source "gh-comments"
  fi
fi

STATE_OK=true
[ -n "$STATE_ERRORS" ] && STATE_OK=false

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
emit STATE_OK         "$STATE_OK"
emit STATE_ERRORS     "$STATE_ERRORS"
