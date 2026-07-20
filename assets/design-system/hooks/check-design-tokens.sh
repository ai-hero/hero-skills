#!/usr/bin/env bash
# PostToolUse hook — flag off-token styling in UI files after a write.
#
# Vendored by scripts/install-design-system.sh, which refuses to overwrite a
# drifted copy. Fix bugs here in hero-skills and re-run the installer; a local
# patch in a consuming repo makes that repo permanently decline updates,
# including fixes for the checks below.
#
# Advisory by design: these patterns have real exceptions (a token definition
# file legitimately contains hex), so the model gets the finding and judges.
# PostToolUse cannot block a tool call that already ran — if you need a gate
# that stops a commit, mirror these checks in pre-commit, where a non-zero
# exit actually stops something.

set -uo pipefail

PAYLOAD="$(cat)"

# A hook that cannot read its own input has failed — it has NOT seen a clean
# file. Exiting 0 on these paths is what would make a payload-schema change
# invisible: the check quietly stops running everywhere, with no signal.
if [ -z "$PAYLOAD" ]; then
  echo "check-design-tokens: empty hook payload" >&2
  exit 2
fi

# Extract the edited path. Prefer jq; fall back to a narrow grep so the hook
# still works on machines without jq rather than silently passing everything.
# Probe that jq WORKS, not merely that it is on PATH: a jq that is present but
# broken (wrong arch, missing lib, shim on a stripped PATH) passes an existence
# check and then fails every parse, taking the hook down a path that assumes it
# succeeded.
if printf '{}' | jq -e . >/dev/null 2>&1; then
  if ! FILE="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"; then
    echo "check-design-tokens: unparsable hook payload" >&2
    exit 2
  fi
else
  # No jq. Require the payload to at least look like JSON before concluding
  # anything from it: without this, an unparsable payload and a payload with no
  # file_path are identical (both yield empty → exit 0), so a schema change
  # would silently disable the hook on every jq-less machine — the exact
  # scenario the block above refuses to allow.
  case "$PAYLOAD" in
    *'{'*'}'*) ;;
    *) echo "check-design-tokens: unparsable hook payload (no jq available)" >&2
       exit 2 ;;
  esac
  # Scope the search to tool_input. `grep -o ... | head -1` over the whole
  # payload takes whichever file_path appears FIRST — with tool_response
  # ordered before tool_input, that is the response's path, and the hook lints
  # the wrong file.
  FILE="$(printf '%s' "$PAYLOAD" \
    | sed 's/.*"tool_input"[[:space:]]*:[[:space:]]*{//' \
    | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
fi

# No file_path at all means a tool that doesn't write files (or a notebook,
# which carries notebook_path). Genuinely nothing to check.
[ -n "$FILE" ] || exit 0

case "$FILE" in
  *.tsx|*.jsx) KIND=jsx ;;
  *.css)       KIND=css ;;
  *) exit 0 ;;
esac

# Vendored registry components are not ours to lint — they are overwritten by
# the next `shadcn add`.
case "$FILE" in
  */components/ui/*|*/components/blocks/*|*/node_modules/*) exit 0 ;;
esac

# Past the point where "not our file" is the answer, an unreadable path means
# the check did not run — which is not the same as passing.
if [ ! -f "$FILE" ] || [ ! -r "$FILE" ]; then
  echo "check-design-tokens: cannot read $FILE" >&2
  exit 2
fi

FINDINGS=""
add() { FINDINGS="${FINDINGS}  - $1\n"; }

# grep is line-based, but Prettier wraps the exact construct these checks anchor
# on across several lines:
#
#   <div
#     className={cn(
#       "mb-4 shadow-lg w-[300px]",
#     )}
#   />
#
# With one line per grep record, `className=` and the offending class are never
# in the same record, so every className-anchored rule below silently passes —
# the same undetectable false negative this hook exists to eliminate, in what is
# the DOMINANT real-world formatting. Scan a newline-collapsed copy instead.
# `[^>]*` still bounds each match to a single JSX tag, so collapsing does not
# let a match run from one element's className into another element's body.
SCAN_FILE="$FILE"

# Strip whole-line `//` comments BEFORE collapsing newlines, on the ORIGINAL
# file where line boundaries still mean something. A comment ends at the
# newline that terminates it — collapse first and there is no newline left to
# stop at, so a whole-file strip-to-first-// would delete everything after the
# FIRST comment anywhere in the file, JSX included.
#
# Only a comment that is the SOLE content of its line is stripped
# (^[[:space:]]*//), deliberately narrower than "strip from // to end of
# line" applied post-collapse. A same-line trailing comment after real code is
# not caught by this — accepted, because the alternative risks a much worse
# failure: `href="https://example.com"` is not a comment, and a same-line
# strip-from-// rule truncates everything after the URL's own `//`, silently
# dropping a real className that followed it on the same line. A whole-line
# comment can never contain that prefix, so this form is not exposed to it.
NOCOMMENT_FILE=""
SRC_FOR_NORM="$FILE"
if NOCOMMENT_FILE="$(mktemp 2>/dev/null)" \
  && LC_ALL=C sed -E '/^[[:space:]]*\/\//d' "$FILE" > "$NOCOMMENT_FILE" 2>/dev/null; then
  SRC_FOR_NORM="$NOCOMMENT_FILE"
