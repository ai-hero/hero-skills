#!/usr/bin/env bash
# Regression table for scripts/hero-lib.sh.
#
# Scoped deliberately: only the two functions with real failure modes are
# covered — hero_field (parses attacker-controlled repo content and feeds it to
# git/gh) and hero_ready_items (parses hand-written frontmatter and previously
# aborted the caller's shell on it). The thin wrappers around them are not
# tested; a test there would pin prose, not behavior.
#
# Every case below is one that was, or could again be, WRONG SILENTLY — the
# listing coming back empty, a value truncated, a malformed id taking the whole
# function down. Loud failures need no regression table.
#
# Usage: bash scripts/hero-lib.test.sh

set -uo pipefail

LIB="$(cd "$(dirname "$0")" && pwd)/hero-lib.sh"
# shellcheck source=/dev/null
. "$LIB" || { echo "cannot source $LIB"; exit 1; }

PASS=0
FAIL=0

check() { # name expected actual
  if [ "$2" = "$3" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL  %s\n      expected: [%s]\n      actual:   [%s]\n' "$1" "$2" "$3"
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---------- hero_field -----------------------------------------------------

mkdir -p "$TMP/cfg"
cat > "$TMP/cfg/HERO.md" <<'EOF'
# Hero Configuration

## Repository

- default-branch: main # the trunk
- quoted-value: "develop"
- empty-value:
- spaced-value:    padded
EOF

check "field: strips trailing comment" \
  "main" "$(hero_field default-branch "$TMP/cfg")"
check "field: strips surrounding quotes" \
  "develop" "$(hero_field quoted-value "$TMP/cfg")"
check "field: trims padding" \
  "padded" "$(hero_field spaced-value "$TMP/cfg")"

hero_field absent-key "$TMP/cfg" >/dev/null 2>&1
check "field: absent returns 1" "1" "$?"

hero_field empty-value "$TMP/cfg" >/dev/null 2>&1
check "field: present-but-empty returns 1" "1" "$?"

# Option injection: a value beginning with `-` reaches git as an OPTION.
# `git fetch origin --upload-pack=<cmd>` executes <cmd> through a shell, so a
# checked-in HERO.md in a cloned repo becomes arbitrary code execution.
cat > "$TMP/cfg/HERO.md" <<'EOF'
- default-branch: --upload-pack=touch /tmp/hero_lib_test_pwned;git-upload-pack
EOF
hero_field default-branch "$TMP/cfg" >/dev/null 2>&1
check "field: rejects leading-dash value (option injection)" "2" "$?"
check "field: rejected value falls back to main" \
  "main" "$(hero_default_branch "$TMP/cfg" 2>/dev/null)"

# ---------- hero_ready_items -----------------------------------------------

W="$TMP/w/my-work"
mkdir -p "$W"

item() { # file id title status deps
  cat > "$W/$1" <<EOF
---
id: $2
title: $3
status: $4
depends_on: $5
---
EOF
}

item 001-done.md 1 "Finished" "done" "[]"
item 002-todo.md 2 "Unblocked" "todo" "[1]"
item 003-blocked.md 3 "Waiting" "todo" "[2]"
item 004-active.md 4 "In flight" "in-progress" "[1]"
item 005-pad.md 007 "Zero padded" "done" "[]"
item 006-padref.md 6 "Refs padded id" "todo" "[7]"
item 007-dangling.md 8 "Dangling ref" "todo" "[99]"
item 008-caps.md 9 "Capitalized status" "DONE" "[]"

OUT="$(hero_ready_items "$W" 2>/dev/null)"

state_of() { printf '%s' "$OUT" | awk -v f="$1" '$2 == f { print $1; exit }'; }

check "ready: satisfied dep is READY"        "READY"   "$(state_of 002-todo.md)"
check "ready: unmet dep is blocked"          "blocked" "$(state_of 003-blocked.md)"
check "ready: in-progress is active, not READY" "active" "$(state_of 004-active.md)"
check "ready: done items are listed"         "done"    "$(state_of 001-done.md)"
# 007 and 7 must compare equal, or a zero-padded id blocks its dependents.
check "ready: zero-padded id resolves"       "READY"   "$(state_of 006-padref.md)"
# A dangling reference must block, not silently resolve.
check "ready: dangling dep blocks"           "blocked" "$(state_of 007-dangling.md)"
# `DONE` must count as done, or every dependent stays blocked forever.
check "ready: status match is case-insensitive" "done"  "$(state_of 008-caps.md)"

# A non-numeric id used to be a FATAL arithmetic error: the function emitted
# NOTHING, which a caller reads as an empty plate rather than as a failure.
item 009-badid.md "AH-12" "Non-numeric id" "done" "[]"
OUT2="$(hero_ready_items "$W" 2>/dev/null)"
COUNT2="$(printf '%s' "$OUT2" | grep -c . )"
check "ready: non-numeric id does not blank the listing" "9" "$COUNT2"
hero_ready_items "$W" 2>&1 >/dev/null | grep -q "non-numeric id"
check "ready: non-numeric id warns on stderr" "0" "$?"

# The store listing is data; notes belong on stderr.
NOTE="$(hero_ready_items "$TMP/nonexistent-store" 2>/dev/null)"
check "ready: missing store prints nothing to stdout" "" "$NOTE"

# Sourced into a caller's shell, a bare `cd` reroutes every later relative path.
BEFORE="$PWD"
hero_ready_items "$W" >/dev/null 2>&1
check "ready: does not change caller's cwd" "$BEFORE" "$PWD"

# ---------- hero_item_field ------------------------------------------------

cat > "$W/010-colon.md" <<'EOF'
---
id: 10
title: Fix auth: token refresh
status: todo
depends_on: []
success: e2e green: login under 30s
---
EOF

# Splitting on every ': ' truncated any value containing a colon — and
# `success` is the field Step 1c reads to decide whether to build.
check "item_field: title keeps its colon" \
  "Fix auth: token refresh" "$(hero_item_field "$W/010-colon.md" title)"
check "item_field: success keeps its colon" \
  "e2e green: login under 30s" "$(hero_item_field "$W/010-colon.md" success)"

# ---------- report ---------------------------------------------------------

if [ "$FAIL" -gt 0 ]; then
  echo "hero-lib: $PASS passed, $FAIL FAILED"
  exit 1
fi
echo "hero-lib: $PASS passed"
