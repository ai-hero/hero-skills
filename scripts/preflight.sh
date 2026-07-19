#!/usr/bin/env bash
# Pre-flight checks for the hero-skills pipeline.
#
# Runs the union of every downstream skill's blocking check so a `one-shot`
# (or any individual skill) can fail fast — before code is edited, before a
# branch is created, before a PR is pushed.
#
# Buckets:
#   tooling  — gh + auth, node ≥18, Playwright MCP registered, pr-review-toolkit
#              installed, pre-commit if .pre-commit-config.yaml exists
#   repo     — HERO.md present + non-stale, auto-approve.yml on default branch,
#              no in-progress merge/rebase/cherry-pick
#   runtime  — per-project .env keys vs .env.example, declared ports free,
#              dependency file present. Scoped to projects touched by the diff
#              when --projects is passed.
#   pipeline — issue tracker auth (Linear / Jira / GitHub Issues), default
#              branch fetch reachability
#
# Usage:
#   scripts/preflight.sh [--bucket tooling|repo|runtime|pipeline|all]
#                        [--projects path1,path2]
#                        [--quiet]
#
# Output (one line per check):
#   [OK]      bucket: detail
#   [WARN]    bucket: detail (continues)
#   [BLOCKER] bucket: detail (sets exit code 1)
#   [SKIP]    bucket: detail (check not applicable)
#
# Exit code: 0 if no blockers, 1 otherwise. Warnings never block.
#
# This script is read-only. It never edits files, creates branches, or
# mutates remote state.

set -uo pipefail

# ---------- arg parsing ----------------------------------------------------

BUCKET=all
PROJECT_SCOPE=""
QUIET=false

while [ $# -gt 0 ]; do
  case "$1" in
    --bucket)    BUCKET="${2:-all}"; shift 2 ;;
    --projects)  PROJECT_SCOPE="${2:-}"; shift 2 ;;
    --quiet)     QUIET=true; shift ;;
    -h|--help)
      sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$BUCKET" in tooling|repo|runtime|pipeline|all) ;; *)
  echo "ERROR: --bucket must be one of: tooling, repo, runtime, pipeline, all" >&2
  exit 2 ;;
esac

# ---------- result tracking ------------------------------------------------

BLOCKERS=0
WARNINGS=0

emit() {
  # $1 = severity (OK|WARN|BLOCKER|SKIP)
  # $2... = message
  local sev="$1"; shift
  case "$sev" in
    BLOCKER) BLOCKERS=$((BLOCKERS+1)) ;;
    WARN)    WARNINGS=$((WARNINGS+1)) ;;
  esac
  $QUIET && [ "$sev" = "OK" ] && return 0
  printf '[%-7s] %s\n' "$sev" "$*"
}

# ---------- shared context -------------------------------------------------

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HERO="$ROOT/HERO.md"
DEFAULT_BRANCH=$(awk -F': ' '/^- default-branch:/ {print $2; exit}' "$HERO" 2>/dev/null | xargs)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}

# Lazy gh-auth probe — set on first call, cached for the rest of the run.
# Used by check_repo / check_pipeline so they don't re-shell `gh auth status`
# when check_tooling ran (the common case) or when invoked standalone via
# `--bucket repo|pipeline`.
ensure_gh_auth_probed() {
  [ -n "${GH_AUTH_OK:-}" ] && return
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    GH_AUTH_OK=true
  else
    GH_AUTH_OK=false
  fi
}

# ---------- bucket: tooling ------------------------------------------------

