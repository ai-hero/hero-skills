#!/usr/bin/env bash
# Fast pre-commit gate for hero-meta.
# Only runs when skill files are staged. Sends only the diff to Sonnet
# for a quick quality check.

set -euo pipefail

# Get staged files relevant to hero-meta
STAGED=$(git diff --cached --name-only 2>/dev/null)
if [[ -z "$STAGED" ]]; then
  exit 0
fi

# Only care about skill files, HERO.md, and plugin structure
RELEVANT_FILES=()
while IFS= read -r file; do
  case "$file" in
    skills/*/SKILL.md) RELEVANT_FILES+=("$file") ;;
    skills/*/references/*) RELEVANT_FILES+=("$file") ;;
    HERO.md) RELEVANT_FILES+=("$file") ;;
    scripts/validate.sh) RELEVANT_FILES+=("$file") ;;
  esac
done <<< "$STAGED"

if [[ ${#RELEVANT_FILES[@]} -eq 0 ]]; then
  exit 0
fi

# Build a focused diff of only the relevant staged changes
DIFF=$(git diff --cached -- "${RELEVANT_FILES[@]}")

# Send only the diff to Sonnet for a fast, scoped audit
set +e
OUTPUT=$(echo "$DIFF" | claude --model sonnet --max-turns 5 -p "$(cat <<'EOF'
You are reviewing a diff to a Claude Code skills plugin. Only check what changed in this diff — do not audit the entire plugin.

For the changed lines, verify:
- Frontmatter fields (name, description) are present and description is 50-200 chars
- Step/sub-step numbering is sequential and matches parent (e.g. Step 3 subs are 3a, 3b not 2a)
- No angle bracket placeholders like <foo> (use UPPER_CASE instead)
- Heading hierarchy is consistent with surrounding context
- No debug code or leftover TODO comments

Read the surrounding files if needed to check consistency with the rest of the plugin.

If everything looks good, output: "hero-meta: PASSED"
If there are issues, output: "hero-meta: ISSUES FOUND" followed by a brief list.
Keep output under 10 lines.
EOF
)")
set -e

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "ISSUES FOUND"; then
  exit 1
fi
