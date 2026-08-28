#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Check a repo's agent-instructions files against docs/AGENTS-MD.md.
#
# Usage: check-agents-md.sh [REPO_ROOT] [--warn-only]
#        check-agents-md.sh --commit-msg FILE
#
# Checks R1-R6 of the standard (the mechanical ones). R7-R10 need judgment
# and are left to a rewrite pass.
#
# Exit codes:
#   0  no errors (warnings allowed), or --warn-only
#   1  at least one error
#   2  no AGENTS.md or CLAUDE.md found

set -uo pipefail

MAX_LINES=200
WARN_LINES=150
RULE_MAX_UNSCOPED=60
SECTION_MAX=5
EMPHASIS_WARN=1
EMPHASIS_MAX=5

# The name must be the whole heading (a trailing ": …", "( …", or "— …" is
# allowed): "## Page layout rules" is a real rule section, not a tree dump.
DERIVABLE='^#{1,4} +(layout|tech(nology)? stack|directory (structure|layout)|project structure|folder structure|data model|architecture overview|dependencies|file[- ]by[- ]file)( *([(:-]|—|–).*)?$'
# Fenced code is exempt from R4/R6 so a writing rule can list the phrases it
# bans without tripping the check.
BANNED="load-bearing|honest take|belt and suspenders|that'?s the unlock|you'?re absolutely right|delve"
EMPHASIS='\b(IMPORTANT|CRITICAL|NEVER|ALWAYS|MUST)\b'

ERRORS=0
WARNINGS=0
WARN_ONLY=0
ROOT=""

error() { echo "  ERROR: $1"; [[ -n "${2:-}" ]] && echo "         Fix:  $2"; ERRORS=$((ERRORS + 1)); }
warn()  { echo "  WARN:  $1"; [[ -n "${2:-}" ]] && echo "         Fix:  $2"; WARNINGS=$((WARNINGS + 1)); }

# --- commit-msg mode --------------------------------------------------------
if [[ "${1:-}" == "--commit-msg" ]]; then
  msg="${2:?usage: --commit-msg FILE}"
  # `git commit -v` appends the staged diff below a scissors line; git strips
  # it after the hook runs, so the hook must stop there too or every commit
  # touching a file that mentions a banned phrase is rejected.
  hits=$(awk -v re="$BANNED" '/^# -+ >8 -+$/{exit} !/^#/ && tolower($0) ~ re {print NR": "$0}' "$msg")
  if [[ -n "$hits" ]]; then
    echo "check-agents-md: commit message uses a banned phrase (R6):"
    echo "$hits" | sed 's/^/  /'
    echo "  Say the specific thing instead of the metaphor."
    exit 1
  fi
  exit 0
fi

for arg in "$@"; do
  case "$arg" in
    --warn-only) WARN_ONLY=1 ;;
    *) ROOT="$arg" ;;
  esac
done
[[ -n "$ROOT" ]] || ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Block HTML comments are removed before the file enters context, so they are
# free and must not count toward any limit.
strip_comments() { perl -0pe 's/<!--.*?-->//gs' "$1"; }
strip_fences() { awk '/^```/{f=!f; next} !f'; }
count_lines() { grep -c '' ; }
rules() { find "$ROOT/.claude/rules" -name '*.md' -type f 2>/dev/null; }

# --- R1: one file, symlinked -----------------------------------------------
echo "check-agents-md: $ROOT"
if [[ -L "$ROOT/CLAUDE.md" ]]; then
  link=$(readlink "$ROOT/CLAUDE.md")
  if [[ "$link" == "AGENTS.md" ]]; then
    TARGET="$ROOT/AGENTS.md"
    [[ -f "$TARGET" ]] || { error "R1: CLAUDE.md -> AGENTS.md, but AGENTS.md is missing"; exit 1; }
  else
    error "R1: CLAUDE.md is a symlink to '$link', not AGENTS.md" "ln -sf AGENTS.md CLAUDE.md"
    TARGET="$ROOT/CLAUDE.md"
  fi
elif [[ -f "$ROOT/CLAUDE.md" && -f "$ROOT/AGENTS.md" ]]; then
  error "R1: AGENTS.md and CLAUDE.md are both regular files — edits will diverge" \
    "Merge CLAUDE.md into AGENTS.md, then: rm CLAUDE.md && ln -s AGENTS.md CLAUDE.md"
  TARGET="$ROOT/AGENTS.md"
