---
name: fleet
# prettier-ignore
description: Create and converge FLEET.md, the local unversioned map of sibling checkouts (group, port). sync scans the folder and proposes rows; review reports drift read-only.
argument-hint: "[sync | review]"
---

# Fleet — The Map of the Checkouts Beside You

A fleet folder holds sibling repos. `FLEET.md` at its top says which of them
are family, which are just parked there, and which host port each dev stack
claims — so a skill run from the folder can fan out to the right repos, and
two stacks never fight over one port. The standard is
[docs/FLEET-MD.md](../../docs/FLEET-MD.md); read it once before the first
`sync`.

## Arguments

- `sync` — bootstrap or converge `FLEET.md`. Investigate, propose, write only
  what the user confirms.
- `review` — report drift between the rows and the folder. Writes nothing.
- (none) — `review`.

## Instructions

### Step 0: Load

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB"
SCAN="$(dirname "$HERO_LIB")/fleet-scan.sh"

if FLEET_ROOT=$(hero_fleet_root); then
  echo "FLEET_ROOT=$FLEET_ROOT"
  hero_fleet_repos "$FLEET_ROOT"
else
  # No FLEET.md above us. The candidate is the nearest folder that is not a
  # repo and holds checkouts: this folder if we are not in git, else the
  # repo's parent.
  CAND=$(git rev-parse --show-toplevel 2>/dev/null); CAND="${CAND:+$(dirname "$CAND")}"; CAND="${CAND:-$PWD}"
  echo "NO_FLEET candidate=$CAND"
  "$SCAN" "$CAND" --list
fi
```

> Each bash block below runs in a fresh shell — re-source `hero-lib.sh` at the top of any block that calls a `hero_*` function.

`NO_FLEET` with `review` → STOP: say there is nothing to review and offer
`sync`. `NO_FLEET` with `sync` → bootstrap (below), but **confirm the
candidate folder first**: show its path and the checkouts the scan found, and
ask. A wrong guess writes a registry into someone's home directory.

### `sync` — converge FLEET.md with the folder

Both modes share one shape: **scan, propose, write only what the user
confirms.** `sync` writes two things: `FLEET.md`, and the `## Fleet` section
of each fleet repo's `AGENTS.md` (step *Make the repos fleet-aware*, both
modes). Any other repo change — a port, a missing `HERO.md` — is routed to
the skill that owns it.

**Bootstrap — no FLEET.md yet.**

1. Scan: `"$SCAN" "$CAND" --list`. Every git checkout directly under the
   folder is a candidate row; plain folders are not.
2. Ask, in one pass, for the `## Fleet` block: name (default: the folder
   name), `org` (the GitHub owner — read it off the first checkout's
   `origin` with `git -C PATH remote get-url origin`, offer it), the template
   repo if there is one, and the port range. Skip what does not apply; only
   `name` is required.
3. Ask for the groups. Offer `template` / `apps` / `infra` / `none` with the
   meanings from the standard, and let the user rename or add. `none` stays.
4. Propose the rows as a table — name, group, port, what — with every group
   defaulted to `none` and the port read from the compose file. Guess nothing
   about membership: a repo is fleet when the user says so. `what` comes from
   the repo's `README.md` first line or `HERO.md`'s framework field; leave it
   blank rather than invent it.
5. Show the whole file, confirm, write `FLEET_ROOT/FLEET.md`. Then run
   `"$SCAN" "$FLEET_ROOT" --review` and show it — a fresh registry that
   already reports collisions is telling the truth on day one.

**Converge — FLEET.md exists.**

1. Run `"$SCAN" "$FLEET_ROOT" --review`. Exit 0 with no output: say so and
   stop. Otherwise, one proposal per finding:

   | Finding | Proposal |
   | --- | --- |
   | `UNLISTED` | add a row; ask the group (default `none`); port from the compose file |
   | `MISSING` | drop the row, or fix `path` if the folder moved — ask |
   | `NOT_GIT` | same as `MISSING`; a folder that stopped being a checkout is not a repo |
   | `PORT_MISMATCH` | the row is the assignment, the compose default is the implementation. Ask which is right. If the repo must change, hand it to `hero-skills:one-shot` in that repo — the standard's last anti-pattern names every place the port appears — never edit the repo from here |
   | `PORT_COLLISION` | pick the next free port in `port-range` for the newer row, propose it; same routing as a mismatch for the repo side |
   | `NO_HERO` | offer `hero-skills:init-hero` in that repo (a subagent, per the standard's fan-out) |
   | `NO_AGENTS` | same, via init-hero's Step 1 |
   | `NOT_FLEET_AWARE` | *Make the repos fleet-aware*, below |

2. If `org` is set, list what exists there and is not on disk —
   `gh repo list ORG --limit 200 --json name,isArchived --jq '.[] | select(.isArchived|not) | .name'`
   minus the folder's checkouts. Print it as *not cloned*; add no rows. A
   repo joins the fleet by being cloned beside the others, not by appearing
   in a listing.
3. Show the proposed rows, confirm, write. Re-run `--review` and show the
   remainder — the repo-side findings that were routed elsewhere stay until
   those PRs merge, and that is the correct state.

**Make the repos fleet-aware — after the rows are written, both modes.**

A clone knows nothing about the folder it sits in, so every fleet repo's own
instructions carry the pointer. For each row whose group is not `none` and
whose `AGENTS.md` (or `CLAUDE.md`) has no `## Fleet` heading — the
`NOT_FLEET_AWARE` rows from `--review` — propose adding the section:

```bash
SECTION="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/assets/fleet/agents-md-fleet-section.md"
cat "$SECTION"
```

Show the list of repos and the section once, confirm once, then append it
(a blank line, then the file's contents) to each repo's `AGENTS.md` — or to
`CLAUDE.md` when that is the regular file and `AGENTS.md` is absent. Do not
rewrite anything else in those files, and do not commit: report the repos
now carrying an uncommitted change and offer `hero-skills:push-pr` from the
fleet root, fanning out to exactly those repos. A repo whose section is
present but differs from the asset is re-vendored the same way; the asset is
authored here, and a per-repo edit to it is output to be overwritten.

### `review` — report drift, write nothing

```bash
"$SCAN" "$FLEET_ROOT" --review
```

Print each finding with its meaning from the standard and the repo it names.
Exit 1 means there is something to fix; say which of `sync` or a repo-side
skill fixes it. Do not write `FLEET.md`, and do not touch a repo.

## Anti-patterns

- **Guessing membership.** A checkout with a `HERO.md` is a repo the hero
  skills run in, not proof it shares the fleet's stack. Default `none`, ask.
- **Editing a repo to satisfy the registry.** Beyond the `## Fleet`
  section, `sync` touches no repo. Port changes and missing configs go through
  the skill that owns them, in that repo, on a PR.
- **Adding rows for repos that are not on disk.** The org listing is
  informational. See the standard.

## Next steps

- Findings routed to repos → run the named skill from the fleet root and pick
  those repos (the standard's fan-out), or `cd` in.
- Clean → nothing. Re-run `review` after cloning or moving a checkout.
