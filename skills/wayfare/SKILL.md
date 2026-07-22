---
name: wayfare
# prettier-ignore
description: Control plane over .plans/ — bind features from the source repo to a target-design repo (HERO.md-configured), pin immutable SHA snapshots, gate and emit hermetic work orders for PR-only builds.
argument-hint: "[status | feature IDEA | pin FEATURE_ID | gate FEATURE_ID | order FEATURE_ID | ready ORDER_ID | do-next | drift [FEATURE_ID] | resync]"
---

# Wayfare — The Control Plane over `.plans/`

Wayfare treats the private `.plans/` store as the **system of record** laid
over the substrates the work actually touches — today the source repo and
the target-design repo, both configured in HERO.md. A **feature** is a set
of typed bindings — edges into those substrates, not prose. A **pin** is an
immutable snapshot of what a binding pointed at, taken at a known moment.
A **work order** is a hermetic build instruction assembled only from pins,
emitted only past the gates, executed only on a PR-only branch — and only
after a human marks it ready.

Wayfare never builds. It binds, pins, gates, and emits;
`hero-skills:one-shot` executes.

## The Substrates

Two substrates are wired today, configured in HERO.md (next section). Three
more — `linear`, `wiki`, `infra` — exist in the model but have **no
connectors yet**: bind them `none` unless the user hands you a ref to record.

| Substrate | What it is                                                          | Live ref                    | Pin form                                 |
| --------- | ------------------------------------------------------------------- | --------------------------- | ---------------------------------------- |
| `source`  | The repo being changed — `source-repo` in HERO.md, normally `.`     | paths on the default branch | commit SHA + paths (git is the snapshot) |
| `target`  | The target-design repo — the end-state source is being moved toward | paths on `target-branch`    | commit SHA + paths (git is the snapshot) |

Both are git repos, so a pin is a SHA — immutable by construction. But the
target repo still moves behind your back (the design evolves on its branch);
that is what drift detection watches, and why builds only ever read the
pinned SHA: a build that reads a live branch is a build whose inputs can
change mid-flight.

## Configuration — the `## Wayfare` block in HERO.md

```markdown
## Wayfare

- source-repo: . # the repo wayfare runs in; virtually always `.`
- target-repo: OWNER/NAME # or a local path or git URL; `none` disables the target substrate
- target-branch: main # the branch the target design lives on
- target-path: specs/ # optional subtree holding the design; omit or `none` for the whole repo
```

Read the keys with `hero_field` (Step 0). A missing block or
`target-repo: none` means wayfare still manages features and orders, but
every target binding is `none` and the target-side gate checks skip.

## Doctrine

1. **`.plans/` is the system of record.** Private and git-ignored (it is the
   same store `hero_work_store` manages) — your plate, not the team's board.
   What the substrates say is input; what `.plans/` says is what you act on.
2. **Features are typed bindings.** Every feature names its edge into each
   substrate in the table — or records `none` explicitly. A substrate silently
   unexamined is how a build ships against a design that moved.
3. **Pins are immutable.** A pin is written once and never edited; re-pinning
   creates the next pin id and the old one stays for provenance. Work orders
   reference pins, never live refs.
4. **Builds are gated and hermetic.** A work order may only be emitted when
   every gate passes, and its body must be executable with zero live external
   lookups — every input is in the body, in a pin snapshot, or in the pinned
   source commit.
5. **PR-only branches.** Execution happens on a branch named per
   `hero_branch_policy` and lands via PR (HERO.md merge method). Never on the
   default branch.
6. **Humans mark ready.** Everything wayfare emits carries `status: planning`.
   Only the user flips an item to `todo` — directly, or via `wayfare ready` —
   and until then it is invisible to `hero-skills:one-shot` by design.
7. **Emit, don't implement.** Same doctrine as `think-it-through`: wayfare
   produces work orders; execution belongs to one-shot.

## Instructions

### Step 0: Load

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB"

ROOT=$(hero_root)
# Only the Wayfare block matters here — don't cat the whole HERO.md into context.
awk '/^## Wayfare/{f=1;next} /^## /{f=0} f' "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG" # hero-lint: allow-inline — display only; values are read via hero_field below
STORE=$(hero_work_store)
mkdir -p "$STORE/pins"

