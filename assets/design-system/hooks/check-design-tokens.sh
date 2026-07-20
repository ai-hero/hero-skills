#!/usr/bin/env bash
# PostToolUse hook — flag off-token styling in UI files after a write.
#
# Wired by scripts/install-design-system.sh into .claude/settings.json as a
# PostToolUse hook on Write|Edit. Reads the hook payload as JSON on stdin and
# emits advisory feedback on stderr with exit 2, which Claude Code surfaces
# back to the model.
#
# Deliberately advisory, not blocking-by-default: these patterns have real
# exceptions (a token definition file legitimately contains hex). Exit 2 gives
# the model the finding and lets it judge. Set DESIGN_TOKENS_STRICT=1 to make
# violations hard failures.

set -uo pipefail

PAYLOAD="$(cat)"

# Extract the edited path. Prefer jq; fall back to a narrow grep so the hook
# still works on machines without jq rather than silently passing everything.
if command -v jq >/dev/null 2>&1; then
  FILE="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty')"
else
  FILE="$(printf '%s' "$PAYLOAD" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
fi

[ -n "$FILE" ] || exit 0
[ -f "$FILE" ] || exit 0

case "$FILE" in
  *.tsx|*.jsx) ;;
  *) exit 0 ;;
esac

# Vendored registry components are not ours to lint — they are overwritten by
# the next `shadcn add`. Same for the token layer, where hex literals belong.
case "$FILE" in
  */components/ui/*|*/components/blocks/*|*/node_modules/*) exit 0 ;;
esac

FINDINGS=""
add() { FINDINGS="${FINDINGS}  - $1\n"; }

# Raw palette classes instead of semantic tokens.
if grep -qE '\b(bg|text|border|ring|divide|outline|fill|stroke|from|via|to)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}\b' "$FILE"; then
  add "Raw palette class. Use a semantic token (bg-background, text-muted-foreground, bg-muted)."
fi

# Color literals belong in the @theme layer, never in a component.
if grep -qE '#[0-9a-fA-F]{3,8}\b|oklch\(' "$FILE"; then
  add "Color literal (hex/oklch) in a component. Define it as a token in the @theme layer."
fi

# Margins on components — parents own layout.
# \b (not a leading space/quote) is load-bearing: a margin is very often the
# FIRST class in the string (className="mb-2 ..."), where there is no
# preceding space to anchor on. Matching on a word boundary catches that,
# the mid-string case, responsive prefixes (sm:mb-2), and negatives (-mt-4),
# while leaving max-w-md / from-blue-500 / zoom-2 alone.
if grep -qE 'className="[^"]*\bm[trblxyse]?-(auto|px|[0-9])' "$FILE"; then
  add "Margin in a component. Parents own spacing: use gap-* / space-* on the parent layout."
fi

# Arbitrary values that should come from a scale. Same first-class problem,
# so anchor on \b rather than a preceding space.
if grep -qE 'className="[^"]*\b(z-\[|rounded-\[|shadow-\[|text-\[[0-9]|[pgm][a-z]*-\[[0-9])' "$FILE"; then
  add "Arbitrary value. Use the token scale (spacing, radius, type, z-index)."
fi

# Numeric z-index (z-50) — outside the named scale, same class of defect as
# z-[9999] and just as common in hand-written UI.
if grep -qE 'className="[^"]*\bz-[0-9]' "$FILE"; then
  add "Numeric z-index. Use the named z-scale (z-dropdown < z-sticky < z-overlay < z-modal < z-toast)."
fi

# A dark: color override means the wrong token was chosen.
if grep -qE 'dark:(bg|text|border|ring)-' "$FILE"; then
  add "dark: color override. Dark mode comes free via tokens — this means the wrong token was used."
fi

# Shadows: the @aihero house rule is borders and hairlines only.
if grep -qE 'className="[^"]*(^|[[:space:]"])shadow-(sm|md|lg|xl|2xl|inner)\b' "$FILE"; then
  add "Shadow class. Elevation is expressed with borders and hairlines (house rule)."
fi

[ -n "$FINDINGS" ] || exit 0

{
  echo "Design-system check — $FILE"
  printf "%b" "$FINDINGS"
  echo "See .claude/rules/design-system.md. Fix at the source (token layer, parent layout,"
  echo "component API) rather than suppressing."
} >&2

if [ "${DESIGN_TOKENS_STRICT:-0}" = "1" ]; then
  exit 1
fi
exit 2
