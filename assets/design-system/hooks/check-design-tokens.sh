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

CWD=""
DIFF_SCAN=""
# Left "" (never "true") on the no-jq path, where diff-scoping is unavailable
# entirely — that correctly routes every payload there to the whole-file
# fallback below, matching this path's behavior before diff-scoping existed.
HAS_DIFF_FIELD=""

# Extract the edited path. Prefer jq; fall back to a narrow grep so the hook
# still works on machines without jq rather than silently passing everything.
# Probe that jq WORKS, not merely that it is on PATH: a jq that is present but
# broken (wrong arch, missing lib, shim on a stripped PATH) passes an existence
# check and then fails every parse, taking the hook down a path that assumes it
# succeeded.
if printf '{}' | jq -e . >/dev/null 2>&1; then
  # Plain -r, not -e: a genuinely malformed payload already fails here (jq's
  # own parse error is a non-zero exit regardless of -e), but -e ALSO treats
  # "valid JSON, key just absent" (// empty producing no output at all) as a
  # failure — indistinguishable from real malformation, and exactly the
  # legitimate no-file_path case (a tool call that doesn't write files) that
  # must fall through to the harmless exit 0 below, not a false exit 2.
  if ! FILE="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"; then
    echo "check-design-tokens: unparsable hook payload" >&2
    exit 2
  fi
  # Relative paths in the payload resolve against its cwd, not ours. No exit-
  # status check needed here (unlike FILE above and DIFF_SCAN below): by this
  # point $PAYLOAD is already confirmed valid JSON — the FILE extraction above
  # would have exited 2 otherwise — and `.cwd // empty` cannot itself error on
  # any value type. DIFF_SCAN's `.edits? | .[]` can fail on a wrong-shaped-but-
  # valid payload; a bare field access with `// empty` cannot.
  CWD="$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null)"
  # What the model just wrote. Scoping the scan to this — rather than the
  # whole file — is what keeps the check reporting only what THIS edit
  # introduced. Against a not-yet-migrated codebase, a whole-file scan fired
  # on 27 of 49 files in one real repo, so nearly every edit returned findings
  # the model did not cause; the channel then gets ignored, which fails
  # silently and looks like passing. Falls back to the whole file below when
  # the payload carries none of these fields.
  #
  # Checked for jq failure the same way FILE= is above (not just 2>/dev/null):
  # an unexpected shape for tool_input.edits (e.g. anything but an array)
  # makes `.[]` error, and swallowing that here would silently degrade
  # diff-scoping to a whole-file scan with zero log signal — reintroducing,
  # one level down, the exact failure class diff-scoping exists to prevent.
  if ! DIFF_SCAN="$(printf '%s' "$PAYLOAD" | jq -r '
    [.tool_input.new_string?, .tool_input.content?, (.tool_input.edits? // [] | .[].new_string?)]
    | map(select(. != null)) | join("\n")
  ' 2>/dev/null)"; then
    echo "check-design-tokens: could not extract diff scope from payload" >&2
    exit 2
  fi
  # Presence, not content — a pure deletion (new_string is the empty string)
  # must still count as diff-scoped, or it silently falls back to a whole-file
  # scan and re-lints every pre-existing violation elsewhere in the file, the
  # exact noise diff-scoping exists to suppress. `[ -n "$DIFF_SCAN" ]` alone
  # cannot tell "field absent" from "field present but empty" — this can.
  if ! HAS_DIFF_FIELD="$(printf '%s' "$PAYLOAD" | jq -r '
    [.tool_input.new_string, .tool_input.content, .tool_input.edits]
    | map(select(. != null)) | length > 0
  ' 2>/dev/null)"; then
    echo "check-design-tokens: could not evaluate diff-field presence" >&2
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
  # the wrong file. No diff-scoping without jq: DIFF_SCAN stays empty, and the
  # whole-file fallback below runs, exactly as it always has on this path.
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

case "$FILE" in
  /*) ;;
  *) [ -n "$CWD" ] && FILE="$CWD/$FILE" ;;
esac

# Vendored registry components are not ours to lint — they are overwritten by
# the next `shadcn add`. Both case arms matter: the bare form (no leading `/`)
# catches a relative file_path with no directory prefix, which the `*/`-form
# arm cannot match at all — that form requires an actual `/` before
# "components", so a payload carrying exactly "components/ui/button.tsx" (no
# CWD available to prepend, or a repo laid out at its own root) slips through
# silently without it.
case "$FILE" in
  */components/ui/*|*/components/blocks/*|*/node_modules/*) exit 0 ;;
  components/ui/*|components/blocks/*) exit 0 ;;
esac

# The text to scan: the payload's own written content when present
# (diff-scoped, see DIFF_SCAN/HAS_DIFF_FIELD above), else the whole file on
# disk. Gated on HAS_DIFF_FIELD, not on DIFF_SCAN being non-empty — a pure
# deletion (new_string == "") must still count as diff-scoped, or it falls
# through to the whole-file branch below and re-lints every pre-existing
# violation elsewhere in the file, on an edit that introduced nothing.
IS_DIFF_SCOPED=0
if [ "$HAS_DIFF_FIELD" = "true" ]; then
  RAW="$DIFF_SCAN"
  IS_DIFF_SCOPED=1
else
  # Missing and unreadable are the SAME failure, not two: a hook that cannot
  # see the file has NOT confirmed it clean either way, and both must fail
  # the same way this whole hook does elsewhere for that reason. An earlier
  # draft of this branch split them (`[ -f ] || exit 0`, unreadable-only exit
  # 2) and silently downgraded "file was deleted or never landed" to a clean
  # pass — reintroducing, one level down, the exact "check did not run read
  # as passing" bug this file exists to keep out.
  if [ ! -f "$FILE" ] || [ ! -r "$FILE" ]; then
    echo "check-design-tokens: cannot read $FILE" >&2
    exit 2
  fi
  if ! RAW="$(cat -- "$FILE" 2>/dev/null)"; then
    echo "check-design-tokens: cannot read $FILE" >&2
    exit 2
  fi
fi

# For CSS: whether hex/oklch belongs here at all is a FILE-level fact — does
# this file declare @theme anywhere — which a diff snippet cannot answer about
# the surrounding file. Always read from disk for this, regardless of
# diff-scoping; PostToolUse fires after the write already landed, so the file
# on disk reflects it.
if [ "$KIND" = css ]; then
  if [ -f "$FILE" ]; then
    LC_ALL=C grep -q '@theme' "$FILE"
    THEME_RC=$?
    if [ "$THEME_RC" -gt 1 ]; then
      echo "check-design-tokens: grep failed (rc=$THEME_RC) probing @theme in $FILE" >&2
      exit 2
    fi
  else
    # No file on disk to check (should not normally happen post-write) —
    # treat as "no @theme", i.e. still subject to the hex check below.
    THEME_RC=1
  fi
fi

FINDINGS=""
add() { FINDINGS="${FINDINGS}  - $1\n"; }

# grep is line-based, but Prettier wraps the exact construct these checks
# anchor on across several lines:
#
#   <div
#     className={cn(
#       "mb-4 shadow-lg w-[300px]",
#     )}
#   />
#
# With one line per grep record, `className=` and the offending class are
# never in the same record, so every className-anchored rule below silently
# passes — the same undetectable false negative this hook exists to
# eliminate, in what is the DOMINANT real-world formatting. Scan a
# newline-collapsed copy instead. `[^>]*` still bounds each match to a single
# JSX tag, so collapsing does not let a match run from one element's
# className into another element's body.
RAWFILE="$(mktemp 2>/dev/null)" || { echo "check-design-tokens: cannot create temp file" >&2; exit 2; }
# The one temp-file write in this pipeline an earlier draft left unchecked —
# every sibling write below (NOCOMMENT_FILE, NORM_FILE, STRIPPED_FILE) already
# verifies its own exit status. A failure here (disk full, permission denied
# mid-write) would otherwise leave $RAWFILE empty or truncated and scan THAT,
# reporting clean on a file that has a real violation.
if ! printf '%s' "$RAW" > "$RAWFILE"; then
  rm -f "$RAWFILE"
  echo "check-design-tokens: cannot write scan buffer for $FILE" >&2
  exit 2
fi

# Strip whole-line `//` comments BEFORE collapsing newlines, on text that
# still has real line boundaries. A comment ends at the newline that
# terminates it — collapse first and there is no newline left to stop at, so
# a whole-text strip-to-first-// would delete everything after the FIRST
# comment anywhere in the scanned text, JSX included.
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
SRC_FOR_NORM="$RAWFILE"
if NOCOMMENT_FILE="$(mktemp 2>/dev/null)" \
  && LC_ALL=C sed -E '/^[[:space:]]*\/\//d' "$RAWFILE" > "$NOCOMMENT_FILE" 2>/dev/null; then
  SRC_FOR_NORM="$NOCOMMENT_FILE"
else
  rm -f "$RAWFILE" "$NOCOMMENT_FILE"
  echo "check-design-tokens: cannot strip comments from $FILE (encoding?)" >&2
  exit 2
fi

# LC_ALL=C makes tr/sed/grep byte-oriented. Without it, BSD tools abort with
# "illegal byte sequence" on a single non-UTF-8 byte (a latin-1 'é', a pasted
# smart quote) — which would either disable a check silently or, once the rc is
# checked, fail the whole hook on an otherwise fine file. Byte mode scans it.
NORM_FILE=""
if NORM_FILE="$(mktemp 2>/dev/null)" && LC_ALL=C tr '\n' ' ' < "$SRC_FOR_NORM" > "$NORM_FILE" 2>/dev/null; then
  SCAN_FILE="$NORM_FILE"
  trap 'rm -f "$RAWFILE" "$NOCOMMENT_FILE" "$NORM_FILE" "${STRIPPED_FILE:-}" 2>/dev/null' EXIT
else
  # Losing the normalized copy means the multi-line cases silently stop being
  # checked — report rather than degrade to the bug we just fixed. $NORM_FILE
  # is included here too: mktemp can succeed and leave a real path in it even
  # when the following tr write is what actually failed, and an early draft's
  # cleanup list missed it on exactly that path — a real, if minor, temp-file
  # leak rather than a silent correctness bug.
  rm -f "$RAWFILE" "$NOCOMMENT_FILE" "$NORM_FILE"
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

if [ "$KIND" = css ]; then
  # `&&`, not `!`: inverting THEME_RC (grep's own exit code, which is also
  # >=2 on a scan failure) would fold "grep errored" into "no @theme found",
  # and the short-circuit after it would then report a clean scan for a check
  # that never actually ran. `-ne 0` treats anything but a clean @theme MATCH
  # as "keep scanning" and lets the earlier THEME_RC>1 guard above catch a
  # real grep error before this line is ever reached.
  # {3,8} here (not JSX's {3,4}|{6}|{8}) is a known, accepted gap: a CSS file
  # already gets no other exemption for hex outside @theme, so a 5- or
  # 7-digit false match here is lower-stakes than in prose.
  if [ "$THEME_RC" -ne 0 ] && scan '#[0-9a-fA-F]{3,8}\b|oklch\('; then
    printf 'Design-system check — %s\n  - Color literal outside the @theme layer. Define it as a token.\n' "$FILE" >&2
    exit 2
  fi
  exit 0
fi

# Anchor the class-level checks on the className attribute in ANY of its
# forms, but ONLY when scanning the whole file. Anchoring on the literal
# `className="` misses className={cn(...)} — which is the form the rules file
# mandates and every registry component uses, i.e. the majority of real code.
# [^>]* keeps the match inside one JSX tag.
#
# When diff-scoped, the anchor is actively wrong rather than merely
# unnecessary: an Edit call very commonly replaces just the class-list STRING
# inside className="...", so `className=` itself never appears in
# new_string — an anchored check against just that snippet would silently
# stop catching what it always caught on the whole file, the exact
# reads-as-installed-catches-nothing failure this hook exists to avoid. Use
# the bare, unanchored pattern there instead; \b still keeps it off partial
# words, and the smaller false-positive surface an anchor buys on a whole
# file matters less on a snippet that IS the edit under review.
CLS="className=[{\"'\`][^>]*"
# 2xs|xs are Tailwind v4's addition to the bottom of the elevation scale
# (v4 renamed the old shadow-sm to shadow-xs and added a smaller shadow-2xs
# below it) — an earlier draft's alternation only carried the v3-era
# sm|md|lg|xl|2xl|inner set, so shadow-xs (the single most common
# small-elevation utility in a v4 codebase) silently passed.
if [ "$IS_DIFF_SCOPED" -eq 1 ]; then
  MARGIN_PAT='\bm[trblxyse]?-(auto|px|[0-9])'
  ARB_PAT='\b[a-z][a-z0-9-]*-\[(calc|[0-9])'
  ZIDX_PAT='\bz-[0-9]'
  SHADOW_PAT='\bshadow(-(2xs|xs|sm|md|lg|xl|2xl|inner))?([[:space:]"'"'"'\`}]|$)'
else
  MARGIN_PAT="${CLS}\bm[trblxyse]?-(auto|px|[0-9])"
  ARB_PAT="${CLS}\b[a-z][a-z0-9-]*-\[(calc|[0-9])"
  ZIDX_PAT="${CLS}\bz-[0-9]"
  SHADOW_PAT="${CLS}\bshadow(-(2xs|xs|sm|md|lg|xl|2xl|inner))?([[:space:]\"'\`}]|\$)"
fi

# Raw palette classes instead of semantic tokens. Unanchored in both modes —
# a raw palette class is wrong wherever it appears, className= context or not.
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
if scan "$MARGIN_PAT"; then
  add "Margin in a component. Parents own spacing: use gap-* / space-* on the parent layout."
fi

# Arbitrary values that should come from a scale. Match ANY utility with a
# bracket value, not a hand-listed prefix set: an earlier [pgm][a-z]*- form
# silently missed w-[300px], h-[48px] and grid-cols-[240px_1fr] because it
# required the bracket to follow the FIRST hyphen. Requiring a digit or calc(
# inside the bracket is what keeps Tailwind's own data-[state=open] and
# aria-[…] variants out.
if scan "$ARB_PAT"; then
  add "Arbitrary value. Use the token scale (spacing, radius, type, z-index)."
fi

# Numeric z-index (z-50) — outside the named scale, same class of defect as
# z-[9999] and just as common in hand-written UI.
if scan "$ZIDX_PAT"; then
  add "Numeric z-index. Use the named z-scale (z-dropdown < z-sticky < z-overlay < z-modal < z-toast)."
fi

# A dark: color override means the wrong token was chosen. Unanchored in both
# modes — like the palette check, wrong wherever it appears.
if scan 'dark:(bg|text|border|ring)-'; then
  add "dark: color override. Dark mode comes free via tokens — this means the wrong token was used."
fi

# Shadows: the @aihero house rule is borders and hairlines only.
# The trailing class is what excludes shadow-none, which is the absence of a
# shadow and therefore always allowed.
if scan "$SHADOW_PAT"; then
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
