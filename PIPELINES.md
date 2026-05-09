# Pipelines

Hero skills that orchestrate multi-step work render a linear-DAG progress line on
the console at each step transition. This doc is the single source of truth for
the canonical pipelines and the rendering format.

## Render Format

At the **start of each step** (just after announcing what is about to run), print:

```
[N/M] (✓) step1 → (✓) step2 → (▶) step3 → ( ) step4 → ... → ( ) stepM

Now running: step3
```

Rules:

- `N` is the 1-indexed current step. `M` is the total number of steps.
- `(✓)` for steps already completed in this session.
- `(▶)` for the step currently starting.
- `( )` for steps not yet run.
- Use Unicode `→` (U+2192) between steps for the arrow chain.
- Keep the entire chain on one line, even if it wraps in narrow terminals.
- The "Now running:" line names the step that just opened, no other prose.

When a step is **skipped** (because it doesn't apply — e.g., `test` step on a
docs-only commit), mark it `(–)` and continue to the next step. Do not collapse
or renumber.

When the pipeline **stops early** (user declined, hard gate, error), print a
final DAG with `(✗)` on the failed/declined step and `( )` on remaining ones,
followed by `Stopped: REASON`.

## Canonical Pipelines

### Pipeline 1: init-project — scaffold a new project end-to-end

```
scaffold → setup-dev → init-hero → first-commit
```

Owner: `hero-skills:create-project`. The skill scaffolds the project, then
chains forward to `hero-skills:setup-dev`, `hero-skills:init-hero`, and a
final commit. Each stage announces itself with the DAG line.

**Naming note for `first-commit`:** When scaffolding a *standalone* repo,
create-project Step 6 already produces the literal first commit (the
scaffold). The DAG node `first-commit` refers specifically to **the commit
that lands `HERO.md` and `CLAUDE.md`** — for standalone repos this is the
second commit; for "added to existing repo" it is just the next commit. The
node is named for the canonical case where everything begins with HERO.md
present from commit one onward.

### Pipeline 2: one-shot — ticket to merged PR in a single invocation

```
plan → implement → test → e2e → commit → push-draft → self-review → respond → ship
```

Owner: `hero-skills:one-shot`. Nine steps:

1. `plan` — fetch ticket / parse description, produce a plan in Plan Mode (calls `plan-work` internals)
2. `implement` — apply the plan as code edits
3. `test` — run lint/typecheck/unit tests (`test-changes`)
4. `e2e` — Playwright-MCP smoke test of the routes affected by the diff (`smoke-ui`). Skipped with `(–)` if HERO.md declares no UI project.
5. `commit` — conventional commit (`commit-changes`)
6. `push-draft` — push and open a draft PR (`push-pr`)
7. `self-review` — review the draft, apply fixes, mark ready (`review-pr`)
8. `respond` — answer Copilot/CodeRabbit/Greptile inline comments and resolve threads (`respond-to-pr`)
9. `ship` — `@auto-approve`, await verdict, merge if green, then reset to default branch (`ship-pr`)

The `e2e` node sits before `commit` so a UI regression aborts the pipeline before
anything is written to git history. For backend-only PRs the node is skipped
(rendered `(–)`), not failed.

The user must explicitly approve at each gate that involves a destructive or
shared-state change: marking the PR ready, posting `@auto-approve`, and
merging. The skill does not skip those confirmations.

### Pipeline 3: hero init/update — generate or refresh HERO.md

```
investigate → confirm → write → commit
```

Owner: `hero-skills:init-hero`. Four steps:

1. `investigate` — deeply scan the repo for evidence of stack, conventions, CI, deploy
2. `confirm` — present findings as a numbered list and ask the user to confirm/correct
3. `write` — write HERO.md, update CLAUDE.md summary sections, and (if the user opted in during `confirm`) install `.github/workflows/auto-approve.yml` via Step 6a of the skill
4. `commit` — stage and commit HERO.md + CLAUDE.md (and the auto-approve workflow if installed this run)

Run by itself (`hero-skills:init-hero` or `hero-skills:init-hero --update`) or
as the third step of Pipeline 1.
