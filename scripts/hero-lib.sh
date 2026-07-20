#!/usr/bin/env bash
# hero-lib.sh — shared helpers for hero-skills.
#
# Sourced by skills, not executed. Every function here exists because the same
# logic was previously inlined in three or more SKILL.md files and had already
# drifted between copies (see git history for the branch-naming divergence that
# prompted this). If you find yourself pasting the same awk/grep into a second
# skill, it belongs here instead.
#
# Usage from a skill:
#
#   HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
#   [ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
#   # shellcheck source=/dev/null
#   . "$HERO_LIB"
#
# All functions are read-only except hero_exclude_add. None of them exit the
# calling shell; they return non-zero and print to stderr so the caller decides
# whether a failure is fatal.

# ---------- repo + config --------------------------------------------------

# Absolute path to the repo root, or the cwd when not in a git repo.
hero_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Read a single `- key: value` field from HERO.md.
#   hero_field default-branch
#   hero_field bot-username
# Prints the value (trimmed, comments stripped) or nothing. Returns 1 if the
# field is absent so callers can distinguish "missing" from "set to empty" —
# a distinction that matters for fields whose fallback is destructive.
hero_field() {
  local key root value
  key="$1"
  root="${2:-$(hero_root)}"
  [ -r "$root/HERO.md" ] || return 1
  value=$(awk -v k="- $key" '
    index($0, k ":") == 1 { sub(/^[^:]*: */, ""); sub(/ *#.*/, ""); print; exit }
  ' "$root/HERO.md")
  # Strip surrounding whitespace and any stray quotes.
  value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^["'"'"']//' -e 's/["'"'"']$//')
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}

# The repo's default branch per HERO.md, falling back to `main`.
#
# The fallback is silent by design at the call sites that only *read* (a diff
# base, a log range). Call sites that branch, merge, or open a PR against it
# should use hero_default_branch_verbose so a missing/mistyped HERO.md field
# can't silently target the wrong branch.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_default_branch() {
  hero_field default-branch "$@" || printf 'main'
}

# Same, but reports where the value came from on stderr. Use before any
# destructive or outward-facing operation.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_default_branch_verbose() {
  local b
  if b=$(hero_field default-branch "$@"); then
    printf '%s' "$b"
    echo "default branch: $b (from HERO.md)" >&2
  else
    printf 'main'
    echo "default branch: main (fallback — HERO.md default-branch not found)" >&2
  fi
}

# Advisory staleness hint: warn when HERO.md is older than the config files
# that shape it. Prints one note and always returns 0 — never blocks.
#
# This is the deliberate *fast subset* of scripts/check-hero-staleness.sh that
# the daily-flow skills (push-pr, one-shot) want at Step 0. The two are meant
# to stay roughly aligned but not identical: the standalone script can carry a
# longer pattern list without forcing this one to match. What it should NOT be
# is two hand-maintained copies of the same subset, which is what it was.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_check_staleness() {
  local root hero_time config_time
  root="${1:-$(hero_root)}"
  [ -r "$root/HERO.md" ] || return 0
  hero_time=$(git -C "$root" log -1 --format=%ct -- HERO.md 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
  config_time=$(git -C "$root" log -1 --format=%ct -- \
    pyproject.toml ':(glob)**/pyproject.toml' \
    package.json ':(glob)**/package.json' \
    go.mod ':(glob)**/go.mod' \
    Cargo.toml ':(glob)**/Cargo.toml' \
    .github/workflows .pre-commit-config.yaml \
    CLAUDE.md Makefile justfile Taskfile.yml 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
  if [ "${config_time:-0}" -gt "${hero_time:-0}" ]; then
    echo "note: HERO.md may be out of date — run hero-skills:init-hero --update to refresh."
  fi
  return 0
}

# ---------- repo-local ignore ----------------------------------------------

# Path to .git/info/exclude, resolved through git so worktrees, bare repos,
# and non-default gitdirs all work. We use info/exclude rather than .gitignore
# so adding an ignore never dirties a tracked file.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_exclude_path() {
  local root exclude
  root="${1:-$(hero_root)}"
  exclude=$(git -C "$root" rev-parse --git-path info/exclude 2>/dev/null) || return 1
  case "$exclude" in
    /*) ;;
    *)  exclude="$root/$exclude" ;;
  esac
  printf '%s' "$exclude"
}

# Idempotently add one or more entries to .git/info/exclude.
#   hero_exclude_add my-work/ .test-output/
hero_exclude_add() {
  local exclude entry
  exclude=$(hero_exclude_path) || {
    echo "hero_exclude_add: not a git repo" >&2
    return 1
  }
  mkdir -p "$(dirname "$exclude")" || return 1
  for entry in "$@"; do
    grep -qxF "$entry" "$exclude" 2>/dev/null \
      || printf '\n%s\n' "$entry" >> "$exclude"
  done
}

# ---------- the my-work store ----------------------------------------------

# Absolute path to the work-item store, created and git-ignored on first use.
#
# One-time migration: the store was formerly `plan-work/`. Move a legacy store
# rather than orphaning its items behind the new name.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_work_store() {
  local root store
  root="${1:-$(hero_root)}"
  store="$root/my-work"
  if [ -d "$root/plan-work" ] && [ ! -d "$store" ]; then
    mv "$root/plan-work" "$store"
    echo "Migrated legacy plan-work/ store to my-work/." >&2
  fi
  mkdir -p "$store" || return 1
  # Keep both names excluded through the transition so a not-yet-migrated
  # legacy store is never accidentally committed either.
  hero_exclude_add my-work/ plan-work/
  printf '%s' "$store"
}

# Read a frontmatter scalar from a work-item, stripping trailing comments.
hero_item_field() {
  awk -F': ' -v k="$2" '
    $1 == k { v = $2; sub(/ *#.*/, "", v); gsub(/^[[:space:]]+|[[:space:]]+$/, "", v); print v; exit }
  ' "$1"
}

