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
#
# Note: the daily-flow skills (commit-changes / push-pr / plan-work /
# test-changes) inline a *fast subset* of this check at Step 0. They're
# meant to be roughly aligned but NOT byte-for-byte identical — this
# script can carry a longer pattern list (Cargo, ruff, biome, agent
# configs, etc.) without forcing the inline copies to match. New patterns
# added here do not automatically need to land in the inline copies.

set -uo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HERO="$ROOT/HERO.md"
[[ -f "$HERO" ]] || exit 0

HERO_TIME=$(git -C "$ROOT" log -1 --format=%ct -- HERO.md 2>/dev/null || echo 0)
# Default-substitute any non-numeric output (corrupt repo, env hijack) to 0.
# This default is load-bearing for the (( arithmetic )) compare below — `set
# -u` would error on an empty value otherwise. Do not drop it.
HERO_TIME=${HERO_TIME:-0}

# Patterns that affect HERO.md fields. Mirrors the old hero-update-precommit
# gate so any commit that would have triggered an update is also caught here.
# `:(glob)**/foo` is git's magic pathspec for recursive matches — `*/foo`
# only matches one directory level deep, which silently misses nested
# subprojects in monorepos.
PATTERNS=(
  pyproject.toml ':(glob)**/pyproject.toml'
  package.json ':(glob)**/package.json'
  go.mod ':(glob)**/go.mod'
  Cargo.toml ':(glob)**/Cargo.toml'
  Gemfile ':(glob)**/Gemfile'
  'requirements*.txt' ':(glob)**/requirements*.txt'
  '.github/workflows'
  .gitlab-ci.yml
  Jenkinsfile
  .circleci
  Dockerfile ':(glob)**/Dockerfile'
  'docker-compose*.yml' ':(glob)**/docker-compose*.yml'
  k8s kubernetes deploy
  .pre-commit-config.yaml
  ruff.toml
  '.eslintrc*' 'eslint.config.*'
  tsconfig.json ':(glob)**/tsconfig.json'
  biome.json ':(glob)**/biome.json'
  '.prettierrc*'
  CLAUDE.md .claude
  .cursorrules .cursor
  .windsurfrules .windsurf
  .github/copilot-instructions.md
  Makefile justfile Taskfile.yml
)

# Find the most recent commit touching any of those paths.
NEWEST=$(git -C "$ROOT" log -1 --format=%ct -- "${PATTERNS[@]}" 2>/dev/null || echo 0)
# Same load-bearing default as HERO_TIME above.
NEWEST=${NEWEST:-0}

if (( NEWEST > HERO_TIME )); then
  cat >&2 <<'EOF'
note: HERO.md may be out of date — project config has changed since the last sync.
      Run `hero-skills:init-hero --update` to refresh.
EOF
fi

exit 0
