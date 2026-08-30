#!/usr/bin/env bash

# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Regression table for scripts/hero-fields.sh.
#
# The map is what every `recalibrate` verb reports before it asks anything, so
# the cases here are the ways that report could lie: a skill listed in
# docs/RECALIBRATE.md with no rows, a set field reported as unset, a field
# refused by the reader reported as merely absent (which would send the verb
# to ask about a value that is actually present and dangerous), and a section
# reported present when its heading is not in the file.
#
# Usage: bash scripts/hero-fields.test.sh

set -uo pipefail

FIELDS="$(cd "$(dirname "$0")" && pwd)/hero-fields.sh"
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

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
R="$(cd "$TMP" && pwd -P)/repo"
mkdir -p "$R"

cat > "$R/HERO.md" <<'EOM'
# Hero Configuration

## Repository

- default-branch: release
- branch-convention:
- commit-convention: --exec=touch /tmp/pwned

## Projects

### app

- language: go
EOM

# Column helpers: the output is TSV, so a field is addressed by its column.
cell() { # key column
  awk -F'\t' -v k="$1" -v c="$2" '$2 == k { print $c }'
}

OUT=$("$FIELDS" push-pr "$R")

check "set field reports its value" \
  "release" "$(printf '%s\n' "$OUT" | cell default-branch 3)"

# `- branch-convention:` with nothing after it is a field the file carries but
# does not answer. Reporting it as set would hide exactly the case
# recalibrate exists to fix.
check "present-but-empty field is unset" \
  "unset" "$(printf '%s\n' "$OUT" | cell branch-convention 3)"

# A leading `-` makes the value an option to every git and gh command it
# reaches. hero_md_field refuses it; the map must say so rather than report
# the field as simply missing.
check "refused value is not reported as unset" \
  "refused" "$(printf '%s\n' "$OUT" | cell commit-convention 3)"

check "absent field is unset" \
  "unset" "$(printf '%s\n' "$OUT" | cell issue-prefix 3)"

check "section row with the heading present" \
  "present" "$(printf '%s\n' "$OUT" | awk -F'\t' '$1 == "Projects" { print $3 }')"

check "section row with the heading absent" \
  "absent" "$("$FIELDS" setup-dev "$R" | awk -F'\t' '$1 == "Developer Setup" { print $3 }')"

# `linters` sits under a heading that does not exist, so it is unset, not
# absent — the section check above covers `*` rows only.
check "field under a missing section is unset" \
  "unset" "$(printf '%s\n' "$OUT" | cell linters 3)"

check "unknown skill exits 2" \
  "2" "$("$FIELDS" nope "$R" >/dev/null 2>&1; echo $?)"

check "--list is sorted and unique" \
  "same" "$("$FIELDS" --list | { A=$(cat); B=$(printf '%s\n' "$A" | sort -u); [ "$A" = "$B" ] && echo same || echo differs; })"

# The map is the claim and the skills are the truth: a skill that offers
# `recalibrate` with no rows would report an empty table and then ask nothing.
MISSING=""
for d in "$PLUGIN_ROOT"/skills/*/; do
  name=$(basename "$d")
  grep -q '^argument-hint:.*recalibrate' "$d/SKILL.md" 2>/dev/null || continue
  "$FIELDS" --list | grep -qx "$name" || MISSING="$MISSING $name"
done
check "every skill offering recalibrate has map rows" "" "$MISSING"

# And the reverse: a map entry for a skill that does not offer the verb is a
# table nothing prints.
EXTRA=""
for name in $("$FIELDS" --list); do
  grep -q '^argument-hint:.*recalibrate' "$PLUGIN_ROOT/skills/$name/SKILL.md" 2>/dev/null ||
    EXTRA="$EXTRA $name"
done
check "every mapped skill offers recalibrate" "" "$EXTRA"

echo "hero-fields: $PASS passed${FAIL:+, $FAIL FAILED}" | sed 's/, 0 FAILED//'
[ "$FAIL" -eq 0 ]
