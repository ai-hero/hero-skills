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

echo "$DIFF" | claude --model sonnet --max-turns 3 -p "$(cat <<EOF
You are syncing HERO.md with codebase changes. Here is the current HERO.md:

$HERO

The staged diff above shows what changed. If any changes affect HERO.md fields
(dependencies, CI workflows, linters, coding agent, code review agent, etc.),
update HERO.md to reflect the new state. Stage the updated file with git add HERO.md.

If nothing in the diff affects HERO.md, output: "HERO.md is up to date" and exit.
Keep output under 5 lines.
EOF
)"