check_tooling() {
  # 1. gh CLI + auth. Capture `gh auth status` once and reuse for both the
  #    pass/fail decision here and the scope check, so check_repo /
  #    check_pipeline can read GH_AUTH_OK instead of re-shelling.
  #    `gh auth status` prints the full scope list on one line like:
  #      `- Token scopes: 'gist', 'read:org', 'repo', 'workflow'`
  #    Strip the prefix and look for 'repo' anywhere in the remaining list.
  GH_AUTH_OK=false
  if command -v gh >/dev/null 2>&1; then
    local auth_out
    if auth_out=$(gh auth status 2>&1); then
      GH_AUTH_OK=true
      local scopes
      scopes=$(printf '%s' "$auth_out" | sed -n "s/^.*Token scopes: //p" | head -1)
      if printf '%s' "$scopes" | grep -q "'repo'"; then
        emit OK "tooling: gh authenticated (scopes: $scopes)"
      else
        emit WARN "tooling: gh authenticated but missing 'repo' scope (got: $scopes) — push-pr / ship-pr may fail"
      fi
    else
      emit BLOCKER "tooling: gh CLI not authenticated — run 'gh auth login'"
    fi
  else
    emit BLOCKER "tooling: 'gh' CLI not installed — https://cli.github.com/"
  fi

  # 2. jq (used by every gh-api call)
  if command -v jq >/dev/null 2>&1; then
    emit OK "tooling: jq present"
  else
    emit BLOCKER "tooling: 'jq' not installed — required by gh api calls"
  fi

  # 3. Node ≥18 (Playwright MCP needs it)
  if command -v node >/dev/null 2>&1; then
    local node_major
    node_major=$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)
    if [ "${node_major:-0}" -ge 18 ] 2>/dev/null; then
      emit OK "tooling: node $(node --version) (>=18)"
    else
      emit WARN "tooling: node $(node --version 2>/dev/null || echo missing) — Playwright MCP needs >=18"
    fi
  else
    emit WARN "tooling: 'node' not installed — push-pr's test-phase UI smoke will be unavailable"
  fi

  # 4. Playwright MCP registered. `claude mcp list` is the canonical check;
  #    if claude CLI isn't available, fall back to the on-disk config.
  if command -v claude >/dev/null 2>&1; then
    if claude mcp list 2>/dev/null | grep -qi "playwright"; then
      emit OK "tooling: playwright MCP registered"
    else
      emit WARN "tooling: playwright MCP not registered — push-pr's test-phase UI smoke will skip. Install: claude mcp add playwright npx @playwright/mcp@latest"
    fi
  elif [ -f "$HOME/.claude.json" ] && grep -q '"playwright"' "$HOME/.claude.json" 2>/dev/null; then
    emit OK "tooling: playwright MCP present in ~/.claude.json"
  else
    emit WARN "tooling: cannot detect playwright MCP — push-pr's test-phase UI smoke may skip. Install: claude mcp add playwright npx @playwright/mcp@latest"
  fi

  # 5. pr-review-toolkit plugin. Check both the user plugin dir and the
  #    project's .claude/plugins/ dir.
  local plugin_found=false
  for d in "$HOME/.claude/plugins/pr-review-toolkit" \
           "$ROOT/.claude/plugins/pr-review-toolkit"; do
    [ -d "$d" ] && plugin_found=true && break
  done
  if $plugin_found; then
    emit OK "tooling: pr-review-toolkit plugin installed"
  else
    emit WARN "tooling: pr-review-toolkit plugin not found — Step 8 (self-review) runs a thinner review. Install: /plugin install pr-review-toolkit"
  fi

  # 6. pre-commit, only if the repo declares hooks. Verify *both* that the
  #    CLI is installed AND that the git hook is actually wired in
  #    (`.git/hooks/pre-commit` contains the pre-commit shim). A repo with
  #    .pre-commit-config.yaml but no installed hook silently skips every
  #    check at commit time — exactly the kind of fail-late that preflight
  #    is meant to catch upstream.
  if [ -f "$ROOT/.pre-commit-config.yaml" ]; then
    if ! command -v pre-commit >/dev/null 2>&1; then
      emit BLOCKER "tooling: 'pre-commit' not installed but .pre-commit-config.yaml exists — Step 6 (commit) will skip every check. Install: pipx install pre-commit"
    else
      # Resolve the hook path via git so we honor core.hooksPath and work
      # correctly inside worktrees (where .git is a file, not a directory)
      # and bare repos. `git rev-parse --git-path` returns the path git
      # would actually use; it may be relative (anchored at $ROOT) or
      # absolute depending on the layout.
      local hook_path
      hook_path=$(git -C "$ROOT" rev-parse --git-path hooks/pre-commit 2>/dev/null)
      case "$hook_path" in
        /*) ;;
        *)  hook_path="$ROOT/$hook_path" ;;
      esac
      if [ -z "$hook_path" ] || [ ! -f "$hook_path" ]; then
        emit BLOCKER "tooling: pre-commit CLI present but git hook not installed at $hook_path — Step 6 (commit) will skip every check. Run: pre-commit install"
      elif ! grep -q "generated by pre-commit" "$hook_path" 2>/dev/null; then
        emit WARN "tooling: $hook_path exists but is not pre-commit-managed — custom hook may be shadowing pre-commit checks. Verify with: pre-commit install --overwrite"
      else
        emit OK "tooling: pre-commit installed and git hook active ($hook_path)"
      fi
    fi
  else
    emit SKIP "tooling: no .pre-commit-config.yaml in repo"
  fi
}

# ---------- bucket: repo state ---------------------------------------------

check_repo() {
  ensure_gh_auth_probed

  # 1. HERO.md present
  if [ -f "$HERO" ]; then
    emit OK "repo: HERO.md present"
  else
    emit BLOCKER "repo: HERO.md missing — run hero-skills:init-hero"
    return 0  # downstream checks read HERO.md; bail this bucket
  fi

  # 2. HERO.md staleness. Fast subset of scripts/check-hero-staleness.sh —
  # intentionally diverged: that script carries a longer pattern list
  # (ruff, eslint, biome, Gemfile, requirements*.txt, agent configs, etc.).
  # Keep this list deliberately tight; the standalone script is the one
  # that grows. See check-hero-staleness.sh's header for the rationale.
  local hero_time config_time
  hero_time=$(git -C "$ROOT" log -1 --format=%ct -- HERO.md 2>/dev/null | grep -E '^[0-9]+$' || echo "")
  config_time=$(git -C "$ROOT" log -1 --format=%ct -- \
    pyproject.toml ':(glob)**/pyproject.toml' \
    package.json ':(glob)**/package.json' \
    go.mod ':(glob)**/go.mod' \
    Cargo.toml ':(glob)**/Cargo.toml' \
    .github/workflows .pre-commit-config.yaml \
    CLAUDE.md Makefile justfile Taskfile.yml 2>/dev/null \
    | grep -E '^[0-9]+$' || echo "")
  if [ -z "$hero_time" ] && [ -z "$config_time" ]; then
    emit SKIP "repo: cannot read git history (empty repo?) — staleness unknown"
  elif [ "${config_time:-0}" -gt "${hero_time:-0}" ]; then
    emit WARN "repo: HERO.md may be stale — run hero-skills:init-hero --update"
  else
    emit OK "repo: HERO.md fresh"
  fi

  # 3. auto-approve.yml on default branch (Step 12 needs it). Reuse the
  # GH_AUTH_OK flag set by check_tooling instead of re-shelling gh auth.
  if [ "${GH_AUTH_OK:-false}" = "true" ]; then
    if gh api "/repos/{owner}/{repo}/contents/.github/workflows/auto-approve.yml?ref=$DEFAULT_BRANCH" \
        --jq '.path' >/dev/null 2>&1; then
      emit OK "repo: auto-approve.yml present on $DEFAULT_BRANCH"
    else
      emit BLOCKER "repo: .github/workflows/auto-approve.yml not on $DEFAULT_BRANCH — Step 12 (ship) will be a no-op. Run hero-skills:init-hero --update, then merge the workflow file to $DEFAULT_BRANCH."
    fi
  else
    emit SKIP "repo: gh unavailable — cannot check auto-approve.yml remotely"
  fi

  # 4. No in-progress merge / rebase / cherry-pick. Resolve each path via
  # `git rev-parse --git-path` so the check works inside worktrees (where
  # .git is a file pointing at the real gitdir) and bare repos. Hard-coded
  # $ROOT/.git/* paths miss those layouts.
  local in_progress=false marker
  for marker in MERGE_HEAD CHERRY_PICK_HEAD rebase-merge rebase-apply; do
    local p
    p=$(git -C "$ROOT" rev-parse --git-path "$marker" 2>/dev/null)
    case "$p" in
      /*) ;;
      *)  p="$ROOT/$p" ;;
    esac
    if [ -e "$p" ]; then
      in_progress=true
      break
    fi
  done
  if $in_progress; then
    emit BLOCKER "repo: in-progress merge/rebase/cherry-pick — resolve before continuing"
  else
    emit OK "repo: working tree clean of in-progress operations"
  fi
}

# ---------- bucket: project runtime ----------------------------------------

# Parses HERO.md projects[] into the PROJECTS array. Each entry is a single
# line `name|path|port|dependency-file|dev-command`. Missing fields are empty.
parse_hero_projects() {
  awk '
    /^## Projects/        { in_projects = 1; next }
    in_projects && /^## / { in_projects = 0 }
    !in_projects          { next }
    /^### / {
      if (name != "") print name "|" path "|" port "|" depfile "|" devcmd
      name = $2; path = ""; port = ""; depfile = ""; devcmd = ""
      for (i = 3; i <= NF; i++) name = name " " $i
      next
    }
    /^- path:/             { sub(/^- path: */, ""); path = $0 }
    /^- port:/             { sub(/^- port: */, ""); port = $0 }
    /^- dependency-file:/  { sub(/^- dependency-file: */, ""); depfile = $0 }
    /^- dev-command:/      { sub(/^- dev-command: */, ""); devcmd = $0 }
    END {
      if (name != "") print name "|" path "|" port "|" depfile "|" devcmd
    }
  ' "$HERO" 2>/dev/null
}

