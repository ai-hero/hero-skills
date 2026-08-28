#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Tests for check-agents-md.sh.
#
# Not -e: the suite has to OBSERVE non-zero exits (1 is the contract for a
# failing repo), so errexit would kill it on the first case it exists to check.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="$HERE/check-agents-md.sh"

PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# fixture NAME — a repo root with a compliant 30-line AGENTS.md and the symlink.
fixture() {
  local d="$WORK/$1"
  mkdir -p "$d/.claude/rules"
  {
    echo "# AGENTS.md"
    echo
    echo "## Conventions"
    for i in $(seq 1 27); do echo "- Rule $i names a trap and the fix for it."; done
  } > "$d/AGENTS.md"
  ln -s AGENTS.md "$d/CLAUDE.md"
  echo "$d"
}

# lines N — print N filler lines.
lines() { for i in $(seq 1 "$1"); do echo "- filler line $i"; done; }

run() { out=$("$CHECK" "$@" 2>&1); rc=$?; }

# --- compliant repo ----------------------------------------------------------
d=$(fixture good)
run "$d"
check "good: rc" "0" "$rc"
check "good: no errors" "yes" "$(grep -q '0 error(s)' <<<"$out" && echo yes || echo no)"

# --- R1 ------------------------------------------------------------------------
d=$(fixture both)
rm "$d/CLAUDE.md"; cp "$d/AGENTS.md" "$d/CLAUDE.md"
run "$d"
check "R1 both regular files: rc" "1" "$rc"
check "R1 both regular files: named" "yes" "$(grep -q 'R1: AGENTS.md and CLAUDE.md are both regular' <<<"$out" && echo yes || echo no)"

d=$(fixture claude_only)
rm "$d/CLAUDE.md"; mv "$d/AGENTS.md" "$d/CLAUDE.md"
run "$d"
check "R1 CLAUDE.md only: rc (warn, not error)" "0" "$rc"
check "R1 CLAUDE.md only: warned" "yes" "$(grep -q 'WARN:  R1' <<<"$out" && echo yes || echo no)"

d=$(fixture wrong_link)
rm "$d/CLAUDE.md"; ln -s README.md "$d/CLAUDE.md"
run "$d"
check "R1 wrong symlink target: rc" "1" "$rc"

d=$(fixture neither); rm "$d/CLAUDE.md" "$d/AGENTS.md"
run "$d"
check "R1 neither: rc" "2" "$rc"

# --- R2 ------------------------------------------------------------------------
d=$(fixture too_long); lines 180 >> "$d/AGENTS.md"
run "$d"
check "R2 210 lines: rc" "1" "$rc"
check "R2 210 lines: named" "yes" "$(grep -q 'R2: AGENTS.md is 210 lines' <<<"$out" && echo yes || echo no)"

d=$(fixture warn_len); lines 130 >> "$d/AGENTS.md"
run "$d"
check "R2 160 lines: rc (warn only)" "0" "$rc"
check "R2 160 lines: warned" "yes" "$(grep -q 'WARN:  R2' <<<"$out" && echo yes || echo no)"

# HTML comments are stripped before load, so they must not count.
d=$(fixture comments)
{ echo "<!--"; for i in $(seq 1 180); do echo "maintainer note $i"; done; echo "-->"; } >> "$d/AGENTS.md"
run "$d"
check "R2 comment lines are free: rc" "0" "$rc"

# --- R3 ------------------------------------------------------------------------
d=$(fixture rule_unscoped); lines 61 >> "$d/.claude/rules/big.md"
run "$d"
check "R3 unscoped 61-line rule: rc" "1" "$rc"
check "R3 unscoped 61-line rule: named" "yes" "$(grep -q 'R3: .claude/rules/big.md' <<<"$out" && echo yes || echo no)"

d=$(fixture rule_scoped)
printf -- '---\ndescription: x\npaths:\n  - "src/**"\n---\n' > "$d/.claude/rules/big.md"; lines 61 >> "$d/.claude/rules/big.md"
run "$d"
check "R3 scoped 61-line rule: rc" "0" "$rc"

d=$(fixture rule_small); lines 20 >> "$d/.claude/rules/small.md"
run "$d"
check "R3 unscoped 20-line rule: rc" "0" "$rc"

# --- R4 ------------------------------------------------------------------------
d=$(fixture shouty); for i in $(seq 1 6); do echo "- IMPORTANT: rule $i" >> "$d/AGENTS.md"; done
run "$d"
check "R4 six emphasized lines: rc" "1" "$rc"

d=$(fixture two_emph); printf -- '- IMPORTANT: one\n- NEVER do two\n' >> "$d/AGENTS.md"
run "$d"
check "R4 two emphasized lines: rc (warn)" "0" "$rc"
check "R4 two emphasized lines: warned" "yes" "$(grep -q 'WARN:  R4' <<<"$out" && echo yes || echo no)"

# Emphasis inside a code fence is code, not shouting.
d=$(fixture fence_emph); { echo '```bash'; for i in $(seq 1 6); do echo "MUST_SET_$i=1"; done; echo '```'; } >> "$d/AGENTS.md"
run "$d"
check "R4 emphasis in fence: rc" "0" "$rc"

