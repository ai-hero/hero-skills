---
name: preflight
# prettier-ignore
description: Run pre-flight checks for the hero-skills pipeline. Catches missing tooling, stale HERO.md, .env mismatches, busy ports — before any step does destructive work.
argument-hint: [--bucket tooling|repo|runtime|pipeline|all] [--projects p1,p2]
disable-model-invocation: true
---

# Preflight — Fail-Fast Checks for the Pipeline

Runs the union of every downstream skill's blocking check so a `one-shot` (or any individual hero skill) fails fast — before code is edited, before a branch is created, before a PR is pushed.

The actual checks live in `scripts/preflight.sh`. This skill is a thin wrapper: it invokes the script, renders the result for the user, and tells them what to fix next.

## Arguments

- `$ARGUMENTS` — Optional flags passed straight to `scripts/preflight.sh`:
  - `--bucket BUCKET` — Run only one bucket. Values: `tooling`, `repo`, `runtime`, `pipeline`, or `all` (default).
  - `--projects p1,p2` — Restrict the `runtime` bucket to specific project paths or names from HERO.md. Useful when the diff only touches part of a monorepo.
  - `--quiet` — Suppress `[OK]` lines; only `[WARN]`, `[BLOCKER]`, `[SKIP]` are printed.

## Buckets

| Bucket | Checks |
|--------|--------|
| `tooling` | `gh` + auth + `repo` scope, `jq`, Node ≥18, Playwright MCP registered, pr-review-toolkit plugin installed, `pre-commit` present when `.pre-commit-config.yaml` exists |
| `repo` | HERO.md present + non-stale, `.github/workflows/auto-approve.yml` on default branch, no in-progress merge/rebase/cherry-pick |
| `runtime` | Per-project `.env` covers every key in `.env.example`, declared `port:` is free, declared `dependency-file:` exists |
| `pipeline` | `origin/DEFAULT_BRANCH` reachable, issue tracker auth (Linear / Jira / GitHub Issues) |

## Severity

- `[OK]` — check passed
- `[WARN]` — non-blocking issue; surface and continue
- `[BLOCKER]` — pipeline will fail; halt
- `[SKIP]` — check not applicable (e.g., no `.env.example`, no projects in HERO.md)

Exit code is `1` if any `BLOCKER` fired, `0` otherwise. Warnings never block.

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

If `HERO.md` is missing, mention it but still run `scripts/preflight.sh` — the script itself reports the missing-HERO blocker with a useful next step (`hero-skills:init-hero`).

### Step 1: Run the Script

Prefer the harness-provided `$CLAUDE_PLUGIN_ROOT` when set (covers worktrees and non-default `~/.claude` layouts), otherwise fall back to the in-repo path, then the user-dir path. Only prepend `CLAUDE_PLUGIN_ROOT` when it's non-empty — otherwise the first candidate would expand to a bare absolute path (`/scripts/preflight.sh`) and silently point at the wrong file:

```bash
PREFLIGHT=""
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && PREFLIGHT="$CLAUDE_PLUGIN_ROOT/scripts/preflight.sh"
[ -x "$PREFLIGHT" ] || PREFLIGHT="$ROOT/.claude/plugins/hero-skills/scripts/preflight.sh"
[ -x "$PREFLIGHT" ] || PREFLIGHT="$HOME/.claude/plugins/hero-skills/scripts/preflight.sh"
"$PREFLIGHT" $ARGUMENTS
```

Stream the output to the user verbatim. Do NOT filter or summarize lines — the structured prefixes (`[OK]`, `[WARN]`, `[BLOCKER]`, `[SKIP]`) are how the user scans the result quickly.

### Step 2: Interpret the Exit Code

Capture the script's exit code. Then:

- **Exit 0, 0 warnings** → "All preflight checks passed. Safe to run hero-skills:one-shot or any individual hero skill."
- **Exit 0, N warnings** → "Preflight passed with N warning(s). Safe to proceed; warnings are advisory and may bite later."
- **Exit 1** → "Preflight found one or more blockers. The hero-skills pipeline will fail if you continue. Fix the blockers above, then re-run hero-skills:preflight."

For each `[BLOCKER]` line, the script already prints the recommended fix inline. Do not re-explain it — just point the user at the line.

### Step 3: Summary

Print a short summary block matching the style of other hero skills:

```
Preflight Summary
=================
Bucket(s):  tooling | repo | runtime | pipeline | all
Projects:   (all) or (the scoped list)

Blockers:   N
Warnings:   M
Skipped:    K

Result:     PASSED | BLOCKED

Next steps:
  hero-skills:one-shot $ARGUMENTS         # Steps 1–12 in one go (once blockers are clear)
  hero-skills:plan-work                   # …or start with Step 1 alone and run the rest manually
  hero-skills:preflight --bucket repo     # Re-run a single bucket after fixing (tooling|repo|runtime|pipeline)
```

If `Result: BLOCKED`, do not suggest `hero-skills:one-shot` as a next step — list the recommended fix commands from the script output instead.

## When This Skill Runs Automatically

`hero-skills:one-shot` calls `scripts/preflight.sh --bucket all` (with `--projects` scoped to the projects the diff touches) at **Step 0.3**, before auto-branching and resume detection. If any blocker fires, one-shot halts before any branch is created.

You can also call it standalone any time — e.g., after adding a new project to HERO.md, after editing a project's `.env`, or when something in the pipeline looks wrong and you want a single command to see the whole environmental state.

## Notes

- The script is read-only. It never edits files, creates branches, modifies remote state, or runs interactive prompts. Safe to run on every invocation.
- For ports: the check uses `lsof -nP -iTCP:PORT -sTCP:LISTEN`. If `lsof` is unavailable (rare on macOS / linux dev boxes, common in minimal containers), the port check skips with `[SKIP]` rather than reporting a false-OK.
- For Playwright MCP: the canonical check is `claude mcp list`. If the `claude` CLI isn't on PATH (unusual but possible), the script falls back to grepping `~/.claude.json` for a `playwright` entry.
- For pr-review-toolkit: the script looks in `~/.claude/plugins/pr-review-toolkit/` and `$ROOT/.claude/plugins/pr-review-toolkit/`. If the plugin lives elsewhere on the user's setup, the check may report a false `[WARN]` — that's safe, since the worst case is `hero-skills:review-pr` falling back to a thinner review.