# Print every work-item as "READY <file> — <title>" or "blocked <file> — <title>".
#
# An item is ready when its status is not `done` and every id in depends_on
# points at an item that IS done. This is the Beads `ready` primitive without a
# database. Ids are normalized to base-10 so `007` and `7` compare equal.
#
# NOTE: readiness is a claim about dependencies, not about the codebase. An
# item stays READY after its work lands until someone marks it done — consumers
# must verify against the repo before acting. See one-shot Step 1c.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_ready_items() {
  local store f d deps ready title done_ids
  store="${1:-$(hero_work_store)}"
  cd "$store" 2>/dev/null || { echo "no my-work/ yet"; return 0; }

  done_ids=" "
  for f in *.md; do
    [ -e "$f" ] || continue
    [ "$(hero_item_field "$f" status)" = "done" ] \
      && done_ids="$done_ids$((10#$(hero_item_field "$f" id))) "
  done

  for f in *.md; do
    [ -e "$f" ] || continue
    [ "$(hero_item_field "$f" status)" = "done" ] && continue
    deps=$(awk -F': ' '/^depends_on:/ { v = $2; sub(/ *#.*/, "", v); gsub(/[][, ]+/, "\n", v); print v; exit }' "$f")
    ready=1
    # Heredoc keeps the loop in the current shell (so `ready` persists) and
    # works under both bash and zsh, which does not word-split unquoted vars.
    while IFS= read -r d; do
      [ -z "$d" ] && continue
      case "$done_ids" in *" $((10#$d)) "*) ;; *) ready=0 ;; esac
    done <<EOF
$deps
EOF
    title=$(hero_item_field "$f" title)
    if [ "$ready" = 1 ]; then
      echo "READY  $f — $title"
    else
      echo "blocked $f — $title"
    fi
  done
}

# ---------- branch naming ---------------------------------------------------
#
# Deriving the name itself is a *model* task, not a shell one — it reads a diff
# or a description and summarizes. What lives here is the policy the model
# applies, in one place, because it was previously stated in both push-pr and
# one-shot and the two had already drifted (one listed a `test/` prefix, the
# other did not; one asked for a 3-5 word slug, the other 2-3).
#
# Skills reference hero_branch_policy in their instructions instead of
# restating the rules. It prints the policy for the model to apply.

hero_branch_policy() {
  cat <<'POLICY'
Branch name = TYPE/SLUG, or ISSUE-ID-SLUG when an issue ID is known.

TYPE — pick from the change's dominant intent:
  feat      new functionality
  fix       bug fix
  refactor  restructuring with no behavior change
  docs      documentation only
  test      tests only
  chore     tooling, CI, dependency bumps

SLUG — 3-5 words, lowercase, hyphen-separated, <=50 chars.
  Strip filler words (the, a, an, for, to, in).
  Derive from the task description when one was given, else from the diff:
  the most-changed top-level directory plus what changed.

ISSUE ID — when the task starts with an issue ID matching
  ^[A-Z][A-Z0-9]{1,9}-[0-9]+(\s|$), or HERO.md sets an issue-prefix and an ID
  appears in the diff or draft commit message, prefer ISSUE-ID-SLUG.
  The match must be anchored at position 0, so "Fix CVE-2024-1234 in auth"
  is NOT an issue ID and falls through to TYPE/SLUG.
POLICY
}
