# Configuration and `recalibrate`

The `## Wayfare` block in HERO.md: every field, how it is read, and what a
bad value does. Read in Step 0 of every verb.

## Configuration: the `## Wayfare` block in HERO.md

```markdown
## Wayfare

- source-repo: . # the repo wayfare runs in; virtually always `.`
- design-project: https://claude.ai/design/PROJECT_UUID # a claude.ai/design link or bare project UUID; `ask` = prompt for the link in-session, never stored; `none` disables the target and runs sync in self-review mode (source only) — sync asks each run whether to add one, unless the comment says `none # PERMANENT — reason` (a repo that structurally can't have one)
- design-transport: auto # auto | designsync | manual — how the design snapshot is refreshed (see Reading the target)
- feedback-repo: none # OWNER/NAME GitHub repo where design-feedback and architecture-feedback issues are filed; `none` keeps feedback in local packets
- ux-flow: flows/ # optional path, relative to the DESIGN PROJECT ROOT, holding the UX prototype flow / guided tour; `none` = the design genuinely has none
- design-system-repo: none # LOCAL PATH to a checkout of the design-system repo; `none` skips the upstream lane entirely. Its own HERO.md `design-project` is where the design system's design is read from, and design-system feedback is written into ITS `.plans/` store rather than filed as an issue
# reconciliation: docs/Design Reconciliation.md # path, relative to the DESIGN PROJECT ROOT, of the target's own rolling reconciliation document. Leave UNSET until you have looked; `none` asserts "looked, it keeps none" and stops plan from proposing it
```

**Read the bound copy before pulling a second project.** An app design project
that consumes a design system typically **vendors it into itself**, at
`_ds/DESIGN_SYSTEM_SLUG-DESIGN_SYSTEM_UUID/`, holding stylesheets, the manifest, the
component surface. When that directory exists in the target snapshot, it is the
better read: the vendored copy is the version **the design is actually bound
to**, whereas the upstream project head is whatever shipped most recently.
Reconciling the source against a design system the design itself has not
adopted yet manufactures drift that is nobody's to fix.

So the order is: use `_ds/` when the target snapshot has it; fall back to
`$DS_SNAP`, the design system's own design project read from
`design-system-repo`'s HERO.md, when it does not. Report the upstream lane as
skipped when neither is available. Say which one was read, because the two can
disagree, and that disagreement is itself a finding (the design is behind its
own system).

**Why the design system gets exactly one key.** `## Design System` in HERO.md
already describes the registry the source *installs from*: namespace,
registry URL, handbook. `design-system-repo` is about that same system as a
**party to the reconciliation**, and it is one key because it answers both
questions the reconciliation asks. Feedback lands in that repo's `.plans/`
store; the design system's **design** is read from that repo's own HERO.md
`design-project`, which is the authority on where its design lives. It
defaults to `none`, and `none` is a complete answer. A repo with no upstream
design system runs the two-layer round it always ran, with no upstream lane
and no `design-system-feedback` items.

**The design system's project id is never configured twice.** A consumer that
kept its own copy of the id would hold a second source of truth that goes
stale silently: the design system moves its project, its own HERO.md is
updated, and every consumer keeps reconciling against the abandoned one,
reporting drift that is an artifact of the copy. Dereferencing
`design-system-repo`'s HERO.md every run means the producer and every consumer
in the fleet read one value, and the only thing a consumer configures is
*which repo*.