else
  rm -f "$NOCOMMENT_FILE"
  echo "check-design-tokens: cannot strip comments from $FILE (encoding?)" >&2
  exit 2
fi

NORM_FILE=""
# LC_ALL=C makes tr/sed/grep byte-oriented. Without it, BSD tools abort with
# "illegal byte sequence" on a single non-UTF-8 byte (a latin-1 'é', a pasted
# smart quote) — which would either disable a check silently or, once the rc is
# checked, fail the whole hook on an otherwise fine file. Byte mode scans it.
if NORM_FILE="$(mktemp 2>/dev/null)" && LC_ALL=C tr '\n' ' ' < "$SRC_FOR_NORM" > "$NORM_FILE" 2>/dev/null; then
  SCAN_FILE="$NORM_FILE"
  trap 'rm -f "$NOCOMMENT_FILE" "$NORM_FILE"' EXIT
else
  # Losing the normalized copy means the multi-line cases silently stop being
  # checked — report rather than degrade to the bug we just fixed.
  rm -f "$NOCOMMENT_FILE"
  echo "check-design-tokens: cannot normalize $FILE for scanning" >&2
  exit 2
fi

# grep exits 1 for "no match" and >=1 for an error. Collapsing those means an
# unreadable or binary file reports as clean; every check would "pass" on a
# file nobody could read.
scan() {
  LC_ALL=C grep -qE "$1" "$SCAN_FILE"
  local rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "check-design-tokens: grep failed (rc=$rc) on $FILE" >&2
    exit 2
  fi
  return "$rc"
}

# Color literals belong in the @theme layer, never in a component — but the
# token layer is exactly the file that defines them in hex/oklch, so a CSS file
# carrying @theme is the one place they are correct.
if [ "$KIND" = css ]; then
  # The @theme probe needs the same rc discipline as scan(): `!` would invert an
  # error (rc>=2) into "no @theme", and && then short-circuits to exit 0 — a
  # clean report from a check that never ran.
  LC_ALL=C grep -q '@theme' "$FILE"
  THEME_RC=$?
  if [ "$THEME_RC" -gt 1 ]; then
    echo "check-design-tokens: grep failed (rc=$THEME_RC) probing @theme in $FILE" >&2
    exit 2
  fi
  if [ "$THEME_RC" -ne 0 ] && scan '#[0-9a-fA-F]{3,8}\b|oklch\('; then
    printf 'Design-system check — %s\n  - Color literal outside the @theme layer. Define it as a token.\n' "$FILE" >&2
    exit 2
  fi
  exit 0
fi

# Anchor the class-level checks on the className attribute in ANY of its forms.
# Anchoring on the literal `className="` misses className={cn(...)} — which is
# the form the rules file mandates and every registry component uses, i.e. the
# majority of real code. [^>]* keeps the match inside one JSX tag.
CLS="className=[{\"'\`][^>]*"

# Raw palette classes instead of semantic tokens.
if scan '\b(bg|text|border|ring|divide|outline|fill|stroke|from|via|to)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}\b'; then
  add "Raw palette class. Use a semantic token (bg-background, text-muted-foreground, bg-muted)."
fi

# A URL fragment is not a color, and plenty of slugs are valid hex: #feed,
# #face, #decade. Strip link-ish attributes before looking, or the rule cries
# wolf on ordinary anchors — which is how a check gets ignored, and then muted.
#
# This was the one rule that bypassed scan(), and it inherited exactly the
# defect scan() exists to prevent: BSD sed aborts with "illegal byte sequence"
# on a single non-UTF-8 byte (a latin-1 'é', a pasted smart quote), emitting
# nothing — so grep matched nothing and the rule reported clean while its
# siblings on the same file correctly exited 2. Check sed's status, then route
# the stripped text through scan() like everything else.
STRIPPED_FILE="$(mktemp 2>/dev/null)" || STRIPPED_FILE=""
if [ -z "$STRIPPED_FILE" ] \
  || ! LC_ALL=C sed -E 's/(href|to|src|action|xlink:href)=("[^"]*"|\{[^}]*\})//g' "$SCAN_FILE" > "$STRIPPED_FILE" 2>/dev/null; then
  rm -f "$STRIPPED_FILE"
  echo "check-design-tokens: cannot strip link attributes from $FILE (encoding?)" >&2
  exit 2