check_runtime() {
  [ -f "$HERO" ] || { emit SKIP "runtime: HERO.md missing — cannot scope checks"; return 0; }

  local projects=()
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    projects+=("$line")
  done < <(parse_hero_projects)

  if [ "${#projects[@]}" -eq 0 ]; then
    emit SKIP "runtime: no projects[] section in HERO.md"
    return 0
  fi

  # Build the scope set if --projects was passed. Use a newline-separated
  # list with `grep -F` (fixed-string match) so paths containing regex
  # metacharacters (`.`, `+`, `*`) match literally — feeding raw user
  # input through `tr ',' '|'` into `grep -E` would over-match (e.g.
  # `.test-output` as ERE matches any string containing `test-output`).
  local scope_list=""
  if [ -n "$PROJECT_SCOPE" ]; then
    scope_list=$(printf '%s' "$PROJECT_SCOPE" | tr ',' '\n')
  fi

  local matched=0
  for entry in "${projects[@]}"; do
    IFS='|' read -r name path port depfile devcmd <<< "$entry"
    [ -z "$path" ] && path="./"
    [ -z "$name" ] && name="(unnamed)"

    # Scope filter: skip projects whose name/path doesn't substring-match
    # any entry in --projects. Substring match is fine because monorepo
    # paths are already unique top-level dirs.
    if [ -n "$scope_list" ]; then
      local in_scope=false needle
      while IFS= read -r needle; do
        [ -z "$needle" ] && continue
        case "$name $path" in
          *"$needle"*) in_scope=true; break ;;
        esac
      done <<< "$scope_list"
      $in_scope || continue
    fi
    matched=$((matched+1))

    local proj_root="$ROOT/${path#./}"
    proj_root="${proj_root%/}"

    if [ ! -d "$proj_root" ]; then
      emit WARN "runtime: project '$name' path '$path' does not exist"
      continue
    fi

    # 1. .env vs .env.example key parity
    if [ -f "$proj_root/.env.example" ]; then
      local example_keys env_keys missing
      example_keys=$(grep -E '^[A-Z_][A-Z0-9_]*=' "$proj_root/.env.example" 2>/dev/null | cut -d= -f1 | sort -u || true)
      if [ -f "$proj_root/.env" ] || [ -f "$proj_root/.env.local" ]; then
        env_keys=$(cat "$proj_root/.env" "$proj_root/.env.local" 2>/dev/null \
          | grep -E '^[A-Z_][A-Z0-9_]*=' | cut -d= -f1 | sort -u || true)
        missing=$(comm -23 <(printf '%s\n' "$example_keys") <(printf '%s\n' "$env_keys") | grep -v '^$' || true)
        if [ -n "$missing" ]; then
          emit BLOCKER "runtime: $name: .env missing keys from .env.example: $(printf '%s' "$missing" | tr '\n' ',' | sed 's/,$//')"
        else
          emit OK "runtime: $name: .env covers all .env.example keys"
        fi
      else
        emit BLOCKER "runtime: $name: .env.example present but no .env / .env.local — copy and fill it in"
      fi
    else
      emit SKIP "runtime: $name: no .env.example"
    fi

    # 2. Declared port is free (only meaningful if a dev-command exists)
    if [ -n "$port" ] && [ -n "$devcmd" ] && [ "$devcmd" != "none" ]; then
      if command -v lsof >/dev/null 2>&1; then
        if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
          local owner
          owner=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -F c 2>/dev/null | awk '/^c/ {print substr($0,2); exit}')
          emit WARN "runtime: $name: port $port already in use by '${owner:-unknown}' — dev server / smoke test may collide"
        else
          emit OK "runtime: $name: port $port free"
        fi
      else
        emit SKIP "runtime: $name: lsof unavailable — cannot check port $port"
      fi
    fi

    # 3. Dependency file present
    if [ -n "$depfile" ] && [ "$depfile" != "none" ]; then
      if [ -f "$proj_root/$depfile" ]; then
        emit OK "runtime: $name: dependency file $depfile present"
      else
        emit BLOCKER "runtime: $name: dependency file $depfile missing"
      fi
    fi
  done

  # If --projects was passed but nothing matched, surface that explicitly
  # so the bucket isn't silently empty (otherwise the user sees only the
  # "no projects[] section" SKIP and misreads it as "all clear").
  if [ -n "$scope_list" ] && [ "$matched" -eq 0 ]; then
    emit SKIP "runtime: no HERO.md project matches --projects '$PROJECT_SCOPE'"
  fi
}

