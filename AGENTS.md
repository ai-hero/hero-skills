# AGENTS.md

hero-skills is the A.I. Hero **plugin** repo: the skills agents invoke, the
assets they install into other repos, and the one workflow the whole fleet
executes. It ships no product and has no build.

Instructions for coding agents working here. Follow these strictly; ask before
deviating.

## The one thing to understand first

`.github/workflows/auto-approve.yaml` is a **reusable workflow that ~25 repos
call at `@main`**. Merging a change to it publishes that change to every one of
them, immediately, with no per-repo PR and no staging step.

That file has a blast radius no other file here has:

- **`main`'s branch protection is the only gate.** Approval required, stale
  approvals dismissed on push, last-push approval required. Without that last
  pair, an approval collected on a benign diff survives a force-push and ships
  fleet-wide seconds later.
- **Roll back by reverting on `main`.** That is the whole procedure.
- **Never rename or move it without sequencing.** Consumers reference it by
  exact path, so a rename breaks auto-approve — which is the mechanism that
  approves the PRs fixing it. Bank the consumer approvals first, then flip.

`assets/auto-approve/caller.yaml` is what gets installed into consumers. It is
not the logic and must stay small.

## Layout

`ls` shows it. The two non-obvious facts: `assets/` is installed **into**
other repos (the auto-approve caller, the design-system rule and hook, the
`## Fleet` section for AGENTS.md), and
`pr-check.yaml` is this repo's own gate while `auto-approve.yaml` is the fleet's.

## Conventions

- **Read before edit.** Match the surrounding style; don't introduce new patterns.
- **This file follows [docs/AGENTS-MD.md](./docs/AGENTS-MD.md)**, and
  `scripts/check-agents-md.sh` gates it on commit.
- **Comments: see [.claude/rules/comments.md](./.claude/rules/comments.md).**
  Claude Code loads it automatically; other agents must read it first. The
  one-line test, so it survives a skimmed read:

  > **Would someone later undo this for a reason this comment prevents?**

  If no, leave it out.
- **`.yaml`, never `.yml`** (PLACE-06). Nothing in this fleet mandates `.yml`.
  The installer defaults fresh installs to `.yaml` but still adopts an existing
  `.yml` — writing the second spelling beside the first would leave two live
  `issue_comment` workflows, and every trigger would run twice.
- **A folder of sibling checkouts is a fleet, not a project.** `FLEET.md` at
  its top maps it ([docs/FLEET-MD.md](./docs/FLEET-MD.md)); every repo skill
  tests for it in Step 0 and fans out instead of running against the folder.
  New skills get the check from `scripts/new-skill.sh`.
- **Work is concurrent, so rebase before you judge.** Several features
  build at once (wayfare's goal turns run one worktree subagent per
  feature), and other people merge underneath every PR. Before a review, an
  approval, or a merge, rebase the PR onto the current default branch with
  `hero_rebase_on_base` and confirm it went through — no conflict, checks
  green on the rebased head. A verdict on a stale head is a verdict on code
  that will not merge. Rebase *before* `@auto-approve`, never between the
  verdict and the merge: branch protection dismisses approvals on push.
- **Assets are vendored downstream, not authored there.** Fix a bug here, then
  re-vendor. A consuming repo's copy is output.
- **Tests are `scripts/*.test.sh` and both runners glob.** Add a suite and it
  gates automatically — no runner edit needed.
- **Agents are created once and versioned, not per run** — see `docs/PIPELINES.md`.

## Commands

```bash
pre-commit run --all-files     # every gate, including the shell suites
bash scripts/validate.sh       # plugin structure
```

## Fleet

This repo is one checkout in a fleet: sibling repos in the folder above it,
mapped by that folder's `FLEET.md` (`hero-skills:fleet`). The map is local and
unversioned, so clone this repo beside the others and run
`hero-skills:fleet review`. The host port this dev stack publishes is claimed
in that map, not chosen here: take the next free port there first, then set
it in every place this repo names it (compose defaults, health checks).
Any hero skill run from the fleet folder fans out to the repos you pick.

Work here is concurrent: other branches — including worktree subagents
building features in parallel — merge underneath every open PR. Before a
review, an approval, or a merge, rebase the PR onto the current default
branch and confirm it can be done (no conflict, checks green on the rebased
head); never review, approve, or merge a stale head. Rebase before the
approval, not after it — approvals are dismissed on push.
