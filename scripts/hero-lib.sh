#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# hero-lib.sh — shared helpers for hero-skills.
#
# Sourced by skills, not executed. Every function here exists because the same
# logic was previously inlined in two or more SKILL.md files and had already
# drifted between copies. If you find yourself pasting the same awk/grep into a
# second skill, it belongs here instead.
#
# Usage from a skill:
#
#   HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
#   [ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
#   # shellcheck source=/dev/null
#   . "$HERO_LIB"
#
# Contract:
#   - Values go to stdout. Human-readable notes go to stderr. A function that
#     returns data never mixes the two, so a caller can parse stdout blindly.
#   - Absence/failure is a non-zero return, never an exit — the caller decides
#     what is fatal. No function exits the calling shell.
#   - Callers' shell state (cwd, variables) is never modified. Functions that
#     need to cd do it inside a subshell.
#   - MUTATING FUNCTIONS: hero_exclude_add (appends to .git/info/exclude) and
#     hero_work_store (mkdir, and migrates a legacy store directory via mv).
#     Everything else is read-only.

# ---------- repo + config --------------------------------------------------

# Absolute path to the repo root, or the cwd when not in a git repo.
hero_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Read a single `- key: value` field from a hero-style markdown file. HERO.md
# and FLEET.md share the grammar, so they share the reader. With BLOCK (a full
# heading line, `## Fleet` or `### auth`), only that section is searched:
# FLEET.md keeps one `### NAME` block per repo, so an unscoped read of `path`
# would return whichever repo happens to come first. PARENT (an H2 line)
# further requires an H3 block to sit under that H2 — the standard invites
# prose after `## Repos`, and a `### auth` under `## Known issues` must not
# answer for the repo row.
#
#   hero_md_field "$root/HERO.md" default-branch
#   hero_md_field "$fleet/FLEET.md" port "### auth" "## Repos"
#
# Prints the value (trimmed, comments stripped) on stdout.
#
# Returns: 0 found, 1 absent or present-but-empty, 2 rejected as unsafe (or a
# BLOCK that is not a heading line — a bare name would silently read as
# "absent").
#
# HERO.md is repo content, so in a cloned repo it is attacker-controlled. Its
# values flow into git and gh command lines across the skills. A value starting
# with `-` is read by those tools as an OPTION rather than an argument, and
# `git fetch origin --upload-pack=...` executes its value through a shell —
# arbitrary command execution from nothing but a checked-in config file.
# Rejecting here covers every call site at once, which is the whole point of
# having one reader.
hero_md_field() {
  local file key block parent value
  file="$1"
  key="$2"
  block="${3:-}"
  parent="${4:-}"
  [ -r "$file" ] || return 1
  block=${block%"${block##*[![:space:]]}"}
  parent=${parent%"${parent##*[![:space:]]}"}
  case "$block" in ''|'## '*|'### '*) ;; *)
    echo "hero_md_field: BLOCK must be a full '## X' or '### X' heading line, got: $block" >&2
    return 2 ;;
  esac
  # Skip fenced code blocks (both files document their own syntax in examples)
  # and keep scanning past a key whose value is empty, so a real setting later
  # in the file is not masked by a placeholder earlier in it.
  value=$(awk -v k="- $key" -v b="$block" -v p="$parent" '
    /^```/ { fence = !fence; next }
    fence  { next }
    /^##+ / {
      h = $0; sub(/[[:space:]]+$/, "", h)
      # An H2 starts a new section. An H3 only matters when the caller asked
      # for an H3 — so a `### x` under `## Fleet` does not end the Fleet
      # section — and an H4 or deeper never opens or closes a block.
      if (h ~ /^## /)                        { sec = h; inblk = (h == b) }
      else if (h ~ /^### / && b ~ /^### /)   inblk = (h == b && (p == "" || sec == p))
      next
    }
    (b == "" || inblk) && index($0, k ":") == 1 {
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      if (v != "") { print v; exit }
    }
  ' "$file")
  # Strip a stray surrounding quote pair (awk already trimmed whitespace).
  value=${value#[\"\']}; value=${value%[\"\']}
  [ -n "$value" ] || return 1
  case "$value" in
    -*)
      echo "hero_md_field: refusing '$key' in ${file##*/} — value starts with '-' and would be read as a command-line option: $value" >&2
      return 2 ;;
  esac
  # Control characters (newline, NUL-ish, escape) have no legitimate place in a
  # config scalar and break line-oriented consumers.
  case "$value" in
    *[[:cntrl:]]*)
      echo "hero_md_field: refusing '$key' in ${file##*/} — value contains control characters" >&2
      return 2 ;;
  esac
  printf '%s' "$value"
}

# Read a single `- key: value` field from HERO.md.
#   hero_field default-branch
#   hero_field bot-username
# First match wins across sections. Keys known to repeat — `platform` (CI/CD
# and Deployment), `health-endpoint` (several per Deployment) — must be read
# with hero_md_field and a BLOCK, or the CI/CD value answers a Deployment
# question.
hero_field() {
  local root
  root="${2:-$(hero_root)}"
  hero_md_field "$root/HERO.md" "$1"
}

# Is this a shape git will accept as a branch name? Used to gate values that
# reach `git fetch`/`checkout`/`merge` and `gh pr create --base`.
hero_is_valid_branch() {
  [ -n "$1" ] || return 1
  case "$1" in -*|*' '*) return 1 ;; esac
  git check-ref-format --branch "$1" >/dev/null 2>&1
}

