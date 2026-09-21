#!/usr/bin/env bash

# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Runs references/loading.md's Step 0 block, which every wayfare skill pastes
# verbatim and which nothing else executes.
#
# It is documentation, so no suite reached it: a change that broke the
# unmigrated lane, or collapsed one of the connection states, shipped with
# every other suite green. The block ends in one summary line, and that line is
# the contract this asserts against.
#
# The cases are the state distinctions the connections standard exists to keep
# (docs/CONNECTIONS.md): a migrated repo, a repo still on the flat keys, and a
# repo that has declared `type: none`. Each was a silent collapse at some point
# in this PR.
#
# Usage: bash scripts/loading.test.sh

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_REPO="$(cd "$HERE/.." && pwd)"
DOC="$ROOT_REPO/references/loading.md"

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

# The first ```bash fence in the doc is Step 0. Extracting rather than copying
# is the point: a copy here would drift from the block skills actually run.
STEP0="$TMP/step0.sh"
awk '/^```bash$/ { if (!seen) { seen = 1; f = 1; next } } f && /^```$/ { exit } f' "$DOC" > "$STEP0"
check "step 0: the block was extracted" \
  "yes" "$([ -s "$STEP0" ] && echo yes || echo no)"
check "step 0: the block parses" \
  "yes" "$(bash -n "$STEP0" 2>/dev/null && echo yes || echo no)"

# A fixture repo. `.plans/` gets created by hero_work_store inside the block,
# so these are real git repos, not bare directories.
mkrepo() { # DIR
  mkdir -p "$1"
  git -C "$1" init -q 2>/dev/null
  git -C "$1" config user.email t@example.com
  git -C "$1" config user.name t
  : > "$1/README.md"
  git -C "$1" add -A >/dev/null 2>&1
  git -C "$1" commit -qm init >/dev/null 2>&1
}

run_step0() { # REPO_DIR -> the summary line
  ( cd "$1" && CLAUDE_PLUGIN_ROOT="$ROOT_REPO" bash "$STEP0" 2>/dev/null ) \
    | grep '^wayfare: source=' | head -1
}
run_step0_err() { # REPO_DIR -> stderr only
  # `{ ...; } 2>&1` with stdout sent to /dev/null inside the group. The
  # `2>&1 >/dev/null` spelling does the same thing, but SC2069 rejects it, and
  # a comment line starting with the linter's own name is read as a directive.
  ( cd "$1" && { CLAUDE_PLUGIN_ROOT="$ROOT_REPO" bash "$STEP0" >/dev/null; } 2>&1 )
}

UUID=6f1c2e88-0a3d-4c77-9d21-8b5e2f4a1c90

# ---------- migrated ------------------------------------------------------

mkrepo "$TMP/migrated"
cat > "$TMP/migrated/HERO.md" <<EOF
# Hero Configuration

## Connections

### design

- type: claude-design
- at: $UUID
- reach: designsync
- ux-flow: flows/

## Wayfare

- source-repo: .
EOF
OUT=$(run_step0 "$TMP/migrated")
check "migrated: the design id is extracted" \
  "yes" "$(printf '%s' "$OUT" | grep -q "design=$UUID" && echo yes || echo no)"
check "migrated: the reach is reported" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'reach=designsync' && echo yes || echo no)"
check "migrated: a set ux-flow survives" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'ux-flow=flows/' && echo yes || echo no)"
check "migrated: no migration nudge" \
  "" "$(run_step0_err "$TMP/migrated" | grep 'still carries' || true)"

# ---------- unmigrated ----------------------------------------------------
# The lane that breaks silently: reading only the new shape reports a
# CONFIGURED design target as absent, and the run drops to self-review.

mkrepo "$TMP/legacy"
cat > "$TMP/legacy/HERO.md" <<EOF
# Hero Configuration

## Wayfare

- source-repo: .
- design-project: $UUID
- design-transport: manual
EOF
OUT=$(run_step0 "$TMP/legacy")
check "unmigrated: the flat design-project is still read" \
  "yes" "$(printf '%s' "$OUT" | grep -q "design=$UUID" && echo yes || echo no)"
check "unmigrated: the flat transport is still read" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'reach=manual' && echo yes || echo no)"
check "unmigrated: and it says so, so the fix is visible" \
  "yes" "$(run_step0_err "$TMP/legacy" | grep -q "design-project" && echo yes || echo no)"

# ---------- declared absent ------------------------------------------------
# `type: none` answers for the whole block. UX_FLOW must be NONE, not UNSET:
# UNSET is "nobody has looked", and sync goes looking on it every run.

mkrepo "$TMP/declared"
cat > "$TMP/declared/HERO.md" <<'EOF'
# Hero Configuration

## Connections

### design

- type: none

### design-system

- type: none

## Wayfare

- source-repo: .
EOF
OUT=$(run_step0 "$TMP/declared")
check "declared none: ux-flow is NONE, not UNSET" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'ux-flow=NONE' && echo yes || echo no)"
check "declared none: the design target is none" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'design=none' && echo yes || echo no)"
# UNSET, NONE and SELF all print `none` without the state, and sync's config
# gate branches on exactly that difference.
check "declared none: ds-repo carries its state" \
  "yes" "$(printf '%s' "$OUT" | grep -q 'ds-repo=none(NONE)' && echo yes || echo no)"

# ---------- this repo IS the design system ---------------------------------

mkrepo "$TMP/producer"
cat > "$TMP/producer/HERO.md" <<'EOF'
# Hero Configuration

## Connections

### design-system

- type: self
- role: producer

## Wayfare

- source-repo: .
EOF
check "self: the producer is not reported as never-asked" \
  "yes" "$(run_step0 "$TMP/producer" | grep -q 'ds-repo=.*(SELF)' && echo yes || echo no)"

# ---------- a refused discriminator ----------------------------------------
# A rejected `type` must not read as a declared `none`: that would silence the
# block's other keys, including a ux-flow that is set and fine.

mkrepo "$TMP/refused"
cat > "$TMP/refused/HERO.md" <<'EOF'
# Hero Configuration

## Connections

### design

- type: -evil
- ux-flow: flows/

## Wayfare

- source-repo: .
EOF
check "refused type: it is reported as REJECTED" \
  "yes" "$(run_step0_err "$TMP/refused" | grep -q 'design.type REJECTED' && echo yes || echo no)"
check "refused type: a set ux-flow is not silenced into NONE" \
  "" "$(run_step0 "$TMP/refused" | grep -o 'ux-flow=NONE' || true)"

if [ "$FAIL" -gt 0 ]; then
  echo "loading: $PASS passed, $FAIL FAILED"
  exit 1
fi
# Floor on the case count, for the reason the sibling suites carry one: this
# suite greps a summary line, and a block that stops being extracted produces
# no line and no failures either.
MIN_CASES=15
if [ "$PASS" -lt "$MIN_CASES" ]; then
  echo "loading: only $PASS cases ran, expected >= $MIN_CASES — a block stopped executing" >&2
  exit 1
fi
echo "loading: $PASS passed"