SOURCE_REPO=$(hero_field source-repo) || SOURCE_REPO=.
TARGET_REPO=$(hero_field target-repo) || TARGET_REPO=none
TARGET_BRANCH=$(hero_field target-branch) || TARGET_BRANCH=main
TARGET_PATH=$(hero_field target-path) || TARGET_PATH=""
[ "$TARGET_PATH" = none ] && TARGET_PATH=""
echo "wayfare: source=$SOURCE_REPO target=$TARGET_REPO@$TARGET_BRANCH${TARGET_PATH:+ path=$TARGET_PATH}"
```

Run `hero_ready_items "$STORE"` inside the verbs that consume the listing
(`status`, `gate`, `order`, `do-next`, `resync`) — not up front: it prints one
row per store item, which the other verbs never read.

If `TARGET_REPO` is `none` and the task needs the target substrate, say so
and offer to add the `## Wayfare` block to HERO.md before continuing.

Then dispatch on the first word of `$ARGUMENTS`; empty means `status`.

### `status` — where everything stands

Print the readiness view grouped by state (`plan` rows first — they are what
waits on the user), then one line per feature: bindings bound vs `none`,
pinned or not, orders emitted and their states. Close with the single next
action per feature (bind → pin → gate → order → ready → do-next).

### `feature IDEA` — bind a feature

1. Investigate before writing: read the relevant source paths, and read the
   target design in the target repo — remote targets are read through the
   bare cache described under `pin`; never write to it. If the idea is still
   vague after investigating, run `hero-skills:think-it-through` (via the
   Skill tool) to grill it to shared understanding first — bindings capture
   conclusions, not guesses.
2. Write one `.plans/NNN-slug.md` item (format below) with `kind: feature`,
   `status: planning`, a `source` and a `target` binding, and explicit
   `none` rows for `linear`, `wiki`, and `infra` (record a ref if the user
   hands one over). `none` is a valid binding, silence is not.
3. Ids continue the store's single sequence per think-it-through's numbering
   rules: number from the highest existing `id`, re-checked immediately
   before writing; zero-pad only the filename.

### `pin FEATURE_ID` — snapshot the bindings

For each binding that is not `none`, resolve its live ref NOW and freeze it
as `.plans/pins/FEATURE_ID/N-SUBSTRATE-slug.md`:

- `source` — `git fetch origin` then pin the default branch head:
  `commit: $(git rev-parse origin/$(hero_default_branch))` plus the bound
  paths. Git makes it immutable; no copy needed.
- `target` — resolve the live head of `target-branch`: a local-path repo via
  `git -C TARGET_REPO fetch && git -C TARGET_REPO rev-parse`, a remote via
  `git ls-remote URL refs/heads/TARGET_BRANCH`. The pin records `repo:`,
  `commit:`, and the bound `paths:` (under `target-path`) — no body copy.
  For content reads, keep one persistent bare mirror at
  `$STORE/.cache/target.git` (git-ignored with the store; `git clone --bare`
  once, `git fetch` to top up) and read
  `git --git-dir "$STORE/.cache/target.git" show COMMIT:PATH` — every verb
  reuses the cache instead of re-cloning, and reads stay hermetic at the
  pinned SHA.
- a URL/ID ref the user bound by hand (deferred substrates) — fetch the
  content, write it as the pin's body, and record
  `sha256: $(shasum -a 256 ...)` of that body in the frontmatter.

Append the new pin ids (`FEATURE_ID.N`) to the feature's `pins:` list. Pins
are append-only: a re-pin creates `FEATURE_ID.N+1`; never edit or delete an
existing pin file. Pin files live under `pins/`, outside `hero_ready_items`'
glob, so they never pollute the readiness listing.

### `gate FEATURE_ID` — run the gates

Report PASS or FAIL per gate, in order, and stop at the first failure with
the concrete fix. Never emit orders past a failing gate.

| Gate | Check                                                                                                      |
| ---- | ---------------------------------------------------------------------------------------------------------- |
| G1   | Bindings complete — `source` and `target` bound (target `none` only when HERO.md disables it), deferred substrates carry explicit `none` |
| G2   | Pinned — every non-`none` binding has a current pin                                                         |
| G3   | Fresh — run the `drift` check (below) on the feature's pins; any `DRIFTED` row fails until re-pinned or the user explicitly accepts it (record the acceptance in the feature's Notes) |
| G4   | Source current — G3's re-resolved source SHA equals `origin` default-branch HEAD (no extra fetch; source drift has no acceptance escape — always re-pin) |
| G5   | Store sound — `hero_ready_items` stderr is clean (no dangling `depends_on`, no duplicate ids)               |
| G6   | Tracker live — only when a `linear` ref is bound: the issue is not closed or cancelled; otherwise skip as N/A |

