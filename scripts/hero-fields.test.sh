#!/usr/bin/env bash

# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Regression table for scripts/hero-fields.sh.
#
# The map is what every `recalibrate` verb reports before it asks anything, so
# the cases here are the ways that report could lie: a set field reported as
# unset, a refused value reported as merely absent (which would send the verb
# to ask about a value that is actually present and dangerous), a broken
# reader reported as either, and a section heading found inside a code fence.
#
# The loop assertions at the bottom carry counters. Without them each one
# compares an empty accumulator against an empty expectation and passes
# whenever the loop examines nothing at all — including when hero-fields.sh
# does not exist.

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

# `platform` appears in the map twice — push-pr reads CI/CD's, ship-pr reads
# Deployment's — so both sections carry one here. hero-lib.sh calls this the
# trap its BLOCK argument exists for; without both sections in the fixture the
# scoping argument is never exercised and could be dropped with no test failing.
cat > "$R/HERO.md" <<'EOM'
# Hero Configuration

## Repository

- default-branch: release
- branch-convention:
- commit-convention: --exec=touch /tmp/pwned

## CI/CD

- platform: github-actions

## Deployment

- platform: fly

## Projects

### app

- language: go
EOM

cell() { # key column — output is TSV, so a field is addressed by its column
  awk -F'\t' -v k="$1" -v c="$2" '$2 == k { print $c }'
}

OUT=$("$FIELDS" push-pr "$R"); RC=$?
check "a clean read exits 0" "0" "$RC"

check "set field reports its value" \
  "release" "$(printf '%s\n' "$OUT" | cell default-branch 3)"

# `- branch-convention:` with nothing after it is a field the file carries but
# does not answer. Reporting it as set would hide exactly the case
# recalibrate exists to fix.
check "present-but-empty field is unset" \
  "(unset)" "$(printf '%s\n' "$OUT" | cell branch-convention 3)"

# A leading `-` makes the value an option to every git and gh command it
# reaches. hero_md_field refuses it; the map must say so rather than report
# the field as simply missing.
check "refused value is not reported as unset" \
  "(refused)" "$(printf '%s\n' "$OUT" | cell commit-convention 3)"

check "section row with the heading present" \
  "(present)" "$(printf '%s\n' "$OUT" | awk -F'\t' '$1 == "Projects" { print $3 }')"

check "section row with the heading absent" \
  "(absent)" "$("$FIELDS" setup-dev "$R" | awk -F'\t' '$1 == "Developer Setup" { print $3 }')"

# A field under a heading that does not exist needs a different question than
# a blank under a heading that does — phase 3 has to create the section.
check "field under a missing section is no-section" \
  "(no-section)" "$(printf '%s\n' "$OUT" | cell linters 3)"

# The same key under two headings. Read unscoped it returns the first match in
# the file, so both rows would say github-actions.
check "CI/CD platform is read from CI/CD" \
  "github-actions" "$(printf '%s\n' "$OUT" | awk -F'\t' '$1 == "CI/CD" && $2 == "platform" { print $3 }')"
check "Deployment platform is read from Deployment" \
  "fly" "$("$FIELDS" ship-pr "$R" | awk -F'\t' '$1 == "Deployment" && $2 == "platform" { print $3 }')"

# hero_md_field skips fenced blocks; the heading probe must agree with it, or
# a HERO.md quoting its own template reports sections it does not have.
mkdir -p "$TMP/fenced"
cat > "$TMP/fenced/HERO.md" <<'EOM'
# Hero Configuration

Example of what this file can hold:

```markdown
## Developer Setup

- tool: git
```
EOM
check "a heading inside a code fence is not present" \
  "(absent)" "$("$FIELDS" setup-dev "$TMP/fenced" | awk -F'\t' '$1 == "Developer Setup" { print $3 }')"

# No HERO.md at all: every row says so, and the command still succeeds —
# recalibrate reads the rows and sends the user to init-hero.
mkdir -p "$TMP/bare"
BARE=$("$FIELDS" push-pr "$TMP/bare"); check "missing HERO.md exits 0" "0" "$?"
check "every row is no-file when there is no HERO.md" \
  "9" "$(printf '%s\n' "$BARE" | tail -n +2 | grep -c '(no-file)' | tr -d ' ')"

# A reader that breaks must not look like a file that is merely empty. This is
# the case that turns a `--exec=` payload into a benign-looking blank.
mkdir -p "$TMP/shim"
sed 's/^hero_md_field() {/hero_md_field() { return 127;/' "$PLUGIN_ROOT/scripts/hero-lib.sh" > "$TMP/shim/hero-lib.sh"
cp "$FIELDS" "$TMP/shim/hero-fields.sh"
SHIM_OUT=$(bash "$TMP/shim/hero-fields.sh" push-pr "$R" 2>/dev/null); SHIM_RC=$?
check "a broken reader is not reported as unset" \
  "0" "$(printf '%s\n' "$SHIM_OUT" | grep -c '(unset)' | tr -d ' ')"
check "a broken reader fails the command" "1" "$SHIM_RC"

# A ROOT that does not exist is a caller bug, not a repo without config.
check "nonexistent ROOT exits 1" \
  "1" "$("$FIELDS" push-pr "$TMP/nope" >/dev/null 2>&1; echo $?)"

