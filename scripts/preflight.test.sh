#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Regression coverage for preflight.sh's pr-review-toolkit detection.
#
# Scoped to the one thing that broke: a marketplace install never lands at
# either legacy directory probe (it writes to
# plugins/cache/MARKETPLACE/PLUGIN/SHA, recorded in installed_plugins.json),
# so the WARN fired on every correctly-installed marketplace plugin. These
# cases pin the installed_plugins.json lookup and its fallback to the legacy
# directories, plus the WARN's step-number text.
#
# HOME is overridden per case so the real machine's plugin state (whatever it
# is) never leaks into the assertion.
#
# Usage: bash scripts/preflight.test.sh

set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")" && pwd)/preflight.sh"

PASS=0
FAIL=0
check() { # name  expected_contains  actual
  case "$3" in
    *"$2"*) PASS=$((PASS + 1)) ;;
    *)
      FAIL=$((FAIL + 1))
      printf 'FAIL  %s\n      expected to contain: [%s]\n      actual:              [%s]\n' "$1" "$2" "$3"
      ;;
  esac
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

run_tooling() { # FAKE_HOME -> pr-review-toolkit line from --bucket tooling
  HOME="$1" "$SCRIPT" --bucket tooling 2>&1 | grep -i 'pr-review-toolkit'
}

# Case 1: marketplace install recorded in installed_plugins.json, no legacy
# directory present -> OK. This is the regression case: before the fix, this
# state produced a WARN on every run.
FAKE_HOME_1="$TMP/marketplace-only"
mkdir -p "$FAKE_HOME_1/.claude/plugins"
printf '{"plugins": {"pr-review-toolkit@claude-plugins-official": [{"scope": "user", "installPath": "x"}]}}' \
  > "$FAKE_HOME_1/.claude/plugins/installed_plugins.json"
OUT1=$(run_tooling "$FAKE_HOME_1")
check "marketplace-only install -> OK" "OK" "$OUT1"

# Case 2: installed_plugins.json absent, legacy directory present -> OK
# (fallback path stays live for a hand-placed, non-marketplace install).
FAKE_HOME_2="$TMP/legacy-only"
mkdir -p "$FAKE_HOME_2/.claude/plugins/pr-review-toolkit"
OUT2=$(run_tooling "$FAKE_HOME_2")
check "legacy-directory-only install -> OK" "OK" "$OUT2"

# Case 3: installed_plugins.json present but lacking the key, no legacy
# directory -> WARN, with the corrected step number.
FAKE_HOME_3="$TMP/neither"
mkdir -p "$FAKE_HOME_3/.claude/plugins"
printf '{"plugins": {}}' > "$FAKE_HOME_3/.claude/plugins/installed_plugins.json"
OUT3=$(run_tooling "$FAKE_HOME_3")
check "no install anywhere -> WARN" "WARN" "$OUT3"
check "WARN cites the corrected step" "Step 5" "$OUT3"

echo ""
echo "preflight.test.sh: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