### `order FEATURE_ID` — emit hermetic work orders

Gates must have passed **in this same session** — run `gate` first, not from
memory. Then break the feature into the smallest units that are each
independently PR-able, and write each as a work-order item (format below):
`kind: work-order`, `status: planning`, `pins:` listing exactly the pins it
consumes, `branch:` per `hero_branch_policy`, `depends_on` for real blockers
only.

**The hermeticity test, before writing each order:** read the body as an
executor with no network access. Is every input either in the body itself, in
a listed pin snapshot, or in the pinned source commit? If anything would need
a live lookup, the order is not hermetic — pin the missing input and try
again.

Print the readiness view — new orders appear as `plan` rows awaiting the
ready-mark (Doctrine 6).

### `ready ORDER_ID` — the human gate

Only ever on the user's explicit instruction, and only for the ids the user
named. Flip `status: planning` to `todo` and add `ready_marked:` with the
date. Never suggest-and-flip in one breath; never batch unnamed items. If the
user asks wayfare to mark something ready that has not passed gates, run
`gate` first and show the result before flipping anything.

### `do-next` — stage the next READY order for one-shot

The bridge from control plane to execution — wayfare stages, one-shot builds:

1. **Select.** From `hero_ready_items`, take the READY rows; prefer
   `kind: work-order` items and pick the lowest id (dependency order already
   holds — READY means every blocker is `done`). No READY row → report what
   blocks instead: `plan` rows awaiting `wayfare ready`, blocked rows and
   their unmet deps, or an empty plate.
2. **Re-verify, don't trust.** Readiness is a claim about dependencies, not
   the world. Re-run the light gates for this order: its pins still match
   their live refs (G3) and the source pin still equals `origin`
   default-branch HEAD (G4) — one `git fetch origin` here serves both G4 and
   step 3's checkout. Either failing → stop and recommend re-pin + re-gate;
   do not build a stale order just because it is marked ready.
3. **Stage the branch.** Require a clean worktree with no merge or rebase in
   progress — if not, stop and name what's uncommitted or in-flight; never
   stash silently. Then (origin already fetched in step 2):

   ```bash
   git checkout -b BRANCH_FROM_ORDER "origin/$(hero_default_branch)"
   ```

   `BRANCH_FROM_ORDER` is the order's `branch:` frontmatter, validated with
   `hero_is_valid_branch` first — a store file is hand-editable and its value
   reaches `git checkout`.
4. **Hand off.** Print the order's id, title, pins, and success criteria,
   then: `Next step: hero-skills:one-shot NNN-slug — build this order on the
   staged branch` (print only — model-invocation-restricted, cannot
   auto-run). One-shot marks it `in-progress`/`done`; do not pre-flip status
   here.

### `drift [FEATURE_ID]` — compare pins to the world

For the current pins of the named feature (or all features): re-resolve each
live ref (branch-head SHA for repo pins, fetched-content hash for snapshot
pins), compare to the pin, and report one row per pin — `FRESH`, `DRIFTED`,
or `UNREACHABLE`. Resolve each unique repo@branch once and compare all its
pins against that answer — not one remote call per pin. Drift does not invalidate an in-flight build — the build is
hermetic against its pins, which is the point; drift is information for the
*next* pin. But G3 will fail on the next `gate` run, so recommend re-pin +
re-gate for any not-yet-ready orders of a drifted feature.

### `resync` — re-read the world, find the gaps, replan

`drift` answers "did my pins go stale?"; `resync` answers "is my plan still
the right plan?" Two passes — the first strictly read-only:

**Pass 1 — report (no writes).** For every feature that is not `done`:

1. Run the drift check on all its current pins.
2. For each drifted binding, diff the pin snapshot against the content
   already fetched for step 1's hash (no second fetch) and summarize what
   actually changed — cosmetic rewording is noise; a changed target design
   (or a rescoped hand-bound issue) is a replan trigger.
3. Check `source` beyond the hash: list commits since the source pin that
   touch the bound paths — work may have landed out-of-band that an order
   duplicates or that satisfies one already.
4. Gap analysis both directions:
   - **Uncovered** — requirements now in the target design (or the Linear
     issue) that no existing order addresses → candidate new orders/features.
   - **Obsolete** — orders whose work the target dropped or the source
     already satisfies → candidates to close out.

   Present it as one table: item/binding, what changed, proposed action
   (re-pin, edit order, new order, new feature, close out).
5. Sanity-check the store itself: `hero_ready_items` stderr warnings
   (dangling deps, duplicate ids) are gaps too.

