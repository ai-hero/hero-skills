#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Migrate a `.plans/` store from the nine-kind schema to schema 1
# (docs/PLAN.md). Run once per repo; `wayfare init` runs it on sight of an
# unmigrated store.
#
# Usage: bash scripts/migrate-plan.sh [STORE] [--dry-run]

set -uo pipefail

LIB="$(cd "$(dirname "$0")" && pwd)/hero-lib.sh"
# shellcheck source=/dev/null
. "$LIB" || { echo "migrate-plan: cannot source $LIB" >&2; exit 1; }

STORE=""
DRY=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    -*) echo "migrate-plan: unknown option '$a'" >&2; exit 2 ;;
    *) STORE="$a" ;;
  esac
done
[ -n "$STORE" ] || STORE=$(hero_work_store) || exit 1
[ -d "$STORE" ] || { echo "migrate-plan: no store at '$STORE'" >&2; exit 1; }

TODAY=$(date +%Y-%m-%d)
WARNED=0
warn() { WARNED=$((WARNED + 1)); echo "migrate-plan: $*" >&2; }

# The whole guard against a second pass. After one run every item reads
# `type: task`, which pass two would take for a legacy item with no `kind` and
# re-derive a shape for — so this is a refusal, not a no-op for tidiness.
if [ -f "$STORE/PLAN.md" ] && [ -n "$(hero_item_field "$STORE/PLAN.md" schema)" ]; then
  echo "migrate-plan: '$STORE' is already at schema $(hero_item_field "$STORE/PLAN.md" schema); nothing to do."
  exit 0
fi

# ---------- derivations ----------------------------------------------------

# kind [+ bot] -> "TYPE SHAPE CHANNEL"; empty SHAPE/CHANNEL print as `-`.
derive_type() { # KIND BOT FILE
  case "$1" in
    ''|work-order|hardening|feature) echo "task story -" ;;
    architecture)                    echo "task structural -" ;;
    polish)                          echo "task visual -" ;;
    bug)                             echo "task defect -" ;;
    security)
      if [ -n "$2" ]; then echo "task dependency -"; else echo "task defect -"; fi ;;
    goal)                            echo "goal - -" ;;
    design-feedback)                 echo "signal - design" ;;
    design-system-feedback)          echo "signal - design-system" ;;
    architecture-feedback)           echo "signal - architecture" ;;
    *)
      # Loud, and never guessed away: the item still migrates (a half-migrated
      # store is worse than a wrong shape) but it carries a Log line saying so.
      warn "$3: unrecognized kind '$1'; migrated as task/story — check it"
      echo "task story -" ;;
  esac
}

# old status -> "STATUS RESOLUTION"; empty RESOLUTION prints as `-`.
derive_status() { # STATUS SUSPENDED_FROM FILE
  case "$1" in
    new)             echo "new -" ;;
    todo)            echo "accepted -" ;;
    planning|ready)  echo "$1 -" ;;
    implementing)    echo "active -" ;;
    committed)       echo "committed -" ;;
    reviewing)       echo "review -" ;;
    queued)          echo "ready -" ;;
    done)            echo "done shipped" ;;
    delivered)       echo "done delivered" ;;
    rejected)        echo "done rejected" ;;
    active)          echo "active -" ;;
    suspended)
      # Suspension stops being a status and becomes `awaiting` being non-empty,
      # so the status it left is simply restored. `suspended_from` was a saved
      # copy of a value that never had to change.
      case "$2" in
        '') warn "$3: suspended with no suspended_from; restored to accepted"
            echo "accepted -" ;;
        *)  derive_status "$2" "" "$3" ;;
      esac ;;
    *)
      warn "$3: unrecognized status '$1'; migrated as new"
      echo "new -" ;;
  esac
}

# ---------- pass 1: move items, read the covers map ------------------------