elif [[ -f "$ROOT/AGENTS.md" ]]; then
  warn "R1: AGENTS.md exists but CLAUDE.md is missing — Claude Code will not load it" \
    "ln -s AGENTS.md CLAUDE.md"
  TARGET="$ROOT/AGENTS.md"
elif [[ -f "$ROOT/CLAUDE.md" ]]; then
  warn "R1: only CLAUDE.md — other agents read AGENTS.md" \
    "git mv CLAUDE.md AGENTS.md && ln -s AGENTS.md CLAUDE.md"
  TARGET="$ROOT/CLAUDE.md"
else
  echo "  ERROR: no AGENTS.md or CLAUDE.md in $ROOT"
  exit 2
fi
NAME="${TARGET##*/}"
STRIPPED=$(strip_comments "$TARGET")
PROSE=$(strip_fences <<<"$STRIPPED")

# --- R2: size ----------------------------------------------------------------
lines=$(count_lines <<<"$STRIPPED")
if (( lines > MAX_LINES )); then
  error "R2: $NAME is $lines lines (max $MAX_LINES)" \
    "Move derivable sections to HERO.md/DESIGN.md, procedures to skills, area rules to .claude/rules with paths:"
elif (( lines > WARN_LINES )); then
  warn "R2: $NAME is $lines lines (warn at $WARN_LINES, max $MAX_LINES)"
fi

# --- R3 + R6 over the rules --------------------------------------------------
while IFS= read -r rule; do
  [[ -n "$rule" ]] || continue
  rs=$(strip_comments "$rule")
  rl=$(count_lines <<<"$rs")
  if (( rl > RULE_MAX_UNSCOPED )); then
    # Only a paths: line inside the frontmatter block scopes the rule; the
    # same line in the body is prose.
    if ! awk 'NR==1 && $0!="---"{exit 1} NR>1 && $0=="---"{exit !found} /^paths:/{found=1} END{exit !found}' "$rule"; then
      error "R3: ${rule#"$ROOT"/} is $rl lines with no paths: frontmatter — it loads in every session" \
        "Add frontmatter: paths: [\"src/**\"] (or split it)"
    fi
  fi
  hits=$(strip_fences <<<"$rs" | grep -n -iE "$BANNED" || true)
  if [[ -n "$hits" ]]; then
    error "R6: ${rule#"$ROOT"/} uses a banned phrase:" "Name the specific thing instead"
    echo "$hits" | sed 's/^/         /'
  fi
done < <(rules)

# --- R4: emphasis ------------------------------------------------------------
emph=$(grep -cE "$EMPHASIS" <<<"$PROSE" || true)
if (( emph > EMPHASIS_MAX )); then
  error "R4: $emph lines shout (IMPORTANT/NEVER/ALWAYS/MUST/CRITICAL); when many lines are emphasized, none is" \
    "Keep at most one; state the others plainly with the trap they prevent"
elif (( emph > EMPHASIS_WARN )); then
  warn "R4: $emph lines carry emphasis words — one is the budget"
fi

# --- R5: derivable sections -------------------------------------------------
# A section ends at the next heading of the same or a higher level; counting
# past that blames the sibling section's lines on the derivable one.
while IFS='|' read -r title body; do
  [[ -n "$title" ]] || continue
  error "R5: \"$title\" has $body lines of content the agent can derive from the tree or manifests" \
    "Keep a <=$SECTION_MAX-line pointer (HERO.md, DESIGN.md, docs/) and delete the rest"
done < <(awk -v max="$SECTION_MAX" -v re="$DERIVABLE" '
  function flush() { if (in_sec && body > max) printf "%s|%d\n", title, body; in_sec = 0 }
  /^#{1,6} / {
    match($0, /^#+/); lvl = RLENGTH
    if (in_sec && lvl <= sec_lvl) flush()
    if (tolower($0) ~ re) { in_sec = 1; sec_lvl = lvl; title = $0; body = 0 }
    next
  }
  in_sec && NF > 0 { body++ }
  END { flush() }
' <<<"$STRIPPED")

# --- R6: banned phrases in the main file ------------------------------------
hits=$(grep -n -iE "$BANNED" <<<"$PROSE" || true)
if [[ -n "$hits" ]]; then
  error "R6: $NAME uses a banned phrase:" "Name the specific thing instead"
  echo "$hits" | sed 's/^/         /'
fi

echo ""
echo "check-agents-md: $ERRORS error(s), $WARNINGS warning(s)"
if (( ERRORS > 0 )) && (( WARN_ONLY == 0 )); then
  exit 1
fi
exit 0