**Pass 2 — replan (only after the user confirms which proposals to apply).**
Re-pin confirmed-drifted bindings, write new and edited items with
`status: planning`, and record accepted drift in the feature's Notes.
Obsolete orders: the user chooses — mark `done` with a Notes line naming what
satisfied it, or delete the file. Then re-run `gate` for every touched
feature. **Resync never marks anything ready** (Doctrine 6) — replanned work
re-enters at `planning`, including orders that were `todo` before the replan
touched them.

## Formats

Features and work orders share the store's sequence, format, and lifecycle —
they are `think-it-through` work-items with extra typed frontmatter, so
`hero_ready_items`, one-shot, and handoff all keep working on them unchanged.

### Feature item — `.plans/NNN-slug.md`

```markdown
---
id: 12
kind: feature
title: Payments v2 cutover
status: planning # planning | todo | in-progress | done — only the user flips planning
depends_on: []
one_way_door: true
success: "Source matches the target design for payments; ELE-142 closed"
bindings:
  - substrate: source
    ref: services/payments/
  - substrate: target
    ref: payments/ # paths under target-path in the target repo
  - substrate: linear
    ref: none # linear/wiki/infra: connectors deferred — examined, not skipped
  - substrate: wiki
    ref: none
  - substrate: infra
    ref: none
pins: [] # appended by `wayfare pin` — ids like 12.1
---

## Context

Why this feature exists and what moving source toward target means here.

## Notes

Gate history, accepted drift (what, when, why), open questions.
```

### Pin snapshot — `.plans/pins/FEATURE_ID/N-SUBSTRATE-slug.md`

```markdown
---
pin: 12.1
substrate: target
ref: payments/
repo: github.com/acme/target-design
commit: FULL_COMMIT_SHA
pinned: 2026-07-22
---

Repo pins have no body — the SHA is the snapshot (Doctrine 3).
```

A pin for a hand-bound URL/ID ref (deferred substrates) instead snapshots the
fetched content as its body, with `sha256:` of that body in place of `repo:`
and `commit:`.

### Work order — `.plans/NNN-slug.md`

```markdown
---
id: 15
kind: work-order
feature: 12
title: Extract payment gateway interface
status: planning # the user marks it todo via `wayfare ready 15`
depends_on: [14] # orders that must land first — blockers only
pins: [12.1, 12.3] # every external input — hermetic, nothing live
branch: feat/extract-payment-gateway
success: "Gateway interface extracted; existing payment tests green"
---

## Work order

Self-contained instructions — hermetic per Doctrine 4: the executor needs no
live lookups.

## Gates

G1–G6 PASS 2026-07-22 (accepted drift: none)
```

## Closing the loop

When every order of a feature is `done`, run `drift` against its `target`
binding: if source now satisfies the target design, mark the feature `done`
(and, when a `linear` ref is bound, offer to close the issue — ask before
writing to the tracker). If it doesn't, the gap is the next feature or
order — bind it, don't stretch the finished one.

## Anti-Patterns

| Smell                                | Why it's wrong                                                       |
| ------------------------------------ | -------------------------------------------------------------------- |
| Building from a live ref             | Doctrine 4 — inputs can change mid-build; orders reference pins.     |
| Editing a pin                        | Doctrine 3 — supersede with the next pin id.                         |
| Marking your own orders ready        | Doctrine 6 — the ready-mark is the user's act.                       |
| Emitting orders past a failing gate  | Doctrine 4 — a red gate stops the line.                              |
| Executing a work order yourself      | Doctrine 7 — wayfare emits; `one-shot` builds.                       |
| A substrate silently skipped         | Doctrine 2 — record `none` explicitly.                               |
| Gating from memory                   | Gates are re-run per `order`, in-session. The world moved since.     |
| `do-next` on a dirty worktree        | Never stash silently — stop and name what's uncommitted.             |
| Resync that silently rewrites items  | Pass 1 is read-only; writes happen only on confirmed proposals.      |

## Next steps

Pick exactly one, from the store's current state:

- **A READY work order exists**: `Next step: hero-skills:wayfare do-next — re-verify, stage its PR-only branch, and hand off to one-shot`.
- **Orders sit in `plan`**: name them — `wayfare ready ORDER_ID` (or editing the file) releases each one.
- **A feature is unbound, unpinned, or ungated**: run `status` — it prints the next verb per feature.
- **The store feels stale** (pins old, tracker moved, work landed out-of-band): `Next step: hero-skills:wayfare resync — re-read the world and replan the gaps`.
