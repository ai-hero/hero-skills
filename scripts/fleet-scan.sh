#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Enumerate the repos checked out in a fleet folder, and diff them against
# FLEET.md. The read-only half of hero-skills:fleet — `review` prints this
# output, `sync` uses it to propose rows.
#
# Usage: fleet-scan.sh [FLEET_ROOT] [--list | --review]
#        fleet-scan.sh -h | --help
#
# --list (default): one line per child directory that is a git checkout:
#   NAME<TAB>PATH<TAB>PORT   (PORT: what the dev compose file publishes, or -)
#
# --review: compare the listing with FLEET.md rows and print one finding per
#   line as CODE<TAB>NAME<TAB>DETAIL, sorted:
#   UNLISTED        a checkout with no row            (detail: path, port)
#   MISSING         a row whose path does not exist   (detail: path)
#   NOT_GIT         a row whose path is not a git repo (detail: path)
#   PORT_MISMATCH   row port differs from compose      (detail: row -> compose)
#   PORT_COLLISION  two rows claim one port           (detail: port, other)
#   NO_HERO         a fleet repo (group != none) without HERO.md
#   NO_AGENTS       a fleet repo without AGENTS.md or CLAUDE.md
#   NOT_FLEET_AWARE a fleet repo whose instructions file has no `## Fleet`
#                   section (assets/fleet/agents-md-fleet-section.md)
#
# Exit codes:
#   0  --list ran; or --review found nothing
#   1  --review found at least one finding
#   2  usage error, or no FLEET.md at the root (--review only)

set -uo pipefail

HERO_LIB="$(cd "$(dirname "$0")" && pwd)/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB" || { echo "fleet-scan: cannot source $HERO_LIB" >&2; exit 2; }

usage() { sed -n '5,31p' "$0" | sed 's/^# \{0,1\}//'; }

MODE=list
ROOT=""
for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --list) MODE=list ;;
    --review) MODE=review ;;
    -*) echo "fleet-scan: unknown option $arg" >&2; usage >&2; exit 2 ;;
    *) ROOT="$arg" ;;
  esac
done
ROOT="${ROOT:-$PWD}"
ROOT=$(cd "$ROOT" 2>/dev/null && pwd -P) || { echo "fleet-scan: no such directory: $ROOT" >&2; exit 2; }

scan() {
  local d
  for d in "$ROOT"/*/; do
    d="${d%/}"
    [ -e "$d/.git" ] || continue
    printf '%s\t%s\t%s\n' "${d##*/}" "$d" "$(hero_compose_port "$d")"
  done
}

if [ "$MODE" = list ]; then
  scan
  exit 0
fi

[ -f "$ROOT/FLEET.md" ] || { echo "fleet-scan: no FLEET.md in $ROOT — run hero-skills:fleet sync to create one" >&2; exit 2; }

LISTING=$(scan)
ROWS=$(hero_fleet_repos "$ROOT")
TAB=$'\t'
NL=$'\n'

# A function, not an inline $( … ): bash 3.2 cannot parse case patterns
# inside a command substitution.
review() {
  PORTS="$NL"
  while IFS="$TAB" read -r name path group rport; do
    [ -n "$name" ] || continue
    [ -e "$path" ] || { printf 'MISSING\t%s\t%s\n' "$name" "$path"; continue; }
    [ -e "$path/.git" ] || { printf 'NOT_GIT\t%s\t%s\n' "$name" "$path"; continue; }
    # The listing already read this checkout's compose file; only a row whose
    # path is not a direct child needs its own read.
    case "$LISTING" in
      *"$TAB$path$TAB"*) actual=${LISTING#*"$TAB$path$TAB"}; actual=${actual%%"$NL"*} ;;
      *) actual=$(hero_compose_port "$path") ;;
    esac
    if [ -n "$rport" ]; then
      [ "$actual" = - ] || [ "$rport" = "$actual" ] || printf 'PORT_MISMATCH\t%s\t%s -> %s\n' "$name" "$rport" "$actual"
      case "$PORTS" in
        *"$NL$rport "*) other=${PORTS#*"$NL$rport "}; printf 'PORT_COLLISION\t%s\t%s, also %s\n' "$name" "$rport" "${other%%"$NL"*}" ;;
      esac
      PORTS="$PORTS$rport $name$NL"
    fi
    [ "$group" != none ] || continue
    [ -f "$path/HERO.md" ] || printf 'NO_HERO\t%s\t%s\n' "$name" "$path"
    if [ -f "$path/AGENTS.md" ] || [ -f "$path/CLAUDE.md" ]; then
      # CLAUDE.md is normally a symlink to AGENTS.md; read whichever resolves.
      grep -qs '^## Fleet' "$path/AGENTS.md" "$path/CLAUDE.md" || printf 'NOT_FLEET_AWARE\t%s\t%s\n' "$name" "$path"
    else
      printf 'NO_AGENTS\t%s\t%s\n' "$name" "$path"
    fi
  done <<< "$ROWS"

  # Rows first, listing second; FILENAME (not NR==FNR) tells them apart when
  # the rows file is empty. macOS awk refuses a newline inside -v.
  awk -F'\t' '
    FILENAME == ARGV[1] { if (NF) seen[$2] = 1; next }
    NF && !($2 in seen) { printf "UNLISTED\t%s\t%s, port %s\n", $1, $2, $3 }
  ' <(printf '%s\n' "$ROWS") <(printf '%s\n' "$LISTING")
}

FINDINGS=$(review)

[ -n "$FINDINGS" ] || exit 0
sort <<< "$FINDINGS"
exit 1
