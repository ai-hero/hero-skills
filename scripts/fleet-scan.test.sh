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
mkrepo lone
mkrepo odd   docker-compose.dev.yaml 'ports:
      - "${HOST_PORT}:3000"'
mkdir -p "$F/sites"; mkrepo sites/web docker-compose.dev.yml 'ports:
      - "3000:3000"'
touch "$F/sites/web/HERO.md"; printf '# W\n\n## Fleet\n' > "$F/sites/web/AGENTS.md"
mkrepo multi docker-compose.dev.yaml 'services:
  db:
    ports:
      - "5432:5432"
  app:
    ports:
      # - "${HOST_PORT:-6666}:3000"
      - "127.0.0.1:33020:3000"'
touch "$F/multi/HERO.md"; printf '## Fleet\n' > "$F/multi/AGENTS.md"

# ---------- --list ---------------------------------------------------------

LIST=$("$SCAN" "$F" --list)
check "list: exit 0 without FLEET.md" "0" "$?"
check "list: HOST_PORT default read from .yaml" \
  "auth	$F/auth	33000" "$(printf '%s\n' "$LIST" | grep '^auth')"
check "list: literal mapping read from .yml" \
  "web	$F/web	3000" "$(printf '%s\n' "$LIST" | grep '^web')"
check "list: no compose file reports -" \
  "extra	$F/extra	-" "$(printf '%s\n' "$LIST" | grep '^extra')"
check "list: compose file without a readable host port reports ?" \
  "odd	$F/odd	?" "$(printf '%s\n' "$LIST" | grep '^odd')"
check "list: without a port-range the first literal wins, comments skipped, bind prefix stripped" \
  "multi	$F/multi	5432" "$(printf '%s\n' "$LIST" | grep '^multi')"
check "list: a plain folder is not a checkout" \
  "" "$(printf '%s\n' "$LIST" | grep 'plain-folder')"

# ---------- --review -------------------------------------------------------

"$SCAN" "$F" --review >/dev/null 2>&1
check "review: no FLEET.md exits 2" "2" "$?"

cat > "$F/FLEET.md" <<'EOM'
# Fleet

## Fleet

- name: test
- port-range: 33000-33099

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

### lone

- group: none
- port: 33002

### odd

- group: none
- port: 33003

### web2

- path: ./sites/web/
- group: apps
- port: 33001

### multi

- group: apps
- port: 33020

### evil

- path: --upload-pack=x
- group: apps

### ../escape

- group: apps
EOM

OUT=$("$SCAN" "$F" --review); RC=$?
check "review: findings exit 1" "1" "$RC"
check "review: every finding, sorted" \
"$(printf 'BAD_ROW\t../escape\ta repo name is [A-Za-z0-9._-] only, not %s../escape%s\nBAD_ROW\tevil\ta value starts with %s-%s or holds a control character\nMISSING\tgone\t%s/gone\nNOT_GIT\tfolder\t%s/plain-folder\nNO_HERO\tclash\t%s/clash\nNOT_FLEET_AWARE\tclash\t%s/clash\nNOT_FLEET_AWARE\tweb\t%s/web\nPORT_COLLISION\tclash\t33000, also auth\nPORT_COLLISION\tweb2\t3000, also web\nPORT_COLLISION\tweb2\t33001, also web\nPORT_MISMATCH\tweb\t33001 -> 3000\nPORT_MISMATCH\tweb2\t33001 -> 3000\nPORT_UNIMPLEMENTED\tlone\t33002 (no compose file)\nPORT_UNPARSED\todd\t33003 (compose file, no readable host port)\nUNLISTED\textra\t%s/extra, port -' "'" "'" "'" "'" "$F" "$F" "$F" "$F" "$F" "$F" | sort)" \
"$OUT"

# A `none` row is exempt from NO_HERO/NO_AGENTS: it lives here, it is not fleet.
check "review: group none is not asked for HERO.md" \
  "" "$(printf '%s\n' "$OUT" | grep 'notes')"
check "review: port-range picks the app port over the database's, and a trailing-slash non-child path is matched" \
  "" "$(printf '%s\n' "$OUT" | grep -E '^(PORT_MISMATCH|UNLISTED)	multi')"

# A repo that committed its own FLEET.md is not a fleet.
touch "$F/HERO.md"
"$SCAN" "$F" --review >/dev/null 2>&1
check "review: HERO.md beside FLEET.md exits 2" "2" "$?"
rm "$F/HERO.md"

# The first sync: a FLEET.md with no rows yet must report every checkout.
printf '# Fleet\n\n## Fleet\n\n- name: t\n' > "$F/FLEET.md"
OUT=$("$SCAN" "$F" --review); RC=$?
check "review: zero rows lists every checkout as UNLISTED, exit 1" \
  "1|$("$SCAN" "$F" --list | wc -l | tr -d ' ')" "$RC|$(printf '%s\n' "$OUT" | grep -c '^UNLISTED')"

# Clean fleet: only the true rows, every fleet repo carries the section, and
# no `none` repo publishes a port a row claims (the host does not care about
# groups).
printf '# W\n\n## Fleet\n' > "$F/web/CLAUDE.md"
rm "$F/clash/docker-compose.dev.yaml"
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

### lone

- group: none

### odd

- group: none

### multi

- group: none

### web2

- path: /nonexistent-but-fleet-relative
- group: none
EOM
# an absolute path is honored (row present, dir missing → MISSING, so drop it)
sed -i '' '/^### web2/,$d' "$F/FLEET.md"
OUT=$("$SCAN" "$F" --review); RC=$?
check "review: clean fleet exits 0 with no output" "0|" "$RC|$OUT"

echo "fleet-scan: $PASS passed${FAIL:+, $FAIL FAILED}" | sed 's/, 0 FAILED//'
[ "$FAIL" -eq 0 ]