# ---------- bucket: pipeline-specific --------------------------------------

check_pipeline() {
  ensure_gh_auth_probed

  # 1. Default branch reachable on origin. Use `git ls-remote --exit-code`
  # instead of `git fetch` — same network round-trip for reachability but
  # ~10× faster (single ref query, no objects pulled, no local refs updated).
  if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git -C "$ROOT" ls-remote --exit-code --heads origin "$DEFAULT_BRANCH" >/dev/null 2>&1; then
      emit OK "pipeline: origin/$DEFAULT_BRANCH reachable"
    else
      emit BLOCKER "pipeline: cannot reach origin/$DEFAULT_BRANCH — check network/auth"
    fi
  else
    emit BLOCKER "pipeline: not inside a git work tree"
  fi

  # 2. Issue tracker auth (only if HERO.md declares one)
  local tool issue_tracker
  tool=$(awk -F': ' '/^- tool:/ {print $2; exit}' "$HERO" 2>/dev/null | xargs)
  issue_tracker=$(awk -F': ' '/^- issue-tracker:/ {print $2; exit}' "$HERO" 2>/dev/null | xargs)
  case "${tool:-${issue_tracker:-none}}" in
    linear)
      # Linear MCP is the usual integration. We can't probe Anthropic's
      # MCP auth state from bash, so check whether a `linear` CLI or
      # LINEAR_API_KEY env var is present.
      if [ -n "${LINEAR_API_KEY:-}" ] || command -v linear >/dev/null 2>&1; then
        emit OK "pipeline: linear credentials detected"
      else
        emit WARN "pipeline: HERO.md says tool=linear but no LINEAR_API_KEY / linear CLI found — Step 1 (plan) may prompt to re-auth"
      fi
      ;;
    jira)
      if [ -n "${JIRA_API_TOKEN:-}" ] && [ -n "${JIRA_EMAIL:-}" ]; then
        emit OK "pipeline: jira credentials detected"
      else
        emit WARN "pipeline: HERO.md says tool=jira but JIRA_API_TOKEN / JIRA_EMAIL not set — Step 1 (plan) may fail to fetch tickets"
      fi
      ;;
    github-issues|github)
      # Reuse GH_AUTH_OK from check_tooling rather than re-shell gh auth.
      if [ "${GH_AUTH_OK:-false}" = "true" ]; then
        emit OK "pipeline: github-issues uses the gh auth checked above"
      else
        emit BLOCKER "pipeline: HERO.md says tool=github-issues but gh is not authenticated"
      fi
      ;;
    none|"")
      emit SKIP "pipeline: no issue tracker configured (plain-description plans only)"
      ;;
    *)
      emit SKIP "pipeline: unknown issue tracker '$tool' — auth check skipped"
      ;;
  esac
}

# ---------- dispatch -------------------------------------------------------

case "$BUCKET" in
  tooling)  check_tooling ;;
  repo)     check_repo ;;
  runtime)  check_runtime ;;
  pipeline) check_pipeline ;;
  all)
    check_tooling
    check_repo
    check_runtime
    check_pipeline
    ;;
esac

# ---------- summary --------------------------------------------------------

echo ""
if [ "$BLOCKERS" -gt 0 ]; then
  echo "preflight: $BLOCKERS blocker(s), $WARNINGS warning(s) — pipeline will fail. Fix blockers above before running hero-skills:one-shot."
  exit 1
elif [ "$WARNINGS" -gt 0 ]; then
  echo "preflight: 0 blockers, $WARNINGS warning(s) — safe to proceed; warnings are advisory."
  exit 0
else
  echo "preflight: all checks passed."
  exit 0
fi
