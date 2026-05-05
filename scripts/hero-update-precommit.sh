#!/usr/bin/env bash
# Fast pre-commit gate for hero-init --update.
# Checks if any staged files could affect HERO.md. If not, exits instantly.
# Only invokes Claude when something relevant changed.

set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# No HERO.md? Nothing to sync.
if [[ ! -f "$ROOT/HERO.md" ]]; then
  exit 0
fi

# Get staged files
STAGED=$(git diff --cached --name-only 2>/dev/null)
if [[ -z "$STAGED" ]]; then
  exit 0
fi

# Patterns that can affect HERO.md
RELEVANT=false
while IFS= read -r file; do
  case "$file" in
    # Dependencies
    pyproject.toml|*/pyproject.toml) RELEVANT=true ;;
    package.json|*/package.json) RELEVANT=true ;;
    go.mod|*/go.mod) RELEVANT=true ;;
    Cargo.toml|*/Cargo.toml) RELEVANT=true ;;
    Gemfile|*/Gemfile) RELEVANT=true ;;
    requirements*.txt|*/requirements*.txt) RELEVANT=true ;;

    # CI/CD
    .github/workflows/*) RELEVANT=true ;;
    .gitlab-ci.yml) RELEVANT=true ;;
    Jenkinsfile) RELEVANT=true ;;
    .circleci/*) RELEVANT=true ;;

    # Deployment
    Dockerfile|*/Dockerfile) RELEVANT=true ;;
    docker-compose*.yml|*/docker-compose*.yml) RELEVANT=true ;;
    k8s/*|kubernetes/*|deploy/*) RELEVANT=true ;;

    # Code quality
    .pre-commit-config.yaml) RELEVANT=true ;;
    ruff.toml) RELEVANT=true ;;
    .eslintrc*|eslint.config.*) RELEVANT=true ;;
    tsconfig.json|*/tsconfig.json) RELEVANT=true ;;
    biome.json|*/biome.json) RELEVANT=true ;;
    .prettierrc*) RELEVANT=true ;;

    # Coding agent configs
    CLAUDE.md|.claude/*) RELEVANT=true ;;
    .cursorrules|.cursor/*) RELEVANT=true ;;
    .windsurfrules|.windsurf/*) RELEVANT=true ;;
    .github/copilot-instructions.md) RELEVANT=true ;;

    # Task runners
    Makefile|justfile|Taskfile.yml) RELEVANT=true ;;
  esac
  $RELEVANT && break
done <<< "$STAGED"

if ! $RELEVANT; then
  # Nothing relevant staged — skip Claude entirely
  exit 0
fi

# Something relevant changed — build diff and ask Claude to sync HERO.md
DIFF=$(git diff --cached)
HERO=$(cat "$ROOT/HERO.md")

# Snapshot the index before Claude runs so we can restore any unintended staging.
# Capture the HERO.md blob hash from the BEFORE state so we can detect whether
# Claude actually changed it (vs. it just being already-tracked in the index).
BEFORE_INDEX=$(git write-tree)
BEFORE_HERO=$(git ls-tree "$BEFORE_INDEX" -- "$ROOT/HERO.md" | awk '{print $3}')

# Always restore the index on exit, even if claude fails. Without this, a
# claude crash/timeout would leave the staging area in whatever partial state
# claude left behind (e.g., wrong files staged, HERO.md half-modified).
_restore_index_on_failure() {
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "hero-update: claude failed (exit $rc) — restoring git index" >&2
    git read-tree "$BEFORE_INDEX" 2>/dev/null \
      || echo "hero-update: WARN: index restore failed; run 'git reset HEAD' manually" >&2
  fi
}
trap _restore_index_on_failure EXIT

echo "$DIFF" | claude --model sonnet --max-turns 3 -p "$(cat <<EOF
You are syncing HERO.md with codebase changes. Current HERO.md:

$HERO

The staged diff above shows what changed. If any changes affect HERO.md fields
(dependencies, CI workflows, linters, coding agent, code review agent, etc.),
update HERO.md and run: git add $ROOT/HERO.md

RULES:
- Only modify HERO.md. Do not touch skill files, script files, or any other file.
- Never run git add/checkout/stash on any path other than HERO.md.
- If the diff shows skill files being renamed or deleted, that is intentional — ignore them.
- If nothing in the diff affects HERO.md, output: "HERO.md is up to date" and stop.
Keep output under 5 lines.
EOF
)"

# Claude succeeded. Discard the trap so a successful run doesn't trigger restore.
trap - EXIT

# Discard anything Claude inadvertently staged, then re-add HERO.md if and
# only if Claude actually modified it (compare blob hash before vs. after).
AFTER_INDEX=$(git write-tree)
if [[ "$BEFORE_INDEX" != "$AFTER_INDEX" ]]; then
  AFTER_HERO=$(git ls-tree "$AFTER_INDEX" -- "$ROOT/HERO.md" | awk '{print $3}')
  git read-tree "$BEFORE_INDEX"
  if [[ "$BEFORE_HERO" != "$AFTER_HERO" ]]; then
    if ! git add "$ROOT/HERO.md"; then
      echo "hero-update: WARN: failed to re-stage HERO.md — update may be lost" >&2
    fi
  fi
fi
