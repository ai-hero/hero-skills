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
if command -v jq >/dev/null 2>&1; then
  if ! FILE="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"; then
    echo "check-design-tokens: unparsable hook payload" >&2
    exit 2
  fi
else
  FILE="$(printf '%s' "$PAYLOAD" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
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

# grep exits 1 for "no match" and >=1 for an error. Collapsing those means an
# unreadable or binary file reports as clean; every check would "pass" on a
# file nobody could read.
scan() {
  grep -qE "$1" "$FILE"
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
  if ! grep -q '@theme' "$FILE" && scan '#[0-9a-fA-F]{3,8}\b|oklch\('; then
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
if printf '%s' "$(sed -E 's/(href|to|src|action|xlink:href)=("[^"]*"|\{[^}]*\})//g' "$FILE")" \
  | grep -qE '#[0-9a-fA-F]{3,8}\b|oklch\('; then
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