fi
trap 'rm -f "$NOCOMMENT_FILE" "$NORM_FILE" "$STRIPPED_FILE"' EXIT
# A colour literal in JSX is always inside a value context — a quoted string
# (style={{color:"#fff"}}), a template literal, or Tailwind's bracket notation
# (bg-[#3D4AB8]) — while prose never is. Requiring one of ["'`[ immediately
# before # is what tells "Ste #1100" (a street address) and "issue #1234" (a
# bare reference) apart from an actual literal, without guessing at length.
# The bracket alternative is load-bearing, not decorative: an earlier draft
# required only a quote and silently stopped catching bg-[#3D4AB8] and
# text-[#3D4AB8], a real and common way a colour enters a component, because
# the character before # there is `[`, never a quote. href-ish attributes are
# already stripped above, so this is the second and independent guard, for
# hex-looking text that was never inside an attribute at all. {3,4}|{6}|{8}
# are the only valid CSS hex lengths; {3,8} (the previous range) also matched
# 5- and 7-digit runs, which are not colours in any syntax and exist only to
# be typo'd addresses and issue numbers.
if SCAN_FILE="$STRIPPED_FILE" scan '["'"'"'`\[]#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b|oklch\('; then
  add "Color literal (hex/oklch) in a component. Define it as a token in the @theme layer."
fi

# Margins on components — parents own layout.
# \b (not a leading space/quote) is load-bearing: a margin is very often the
# FIRST class in the string (className="mb-2 ..."), where there is no
# preceding space to anchor on. Matching on a word boundary catches that,
# the mid-string case, responsive prefixes (sm:mb-2), and negatives (-mt-4),
# while leaving max-w-md / from-blue-500 / zoom-2 alone.
if scan "${CLS}\bm[trblxyse]?-(auto|px|[0-9])"; then
  add "Margin in a component. Parents own spacing: use gap-* / space-* on the parent layout."
fi

# Arbitrary values that should come from a scale. Match ANY utility with a
# bracket value, not a hand-listed prefix set: an earlier [pgm][a-z]*- form
# silently missed w-[300px], h-[48px] and grid-cols-[240px_1fr] because it
# required the bracket to follow the FIRST hyphen. Requiring a digit or calc(
# inside the bracket is what keeps Tailwind's own data-[state=open] and
# aria-[…] variants out.
if scan "${CLS}\b[a-z][a-z0-9-]*-\[(calc|[0-9])"; then
  add "Arbitrary value. Use the token scale (spacing, radius, type, z-index)."
fi

# Numeric z-index (z-50) — outside the named scale, same class of defect as
# z-[9999] and just as common in hand-written UI.
if scan "${CLS}\bz-[0-9]"; then
  add "Numeric z-index. Use the named z-scale (z-dropdown < z-sticky < z-overlay < z-modal < z-toast)."
fi

# A dark: color override means the wrong token was chosen.
if scan 'dark:(bg|text|border|ring)-'; then
  add "dark: color override. Dark mode comes free via tokens — this means the wrong token was used."
fi

# Shadows: the @aihero house rule is borders and hairlines only.
# The trailing class is what excludes shadow-none, which is the absence of a
# shadow and therefore always allowed.
if scan "${CLS}\bshadow(-(sm|md|lg|xl|2xl|inner))?([[:space:]\"'\`}]|$)"; then
  add "Shadow class. Elevation is expressed with borders and hairlines (house rule)."
fi

[ -n "$FINDINGS" ] || exit 0

{
  echo "Design-system check — $FILE"
  printf "%b" "$FINDINGS"
  echo "See .claude/rules/design-system.md. Fix at the source (token layer, parent layout,"
  echo "component API) rather than suppressing."
} >&2

# Exit 2 is the ONLY code that feeds stderr back to the model on PostToolUse.
# Every other non-zero is a "non-blocking error": the model never sees the
# finding and the user gets only the first stderr line. A DESIGN_TOKENS_STRICT
# knob that exited 1 used to live here and made the check strictly weaker than
# its default — do not reintroduce one.
exit 2
