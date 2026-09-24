#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Tests for validate.sh's own guards: the sanctioned WAYFARE_ROOT line scan,
# the '../../' escape scan, and cross-agent manifest agreement.
#
# validate.sh derives PLUGIN_ROOT from "$(cd "$(dirname "$0")/.." && pwd)",
# so each fixture is a full copy of this plugin's own skills/, references/,
# docs/, assets/ and manifests (known-clean, since `bash scripts/validate.sh`
# passes on the real tree) plus a copy of validate.sh itself, with exactly
# one thing perturbed per case. A truly minimal tree would trip validate.sh's
# own hardcoded skill lists (CHAINED_SKILLS, the wayfare-build-task
# work-item-store guard) with unrelated errors that have nothing to do with
# the case under test.
#
# Not -e: cases assert on non-zero exit codes, which errexit would kill the
# suite on the first one.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_REPO="$(cd "$HERE/.." && pwd)"

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
check_contains() { # name haystack needle
  # Here-string, not `printf | grep -q`: under pipefail, grep -q exits the
  # moment it matches, SIGPIPEs a still-writing printf on large output, and
  # a genuine match then reads as a failure. See scripts/validate.sh's own
  # chained-skill guard for the same fix.
  if grep -qF "$3" <<< "$2"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL  %s\n      expected to contain: [%s]\n' "$1" "$3"
  fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

BASE="$WORK/base"
mkdir -p "$BASE/scripts" "$BASE/.claude-plugin" "$BASE/.codex-plugin" "$BASE/.agents/plugins" "$BASE/assets"
cp "$ROOT_REPO/scripts/validate.sh" "$BASE/scripts/validate.sh"
cp -R "$ROOT_REPO/skills" "$BASE/skills"
cp -R "$ROOT_REPO/references" "$BASE/references"
cp -R "$ROOT_REPO/docs" "$BASE/docs"
cp "$ROOT_REPO/README.md" "$BASE/README.md"
cp "$ROOT_REPO/AGENTS.md" "$BASE/AGENTS.md"
cp -R "$ROOT_REPO/assets/auto-approve" "$BASE/assets/auto-approve"
cp -R "$ROOT_REPO/assets/design-system" "$BASE/assets/design-system"
cp -R "$ROOT_REPO/assets/fleet" "$BASE/assets/fleet"
cp "$ROOT_REPO/.claude-plugin/plugin.json" "$BASE/.claude-plugin/plugin.json"
cp "$ROOT_REPO/.claude-plugin/marketplace.json" "$BASE/.claude-plugin/marketplace.json"
cp "$ROOT_REPO/.codex-plugin/plugin.json" "$BASE/.codex-plugin/plugin.json"
cp "$ROOT_REPO/.agents/plugins/marketplace.json" "$BASE/.agents/plugins/marketplace.json"

fixture() { # NAME -> path; a fresh copy of BASE
  local d="$WORK/$1"
  rm -rf "$d"
  cp -R "$BASE" "$d"
  echo "$d"
}

run_validate() { # DIR -> sets OUT and RC
  OUT=$("$1/scripts/validate.sh" 2>&1)
  RC=$?
}

# A dummy skill for the WAYFARE_ROOT-scan and '../../'-scan cases, so the
# mutation under test doesn't have to land inside a real pipeline skill and
# risk tripping one of validate.sh's other, unrelated guards.
mk_zztest_skill() { # DIR BODY_EXTRA
  mkdir -p "$1/skills/zztest"
  cat > "$1/skills/zztest/SKILL.md" <<EOF
---
name: zztest
description: A test skill used only by validate.test.sh fixtures, long enough.
---

# zztest

$2
EOF
}

# ---------- clean fixture ---------------------------------------------------

d=$(fixture clean)
run_validate "$d"
check "clean fixture: rc" "0" "$RC"
check_contains "clean fixture: ALL CHECKS PASSED" "$OUT" "ALL CHECKS PASSED"

# ---------- sanctioned WAYFARE_ROOT line: fence variants --------------------

d=$(fixture fence-col0)
printf '\n```bash\necho "$CLAUDE_PLUGIN_ROOT"\n```\n' >> "$d/references/zz.md"
run_validate "$d"
check "column-0 fence: rc" "1" "$RC"
check_contains "column-0 fence: reported" "$OUT" "outside the one sanctioned WAYFARE_ROOT line"

d=$(fixture fence-indented)
printf '\n  ```bash\n  echo "$CLAUDE_PLUGIN_ROOT"\n  ```\n' >> "$d/references/zz.md"
run_validate "$d"
check "indented fence: rc" "1" "$RC"
check_contains "indented fence: reported" "$OUT" "outside the one sanctioned WAYFARE_ROOT line"

d=$(fixture fence-tilde)
printf '\n~~~bash\necho "$CLAUDE_PLUGIN_ROOT"\n~~~\n' >> "$d/references/zz.md"
run_validate "$d"
check "~~~ fence: rc" "1" "$RC"
check_contains "~~~ fence: reported" "$OUT" "outside the one sanctioned WAYFARE_ROOT line"

d=$(fixture sanctioned-trailing)
printf '\n```bash\nWAYFARE_ROOT="${CLAUDE_PLUGIN_ROOT:-${WAYFARE_ROOT:-$HOME/.claude/plugins/wayfare-skills}}"  # comment\n```\n' >> "$d/references/zz.md"
run_validate "$d"
check "sanctioned line + trailing text: rc" "1" "$RC"
check_contains "sanctioned line + trailing text: reported" "$OUT" "outside the one sanctioned WAYFARE_ROOT line"

d=$(fixture hardcoded-path)
printf '\n```bash\nPREFLIGHT="$HOME/.claude/plugins/wayfare-skills/scripts/preflight.sh"\n```\n' >> "$d/references/zz.md"
run_validate "$d"
check "hardcoded plugin path: rc" "1" "$RC"
check_contains "hardcoded plugin path: reported" "$OUT" "outside the one sanctioned WAYFARE_ROOT line"

d=$(fixture wayfare-root-scan-zero-files)
rm -rf "$d/skills" "$d/references"
mkdir -p "$d/skills" "$d/references"
run_validate "$d"
check_contains "WAYFARE_ROOT scan, zero files: reported" "$OUT" "WAYFARE_ROOT scan of skills/ and references/ found zero files"

# ---------- '../../' escape guard -------------------------------------------

d=$(fixture dotdot-bare)
mk_zztest_skill "$d" 'See ../../scripts/x for details.'
run_validate "$d"
check "'../../scripts/x': rc" "1" "$RC"
check_contains "'../../scripts/x': reported" "$OUT" "does not point cleanly into references/ or docs/"

d=$(fixture dotdot-walked-back-out)
mk_zztest_skill "$d" 'See ../../references/../scripts/x for details.'
run_validate "$d"
check "'../../references/../scripts/x': rc" "1" "$RC"
check_contains "'../../references/../scripts/x': reported" "$OUT" "does not point cleanly into references/ or docs/"

d=$(fixture dotdot-docs-passes)
mk_zztest_skill "$d" 'See ../../docs/X for details.'
run_validate "$d"
check "'../../docs/X': not reported" "" "$(printf '%s' "$OUT" | grep -o 'does not point cleanly' || true)"

d=$(fixture dotdot-scan-zero-files)
rm -rf "$d/skills"
mkdir -p "$d/skills"
run_validate "$d"
check_contains "'../../' scan, zero files: reported" "$OUT" "'../../' scan of skills/ found zero files"

# ---------- goal-turn build launch: no stray permissions grant --------------

d=$(fixture goals-launch-carries-grant)
# Insert a line into the SAME paragraph as the commit-only literal (no blank
# line before it), the shape the guard exists to catch: a later edit putting
# the permissions literal back into step 4's per-task build invocation.
awk '
  { print }
  /commit only: goal G branch GOAL_BRANCH/ {
    print "   Also carries `gates pre-authorized in-session` right here."
  }
' "$d/references/goals.md" > "$d/references/goals.md.tmp" && mv "$d/references/goals.md.tmp" "$d/references/goals.md"
run_validate "$d"
check "goals.md launch paragraph carries grant: rc" "1" "$RC"
check_contains "goals.md launch paragraph carries grant: reported" "$OUT" "carries both the commit-only line and the permissions grant"

d=$(fixture goals-grant-different-paragraph)
# Same two literals, but the grant lands in its own paragraph (a blank line
# on each side) rather than merged into the build-launch one — must pass,
# since it's the paragraph, not the file, that's guarded.
awk '
  { print }
  /commit only: goal G branch GOAL_BRANCH/ {
    print ""
    print "   A separate paragraph naming `gates pre-authorized in-session`."
  }
' "$d/references/goals.md" > "$d/references/goals.md.tmp" && mv "$d/references/goals.md.tmp" "$d/references/goals.md"
run_validate "$d"
check "goals.md grant in its own paragraph: rc" "0" "$RC"

d=$(fixture goals-launch-literal-missing)
sed 's/commit only: goal G branch GOAL_BRANCH/commit-only mode/' "$d/references/goals.md" > "$d/references/goals.md.tmp" && mv "$d/references/goals.md.tmp" "$d/references/goals.md"
run_validate "$d"
check "goals.md missing commit-only literal: rc" "1" "$RC"
check_contains "goals.md missing commit-only literal: reported" "$OUT" "no longer carries the commit-only build-launch literal"

# ---------- cross-agent manifest agreement ----------------------------------

d=$(fixture codex-version-mismatch)
jq '.version = "9.9.9"' "$d/.codex-plugin/plugin.json" > "$d/.codex-plugin/plugin.json.tmp" && mv "$d/.codex-plugin/plugin.json.tmp" "$d/.codex-plugin/plugin.json"
run_validate "$d"
check "codex version mismatch: rc" "1" "$RC"
check_contains "codex version mismatch: reported" "$OUT" "Manifest versions disagree"

d=$(fixture codex-skills-path-wrong)
jq '.skills = "./other/"' "$d/.codex-plugin/plugin.json" > "$d/.codex-plugin/plugin.json.tmp" && mv "$d/.codex-plugin/plugin.json.tmp" "$d/.codex-plugin/plugin.json"
run_validate "$d"
check "codex skills path wrong: rc" "1" "$RC"
check_contains "codex skills path wrong: reported" "$OUT" "not './skills/'"

d=$(fixture agents-name-missing)
jq '.plugins[0].name = "wrongname"' "$d/.agents/plugins/marketplace.json" > "$d/.agents/plugins/marketplace.json.tmp" && mv "$d/.agents/plugins/marketplace.json.tmp" "$d/.agents/plugins/marketplace.json"
run_validate "$d"
check "agents entry name missing: rc" "1" "$RC"
check_contains "agents entry name missing: reported" "$OUT" "no .plugins entry named 'wayfare'"

d=$(fixture agents-name-duplicate)
jq '.plugins += [.plugins[0]]' "$d/.agents/plugins/marketplace.json" > "$d/.agents/plugins/marketplace.json.tmp" && mv "$d/.agents/plugins/marketplace.json.tmp" "$d/.agents/plugins/marketplace.json"
run_validate "$d"
check "duplicate agents entry: rc" "1" "$RC"
check_contains "duplicate agents entry: reported" "$OUT" "more than one .plugins entry named 'wayfare'"

d=$(fixture agents-plugins-not-array)
echo '{"plugins":"oops"}' > "$d/.agents/plugins/marketplace.json"
run_validate "$d"
check "'.plugins' not an array: rc" "1" "$RC"
check_contains "'.plugins' not an array: no abort, error reported" "$OUT" "no .plugins entry named 'wayfare'"

d=$(fixture claude-manifest-missing)
rm -f "$d/.claude-plugin/plugin.json"
run_validate "$d"
check "missing .claude-plugin/plugin.json: nonzero rc" "yes" "$([ "$RC" -ne 0 ] && echo yes || echo no)"
check "missing .claude-plugin/plugin.json: no unbound-variable crash" "" "$(printf '%s' "$OUT" | grep -io 'unbound variable' || true)"

if [ "$FAIL" -gt 0 ]; then
  echo "validate: $PASS passed, $FAIL FAILED"
  exit 1
fi
# Floor on the case count: a fixture-build step failing silently (e.g. a `cp`
# that stops matching a moved directory) would otherwise leave every
# check() call skipped rather than failed, and the suite would report clean.
MIN_CASES=20
if [ "$PASS" -lt "$MIN_CASES" ]; then
  echo "validate: only $PASS cases ran, expected >= $MIN_CASES — a fixture step stopped executing" >&2
  exit 1
fi
echo "validate: $PASS passed"
