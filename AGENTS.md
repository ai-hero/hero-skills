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

| Path | Purpose |
| --- | --- |
| `skills/` | One directory per skill, each a `SKILL.md`. The instructions agents actually follow. |
| `scripts/` | Shell helpers plus their `*.test.sh` suites. `validate.sh` checks plugin structure. |
| `assets/` | Files installed **into** other repos — the auto-approve caller, the design-system rule and hook. |
| `.github/workflows/` | `auto-approve.yaml` (shared, fleet-wide) and `pr-check.yaml` (this repo's own gate). |
| `docs/` | Everything that is not an entry document. |

## Conventions

- **Read before edit.** Match the surrounding style; don't introduce new patterns.
- **Comments: see [.claude/rules/comments.md](./.claude/rules/comments.md).**
  Claude Code loads it automatically; other agents must read it first. The
  one-line test, so it survives a skimmed read:

  > **Would someone later undo this for a reason this comment prevents?**

  If no, leave it out.
- **`.yaml`, never `.yml`** (PLACE-06). Nothing in this fleet mandates `.yml`.
  The installer defaults fresh installs to `.yaml` but still adopts an existing
  `.yml` — writing the second spelling beside the first would leave two live
  `issue_comment` workflows, and every trigger would run twice.
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