# `grep "^$SKILL|"` used to interpolate the argument as a regex, so `push.pr`
# printed push-pr's table and exited 0.
check "a regex metachar does not match a skill" \
  "2" "$("$FIELDS" 'push.pr' "$R" >/dev/null 2>&1; echo $?)"

check "unknown skill exits 2" \
  "2" "$("$FIELDS" nope "$R" >/dev/null 2>&1; echo $?)"

# --help is a slice of the header comment by line number, so it rots silently
# when that block is reflowed. Pin both ends of the range.
HELP=$("$FIELDS" --help)
check "--help does not start with the copyright" \
  "0" "$(printf '%s\n' "$HELP" | grep -c 'All Rights Reserved' | tr -d ' ')"
check "--help reaches the exit contract" \
  "1" "$(printf '%s\n' "$HELP" | grep -c '2 unknown skill' | tr -d ' ')"

# Both modes emit the same five columns, so one record type describes the
# whole command and a column index means the same thing in each.
check "--all rows all have 5 columns" \
  "" "$("$FIELDS" --all | awk -F'\t' 'NF != 5 { print NR }' | tr '\n' ' ' | sed 's/ $//')"

# The map is 80-odd hand-edited lines and will grow. A short row yields an
# empty DECIDES cell, so recalibrate reports a field without saying what it
# decides; a duplicate asks the same question twice in one run.
check "no duplicate SKILL/SECTION/KEY row" \
  "" "$("$FIELDS" --all | tail -n +2 | cut -f1-3 | sort | uniq -d | tr '\n' ' ' | sed 's/ $//')"
check "no DECIDES cell is empty" \
  "" "$("$FIELDS" --all | tail -n +2 | awk -F'\t' '$5 == "" { print $1 }' | sort -u | tr '\n' ' ' | sed 's/ $//')"
check "no DECIDES cell contains a pipe" \
  "0" "$("$FIELDS" --all | tail -n +2 | cut -f5 | grep -c '|' | tr -d ' ')"

check "--list is non-empty" \
  "yes" "$([ "$("$FIELDS" --list | wc -l | tr -d ' ')" -gt 0 ] && echo yes || echo no)"

# Every listed name is a real skill directory — catches a typo'd skill name in
# a new map row, which would otherwise surface only when someone runs the verb.
BAD_NAME=""
for name in $("$FIELDS" --list); do
  [ -d "$PLUGIN_ROOT/skills/$name" ] || BAD_NAME="$BAD_NAME $name"
done
check "every mapped name is a skill directory" "" "$BAD_NAME"

# init-hero is the whole-file pass: its recalibrate re-investigates the repo
# rather than reading a field table, so it is the one mapped skill that does
# not invoke this script. Naming the exemption here is what stops it being
# "fixed" into the loop below.
NO_INVOCATION="init-hero"

# The map is the claim and the skills are the truth. Match the frontmatter
# anchored to the first block: create-skill/SKILL.md carries a second
# `argument-hint:` at column 0 inside a fenced template, so an unanchored grep
# counts a skill whose *example* mentions the verb.
declares_verb() { # skill-dir
  awk 'NR == 1 { if ($0 != "---") exit 1; next }
       $0 == "---" { exit !found }
       /^argument-hint:.*recalibrate/ { found = 1 }
       END { exit !found }' "$1/SKILL.md" 2>/dev/null
}

MISSING=""
DECLARED=0
for d in "$PLUGIN_ROOT"/skills/*/; do
  name=$(basename "$d")
  declares_verb "$d" || continue
  DECLARED=$((DECLARED + 1))
  "$FIELDS" --list | grep -qx "$name" || MISSING="$MISSING $name"
done
check "every skill offering recalibrate has map rows" "" "$MISSING"

EXTRA=""
MAPPED=0
WRONG_CALL=""
for name in $("$FIELDS" --list); do
  MAPPED=$((MAPPED + 1))
  declares_verb "$PLUGIN_ROOT/skills/$name" || EXTRA="$EXTRA $name"
  # The binding a 16-file copy-paste actually breaks: a block still reading
  # `hero-fields.sh" push-pr` inside another skill prints the wrong table and
  # asks about fields that skill never reads.
  case " $NO_INVOCATION " in
    *" $name "*) ;;
    *) grep -q "hero-fields.sh\" $name\$" "$PLUGIN_ROOT/skills/$name/SKILL.md" ||
         WRONG_CALL="$WRONG_CALL $name" ;;
  esac
done
check "every mapped skill offers recalibrate" "" "$EXTRA"
check "every mapped skill invokes hero-fields.sh with its own name" "" "$WRONG_CALL"

# Both loops accumulate into a variable that starts empty, so each passes when
# it examines nothing. These two are what make them mean something.
check "the declared-skills loop examined every mapped skill" "$MAPPED" "$DECLARED"
check "the mapped-skills loop examined something" \
  "yes" "$([ "$MAPPED" -gt 0 ] && echo yes || echo no)"

echo "hero-fields: $PASS passed${FAIL:+, $FAIL FAILED}" | sed 's/, 0 FAILED//'
[ "$FAIL" -eq 0 ]
