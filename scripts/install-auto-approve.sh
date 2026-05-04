#!/usr/bin/env bash
# Install hero-skills' auto-approve.yml into a target repository.
#
# Usage: ./install-auto-approve.sh [TARGET_REPO_ROOT]
#   If TARGET_REPO_ROOT is omitted, uses the current git repo's toplevel.
#
# Idempotent: if the target file already matches the source, no-op.
# Preserves any existing file by writing to .new and asking the caller
# to diff/merge — the script itself never overwrites without intent.

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$PLUGIN_ROOT/.github/workflows/auto-approve.yml"

if [[ ! -f "$SOURCE" ]]; then
  echo "ERROR: source file not found at $SOURCE" >&2
  exit 1
fi

TARGET_ROOT="${1:-$(git rev-parse --show-toplevel)}"
TARGET_DIR="$TARGET_ROOT/.github/workflows"
TARGET="$TARGET_DIR/auto-approve.yml"

mkdir -p "$TARGET_DIR"

if [[ -f "$TARGET" ]] && cmp -s "$SOURCE" "$TARGET"; then
  echo "OK: $TARGET already up to date"
  exit 0
fi

if [[ -f "$TARGET" ]]; then
  cp "$SOURCE" "$TARGET.new"
  echo "EXISTS: $TARGET"
  echo "  Wrote new version to $TARGET.new"
  echo "  Diff:  diff -u $TARGET $TARGET.new"
  echo "  Apply: mv $TARGET.new $TARGET"
  exit 2
fi

cp "$SOURCE" "$TARGET"
echo "INSTALLED: $TARGET"
echo ""
echo "Reminder: GitHub only triggers issue_comment workflows that already"
echo "exist on the default branch. Commit and merge this file before"
echo "@auto-approve will work on PRs."
