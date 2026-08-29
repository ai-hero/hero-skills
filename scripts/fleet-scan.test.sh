#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Regression table for scripts/fleet-scan.sh.
#
# Each case is a drift that would otherwise go unreported: a port read from
# the wrong spelling of the compose file, a collision hidden behind a
# `HOST_PORT` grep, a row that points at a folder that is no longer a repo.
#
# Usage: bash scripts/fleet-scan.test.sh

set -uo pipefail

SCAN="$(cd "$(dirname "$0")" && pwd)/fleet-scan.sh"

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
F="$(cd "$TMP" && pwd -P)/fleet"

mkrepo() { # name [compose-file [content]]
  mkdir -p "$F/$1/.git"
  [ -n "${2:-}" ] && printf '%s\n' "$3" > "$F/$1/$2"
  return 0
}

mkrepo auth  docker-compose.dev.yaml 'ports:
      - ${HOST_PORT:-33000}:3000'
touch "$F/auth/HERO.md"; printf '# A\n\n## Fleet\n\ntext\n' > "$F/auth/AGENTS.md"
mkrepo web   docker-compose.dev.yml  'ports:
      - "3000:3000"'
touch "$F/web/HERO.md"; printf '# W\n' > "$F/web/CLAUDE.md"
mkrepo clash docker-compose.dev.yaml 'ports:
      - ${HOST_PORT:-33000}:3000'
touch "$F/clash/AGENTS.md"
mkrepo extra
mkrepo notes
mkdir -p "$F/plain-folder"

# ---------- --list ---------------------------------------------------------

LIST=$("$SCAN" "$F" --list)
check "list: exit 0 without FLEET.md" "0" "$?"
check "list: HOST_PORT default read from .yaml" \
  "auth	$F/auth	33000" "$(printf '%s\n' "$LIST" | grep '^auth')"
check "list: literal mapping read from .yml" \
  "web	$F/web	3000" "$(printf '%s\n' "$LIST" | grep '^web')"
check "list: no compose file reports -" \
  "extra	$F/extra	-" "$(printf '%s\n' "$LIST" | grep '^extra')"
check "list: a plain folder is not a checkout" \
  "" "$(printf '%s\n' "$LIST" | grep 'plain-folder')"

# ---------- --review -------------------------------------------------------

"$SCAN" "$F" --review >/dev/null 2>&1
check "review: no FLEET.md exits 2" "2" "$?"

cat > "$F/FLEET.md" <<'EOM'
# Fleet

## Fleet

- name: test

## Repos

### auth

- group: apps
- port: 33000

### web

- group: apps
- port: 33001

### clash

- group: apps
- port: 33000

### notes

- group: none

### gone

- group: apps
- port: 33002

### folder

- path: ./plain-folder
- group: apps
EOM

OUT=$("$SCAN" "$F" --review); RC=$?
check "review: findings exit 1" "1" "$RC"
check "review: every finding, sorted" \
"$(printf 'MISSING\tgone\t%s/gone\nNOT_GIT\tfolder\t%s/plain-folder\nNO_HERO\tclash\t%s/clash\nNOT_FLEET_AWARE\tclash\t%s/clash\nNOT_FLEET_AWARE\tweb\t%s/web\nPORT_COLLISION\tclash\t33000, also auth\nPORT_MISMATCH\tweb\t33001 -> 3000\nUNLISTED\textra\t%s/extra, port -' "$F" "$F" "$F" "$F" "$F" "$F" | sort)" \
"$OUT"

# A `none` row is exempt from NO_HERO/NO_AGENTS: it lives here, it is not fleet.
check "review: group none is not asked for HERO.md" \
  "" "$(printf '%s\n' "$OUT" | grep 'notes')"

# Clean fleet: only the true rows, and every fleet repo carries the section.
printf '# W\n\n## Fleet\n' > "$F/web/CLAUDE.md"
cat > "$F/FLEET.md" <<'EOM'
## Repos

### auth

- group: apps
- port: 33000

### web

- group: apps
- port: 3000

### clash

- group: none

### extra

- group: none

### notes

- group: none
EOM
OUT=$("$SCAN" "$F" --review); RC=$?
check "review: clean fleet exits 0 with no output" "0|" "$RC|$OUT"

echo "fleet-scan: $PASS passed${FAIL:+, $FAIL FAILED}" | sed 's/, 0 FAILED//'
[ "$FAIL" -eq 0 ]
