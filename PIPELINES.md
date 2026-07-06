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
plan → implement → test → simplify → push → self-review → mark-ready → await-review → respond → ship
```

Owner: `hero-skills:one-shot`. Invoked with an issue ID or description it starts at `plan`; invoked with no arguments it resumes the current goal (in-progress branch/diff/PR) from the detected step and drives it to merged + a reset checkout. Ten steps — each maps to a single skill (or `inline` when one-shot drives it directly without delegating):

| # | Step | Skill to run standalone | Notes |
|---|------|-------------------------|-------|
| 1 | `plan` | `inline` (Plan Mode) | fetches a Linear issue if `$ARGUMENTS` is an issue ID, else treats it as a plain-text description |
| 2 | `implement` | `inline` (Plan Mode → edits) | applies the approved plan as code edits |
| 3 | `test` | `hero-skills:test-changes` | run lint/typecheck/unit tests, including UI smoke via Playwright MCP |
| 4 | `simplify` | `/simplify` (external) | review the dirty diff for reuse/quality/efficiency and fix; `(–)` if `/simplify` unavailable |
| 5 | `push` | `hero-skills:push-pr` | commits outstanding work with a conventional commit and pushes a draft PR |
| 6 | `self-review` | `hero-skills:review-pr --no-mark-ready` (Steps 1–8) | run pr-review-toolkit agents on the draft, apply fixes |
| 7 | `mark-ready` | `hero-skills:review-pr`'s own Step 9, or `gh pr ready` | hard user gate that converts draft → ready |
| 8 | `await-review` | `inline` (poll) | poll for the configured Code Review Agent's first comment; `(–)` if `agent: none` |
| 9 | `respond` | `hero-skills:respond-to-comments` | address the bot's inline comments and resolve threads |
| 10 | `ship` | `hero-skills:ship-pr` | `@auto-approve`, await verdict, ask the user to merge, merge, reset to default branch |

UI smoke runs inside `test`; backend-only PRs skip it.

`simplify` sits between `test` and `push` so the dirty diff is tidied
before it lands in git history. `push-pr` also invokes `/simplify`
internally for standalone use; running one-shot just makes that step visible
in the DAG and pays a no-op cost on the second invocation.

`mark-ready` is split from `self-review` so the conversion from draft → ready
is a visible, separately-gated step. `await-review` is split from `respond`
so the poll-for-bot phase is visible even when there is nothing to respond to.

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