# --- R5 ------------------------------------------------------------------------
d=$(fixture layout_table)
{ echo; echo "## Layout"; echo; echo "| Path | Purpose |"; echo "| --- | --- |"
  for i in $(seq 1 6); do echo "| \`dir$i/\` | thing $i |"; done; echo; echo "## After"; echo "- x"; } >> "$d/AGENTS.md"
run "$d"
check "R5 8-line Layout table: rc" "1" "$rc"
check "R5 8-line Layout table: named" "yes" "$(grep -q 'R5: "## Layout" has 8 lines' <<<"$out" && echo yes || echo no)"

d=$(fixture layout_pointer)
{ echo; echo "## Tech Stack"; echo "See HERO.md."; echo; echo "## Layout"; echo "\`ls\` shows it; assets/ is vendored downstream."; } >> "$d/AGENTS.md"
run "$d"
check "R5 pointer sections: rc" "0" "$rc"

# A derivable heading's body ends at the next heading of the same level —
# the following section's lines must not be blamed on it.
d=$(fixture layout_then_long)
{ echo; echo "## Layout"; echo "See HERO.md."; echo; echo "## Conventions"; lines 10; } >> "$d/AGENTS.md"
run "$d"
check "R5 sibling section not counted: rc" "0" "$rc"

# Only a heading that IS the name is derivable; one that contains it is a rule.
d=$(fixture layout_rules)
{ echo; echo "## Page layout rules"; lines 8; } >> "$d/AGENTS.md"
run "$d"
check "R5 heading containing 'layout': rc" "0" "$rc"

d=$(fixture layout_suffixed)
{ echo; echo "## Data model — Phase 1 (singleton)"; lines 8; } >> "$d/AGENTS.md"
run "$d"
check "R5 name with trailing dash clause: rc" "1" "$rc"

# docs/AGENTS-MD.md is the spec: every name it lists under R5 must trip the
# checker, so the doc and the regex cannot drift apart.
DOC="$HERE/../docs/AGENTS-MD.md"
for name in $(grep -E '^5\. \*\*R5' "$DOC" | grep -oE '`[^`]+`' | tr -d '`' | tr ' ' '_'); do
  d=$(fixture "doc_r5_$name")
  { echo; echo "## ${name//_/ }"; lines 8; } >> "$d/AGENTS.md"
  run "$d"
  check "R5 doc-listed heading '${name//_/ }': rc" "1" "$rc"
done

# --- R6 ------------------------------------------------------------------------
# Same contract for R6: every phrase the doc lists must be caught.
while IFS= read -r phrase; do
  d=$(fixture "doc_r6_$(tr -c 'a-z' _ <<<"$phrase")")
  echo "- Careful, this is $phrase here." >> "$d/AGENTS.md"
  run "$d"
  check "R6 doc-listed phrase '$phrase': rc" "1" "$rc"
done < <(grep -E '^6\. \*\*R6' "$DOC" | grep -oE '`[^`]+`' | tr -d '`')

d=$(fixture banned); echo "- This config is load-bearing." >> "$d/AGENTS.md"
run "$d"
check "R6 banned phrase in prose: rc" "1" "$rc"
check "R6 banned phrase in prose: line shown" "yes" "$(grep -q 'load-bearing' <<<"$out" && echo yes || echo no)"

d=$(fixture banned_in_rule); echo "Give an honest take." > "$d/.claude/rules/writing.md"
run "$d"
check "R6 banned phrase in a rule: rc" "1" "$rc"

# A writing rule may list the phrases it bans, inside a code fence.
d=$(fixture banned_fenced)
printf -- 'Do not write these:\n\n```text\nload-bearing\nhonest take\n```\n' > "$d/.claude/rules/writing.md"
run "$d"
check "R6 banned list in fence: rc" "0" "$rc"

# --- --warn-only ----------------------------------------------------------------
d=$(fixture warn_only); lines 180 >> "$d/AGENTS.md"
run "$d" --warn-only
check "--warn-only on failing repo: rc" "0" "$rc"
check "--warn-only still reports" "yes" "$(grep -q 'ERROR: R2' <<<"$out" && echo yes || echo no)"

# --- --commit-msg ----------------------------------------------------------------
m="$WORK/msg"; echo "feat: the load-bearing fix" > "$m"
run --commit-msg "$m"
check "commit-msg banned: rc" "1" "$rc"
echo "feat: strip inbound headers in filterHeaders" > "$m"
run --commit-msg "$m"
check "commit-msg clean: rc" "0" "$rc"
# Comment lines in a commit template are not the message.
printf 'feat: x\n# load-bearing is mentioned in this git comment\n' > "$m"
run --commit-msg "$m"
check "commit-msg banned only in # comment: rc" "0" "$rc"
# `git commit -v` puts the staged diff under a scissors line; git strips it
# after the hook, so a diff that mentions a phrase must not fail the commit.
printf 'feat: x\n# ------------------------ >8 ------------------------\n+settings are load-bearing here\n' > "$m"
run --commit-msg "$m"
check "commit-msg banned only below scissors: rc" "0" "$rc"

echo ""
echo "check-agents-md.test.sh: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
