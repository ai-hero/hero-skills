#!/usr/bin/env bash
# Scaffold a new hero skill.
# Usage: ./scripts/new-skill.sh <skill-name> [description]
# Example: ./scripts/new-skill.sh hero-deploy "Deploy to production environments"

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$PLUGIN_ROOT/skills"

# ─── Parse args ───────────────────────────────────────────────────

SKILL_NAME="${1:-}"
DESCRIPTION="${*:2}"

if [[ -z "$SKILL_NAME" ]]; then
  echo "Usage: $0 <skill-name> [description]"
  echo ""
  echo "Examples:"
  echo "  $0 hero-deploy \"Deploy to production environments\""
  echo "  $0 hero-lint \"Run linters across all projects\""
  exit 1
fi

# Validate kebab-case
if [[ ! "$SKILL_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: skill name must be kebab-case (lowercase, hyphens). Got: $SKILL_NAME"
  exit 1
fi

# Check if exists
if [[ -d "$SKILLS_DIR/$SKILL_NAME" ]]; then
  echo "Error: skill '$SKILL_NAME' already exists at $SKILLS_DIR/$SKILL_NAME"
  exit 1
fi

# Default description
if [[ -z "$DESCRIPTION" ]]; then
  DESCRIPTION="TODO: Describe what this skill does and when to use it. Include trigger phrases."
fi

# ─── Create skill ─────────────────────────────────────────────────

mkdir -p "$SKILLS_DIR/$SKILL_NAME"

cat > "$SKILLS_DIR/$SKILL_NAME/SKILL.md" << EOF
---
name: $SKILL_NAME
# prettier-ignore
description: $DESCRIPTION
argument-hint: [args]
disable-model-invocation: true
---

# ${SKILL_NAME} - TODO: Title

TODO: Brief description of what this skill does.

## Arguments

- \`\$ARGUMENTS\` - TODO: describe arguments

## Instructions

### Step 0: Load Hero Configuration

\`\`\`bash
ROOT=\$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "\$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
\`\`\`

Read \`HERO.md\` if it exists. This skill uses:
- TODO: list which HERO.md sections this skill reads

If \`HERO.md\` is missing, suggest \`/hero-init\` but proceed with auto-detection.

### Step 1: TODO

TODO: First step of the skill.

### Step 2: TODO

TODO: Second step.

## Examples

\`\`\`
/$SKILL_NAME                # TODO: example usage
\`\`\`

## Notes

- TODO: important notes
EOF

echo "Created: $SKILLS_DIR/$SKILL_NAME/SKILL.md"
echo ""
echo "Next steps:"
echo "  1. Edit $SKILLS_DIR/$SKILL_NAME/SKILL.md"
echo "  2. Run ./scripts/validate.sh to check"
echo "  3. Commit and push"