# Validate + normalize a git repo reference before it reaches `git ls-remote`,
# `git clone`, or `git -C` as a REMOTE URL. This is to a repo URL what
# hero_is_valid_branch is to a branch name.
#
# HERO.md is attacker-controlled in a cloned repo, and hero_field only blocks a
# leading `-` and control chars — NOT git's `ext::sh -c "..."` transport helper,
# which git executes as a shell command. A `target-repo: ext::sh -c "curl …|sh"`
# therefore sails through hero_field and runs on the victim's machine the moment
# a skill feeds it to `git ls-remote`. This gate closes that at the one place
# every call site can share.
#
# Accepts and echoes a NORMALIZED value on stdout:
#   OWNER/NAME        -> https://github.com/OWNER/NAME  (GitHub shorthand git won't resolve itself)
#   https:// ssh://   -> unchanged
#   git@host:path     -> unchanged (scp-style ssh)
#   an existing local directory -> unchanged
#   none              -> unchanged (callers treat "disabled" uniformly)
# Everything else — `::` transport helpers, file://, other URL schemes, a
# non-existent bare path — is REJECTED: non-zero return, message on stderr.
hero_normalize_repo_ref() {
  local ref="$1"
  [ -n "$ref" ] || return 1
  [ "$ref" = none ] && { printf 'none'; return 0; }
  # `word::rest` is the transport-helper syntax (ext::, fd::, …) — the RCE path.
  case "$ref" in
    *::*)
      echo "hero_normalize_repo_ref: refusing '$ref' — '::' transport-helper syntax runs a command" >&2
      return 2 ;;
  esac
  case "$ref" in
    https://*|ssh://*) printf '%s' "$ref"; return 0 ;;
    file://*)
      echo "hero_normalize_repo_ref: refusing '$ref' — file:// is not an allowed transport" >&2
      return 2 ;;
    *://*)
      echo "hero_normalize_repo_ref: refusing '$ref' — only https:// and ssh:// URL transports are allowed" >&2
      return 2 ;;
  esac
  # scp-style ssh (git@host:path): a colon, no scheme, no space.
  case "$ref" in
    *' '*) ;;                         # a space is never a valid ref → reject below
    *@*:*) printf '%s' "$ref"; return 0 ;;
  esac
  # An existing local directory is a safe, non-executing target.
  if [ -d "$ref" ]; then printf '%s' "$ref"; return 0; fi
  # GitHub OWNER/NAME shorthand: exactly one slash, safe chars, no colon/space.
  # In `case` globs `*` matches `/` too, so guard the slash count explicitly
  # (*/*/* = two+ slashes) rather than relying on char classes to exclude it.
  case "$ref" in
    *' '*|*:*|*/*/*) ;;                     # space, colon, or 2+ slashes → not shorthand
    */*)
      case "$ref" in
        *[!A-Za-z0-9_./-]*) ;;              # any char outside the safe set → reject
        *) printf 'https://github.com/%s' "$ref"; return 0 ;;
      esac ;;
  esac
  echo "hero_normalize_repo_ref: refusing '$ref' — not OWNER/NAME, https://, ssh://, git@host:path, or an existing local directory" >&2
  return 2
}

# The repo's default branch per HERO.md, falling back to `main`.
#
# The fallback is silent by design at the call sites that only *read* (a diff
# base, a log range). Call sites that branch, merge, or open a PR against it
# should use hero_default_branch_verbose so a missing/mistyped HERO.md field
# can't silently target the wrong branch.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_default_branch() {
  local b
  if b=$(hero_field default-branch "$@") && hero_is_valid_branch "$b"; then
    printf '%s' "$b"
    return 0
  fi
  # A value that is not a valid branch name is as dangerous as one starting with
  # `-`: `main:refs/heads/evil`, `..`, `@{u}` and `main^` are all accepted by
  # `git fetch`/`checkout` as something other than the branch they resemble.
  # hero_field's character gate cannot catch those; check-ref-format can.
  [ -n "${b:-}" ] && echo "hero_default_branch: '$b' is not a valid branch name — using main" >&2
  printf 'main'
}

# Same, but reports where the value came from on stderr. Use before any
# destructive or outward-facing operation.
# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_default_branch_verbose() {
  local b rc
  b=$(hero_field default-branch "$@"); rc=$?
  if [ "$rc" = 0 ] && hero_is_valid_branch "$b"; then
    printf '%s' "$b"
    echo "default branch: $b (from HERO.md)" >&2
    return 0
  fi
  printf 'main'
  # Distinct messages: "not found" sends an operator hunting for a missing key
  # that is actually present and was rejected.
  case "$rc" in
    2) echo "default branch: main (fallback — HERO.md value REJECTED as unsafe)" >&2 ;;
    *) if [ -n "${b:-}" ]; then
         echo "default branch: main (fallback — '$b' is not a valid branch name)" >&2
       else
         echo "default branch: main (fallback — HERO.md default-branch not found)" >&2
       fi ;;
  esac
  return 3
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
    echo "note: HERO.md may be out of date — run hero-skills:init-hero --update to refresh." >&2
  fi
  return 0
}

# ---------- fleet ----------------------------------------------------------
#
# A fleet is a folder of sibling checkouts with a FLEET.md at its top — the
# operator's local map of the repos they work across. It is unversioned and
# never inside a repo; docs/FLEET-MD.md is the standard.
#
# Every function here defaults to $PWD, not hero_root: a fleet folder is by
# definition not a repo root, and under a dotfiles-managed $HOME hero_root is
# $HOME, which would hide every fleet beneath it.

