#!/usr/bin/env bash
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
#     hero_work_store (mkdir, and migrates a legacy plan-work/ directory via
#     mv). Everything else is read-only.

# ---------- repo + config --------------------------------------------------

# Absolute path to the repo root, or the cwd when not in a git repo.
hero_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Read a single `- key: value` field from HERO.md.
#   hero_field default-branch
#   hero_field bot-username
# Prints the value (trimmed, comments stripped) on stdout.
#
# Returns: 0 found, 1 absent or present-but-empty, 2 rejected as unsafe.
#
# HERO.md is repo content, so in a cloned repo it is attacker-controlled. Its
# values flow into git and gh command lines across the skills. A value starting
# with `-` is read by those tools as an OPTION rather than an argument, and
# `git fetch origin --upload-pack=...` executes its value through a shell —
# arbitrary command execution from nothing but a checked-in config file.
# Rejecting here covers every call site at once, which is the whole point of
# having one reader.
hero_field() {
  local key root value
  key="$1"
  root="${2:-$(hero_root)}"
  [ -r "$root/HERO.md" ] || return 1
  # Skip fenced code blocks (HERO.md documents its own syntax in examples) and
  # keep scanning past a key whose value is empty, so a real setting later in
  # the file is not masked by a placeholder earlier in it.
  value=$(awk -v k="- $key" '
    /^```/ { fence = !fence; next }
    fence  { next }
    index($0, k ":") == 1 {
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      if (v != "") { print v; exit }
    }
  ' "$root/HERO.md")
  # Strip surrounding whitespace and any stray quotes.
  value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^["'"'"']//' -e 's/["'"'"']$//')
  [ -n "$value" ] || return 1
  case "$value" in
    -*)
      echo "hero_field: refusing '$key' — value starts with '-' and would be read as a command-line option: $value" >&2
      return 2 ;;
  esac
  # Control characters (newline, NUL-ish, escape) have no legitimate place in a
  # HERO.md scalar and break line-oriented consumers.
  case "$value" in
    *[[:cntrl:]]*)
      echo "hero_field: refusing '$key' — value contains control characters" >&2
      return 2 ;;
  esac
  printf '%s' "$value"
}

# Is this a shape git will accept as a branch name? Used to gate values that
# reach `git fetch`/`checkout`/`merge` and `gh pr create --base`.
hero_is_valid_branch() {
  [ -n "$1" ] || return 1
  case "$1" in -*|*' '*) return 1 ;; esac
  git check-ref-format --branch "$1" >/dev/null 2>&1
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

  # Establish we can actually ignore the store BEFORE creating or migrating
  # anything. Doing it after meant a non-git directory got a store created and
  # left un-ignored, with the function still returning 0.
  hero_exclude_path >/dev/null || {
    echo "hero_work_store: not a git repo — refusing to create an un-ignorable store" >&2
    return 1
  }

  # `[ -d ]` is true for a symlink to a directory, and `mv` renames the LINK.
  # A repo that commits `plan-work -> ../../../.claude` (git preserves symlinks
  # on clone) would silently become `my-work -> ../../../.claude`, redirecting
  # every later work-item write outside the checkout — into a directory the
  # agent itself reads back. Refuse rather than migrate.
  if [ -L "$root/plan-work" ]; then
    echo "hero_work_store: refusing to migrate '$root/plan-work' — it is a symlink" >&2
    return 1
  fi
  if [ -L "$store" ]; then
    echo "hero_work_store: refusing to use '$store' — it is a symlink" >&2
    return 1
  fi
  if [ -d "$root/plan-work" ] && [ ! -e "$store" ]; then
    mv "$root/plan-work" "$store" || return 1
    echo "Migrated legacy plan-work/ store to my-work/." >&2
  fi

  if [ -d "$root/plan-work" ] && [ -d "$store" ]; then
    echo "hero_work_store: both plan-work/ and my-work/ exist — items in plan-work/ are NOT migrated and will be invisible. Merge them by hand." >&2
  fi
  mkdir -p "$store" || {
    echo "hero_work_store: cannot create '$store'" >&2
    return 1
  }
  # Keep both names excluded through the transition so a not-yet-migrated
  # legacy store is never accidentally committed either.
  hero_exclude_add my-work/ plan-work/ || return 1
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
# was no `d` for the numeric guard to reject.
hero_item_deps() {
  awk '
    /^---[[:space:]]*$/ { fence++; if (fence >= 2) exit; next }
    fence != 1 { next }
    /^depends_on:/ {
      v = $0; sub(/^[^:]*: */, "", v); sub(/ *#.*/, "", v)
      gsub(/[][,]/, " ", v)
      n = split(v, parts, /[[:space:]]+/)
      for (i = 1; i <= n; i++) if (parts[i] != "") print parts[i]
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

# Normalize a work-item status: lowercase, empty defaults to `todo`.
# `Done` silently not matching `done` left every dependent blocked forever.
hero_item_status() {
  local s
  s=$(hero_item_field "$1" status | tr '[:upper:]' '[:lower:]')
  printf '%s' "${s:-todo}"
}

# Print one line per work-item:  STATE  file — title
#
# STATE is one of:
#   READY    not done, and every depends_on target is done
#   blocked  not done, but a dependency is unmet or unresolvable
#   active   status is in-progress — someone is already on it
#   done     completed
#
# `done` rows are PRINTED, not hidden. Callers need to see them: one-shot's
# Step 1c resolves an argument against this listing to answer "has this already
# landed?", and handoff reads it to update an existing item rather than
# duplicating it. Filtering them out silently defeated both.
#
# `active` is separated from READY so two sessions cannot both pick up the same
# in-flight item — one-shot marks an item in-progress before its first edit
# specifically to prevent that, and folding it into READY undid it.
#
# NOTE: readiness is a claim about DEPENDENCIES, not about the codebase. An item
# stays READY after its work lands until someone marks it done — consumers must
# verify against the repo before acting.
#
# Runs in a subshell: it cds, and leaking that into a sourced caller's shell
# silently reroutes every later relative path.
hero_ready_items() (
  local store f d deps ready title id state done_ids
  store="${1:-$(hero_work_store)}" || return 1
  cd "$store" 2>/dev/null || { echo "hero_ready_items: no store at ${store}" >&2; return 1; }

  # Collect done ids. A non-numeric or absent id is skipped with a warning
  # rather than evaluated: `$((10#AH-12))` is a FATAL arithmetic error that
  # aborts mid-loop and emits nothing at all, which a caller reads as an empty
  # plate. One malformed hand-written item must not erase the whole listing.
  done_ids=" "
  for f in *.md; do
    [ -e "$f" ] || continue
    [ "$(hero_item_status "$f")" = "done" ] || continue
    id=$(hero_item_field "$f" id)
    case "$id" in
      ''|*[!0-9]*)
        echo "hero_ready_items: $f has a non-numeric id ('$id') — dependents on it cannot resolve" >&2
        continue ;;
    esac
    case "$done_ids" in
      *" $((10#$id)) "*)
        echo "hero_ready_items: duplicate id $id — dependents may resolve against the wrong item" >&2 ;;
    esac
    done_ids="$done_ids$((10#$id)) "
  done

  for f in *.md; do
    [ -e "$f" ] || continue
    state=$(hero_item_status "$f")
    title=$(hero_item_field "$f" title)
    case "$state" in
      done)        echo "done    $f — $title"; continue ;;
      in-progress) echo "active  $f — $title"; continue ;;
    esac
    deps=$(hero_item_deps "$f")
    ready=1
    # Heredoc keeps the loop in this shell (so `ready` persists) and works under
    # both bash and zsh, which does not word-split unquoted vars.
    while IFS= read -r d; do
      [ -z "$d" ] && continue
      case "$d" in
        ''|*[!0-9]*)
          echo "hero_ready_items: $f depends_on '$d', which is not a numeric id — treating as unmet" >&2
          ready=0; continue ;;
      esac
      case "$done_ids" in *" $((10#$d)) "*) ;; *) ready=0 ;; esac
    done <<EOF
$deps
EOF
    if [ "$ready" = 1 ]; then
      echo "READY   $f — $title"
    else
      echo "blocked $f — $title"
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
