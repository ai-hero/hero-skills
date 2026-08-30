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
that lands `HERO.md` and `AGENTS.md`** — for standalone repos this is the
second commit; for "added to existing repo" it is just the next commit. The
node is named for the canonical case where everything begins with HERO.md
present from commit one onward.

### Pipeline 2: one-shot — ticket to merged PR in a single invocation

```
plan → implement → simplify → push → self-review → mark-ready → await-review → respond → ship
```

Owner: `hero-skills:one-shot`. Invoked with an issue ID or description it starts at `plan`; invoked with no arguments it resumes the current goal (in-progress branch/diff/PR on the current branch, plus the in-flight item's `## Subtasks` checklist — the plan file is the state file, so a run that died mid-implement resumes at its first unchecked line) from the detected step and drives it — through the usual user gates — to merged + a reset checkout. Nine steps — each maps to a single skill (or `inline` when one-shot drives it directly without delegating):

| # | Step | Skill to run standalone | Notes |
| --- | --- | --- | --- |
| 1 | `plan` | `hero-skills:think-it-through` | resolve `$ARGUMENTS` against `.plans/` and the tracker first; grill only if nothing matches. Re-verifies the item is still outstanding before building |
| 2 | `implement` | `inline` | executes the resolved work-item against its `success` criteria |
| 3 | `simplify` | `/simplify` (external) | review the dirty diff for reuse/quality/efficiency and fix; `(–)` if `/simplify` unavailable |
| 4 | `push` | `hero-skills:push-pr` | tests first (lint/typecheck/unit + UI smoke via Playwright MCP), then commits outstanding work with a conventional commit and pushes a draft PR |
| 5 | `self-review` | `hero-skills:review-pr --no-mark-ready` (Steps 1–8) | run the pr-review-toolkit agents plus a security pass on the draft, apply fixes |
| 6 | `mark-ready` | `hero-skills:review-pr`'s own Step 9, or `gh pr ready` | hard user gate that converts draft → ready |
| 7 | `await-review` | `inline` (poll) | poll for the configured Code Review Agent's first comment; `(–)` if `agent: none` |
| 8 | `respond` | `hero-skills:respond-to-comments` | address the bot's inline comments and resolve threads |
| 9 | `ship` | `hero-skills:ship-pr` | `@auto-approve`, await verdict, ask the user to merge, merge, reset to default branch |

UI smoke runs inside `push`'s test phase (absorbed from the former `test-changes` skill — `hero-skills:push-pr test` runs it standalone); backend-only PRs skip it.

`simplify` sits between `implement` and `push` so the dirty diff is tidied
before it lands in git history. `push-pr` also invokes `/simplify`
internally for standalone use; running one-shot just makes that step visible
in the DAG and pays a no-op cost on the second invocation.

**The work-item store closes this pipeline's loop.** `think-it-through`,
`handoff`, `harden`, and `wayfare` write items into the git-ignored `.plans/`
store, and all read it back so they build on the plate rather than beside it. What
one-shot alone does is *execute* an item and close it out: Step 1 resolves
against the store before grilling anything new, and Step 9a marks the merged
item `done` — no other skill does that automatically.
Because nothing else observes the codebase on the store's behalf, Step 1 also
re-checks a resolved item's `success` criteria against reality — `status: todo`
only means nobody edited the file, not that the work is still outstanding.

**Architecture chains.** `wayfare sync` (both modes) runs
`hero-skills:architecture review` — and offers its `sync` — before judging
the roadmap, and `think-it-through` delegates a leading `arch` argument to
the same skill. Both edges require `architecture` to stay model-invocable
(guarded by validate.sh's `CHAINED_SKILLS`).

**The design return channel.** Every other edge flows target → source. One
flows back: one-shot logs a divergence it found while building into the
feature's `## Design Feedback`, and `wayfare sync` delivers it. Two
destinations, no third: a configured `feedback-repo` gets an issue wayfare
files itself (entries verbatim plus a manifest, destination confirmed
in-session), and everything else — `feedback-repo: none`, a rejected value,
or a repo with issues disabled — gets a packet under `$STORE/.feedback/`
that the user delivers by hand. `.plans/` is git-ignored and wayfare never writes the target, so
there is no other way out. Delivery deliberately does *not* route through
`hero-skills:handoff`: that skill distills the *current* conversation, which
would both narrate the wrong session and carry this repo's branches and PR
numbers into a third party's tracker. See
`skills/wayfare/references/feedback-channels.md`.

**one-shot authors only Step 2a items.** Step 2a pushes discovered or
mis-scoped work out of the running item into its own `.plans/` item — a
`kind: feature` carve when it satisfies target-design paths
(`origin: one-shot`), an ordinary `status: planning` work-item otherwise —
which is how the one-item-one-PR scope guard survives contact with
implementation. Everything else in the store is authored by the producers
above.

`mark-ready` is split from `self-review` so the conversion from draft → ready
is a visible, separately-gated step. `await-review` is split from `respond`
so the poll-for-bot phase is visible even when there is nothing to respond to.

The user must explicitly approve at each gate that involves a destructive or
shared-state change: marking the PR ready, posting `@auto-approve`, and
merging. The skill does not skip those confirmations.

### Pipeline 3: hero init/recalibrate — generate or refresh HERO.md

```
investigate → confirm → write → commit
```

Owner: `hero-skills:init-hero`. Four steps:

1. `investigate` — deeply scan the repo for evidence of stack, conventions, CI, deploy
2. `confirm` — present findings as a numbered list and ask the user to confirm/correct
3. `write` — write HERO.md, update AGENTS.md summary sections (CLAUDE.md is a symlink to it), and (if the user opted in during `confirm`) install `.github/workflows/auto-approve.yaml` via Step 6a and the design-system enforcement layer via Step 6b
4. `commit` — stage and commit HERO.md + AGENTS.md + the CLAUDE.md symlink (and the auto-approve workflow / design-system rule + hook if installed this run)

Run by itself (`hero-skills:init-hero` or `hero-skills:init-hero recalibrate`) or
as the third step of Pipeline 1.

Every other skill that reads HERO.md carries a scoped slice of this pipeline
as its own `recalibrate` verb: the same four steps, over only the fields that
skill reads, ending at `commit` without going on to do the skill's work. The
field map is `scripts/hero-fields.sh`; the contract is
[RECALIBRATE.md](./RECALIBRATE.md).

### Pipeline 4: wayfare deps — one Dependabot PR to merged and deployed

```
gather → select → ready-mark → current → review → test → ship → close-out
```

Owner: `hero-skills:wayfare deps [PR_NUMBER]` — see its `deps` verb for the
steps. The bot already implemented the bump, so there is no `implement` and
no PR of ours; `test` and `ship` delegate to `hero-skills:push-pr test` and
`hero-skills:ship-pr`, and the item is `done` only once the deployment
verifies.
