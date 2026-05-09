#!/usr/bin/env bash
# Advisory check for stale HERO.md.
#
# Compares the last-commit time of HERO.md against the last-commit time of
# files that affect the HERO.md schema (deps, CI, deploy, code quality, agent
# configs, task runners). If any of those is newer, prints a hint to stderr
# suggesting `hero-skills:init-hero --update`.
#
# Always exits 0 — this is purely informational.
#
# Usage: scripts/check-hero-staleness.sh
#
# Replaces the old hero-update-precommit.sh hook (which auto-ran Claude on
# every commit). Pre-commit was too slow; we let skills surface the hint
# on demand instead.

set -uo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HERO="$ROOT/HERO.md"
[[ -f "$HERO" ]] || exit 0

HERO_TIME=$(git -C "$ROOT" log -1 --format=%ct -- HERO.md 2>/dev/null || echo 0)
HERO_TIME=${HERO_TIME:-0}

# Patterns that affect HERO.md fields. Mirrors the old hero-update-precommit
# gate so any commit that would have triggered an update is also caught here.
PATTERNS=(
  pyproject.toml '*/pyproject.toml'
  package.json '*/package.json'
  go.mod '*/go.mod'
  Cargo.toml '*/Cargo.toml'
  Gemfile '*/Gemfile'
  'requirements*.txt' '*/requirements*.txt'
  '.github/workflows'
  .gitlab-ci.yml
  Jenkinsfile
  .circleci
  Dockerfile '*/Dockerfile'
  'docker-compose*.yml' '*/docker-compose*.yml'
  k8s kubernetes deploy
  .pre-commit-config.yaml
  ruff.toml
  '.eslintrc*' 'eslint.config.*'
  tsconfig.json '*/tsconfig.json'
  biome.json '*/biome.json'
  '.prettierrc*'
  CLAUDE.md .claude
  .cursorrules .cursor
  .windsurfrules .windsurf
  .github/copilot-instructions.md
  Makefile justfile Taskfile.yml
)

# Find the most recent commit touching any of those paths.
NEWEST=$(git -C "$ROOT" log -1 --format=%ct -- "${PATTERNS[@]}" 2>/dev/null || echo 0)
NEWEST=${NEWEST:-0}

if (( NEWEST > HERO_TIME )); then
  cat >&2 <<'EOF'
note: HERO.md may be out of date — project config has changed since the last sync.
      Run `hero-skills:init-hero --update` to refresh.
EOF
fi

exit 0