ITEMS="$STORE/items"
LEGACY=""
for f in "$STORE"/*.md; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in PLAN.md) continue ;; esac
  LEGACY="$LEGACY$f
"
done

if [ -z "$LEGACY" ] && [ ! -d "$ITEMS" ]; then
  echo "migrate-plan: '$STORE' holds no items; writing PLAN.md only."
fi

# id:parent:rank triples, space-delimited, looked up by string match. bash 3.2
# ships on macOS and has no associative arrays.
PARENT_MAP=" "
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ "$(hero_item_field "$f" kind)" = goal ] || continue
  gid=$(hero_norm_id "$(hero_item_field "$f" id)")
  [ -n "$gid" ] || { warn "$(basename "$f"): goal with no id; its covers are dropped"; continue; }
  rank=0
  while IFS= read -r cid; do
    [ -n "$cid" ] || continue
    cid=$(hero_norm_id "$cid")
    rank=$((rank + 1))
    case "$PARENT_MAP" in
      *" $cid:"*) warn "item $cid is covered by more than one goal; keeping the first" ; continue ;;
    esac
    PARENT_MAP="$PARENT_MAP$cid:$gid:$rank "
  done <<EOF
$(hero_item_list_field "$f" covers)
EOF
done <<EOF
$LEGACY
EOF

# ---------- pass 2: rewrite each item --------------------------------------

MAXID=0
COUNT=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  base=$(basename "$f")
  id=$(hero_norm_id "$(hero_item_field "$f" id)")
  case "$id" in
    ''|*[!0-9]*) warn "$base: id '$id' is not a number; the file is moved but its links cannot resolve" ;;
    *) [ "$id" -gt "$MAXID" ] && MAXID=$id ;;
  esac

  # Deliberate word splitting: the derive_* helpers print a fixed-arity tuple.
  # shellcheck disable=SC2046
  set -- $(derive_type "$(hero_item_field "$f" kind)" "$(hero_item_field "$f" bot)" "$base")
  ntype=$1 nshape=$2 nchannel=$3
  # shellcheck disable=SC2046
  set -- $(derive_status "$(hero_item_status "$f")" "$(hero_item_field "$f" suspended_from)" "$base")
  nstatus=$1 nresolution=$2
  # A goal's ending is the goal being met; `shipped` is a task's word for it.
  [ "$ntype" = goal ] && nresolution="-"

  parent="-" ; rank="-"
  case "$PARENT_MAP" in
    *" $id:"*)
      triple=${PARENT_MAP#* $id:}
      triple=${triple%% *}
      parent=${triple%:*}
      rank=${triple#*:} ;;
  esac

  out="$ITEMS/$base"
  if [ "$DRY" = 1 ]; then
    desc=$ntype
    [ "$nshape" != "-" ] && desc="$desc/$nshape"
    [ "$nchannel" != "-" ] && desc="$desc/$nchannel"
    echo "would migrate $base -> items/  ($desc, $nstatus)"
    COUNT=$((COUNT + 1)); continue
  fi
  mkdir -p "$ITEMS" || exit 1

  awk -v ntype="$ntype" -v nshape="$nshape" -v nchannel="$nchannel" \
      -v nstatus="$nstatus" -v nresolution="$nresolution" \
      -v parent="$parent" -v rank="$rank" -v today="$TODAY" -v base="$base" '
    function emitopt(k, v) { if (v != "-" && v != "") printf "%s: %s\n", k, v }
    # `source: a, b` was a comma string on some items and a YAML list on
    # others. Schema 1 says list, and the two readers must agree.
    function aslist(v,   n, parts, i, out) {
      if (v ~ /^\[/) return v
      n = split(v, parts, /,[[:space:]]*/)
      out = ""
      for (i = 1; i <= n; i++) {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", parts[i])
        if (parts[i] == "") continue
        out = out (out == "" ? "" : ", ") parts[i]
      }
      return "[" out "]"
    }
    function logline(tag, body,   d) {
      # `- DATE (ACTOR): text` -> `- DATE (ACTOR) TAG: text`; with no actor,
      # the tag goes straight after the date.
      if (body ~ /^- [0-9-]+ \([^)]*\):/) { sub(/\):/, ") " tag ":", body); return body }
      if (body ~ /^- [0-9-]+ \([^)]*\)/)  { sub(/\)/, ") " tag ":", body); return body }
      if (body ~ /^- [0-9-]+/)            { sub(/^(- [0-9-]+)/, "& " tag ":", body); return body }
      return body
    }

    BEGIN { fence = 0; sect = ""; nlog = 0; unknown_kind = 0 }

    /^---[[:space:]]*$/ {
      fence++
      if (fence == 1) { print; next }
      if (fence == 2) {
        emitopt("parent", parent)
        emitopt("rank", rank)
        if (srcref != "" || tgtref != "") {
          print "anchors:"
          if (srcref != "") print "  source: " srcref
          if (tgtref != "") print "  target: " tgtref
        }
        print
        next
      }
      print; next
    }

    fence == 1 {
      # Known fields are rewritten; everything else passes through verbatim,
      # so bot/pr/severity/branch/success/msg_id/budget survive untouched.
      if ($0 ~ /^kind:/)  { print "type: " ntype; emitopt("shape", nshape); emitopt("channel", nchannel); next }
      if ($0 ~ /^status:/) { print "status: " nstatus; emitopt("resolution", nresolution); next }
      if ($0 ~ /^source_ref:/) { srcref = $0; sub(/^source_ref:[[:space:]]*/, "", srcref); sub(/[[:space:]]*#.*/, "", srcref); next }
      if ($0 ~ /^target_ref:/) { tgtref = $0; sub(/^target_ref:[[:space:]]*/, "", tgtref); sub(/[[:space:]]*#.*/, "", tgtref); next }
      if ($0 ~ /^suspended_from:/) next
      if ($0 ~ /^covers:/) { incovers = 1; next }
      if (incovers && $0 ~ /^[[:space:]]+-/) next
      incovers = 0
      if ($0 ~ /^source:/) { v = $0; sub(/^source:[[:space:]]*/, "", v); sub(/[[:space:]]*#.*/, "", v); if (v != "") { print "source: " aslist(v); next } }
      if ($0 ~ /^target:/) { v = $0; sub(/^target:[[:space:]]*/, "", v); sub(/[[:space:]]*#.*/, "", v); if (v != "") { print "target: " aslist(v); next } }
      print; next
    }

    # ---- body ----
    /^## Comments[[:space:]]*$/       { sect = "note"; next }
    /^## Mistakes[[:space:]]*$/       { sect = "mistake"; next }
    /^## Turn log[[:space:]]*$/       { sect = "turn"; next }
    /^## Design Feedback[[:space:]]*$/ { sect = "signal"; next }
    /^## /                            { sect = ""; print; next }

    sect != "" {
      if ($0 ~ /^[[:space:]]*$/) next
      if (sect == "signal") {
        # An entry already promoted to a feedback item is state the item owns;
        # copying it here would be a second, diverging record of it.
        if ($0 ~ /\[item:/) { next }
        d = $0
        if (match(d, /[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/)) {
          dt = substr(d, RSTART, RLENGTH)
          sub(/^-[[:space:]]*DF-[0-9]+-[0-9-]+[[:space:]]*/, "", d)
          sub(/^\[[a-z]+\][[:space:]]*/, "", d)
          nlog++; lg[nlog] = "- " dt " (migrate) signal: " d
        } else { nlog++; lg[nlog] = logline("signal", $0) }
        next
      }
      if ($0 ~ /^-[[:space:]]/) { nlog++; lg[nlog] = logline(sect, $0) }
      else                      { nlog++; lg[nlog] = $0 }
      next
    }

    { print }

    END {
      print ""
      print "## Log"
      print ""
      for (i = 1; i <= nlog; i++) print lg[i]
      print "- " today " (migrate) note: migrated to schema 1 from " base
    }
  ' "$f" > "$out.tmp" && mv "$out.tmp" "$out" || { echo "migrate-plan: failed on $base" >&2; exit 1; }
  [ "$out" = "$f" ] || rm -f "$f"
  COUNT=$((COUNT + 1))
done <<EOF
$LEGACY
EOF

# ---------- PLAN.md --------------------------------------------------------

ROOT=${STORE%/.plans}
REPO=$(git -C "$ROOT" remote get-url origin 2>/dev/null \
  | sed -e 's#^git@[^:]*:##' -e 's#^https\{0,1\}://[^/]*/##' -e 's#\.git$##')
BRANCH=$(cd "$ROOT" && hero_default_branch 2>/dev/null) || BRANCH=main
HEAD=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)
DESIGN=$(hero_field design-project "$ROOT" 2>/dev/null) || DESIGN=none

if [ "$DRY" = 1 ]; then
  echo "would write $STORE/PLAN.md (repo ${REPO:-unknown}, next_id $((MAXID + 1)))"
  echo "migrate-plan: dry run — $COUNT item(s), $WARNED warning(s)."
  exit 0
fi

{
  echo "---"
  echo "schema: 1"
  [ -n "$REPO" ] && echo "repo: $REPO"
  echo "default_branch: $BRANCH"
  echo "initialized: $TODAY"
  echo "next_id: $((MAXID + 1))"
  echo "source:"
  echo "  root: ."
  [ -n "$HEAD" ] && echo "  head: $HEAD"
  case "$DESIGN" in
    ''|none|ask) : ;;
    *) echo "target:"; echo "  project: $DESIGN" ;;
  esac
  echo "---"
  echo ""
  echo "## Scope"
  echo ""
  echo "TODO — one paragraph: what this repo is and what the plan over it is"
  echo "for. \`wayfare init\` fills this in; the migrator cannot know it."
  echo ""
  echo "## Log"
  echo ""
  echo "- $TODAY (migrate) note: migrated $COUNT item(s) from the nine-kind schema"
} > "$STORE/PLAN.md"

echo "migrate-plan: migrated $COUNT item(s) into $STORE/items/, wrote PLAN.md."
[ "$WARNED" -gt 0 ] && echo "migrate-plan: $WARNED warning(s) above need a look."
exit 0