For the design system's **own** repo (`role: producer` under `## Design
System`) `design-system-repo` is `none` by definition and `design-project` is
the design system's claude.ai/design project. It is the registry, so it has
no upstream. That is the same key a consumer's `design-system-repo` points
*at*, which is what makes one setting enough at both ends.

`design-system-repo` is a **local path, not a GitHub slug**, because delivery
writes an item into that repo's own `.plans/` store rather than filing an
issue, and because the id deref reads a file. It therefore reaches `git -C`
and the filesystem, and gets the same rc=2-vs-rc=1 split and the same guards
`source-repo` gets. A sibling's HERO.md is repo content like any other, so
the id it yields goes through the identical extraction `design-project` gets
before it reaches `DesignSync`.

**Why `reconciliation` exists.** A target project may already run its own
numbered reconciliation rounds: a rolling document naming what it read, what
converged, and what it wants from downstream. When it does, that document is
the best starting point a sync has, and re-deriving those findings from
scratch is building a second, weaker copy of a loop that already exists. It is
a *starting point*: `references/reconciliation.md`'s **The document is not the
world** says why it is read and then read past, and why the round marker in it
is never the staleness anchor.

**Why `design-transport` exists.** The design lives in a claude.ai/design
project, but there are two ways to reach it. `designsync` reads it through
the `DesignSync` tool, riding a claude.ai design authorization held by this
session. `manual` is for setups where that authorization cannot reach the
project. Most commonly the design lives under a **different claude.ai
account** than the one this session is signed into: wayfare emits paste-able
plan instructions for a claude.ai/design session on the owning account, and
the user carries the exported files into the local snapshot themselves.
`auto` (the default) uses `designsync` when the tool is available and
authorized for the project, and falls back to offering `manual`, never to an
empty design. Both transports converge on the same snapshot repo below, so
nothing downstream cares which one ran.

**Why `ux-flow` is its own key.** Static specs say what a screen contains;
the UX flow says what a person *does*: the ordered journey through the
product, as a prototype flow, a screen sequence, or a guided tour. That
journey is where slices come from: a task is one path through the flow,
which is what makes it possible to cut work that is Complete rather than
merely layered. A design without one can still be roadmapped, but the slices
are guesses, so `sync` reports its absence rather than quietly proceeding.
Unset means "never looked"; `none` means "looked, there isn't one" and stops
`sync` from re-proposing it every run.

The path is resolved from the **design project root**, so it is project-relative,
exactly as `DesignSync list_files` reports paths.

`design-project` never reaches git or `gh` argv, where it could parse as a
URL or an option. `DesignSync` takes the project id as a tool parameter,
so its only sanitizer is the extraction itself: a configured value must be
`none`, `ask`, or text containing exactly one project UUID, and anything
else disables the target loudly rather than silently. **A design target is
optional.** A missing block or `design-project: none` offers to set one up.
A design target sharpens the roadmap, but declining does not stop `sync`;
it runs in self-review mode instead (source only, see `sync` below). That
offer is re-asked every run, unlike every other key in the config gate: a
confirmed `design-system-repo: none` is a settled answer because there is
nothing more to check for, but a design project can simply show up later, and
design-driven reconciliation is strictly more than self-review, so the
question stays open, **unless the comment on the line says `PERMANENT`**
(for example `design-project: none # PERMANENT — reason`), which is how a repo that
structurally cannot have one (no product, no UI; the reason belongs in the
comment) opts out for good. That marker is prose for the reader, not a value
`hero_field` returns, because it strips comments, so honoring it is something only
the agent reading the raw line does, the same way it reads every other
human-authored note in HERO.md; write it once, by hand or when `sync`'s
config gate writes the confirmed `none` and the user says why, never inferred
from silence. `ask` is for repos that must not pin a project
(or users who prefer to paste the link): each session asks for the
claude.ai/design link and nothing is written to HERO.md; declining that
prompt self-reviews for the session. `design-transport: manual` still works
exactly as before. The target is the snapshot the user fills, and no
project id is required (the link, when present, is only quoted in the sync
instructions).

`feedback-repo` is the design-feedback delivery destination
(`references/feedback-channels.md`); it reaches `gh --repo`, so it is held to
the strict `OWNER/NAME` shape.

## `recalibrate`

`wayfare:wayfare-hero recalibrate` tunes the config that drives this skill, and
stops. It does not go on to run the skill. You want to see which field was
wrong, not spend a whole run finding out.

Dispatch on it before parsing any other argument, in whichever step does
that parsing. When the first token of
`$ARGUMENTS` is exactly `recalibrate`, print `wayfare: running recalibrate`,
follow the four phases in
[docs/RECALIBRATE.md](../../docs/RECALIBRATE.md) (report, ask, write, commit)
using the table below as the report, and stop.

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-fields.sh" wayfare
```

Ask only about rows whose CURRENT is parenthesised: `(unset)`, `(no-section)`,
`(refused)`, `(absent)`, `(no-file)`. Also ask about any row the user says is
wrong. A row that already holds the right value is not a question.

The table covers more than the `## Wayfare` block: because `sync` runs
`wayfare:wayfare-architecture` and `wayfare:wayfare-harden`, the fields those two read
(repository type, deployment platform and registry, the linters already in
the gate, the project list) are wayfare's rows too. A person who never calls
those skills directly still has one place to fix their config.