# Nearest ancestor (inclusive) of START holding FLEET.md, or return 1. A
# directory holding HERO.md beside it is a repo that committed a FLEET.md —
# repo content, not the operator's map — so it is passed over (stderr note)
# and the walk continues upward.
# shellcheck disable=SC2120  # in-file callers take the default; the tests pass START
hero_fleet_root() { # [START]
  local d
  d=$(cd "${1:-$PWD}" && pwd -P) || return 1
  # Parameter expansion, not $(dirname): a subshell per level, and a dirname
  # that returns empty (stripped PATH) would leave `d` unchanged and spin.
  while [ -n "$d" ]; do
    if [ -f "$d/FLEET.md" ]; then
      if [ -f "$d/HERO.md" ]; then
        echo "hero_fleet_root: passing over $d — FLEET.md beside HERO.md is a repo, not a fleet" >&2
      else
        printf '%s' "$d"; return 0
      fi
    fi
    [ "$d" = "/" ] && return 1
    d=${d%/*}; d=${d:-/}
  done
  return 1
}

# True when DIR (default $PWD) is a fleet folder rather than a repo: it holds
# FLEET.md and no HERO.md. Skills test this in Step 0 and hand off to "At the
# fleet root" in docs/FLEET-MD.md instead of treating the folder as a project.
hero_at_fleet_root() { # [DIR]
  local d
  d="${1:-$PWD}"
  [ -f "$d/FLEET.md" ] && [ ! -f "$d/HERO.md" ]
}

# A fleet-level `- key: value` from the `## Fleet` section.
#   hero_fleet_field name
hero_fleet_field() { # KEY [FLEET_ROOT]
  local root
  root="${2:-$(hero_fleet_root)}" || return 1
  hero_md_field "$root/FLEET.md" "$1" "## Fleet"
}

# One `- key: value` from a repo's `### NAME` block under `## Repos`.
#   hero_fleet_repo_field auth port
hero_fleet_repo_field() { # NAME KEY [FLEET_ROOT]
  local root
  root="${3:-$(hero_fleet_root)}" || return 1
  hero_md_field "$root/FLEET.md" "$2" "### $1" "## Repos"
}

# Every repo listed under `## Repos`, one per line:
# NAME<TAB>PATH<TAB>GROUP<TAB>PORT. One awk pass, not a loop over
# hero_fleet_repo_field: that re-parses FLEET.md three times per row.
# PATH is absolute and physical when the directory exists (a relative `path:`
# resolves against the fleet root and defaults to ./NAME); GROUP is lowercased
# and defaults to `none`, which means "lives here, not fleet"; PORT is digits
# or empty when unclaimed. Columns 2 and 3 are never empty, so a caller's
# `IFS=$'\t' read` is safe — do not add an optional column before PORT.
#
# A row that cannot be trusted is SKIPPED, not defaulted: a leading `-` or a
# control character in a value, a non-numeric port, a name that is not
# [A-Za-z0-9._-] or is `.`/`..`, a path resolving outside the fleet, or a
# duplicate name. Substituting a default path would point the caller's `cd` at
# a different directory than the one the row names. Each skip is one stderr
# line `hero_fleet_repos: skipping 'NAME' — REASON` (fleet-scan.sh reads
# them back as BAD_ROW), and the function returns 3 when any row was skipped.
#
# Locals are rpath/rgroup/rport, never `path`: sourced from zsh, `local path`
# empties the PATH-tied array and awk becomes "command not found" — an empty
# registry with rc 0.
hero_fleet_repos() { # [FLEET_ROOT]
  local root
  root="${1:-$(hero_fleet_root)}" || return 1
  [ -r "$root/FLEET.md" ] || { echo "hero_fleet_repos: cannot read $root/FLEET.md" >&2; return 1; }
  awk '
    # \034 (file separator), not a tab: `read` with a whitespace IFS collapses
    # consecutive tabs, so an empty path would shift group into its column.
    function flush() { if (name != "") printf "%s\034%s\034%s\034%s\n", name, rpath, rgroup, rport; name = "" }
    /^```/ { fence = !fence; next }
    fence  { next }
    /^## /  { flush(); sec = $0; sub(/[[:space:]]+$/, "", sec); next }
    sec == "## Repos" && /^### / {
      flush(); name = $0; sub(/^### +/, "", name); sub(/[[:space:]]+$/, "", name)
      rpath = ""; rgroup = ""; rport = ""; next
    }
    name != "" && /^- (path|group|port):/ {
      k = $0; sub(/^- /, "", k); sub(/:.*/, "", k)
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v); gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      if (k == "path") rpath = v; else if (k == "group") rgroup = v; else rport = v
    }
    END { flush() }
  ' "$root/FLEET.md" | {
    local name rpath rgroup rport v reason seen nbad real
    seen=" "; nbad=0
    while IFS=$'\034' read -r name rpath rgroup rport; do
      reason=""
      case "$name" in
        .|..|''|*[!A-Za-z0-9._-]*) reason="a repo name is [A-Za-z0-9._-] only, not '$name'" ;;
      esac
      [ -n "$reason" ] || case "$seen" in *" $name "*) reason="duplicate row" ;; esac
      rpath=${rpath#[\"\']}; rpath=${rpath%[\"\']}
      rgroup=${rgroup#[\"\']}; rgroup=${rgroup%[\"\']}
      rport=${rport#[\"\']}; rport=${rport%[\"\']}
      for v in "$rpath" "$rgroup" "$rport"; do
        [ -n "$reason" ] || case "$v" in -*|*[[:cntrl:]]*) reason="a value starts with '-' or holds a control character" ;; esac
      done
      [ -n "$reason" ] || case "$rport" in *[!0-9]*) reason="port is not a number: $rport" ;; esac
      if [ -n "$reason" ]; then
        echo "hero_fleet_repos: skipping '$name' — $reason" >&2
        nbad=$((nbad + 1)); continue
      fi
      seen="$seen$name "
      rgroup=$(printf '%s' "${rgroup:-none}" | tr '[:upper:]' '[:lower:]')
      [ -n "$rpath" ] || rpath="./$name"
      rpath=${rpath%/}
      case "$rpath" in /*) ;; *) rpath="$root/${rpath#./}" ;; esac
      if [ -d "$rpath" ]; then
        real=$(cd "$rpath" && pwd -P)
        case "$real" in "$root"/*) rpath=$real ;; *)
          echo "hero_fleet_repos: skipping '$name' — path resolves outside the fleet: $real" >&2
          nbad=$((nbad + 1)); continue ;;
        esac
      fi
      printf '%s\t%s\t%s\t%s\n' "$name" "$rpath" "$rgroup" "$rport"
    done
    [ "$nbad" -eq 0 ] || return 3
  }
}

# Host port a checkout's dev compose file publishes: digits, `-` when there is
# no compose file, `?` when there is one but no host port could be read (the
# two are different findings — "not implemented" vs "unreadable"). Reads BOTH
# spellings, skips commented-out lines, and reads `HOST_PORT:-N`, a literal
# `[HOST:]PUBLISHED:CONTAINER` mapping, or long-syntax `published:` — an
# earlier fleet reconcile grepped only `HOST_PORT` in `.yaml` and silently
# reported two live repos as claiming no port at all. A multi-service file
# publishes several ports (the database's first, typically); with RANGE
# (`33000-33099`) the one inside it wins, else the first literal.
hero_compose_port() { # DIR [RANGE]
  local f ports lo hi p
  for f in docker-compose.dev.yaml docker-compose.dev.yml docker-compose.yaml docker-compose.yml compose.yaml compose.yml; do
    [ -r "$1/$f" ] || continue
    ports=$(sed -nE '/^[[:space:]]*#/d; s/.*HOST_PORT:-([0-9]+).*/\1/p' "$1/$f" | head -1)
    [ -n "$ports" ] || ports=$(sed -nE '/^[[:space:]]*#/d
      s/^[[:space:]]*-[[:space:]]*"?(([0-9.]+|\[[0-9a-fA-F:]+\]):)?([0-9]{2,5}):[0-9]{2,5}"?.*/\3/p
      s/^[[:space:]]*published:[[:space:]]*"?([0-9]{2,5})"?.*/\1/p' "$1/$f")
    [ -n "$ports" ] || { printf '?'; return 0; }
    if [ -n "${2:-}" ]; then
      lo=${2%-*}; hi=${2#*-}
      for p in $ports; do
        [ "$p" -ge "$lo" ] 2>/dev/null && [ "$p" -le "$hi" ] 2>/dev/null && { printf '%s' "$p"; return 0; }
      done
    fi
    printf '%s' "${ports%%
*}"
    return 0
  done
  printf -- '-'
}

# ---------- concurrent work --------------------------------------------------
#
# Several features build at once — worktree subagents here, other people
# elsewhere — so a PR's head is routinely behind the default branch by the time
# it is reviewed, approved, or merged. A gate that judged a stale head judged
# code that is not what will merge. Every skill that reviews, approves, or
# merges rebases first, through this one function.

# Rebase the current branch onto a freshly fetched origin/BASE and push it
# with --force-with-lease. Prints one line on stderr saying what happened.
#
# Returns: 0 already up to date, or rebased and pushed;
#          1 the rebase conflicts — it is ABORTED, the branch is unchanged, and
#            the conflicting files are listed on stderr for the caller to STOP on;
#          2 cannot proceed: dirty tree, detached HEAD, on the base itself, a
#            fetch failure, or a push the lease refused (someone else pushed —
#            fetch and re-run; never retry without the lease).
#
# Branch protection dismisses approvals on push, so a caller that has already
# collected an approval must re-trigger it after a rebase — rebase BEFORE the
# approval, and only re-check (not re-rebase) between approval and merge.
hero_rebase_on_base() { # BASE
  local base branch behind conflicts
  base="$1"
  hero_is_valid_branch "$base" || { echo "hero_rebase_on_base: not a branch name: '$base'" >&2; return 2; }
  branch=$(git branch --show-current)
  [ -n "$branch" ] || { echo "hero_rebase_on_base: detached HEAD — check out the PR branch first" >&2; return 2; }
  [ "$branch" != "$base" ] || { echo "hero_rebase_on_base: on $base itself — nothing to rebase" >&2; return 2; }
  if [ -n "$(git status --porcelain)" ]; then
    echo "hero_rebase_on_base: working tree is dirty — commit or discard first:" >&2
    git status --short >&2
    return 2
  fi
  git fetch -q origin "$base" || { echo "hero_rebase_on_base: git fetch origin $base failed" >&2; return 2; }
  behind=$(git rev-list --count "HEAD..origin/$base")
  if [ "$behind" -eq 0 ]; then
    echo "hero_rebase_on_base: $branch is up to date with origin/$base" >&2
    return 0
  fi
  if ! git rebase -q "origin/$base" >/dev/null 2>&1; then
    conflicts=$(git diff --name-only --diff-filter=U)
    git rebase --abort
    echo "hero_rebase_on_base: rebasing $branch onto origin/$base conflicts — aborted, branch unchanged. Conflicting files:" >&2
    printf '  %s\n' $conflicts >&2
    return 1
  fi
  git push -q --force-with-lease origin "$branch" 2>/dev/null || {
    echo "hero_rebase_on_base: push refused by the lease — origin/$branch moved; fetch, inspect, re-run" >&2
    return 2
  }
  echo "hero_rebase_on_base: rebased $branch onto origin/$base ($behind commits behind) and pushed" >&2
}

# True when DIR (default $PWD) is a linked git worktree: its `.git` is a file
# pointing into the primary checkout. ship-pr uses this to skip the
# default-branch reset — the default branch is checked out in the primary, so
# `git checkout main` here fails, and the worktree is the caller's to remove.
hero_in_worktree() { # [DIR]
  local d
  d="${1:-$PWD}"
  [ -f "$d/.git" ] && grep -q '/worktrees/' "$d/.git" 2>/dev/null
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
#   hero_exclude_add .plans/ .test-output/
#
# Fails PER ENTRY, not per call: returning only the last iteration's status
# meant a failed append for entry 1 was swallowed when entry 2 succeeded —
# the store stayed un-ignored with nothing programmatically detectable.
hero_exclude_add() {
  local exclude entry rc
  exclude=$(hero_exclude_path) || {
    echo "hero_exclude_add: not a git repo" >&2
    return 1
  }
  mkdir -p "$(dirname "$exclude")" || {
    echo "hero_exclude_add: cannot create $(dirname "$exclude")" >&2
    return 1
  }
  rc=0
  for entry in "$@"; do
    grep -qxF "$entry" "$exclude" 2>/dev/null && continue
    printf '\n%s\n' "$entry" >> "$exclude" 2>/dev/null || {
      echo "hero_exclude_add: cannot append '$entry' to $exclude" >&2
      rc=1
    }
  done
  return "$rc"
}

# ---------- PR review markers ----------------------------------------------

# review-pr stamps this into its self-review comment; one-shot Step 5, ship-pr
# Step 3a, resume-state, and auto-approve.yaml's prior-review gate all look
# for it. Change it here and in the workflow together, or the gate stops
# recognizing every self-review.
HERO_SELF_REVIEW_MARKER='ai-hero:self-review'

# Count of self-review comments on a PR. Prints nothing and returns 1 when
# the API call fails — an empty count must never read as zero.
hero_self_review_count() { # PR_NUMBER
  gh api "/repos/{owner}/{repo}/issues/$1/comments" \
    --jq "[.[] | select(.body | test(\"$HERO_SELF_REVIEW_MARKER\"))] | length" 2>/dev/null
}

# ---------- the .plans store ------------------------------------------------

# Absolute path to the work-item store, created and git-ignored on first use.
# A dot-directory: tool-private state, like `.beads/` — it keeps the repo root
# clean and is far less likely to collide with a real project directory.
#
# One-time migration: the store was formerly `my-work/`, and before that
# `plan-work/`. Move a legacy store rather than orphaning its items behind
# the new name.
# Where the store IS, without creating it: read-only callers (resume-state)
# need the path and must not mkdir or touch .git/info/exclude.
# A worktree shares the repo's items: resolve the store under the primary
# checkout, or a worktree gets an empty private store and a build launched
# there plans from nothing. Read the worktree's `.git` FILE rather than
# asking git: a caller with GIT_DIR exported (pre-commit hooks do) would get
# the answer for a different repo.
hero_store_path() { # [ROOT]
  local root gitdir
  root="${1:-$(hero_root)}"
  if [ -f "$root/.git" ]; then
    gitdir=$(sed -n 's/^gitdir: //p' "$root/.git")
    case "$gitdir" in */.git/worktrees/*) root=${gitdir%/.git/worktrees/*} ;; esac
  fi
  printf '%s' "$root/.plans"
}

# shellcheck disable=SC2120  # optional arg; callers usually rely on the default
hero_work_store() {
  local root store legacy
  store=$(hero_store_path "${1:-}")
  root=${store%/.plans}

  # Establish we can actually ignore the store BEFORE creating or migrating
  # anything. Doing it after meant a non-git directory got a store created and
  # left un-ignored, with the function still returning 0. Check — and later
  # write — against $root, not the cwd: with an explicit root argument, the
  # cwd may be a DIFFERENT repo, and the guard passing on the wrong repo
  # created an un-ignored store in $root while polluting the cwd's excludes.
  hero_exclude_path "$root" >/dev/null || {
    echo "hero_work_store: '$root' is not a git repo — refusing to create an un-ignorable store" >&2
    return 1
  }

  # A store that is a symlink redirects every later work-item write outside
  # the checkout — into a directory the agent itself reads back. Refuse.
  if [ -L "$store" ]; then
    echo "hero_work_store: refusing to use '$store' — it is a symlink" >&2
    return 1
  fi
  for legacy in my-work plan-work; do
    # `[ -d ]` is true for a symlink to a directory, and `mv` renames the
    # LINK: a repo that commits `my-work -> ../../../.claude` (git preserves
    # symlinks on clone) would silently become `.plans -> ../../../.claude`.
    # Refuse rather than migrate — but only when a migration would actually
    # happen; a stale legacy symlink next to a healthy `.plans/` must not
    # brick the store forever.
    if [ -L "$root/$legacy" ]; then
      if [ ! -e "$store" ]; then
        echo "hero_work_store: refusing to migrate '$root/$legacy' — it is a symlink" >&2
        return 1
      fi
      echo "hero_work_store: ignoring legacy '$root/$legacy' — it is a symlink" >&2
      continue
    fi
    if [ -d "$root/$legacy" ] && [ ! -e "$store" ]; then
      mv "$root/$legacy" "$store" || {
        echo "hero_work_store: cannot migrate '$root/$legacy' to '$store'" >&2
        return 1
      }
      echo "Migrated legacy $legacy/ store to .plans/." >&2
    fi
    if [ -d "$root/$legacy" ] && [ -d "$store" ]; then
      echo "hero_work_store: both $legacy/ and .plans/ exist — items in $legacy/ are NOT migrated and will be invisible. Merge them by hand." >&2
    fi
    # Keep the legacy name excluded through the transition so a not-yet-migrated
    # legacy store is never accidentally committed either. The subshell cd
    # targets $root's excludes even when the caller's cwd is another repo.
    ( cd "$root" && hero_exclude_add "$legacy/" ) || return 1
  done
  mkdir -p "$store" || {
    echo "hero_work_store: cannot create '$store'" >&2
    return 1
  }
  ( cd "$root" && hero_exclude_add .plans/ ) || return 1
  printf '%s' "$store"
}

# Read a frontmatter scalar from a work-item.
#
# Bounded to the frontmatter block between the first two `---` fences: without
# that, a `status: done` line appearing in the BODY (acceptance criteria, a
# pasted log) was read as the item's status.
#
# Splits on the FIRST colon only and strips surrounding quotes. Splitting on
# every ': ' truncated any value containing a colon; not stripping quotes made
# `status: "done"` fail to equal `done`, which silently blocked every dependent
# forever. hero_field already strips quotes — the two readers in this file must
# agree on the same syntax.
hero_item_field() {
  awk -v k="$2" '
    /^---[[:space:]]*$/ { fence++; if (fence >= 2) exit; next }
    fence != 1 { next }
    index($0, k ":") == 1 {
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      gsub(/^["'"'"']|["'"'"']$/, "", v)
      print v
      exit
    }
  ' "$1"
}

# Print an item'"'"'s depends_on ids, one per line.
#
# Handles BOTH YAML forms. Only the inline form was parsed before, so a block
# sequence —
#
#   depends_on:
#     - 99
#
# — yielded an empty value, the readiness loop never ran, and the item was
# reported READY despite depending on work that does not exist. Silently: there
# was no `d` for the readiness loop's existence check to flag as missing.
hero_item_deps() {
  awk '
    /^---[[:space:]]*$/ { fence++; if (fence >= 2) exit; next }
    fence != 1 { next }
    /^depends_on:/ {
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v)
      gsub(/[][,]/, " ", v)
      n = split(v, parts, /[[:space:]]+/)
      # Strip surrounding quotes per entry, mirroring the block branch below —
      # quoting is handled here, in the parser, not by the id normalizer.
      for (i = 1; i <= n; i++) {
        p = parts[i]
        gsub(/^["'"'"']|["'"'"']$/, "", p)
        if (p != "") print p
      }
      block = 1
      next
    }
    # A block sequence continues while lines are indented `- item` entries.
    block && /^[[:space:]]+-[[:space:]]*/ {
      v = $0; sub(/^[[:space:]]*-[[:space:]]*/, "", v); sub(/ *#.*/, "", v)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      gsub(/^["'"'"']|["'"'"']$/, "", v)
      if (v != "") print v
      next
    }
    { block = 0 }
  ' "$1"
}

# Normalize a work-item status: lowercase, empty defaults to `new`.
# `Done` silently not matching `done` left every dependent blocked forever.
# The default is `new`, not `todo`: `todo` on a plain item means READY-eligible,
# so a status-less item went straight to one-shot untriaged.
hero_item_status() {
  local s
  s=$(hero_item_field "$1" status | tr '[:upper:]' '[:lower:]')
  printf '%s' "${s:-new}"
}

# Map a kind to its CLASS — the class picks the status enum (see the table on
# hero_ready_items). Prints the class; prints `unknown` and warns for a kind
# not in the table. Both of hero_ready_items' loops call this so the kind list
# exists once: a second copy in the terminal-status pass is how a fourth
# feedback kind would get added to one and forgotten in the other, leaving its
# dependents blocked forever.
#
# An unrecognized kind rides the plain enum with READY downgraded to backlog.
# Not `invalid`: that hid every such item behind a stderr line. Not plain
# either: `todo` means opposite things in the plain and build enums, so a typo
# like `kind: features` would hand an unplanned feature straight to one-shot.
# Listed-but-never-READY is the one reading safe under both.
hero_item_class() {
  case "$1" in
    ''|work-order|hardening)                                      printf plain ;;
    feature|architecture|polish|security)                         printf build ;;
    goal)                                                         printf goal ;;
    design-feedback|architecture-feedback|design-system-feedback) printf feedback ;;
    *)
      echo "hero_ready_items: $2 has unrecognized kind '$1' — listed on the plain enum but never handed out READY; add it to hero_item_class or fix the frontmatter" >&2
      printf unknown ;;
  esac
}

