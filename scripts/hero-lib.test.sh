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

W="$TMP/w/.plans"
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

# state_of FILE [LISTING] — the STATE column for FILE, defaulting to $OUT.
state_of() { printf '%s' "${2:-$OUT}" | awk -v f="$1" '$2 == f { print $1; exit }'; }

check "ready: satisfied dep is READY"        "READY"   "$(state_of 002-todo.md)"
check "ready: unmet dep is blocked"          "blocked" "$(state_of 003-blocked.md)"
check "ready: in-progress is active, not READY" "active" "$(state_of 004-active.md)"
check "ready: done items are listed"         "done"    "$(state_of 001-done.md)"
# 007 and 7 must compare equal, or a zero-padded legacy id blocks its dependents.
check "ready: zero-padded id resolves"       "READY"   "$(state_of 006-padref.md)"
# A dangling reference must block, not silently resolve — and must SAY it is
# dangling: nothing will ever mark a nonexistent id done, so an unnamed
# dangling ref reads as ordinary waiting when it is actually forever.
check "ready: dangling dep blocks"           "blocked" "$(state_of 007-dangling.md)"
printf '%s' "$OUT" | grep -q '007-dangling.md.*\[missing dep: 99\]'
check "ready: dangling dep is named on the listing" "0" "$?"
hero_ready_items "$W" 2>&1 >/dev/null | grep -q "no item carries"
check "ready: dangling dep warns on stderr" "0" "$?"
# `DONE` must count as done, or every dependent stays blocked forever.
check "ready: status match is case-insensitive" "done"  "$(state_of 008-caps.md)"

# Ids are integers by convention, but a hand-written oddball must degrade
# gracefully: a non-numeric id used to be a FATAL arithmetic error that
# emitted NOTHING — a caller reads that as an empty plate, not as a failure.
item 009-strid.md "AH-12" "String id" "done" "[]"
item 00a-strdep.md "b3f2" "Depends on string id" "todo" "[ah-12]"
OUT2="$(hero_ready_items "$W" 2>/dev/null)"
COUNT2="$(printf '%s' "$OUT2" | grep -c . )"
check "ready: string id does not blank the listing" "10" "$COUNT2"
# Ids compare case-insensitively — `ah-12` must resolve against `AH-12`.
check "ready: string-id dep resolves case-insensitively" "READY" "$(state_of 00a-strdep.md "$OUT2")"

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

# ---------- silent-READY regressions ---------------------------------------
#
# Each of these reported an item as READY (or its dependent as permanently
# blocked) with nothing on stderr — an agent would have picked up work whose
# dependencies do not exist, or skipped work that was actually unblocked.

cat > "$W/011-mldeps.md" <<'EOF'
---
id: 11
title: Block sequence deps
status: todo
depends_on:
  - 99
  - 100
---
EOF
# YAML block sequences are the standard list form. Only the inline form parsed,
# so this yielded "no dependencies" and the item was handed out as READY.
OUT3="$(hero_ready_items "$W" 2>/dev/null)"
check "deps: block sequence blocks" "blocked" "$(state_of 011-mldeps.md "$OUT3")"

cat > "$W/012-quoted.md" <<'EOF'
---
id: 12
title: Quoted status
status: "done"
depends_on: []
---
EOF
cat > "$W/013-dep.md" <<'EOF'
---
id: 13
title: Depends on the quoted-done item
status: todo
depends_on: [12]
---
EOF
item 015-qdep.md 15 "Quoted inline dep" "todo" '["12"]'
OUT4="$(hero_ready_items "$W" 2>/dev/null)"
# A quoted status did not equal `done`, so every dependent blocked forever.
check "status: quoted done counts as done" "done"  "$(state_of 012-quoted.md "$OUT4")"
check "status: its dependent unblocks"     "READY" "$(state_of 013-dep.md "$OUT4")"
# The inline-array parser must strip entry quotes like the block parser does,
# or `depends_on: ["12"]` emits `"12"` and never matches id 12.
check "deps: quoted inline entry resolves" "READY" "$(state_of 015-qdep.md "$OUT4")"

cat > "$W/014-body.md" <<'EOF'
---
id: 14
title: Body mentions a status
depends_on: []
---

Run until `status: done` appears in the log.
EOF
OUT5="$(hero_ready_items "$W" 2>/dev/null)"
# Frontmatter only — a body line must not be read as the item's own field.
check "field: body line is not frontmatter" "READY" "$(state_of 014-body.md "$OUT5")"

hero_ready_items "$TMP/definitely-not-a-store" >/dev/null 2>&1
check "ready: missing store returns non-zero" "1" "$?"

# ---------- branch-name gate -----------------------------------------------
#
# hero_field's character gate cannot catch a value that is a valid STRING but
# not a valid BRANCH: git reads these as something other than the branch they
# resemble. This gate existed but was never wired to a caller.

branch_case() { # value expected
  printf '# H\n\n- default-branch: %s\n' "$1" > "$TMP/cfg/HERO.md"
  check "branch: $1" "$2" "$(hero_default_branch "$TMP/cfg" 2>/dev/null)"
}
branch_case "main:refs/heads/evil" "main"
branch_case "main^"                "main"
branch_case "@{u}"                 "main"
branch_case ".."                   "main"
branch_case "develop"              "develop"
branch_case "release/2.0"          "release/2.0"

# ---------- report ---------------------------------------------------------

if [ "$FAIL" -gt 0 ]; then
  echo "hero-lib: $PASS passed, $FAIL FAILED"
  exit 1
fi
echo "hero-lib: $PASS passed"
