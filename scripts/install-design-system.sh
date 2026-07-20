#!/usr/bin/env bash
# Install hero-skills' design-system enforcement layer into a target repository.
#
# Usage: ./install-design-system.sh [TARGET_REPO_ROOT]
#   If TARGET_REPO_ROOT is omitted, uses the current git repo's toplevel.
#
# Writes:
#   .claude/rules/design-system.md      path-scoped UI constraints
#   .claude/hooks/check-design-tokens.sh  PostToolUse token check
# and wires the hook into .claude/settings.json.
#
# Idempotent. Never overwrites a customized file: on drift it writes .new and
# exits 2 so the caller can diff and decide — same contract as
# install-auto-approve.sh.
#
# Exit codes:
#   0  everything installed or already up to date
#   1  source files missing, or settings.json could not be wired
#   2  an existing file differs; .new written, caller must reconcile

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_RULE="$PLUGIN_ROOT/assets/design-system/rules/design-system.md"
SRC_HOOK="$PLUGIN_ROOT/assets/design-system/hooks/check-design-tokens.sh"

for f in "$SRC_RULE" "$SRC_HOOK"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: source file not found at $f" >&2
    exit 1
  fi
done

TARGET_ROOT="${1:-$(git rev-parse --show-toplevel)}"
DRIFT=0

# copy_or_flag SOURCE TARGET — install, no-op, or flag drift.
copy_or_flag() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"

  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    echo "OK: $dst already up to date"
    return 0
  fi

  if [[ -f "$dst" ]]; then
    cp "$src" "$dst.new"
    echo "EXISTS: $dst"
    echo "  Wrote new version to $dst.new"
    echo "  Diff:  diff -u $dst $dst.new"
    echo "  Apply: mv $dst.new $dst"
    DRIFT=1
    return 0
  fi

  cp "$src" "$dst"
  echo "INSTALLED: $dst"
}

copy_or_flag "$SRC_RULE" "$TARGET_ROOT/.claude/rules/design-system.md"
copy_or_flag "$SRC_HOOK" "$TARGET_ROOT/.claude/hooks/check-design-tokens.sh"
chmod +x "$TARGET_ROOT/.claude/hooks/check-design-tokens.sh" 2>/dev/null || true

# --- Wire the PostToolUse hook into .claude/settings.json ---------------------
SETTINGS="$TARGET_ROOT/.claude/settings.json"
HOOK_CMD='$CLAUDE_PROJECT_DIR/.claude/hooks/check-design-tokens.sh'

if ! command -v jq >/dev/null 2>&1; then
  echo ""
  echo "NOTE: jq not found — could not wire the hook automatically."
  echo "Add this to $SETTINGS by hand:"
  echo '  "hooks": { "PostToolUse": [ { "matcher": "Write|Edit",'
  echo "    \"hooks\": [ { \"type\": \"command\", \"command\": \"$HOOK_CMD\" } ] } ] }"
  [[ $DRIFT -eq 1 ]] && exit 2
  exit 0
fi

mkdir -p "$(dirname "$SETTINGS")"
[[ -f "$SETTINGS" ]] || echo '{}' > "$SETTINGS"

if ! jq -e . "$SETTINGS" >/dev/null 2>&1; then
  echo "ERROR: $SETTINGS is not valid JSON — refusing to modify it." >&2
  echo "Fix the file, then re-run this installer." >&2
  exit 1
fi

if jq -e --arg cmd "$HOOK_CMD" \
  '[.hooks.PostToolUse[]?.hooks[]?.command] | index($cmd)' \
  "$SETTINGS" >/dev/null 2>&1; then
  echo "OK: PostToolUse hook already wired in $SETTINGS"
else
  TMP="$(mktemp)"
  jq --arg cmd "$HOOK_CMD" '
    .hooks //= {} |
    .hooks.PostToolUse //= [] |
    .hooks.PostToolUse += [{
      matcher: "Write|Edit",
      hooks: [{ type: "command", command: $cmd }]
    }]
  ' "$SETTINGS" > "$TMP"

  # Only replace the real file once jq produced valid JSON — a failed jq run
  # must not truncate the user's settings.
  if jq -e . "$TMP" >/dev/null 2>&1; then
    mv "$TMP" "$SETTINGS"
    echo "WIRED: PostToolUse hook added to $SETTINGS"
  else
    rm -f "$TMP"
    echo "ERROR: failed to update $SETTINGS — left unchanged." >&2
    exit 1
  fi
fi

echo ""
echo "Design-system enforcement installed."
echo "  Rule:  .claude/rules/design-system.md  (loads on **/*.{tsx,jsx,css})"
echo "  Hook:  .claude/hooks/check-design-tokens.sh  (advisory; DESIGN_TOKENS_STRICT=1 to enforce)"

[[ $DRIFT -eq 1 ]] && exit 2
exit 0