# Normalize a work-item id for comparison: all-digit ids (the standard form)
# drop leading zeros so `007` equals `7`; anything else lowercases and
# compares verbatim rather than aborting — the old `$((10#$id))` arithmetic
# was a FATAL error on any non-digit and silently blanked the whole listing.
# Quote-stripping is the frontmatter readers' job, not this function's.
hero_norm_id() {
  case "$1" in
    ''|*[!0-9]*) printf '%s' "$1" | tr '[:upper:]' '[:lower:]' ;;
    *) printf '%s' "$((10#$1))" ;;
  esac
}

# Print one line per work-item:  STATE  file — title
# A blocked row whose dependency does not exist anywhere in the store gets a
# trailing ` [missing dep: ID…]` annotation — that reference can NEVER be
# satisfied, which is different from ordinary waiting.
#
# STATE is one of:
#   READY    not done, and every depends_on target is done
#   blocked  not done, but a dependency is unmet or unresolvable
#   plan     status is planning — still being shaped; a HUMAN marks it todo
#            (`ready` for a build kind)
#   active   status is in-progress — someone is already on it
#   done     completed
#   new      status is new (or absent): created, not yet triaged. Never READY —
#            nobody has decided this should be worked on
#   backlog  build kinds (and unrecognized ones) — status is todo: on the
#            roadmap, not yet planned; annotated `[deps unmet]` when a
#            dependency isn't done
#   review   build kinds only — status is reviewing: PR open, awaiting merge
#   feedback feedback kinds only — status is todo or queued: a divergence
#            written but not yet landed upstream. Never READY: a feedback item
#            is DELIVERED, never built, so handing one to one-shot is wrong
#   goal     kind: goal only — status is todo: approved, waiting to run. Never
#            READY: a goal is a container for features, and one-shot builds
#            features. `wayfare goal` selects goals by kind instead
#   invalid  no usable id, OR an unrecognized status — either way the item
#            cannot participate in dependency order and is never handed out READY
#
# Kind picks a CLASS, and the class picks the status enum:
#
#   plain     '' / work-order / hardening — new | planning | todo | in-progress | done.
#             LEGACY: every producer now writes a build kind. The arm stays so
#             existing stores keep listing; dropping it would demote every
#             pre-rule item to backlog with a stderr line as the only trace
#   build     feature / architecture / polish / security — new | todo | planning | ready |
#             implementing | reviewing | done, mapped here as
#             new | backlog | plan | READY-eligible |
#             active | review | done. For a build kind, `ready` (not `todo`) is
#             the state eligible to become READY: `todo` means "identified,
#             unplanned", and handing an unplanned one to one-shot would skip
#             planning entirely
#   feedback  design-feedback / architecture-feedback / design-system-feedback —
#             new | todo | queued | delivered | rejected, mapped as new | feedback
#             | feedback | done | done
#   goal      goal — new | todo | active | done, mapped as new | goal | active |
#             done. Spans several features via `covers:`; its own DoD is what
#             the goal loop checks against
#
# Plain items keep the original enum; `ready`/`implementing`/`reviewing` on a
# plain item stay invalid (loud). An unrecognized kind rides the plain enum with
# READY downgraded to backlog — see the class gate for why that is the only
# reading safe under both failure modes.
#
# `done` rows are PRINTED, not hidden. Callers need to see them: one-shot's
# Step 1c resolves an argument against this listing to answer "has this already
# landed?", and handoff reads it to update an existing item rather than
# duplicating it. Filtering them out silently defeated both.
#
# `active` is separated from READY so two sessions cannot both pick up the same
# in-flight item — one-shot marks an item in-progress (`implementing` for a
# feature) before its first edit specifically to prevent that, and folding it
# into READY undid it.
#
# `planning` is never READY regardless of dependencies: the item is still being
# shaped and awaits a human ready-mark. Skills that emit plain items write them
# as `planning`; only the user's explicit say-so flips one to `todo` (`ready`
# for a build kind) — without this state, freshly emitted items were
# handed straight to one-shot. Wayfare emits features as `todo`, which for a
# feature means backlog — still never READY.
#
# NOTE: readiness is a claim about DEPENDENCIES, not about the codebase. An item
# stays READY after its work lands until someone marks it done — consumers must
# verify against the repo before acting.
#
# Runs in a subshell: it cds, and leaking that into a sourced caller's shell
# silently reroutes every later relative path.
hero_ready_items() (
  local store f d raw deps ready title id state kind class enum row all_ids done_ids missing
  store="${1:-$(hero_work_store)}" || return 1
  cd "$store" 2>/dev/null || { echo "hero_ready_items: no store at ${store}" >&2; return 1; }
  # zsh errors out on an unmatched glob (bash leaves it literal for the
  # `[ -e ]` guard to skip), so an EMPTY store aborted with a raw "no matches
  # found" and rc=1 — indistinguishable from a missing store. nullglob makes
  # it an empty listing in both shells.
  setopt localoptions nullglob 2>/dev/null || true

  # Collect every id and the done subset. Ids are integers by convention, but
  # comparison is string-tolerant (hero_norm_id), so the ids rejected here are
  # EMPTY ones and ids containing whitespace — whitespace would inject extra
  # tokens into the space-delimited sets below, letting a dep on a NONEXISTENT
  # id resolve (and even count as done) with no warning at all. A malformed
  # hand-written item must not erase or corrupt the whole listing.
  all_ids=" "
  done_ids=" "
  for f in *.md; do
    [ -e "$f" ] || continue
    id=$(hero_norm_id "$(hero_item_field "$f" id)")
    case "$id" in
      '')
        echo "hero_ready_items: $f has no id — dependents on it cannot resolve" >&2
        continue ;;
      *[[:space:]]*)
        echo "hero_ready_items: $f has a whitespace-containing id ('$id') — dependents on it cannot resolve" >&2
        continue ;;
    esac
    case "$all_ids" in
      *" $id "*)
        echo "hero_ready_items: duplicate id $id — dependents may resolve against the wrong item" >&2 ;;
    esac
    all_ids="$all_ids$id "
    # The same alphabet gate the listing loop applies, applied BEFORE anything
    # is admitted to done_ids. Without it an item the listing prints as
    # `invalid` (`kind: foo bar`, `status: done`) still unblocked its
    # dependents — invisible on the listing, live in the dependency order.
    state=$(hero_item_status "$f")
    kind=$(hero_item_field "$f" kind | tr '[:upper:]' '[:lower:]')
    case "$state$kind" in *[!a-z-]*) continue ;; esac
    class=$(hero_item_class "$kind" "$f" 2>/dev/null)
    # TERMINAL, not literally `done`. A feedback item ends at `delivered` or
    # `rejected`; keying on the word `done` alone left every dependent of an
    # answered upstream question blocked forever.
    case "$class:$state" in
      feedback:delivered|feedback:rejected) done_ids="$done_ids$id " ;;
      feedback:*) ;;
      *:done) done_ids="$done_ids$id " ;;
    esac
  done

  for f in *.md; do
    [ -e "$f" ] || continue
    state=$(hero_item_status "$f")
    title=$(hero_item_field "$f" title)
    kind=$(hero_item_field "$f" kind | tr '[:upper:]' '[:lower:]')
    # Gate the ALPHABET before the table: both values come from hand-editable
    # frontmatter, and the kind-keyed patterns below anchor on a `:` join — a
    # smuggled colon (`status: x:todo`) would otherwise match the `*:todo` arm
    # and walk an unrecognized status straight into READY, the exact silent
    # fall-through the invalid arm exists to stop. Every legal keyword is
    # lowercase letters and hyphens only.
    case "$state$kind" in
      *[!a-z-]*)
        echo "hero_ready_items: $f has a malformed status/kind ('$state' / '$kind') — keywords are lowercase letters and hyphens only; not eligible for READY" >&2
        echo "invalid $f — $title"
        continue ;;
    esac
    class=$(hero_item_class "$kind" "$f")
    # An item with no usable id is broken whatever its status: nothing can
    # depend on it and nothing can mark it done. Checked before the status
    # table so there is one rule instead of one per status.
    id=$(hero_norm_id "$(hero_item_field "$f" id)")
    case "$id" in
      ''|*[[:space:]]*) echo "invalid $f — $title"; continue ;;
    esac
    # One CLASS-keyed table, not a case block per kind: shared states appear
    # once, and only the genuinely divergent arms name a class (see the state
    # list above for the mapping and the ready-vs-todo rationale).
    # `build:in-progress` aliases to active so features written before the
    # lifecycle rename still list, not invalidate.
    row=READY
    # Every arm names its classes. A `*:` wildcard here would let a feedback
    # item at `in-progress` print `active` — byte-identical to a feature
    # mid-build, and the row carries no kind, so `wayfare goal` tier 1 would
    # hand it to one-shot. `*:new` is the one exception: new is in every enum.
    case "$class:$state" in
      *:new)                            echo "new     $f — $title"; continue ;;
      plain:done|build:done|goal:done|unknown:done)
                                        echo "done    $f — $title"; continue ;;
      # Delivered and rejected are both TERMINAL and both frozen — a rejection
      # is kept on purpose, because "we raised this and they said no" is the
      # history that stops it being raised again next quarter.
      feedback:delivered|feedback:rejected) echo "done    $f — $title"; continue ;;
      # Open feedback: written, not yet landed upstream. Its own row word, so
      # the backlog count is a scan rather than a judgment about prose — this
      # is the return channel's only backlog surface, and a miscount of zero is
      # indistinguishable from "no feedback exists".
      feedback:todo|feedback:queued)    echo "feedback $f — $title"; continue ;;
      # A goal is a container for features, not a unit of work. It is never
      # READY, because READY means "hand this to one-shot" and one-shot builds
      # features. `wayfare goal` takes a goal by id, never off the READY tier.
      goal:todo)                        echo "goal    $f — $title"; continue ;;
      goal:active|build:implementing|build:in-progress|plain:in-progress|unknown:in-progress)
                                        echo "active  $f — $title"; continue ;;
      build:reviewing)                  echo "review  $f — $title"; continue ;;
      plain:planning|build:planning|unknown:planning)
                                        echo "plan    $f — $title"; continue ;;
      build:todo|unknown:todo)          row=backlog ;; # never READY, but falls through to the dep check: dangling refs must still warn, and unmet deps must annotate the row (`wayfare goal` reads them)
      build:ready|plain:todo) ;;  # the only READY-eligible arms — dep check below
      *)
        # An UNRECOGNIZED status must never fall through to the READY path. The
        # display label is `plan` while the keyword is `planning`, so `status:
        # plan` — or any typo like `plannig` — is an easy hand/model error that
        # would otherwise be handed straight to one-shot with no human
        # ready-mark, silently defeating the gate the planning state exists to
        # enforce. Treat it like a rejected id: name it loudly, never READY.
        case "$class" in
          build)    enum="new/todo/planning/ready/implementing/reviewing/done (kind: $kind)" ;;
          feedback) enum="new/todo/queued/delivered/rejected (kind: $kind)" ;;
          goal)     enum="new/todo/active/done (kind: goal)" ;;
          *)        enum="new/planning/todo/in-progress/done" ;;
        esac
        echo "hero_ready_items: $f has unrecognized status '$state' — not one of $enum; not eligible for READY" >&2
        echo "invalid $f — $title"
        continue ;;
    esac
    deps=$(hero_item_deps "$f")
    ready=1
    missing=""
    # Heredoc keeps the loop in this shell (so `ready` persists) and works under
    # both bash and zsh, which does not word-split unquoted vars.
    while IFS= read -r raw; do
      [ -z "$raw" ] && continue
      d=$(hero_norm_id "$raw")
      case "$all_ids" in
        *" $d "*) ;;
        *)
          # A dangling reference blocks FOREVER, silently, unless it is named:
          # nothing will ever mark a nonexistent id done. Say so on both the
          # listing (so the model sees it) and stderr (so a human does) — and
          # say it with the RAW value as written in the file, so grepping the
          # store for the printed token actually finds it.
          echo "hero_ready_items: $f depends_on '$raw', which no item carries — blocked until the reference is fixed" >&2
          missing="$missing $raw"
          ready=0
          continue ;;
      esac
      case "$done_ids" in *" $d "*) ;; *) ready=0 ;; esac
    done <<EOF
$deps
EOF
    # backlog rows report dep state without ever becoming READY: `[deps unmet]`
    # is what `wayfare goal`'s "backlog whose deps are all done" tier reads, and the
    # missing-dep annotation keeps a bootstrap-time typo'd id loud instead of
    # a feature that silently never becomes selectable.
    if [ "$row" = backlog ]; then
      if [ "$ready" = 1 ]; then
        echo "backlog $f — $title"
      else
        echo "backlog $f — $title [deps unmet${missing:+; missing dep:$missing}]"
      fi
    elif [ "$ready" = 1 ]; then
      echo "READY   $f — $title"
    else
      echo "blocked $f — $title${missing:+ [missing dep:$missing]}"
    fi
  done
)

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
