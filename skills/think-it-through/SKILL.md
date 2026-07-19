---
name: think-it-through
# prettier-ignore
description: Brainstorm and grill an idea one question at a time into principal-level shared understanding, captured as dependency-aware work-items. Arch mode manages specs/ architecture docs and ADRs.
argument-hint: "[IDEA_OR_TASK | arch create|update|review|init [SPEC_NAME]]"
---

# Think It Through — Brainstorm, Grill to Shared Understanding, Then Work Items

Take a rough idea or a vague task and think it all the way through with the
user: brainstorm it, then grill it — one question at a time — until it is
understood at a principal-engineer level: goals and non-goals explicit, failure
modes named, reversibility judged, success measurable. Then break it into
dependency-aware work-items in a private, git-ignored `my-work/` store — your
plate, not the team's.

This is the sharp, thorough sibling of ordinary planning. Ordinary
brainstorming asks enough questions to feel comfortable; this keeps asking —
relentlessly, but collaboratively — until _you_ can defend every decision,
because unexamined assumptions are where wasted work comes from.

## The Prime Directive

**Do not write code, scaffold, or emit work-items until you and the user have
reached explicit shared understanding.** The user signals this — you do not
declare it yourself. Interview relentlessly up to that point. When in doubt,
ask one more question rather than assume.

## When to Use

- Starting a feature, refactor, or migration that is more than a one-line change.
- A task that arrived vague ("make onboarding better", "clean up billing").
- Any decision that is expensive to reverse (schema, public API, data model, auth).
- Whenever you catch yourself about to build on an assumption you have not stated.

Skip it for the genuinely trivial (a typo, a copy tweak, a dependency bump) —
grilling those is theater.

## The Method

### 1. One question at a time — never a batch

Ask a single question, present your recommended answer, and wait for the reply
before asking the next. Batched questions are bewildering and destroy the
dependency order between decisions. This is non-negotiable; it is the whole
technique.

### 2. Always propose your recommended answer

Every question carries your best-guess answer and a one-line reason. The user
reacts to a concrete proposal instead of starting from a blank page — that is
faster and surfaces disagreement immediately. "I'd default to X because Y —
agree, or is there a constraint I'm missing?"

### 3. Walk the design tree, parents before children

Treat the work as a tree of decisions. Resolve a parent decision before the
decisions that depend on it, because an early answer reshapes every question
below it. Don't ask about the button colour before you know whether there's a
button.

### 4. Investigate over interrogate

If a question can be answered by reading the codebase, the docs, or the git
history — go read it. Don't spend the user's attention on something you can
find yourself. Come back with "I checked; the repo already does X here, so I'll
assume we extend that — right?"

### 5. Force precise language

When the user uses a vague or overloaded term, pin it down. "You said
'account' — do you mean a Customer or a User?" Ambiguous words hide ambiguous
designs. Name things once, precisely, and reuse the name.

### 6. Stress-test with adversarial scenarios

Invent the awkward case and ask how it behaves. "What happens if two of these
arrive at once?" "What if the user is offline mid-flow?" A design that only
answers the happy path is not understood yet.

## The Principal Checklist

Before you and the user agree understanding is complete, every one of these
must have an explicit answer. Track them as you grill; when one is still blank,
that is your next question.

- **Context & scope** — what problem, stated as background, not as the solution.
- **Goals** — what success looks like, concretely.
- **Non-goals** — what could reasonably be in scope but is deliberately excluded.
  (Not "shouldn't crash" — that's a goal. A non-goal is "we are not handling
  multi-currency in this pass.")
- **Alternatives considered** — at least one other approach, and why the chosen
  one won. If there was no alternative, you haven't looked.
- **Reversibility** — is this a one-way door (expensive to undo: schema, data
  loss, public contract, money) or a two-way door (cheap to change)? One-way
  doors get slow, deep scrutiny; two-way doors get decided fast and moved past.
- **Measurable success criteria** — what you will observe to know it worked,
  stated before building.
- **Failure modes** — the ways this breaks, and the blast radius of each.
- **Cross-cutting concerns** — security, privacy, observability: addressed
  while they're still cheap to change, not bolted on later.
- **Second-order effects & cost** — who else is affected, what this makes harder
  later, and the ongoing operational/maintenance cost.

Not every item needs a paragraph — a one-way-door "no" can be a sentence. But
none may be silently skipped. Skipping is how a two-week detour begins.

## Instructions

**Mode dispatch:** if `$ARGUMENTS` starts with `arch`, skip the grilling flow and jump to **Arch Mode** below (absorbed from the former `hero-skills:document-arch`). Everything else is an idea or task to think through.

### Step 0: Load context and the my-work store

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# The store is a git-ignored folder of markdown work-items — your private
# plate for THIS repo. Ensure it exists and is excluded from git via
# .git/info/exclude (repo-local, untracked) rather than .gitignore, so we
# never dirty a tracked file.
#
# One-time migration: this store was formerly named `plan-work/`. If a legacy
# store exists and no `my-work/` does yet, move it so existing work-items carry
# over instead of being orphaned behind the new name.
if [ -d "$ROOT/plan-work" ] && [ ! -d "$ROOT/my-work" ]; then
  mv "$ROOT/plan-work" "$ROOT/my-work"
  echo "Migrated legacy plan-work/ store to my-work/."
fi
mkdir -p "$ROOT/my-work"
EXCLUDE_FILE=$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)
case "$EXCLUDE_FILE" in
  /*) ;;
  *)  EXCLUDE_FILE="$ROOT/$EXCLUDE_FILE" ;;
esac
mkdir -p "$(dirname "$EXCLUDE_FILE")"
# Keep both names excluded through the transition, so a not-yet-migrated
# legacy store never gets accidentally committed either.
for entry in my-work/ plan-work/; do
  grep -qxF "$entry" "$EXCLUDE_FILE" 2>/dev/null \
    || printf '\n%s\n' "$entry" >> "$EXCLUDE_FILE"
done

# Show what's already on the plate so grilling builds on it, not beside it.
ls "$ROOT/my-work"/*.md 2>/dev/null || echo "my-work/ is empty"
```

Read any existing work-items first — new grilling may resolve, block, or
supersede work already captured. Grill against the current plate, not a blank
slate.

### Step 1: Frame the work

Restate what you understand the user wants in one or two sentences and confirm
it. If `$ARGUMENTS` names an issue tracker ID and one is configured in HERO.md,
fetch it first for context. Then explore the codebase enough to ask informed
questions (Step 4 of the method — investigate before interrogating).

If the request describes several independent pieces, say so immediately and
decompose before drilling in — grilling the details of something that should be
three separate efforts wastes the whole conversation.

### Step 2: Grill

Run the method above. One question at a time, each with your recommended answer,
walking the design tree, filling the principal checklist. Read the codebase
whenever it can answer a question. Keep going until the checklist has no blanks
_and_ the user confirms shared understanding.

Announce progress lightly so the user sees the tree being walked, e.g.
`[resolved: data model] → now on: reversibility of the migration`.

### Step 3: Confirm the gate

State plainly: "I think we have shared understanding — here's the shape of it:
[2–4 sentence synthesis covering goals, non-goals, chosen approach, the riskiest
decision]. Ready for me to write this into `my-work/`?" Wait for the user's
yes. Do not emit anything before it.

### Step 4: Emit work-items

Break the understood work into the smallest units that each deliver something
testable and can be reviewed on their own. For each, write one file to
`my-work/` (see the format below). Set `depends_on` to encode the real order —
this is the payoff over a flat TODO list. Flag any one-way-door item with
`one_way_door: true`.

Number items sequentially from the highest existing `id` in `my-work/` (so
concurrent efforts don't collide). The `id` frontmatter field is a plain
integer; zero-pad only the **filename** prefix (`007-slug.md`) so `ls` sorts
them — `depends_on` references the plain integer id. After writing, print the
readiness view (below) so the user sees what to start first.

When the grilling settled a **one-way-door architectural decision** (schema,
public API, data model, service boundary), offer to also record it as an ADR
under `specs/decisions/` via Arch Mode — the grilled Context / Alternatives /
Reversibility answers _are_ the ADR content; don't make the user re-derive
them later.

## The Work-Item Format

One markdown file per item at `my-work/NNN-slug.md`:

```markdown
---
id: 7 # a plain integer; only the filename is zero-padded (007-slug.md) for sorting
title: Add OAuth device-flow login
status: ready # ready | blocked | in-progress | done
depends_on: [3, 5] # ids that must be `done` before this can start
one_way_door: false # true = expensive to reverse; got extra scrutiny
success: "User completes device-flow login in under 30s; e2e test green"
---

## Context

Why this work exists — the principal-level framing, not a restatement of the title.

## Non-goals

What is explicitly out of scope for this item.

## Approach

The chosen approach and why it won over the alternative(s) considered.

## Failure modes

How it can break and the blast radius of each.

## Notes

Second-order effects, ongoing cost, and any open question still worth flagging.
```

Keep the body proportional to the risk: a two-way-door chore might have a
one-line Approach and empty Non-goals; a one-way-door schema change earns every
section. The frontmatter fields are always present.

## "What's Ready" — the one query that matters

An item is **ready** when its `status` is not `done` and every id in its
`depends_on` points to an item that _is_ `done`. That is the Beads `ready`
primitive without a database — a plain read over the folder:

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT/my-work" 2>/dev/null || { echo "no my-work/ yet"; exit 0; }

# Read a frontmatter scalar, stripping any trailing "# comment" and whitespace.
fm() { awk -F': ' -v k="$2" '$1==k{v=$2; sub(/ *#.*/,"",v); gsub(/^[[:space:]]+|[[:space:]]+$/,"",v); print v; exit}' "$1"; }
# Normalize an id to a base-10 integer so 007 and 7 compare equal.
norm() { printf '%s' "$((10#${1:-0}))"; }

# Collect the ids whose status is done (normalized).
done_ids=" "
for f in *.md; do
  [ -e "$f" ] || continue
  [ "$(fm "$f" status)" = "done" ] && done_ids="$done_ids$(norm "$(fm "$f" id)") "
done

# An item is ready if it is not done and every depends_on id is done.
for f in *.md; do
  [ -e "$f" ] || continue
  [ "$(fm "$f" status)" = "done" ] && continue
  # Split deps onto separate lines and read them with a heredoc-fed loop:
  # portable across bash/zsh (zsh doesn't word-split unquoted vars) and the
  # heredoc keeps the loop in the current shell so `ready` persists.
  deps=$(awk -F': ' '/^depends_on:/{v=$2; sub(/ *#.*/,"",v); gsub(/[][, ]+/,"\n",v); print v; exit}' "$f")
  ready=1
  while IFS= read -r d; do
    [ -z "$d" ] && continue
    case "$done_ids" in *" $(norm "$d") "*) ;; *) ready=0 ;; esac
  done <<EOF
$deps
EOF
  title=$(fm "$f" title)
  [ "$ready" = 1 ] && echo "READY  $f — $title" || echo "blocked $f — $title"
done
```

Run this any time to see what to pick up next. Ready items — pick the
highest-priority (or the user's choice) and start it, moving its `status` to
`in-progress`, then `done` when it lands.

## Arch Mode — Architecture Specs (absorbed from document-arch)

Create and maintain architecture documentation in the project's `specs/` folder using Mermaid diagrams and structured markdown. **This mode only operates on specification documents in `specs/`; it does NOT modify source code.**

Commands (`$ARGUMENTS` after the leading `arch`):

- `arch init` — initialize `specs/` with starter templates
- `arch create [SPEC_NAME]` — gather context from the relevant source files, ask clarifying questions (aspect, detail level, patterns), generate the spec with the appropriate Mermaid diagram, write `specs/SPEC_NAME.md`, update `specs/README.md`
- `arch update [SPEC_NAME]` — read the existing spec, analyze the codebase for changes, update preserving structure, note changes with the date
- `arch review` — list all specs, compare against the codebase, report up-to-date / needs-update / missing. Do NOT auto-update — just report.

Load `HERO.md` first (**Repository** type for layout, **Projects** for architecture context, **Deployment** for deployment diagrams); in a monorepo root, ask which project to document.

Folder layout:

```
PROJECT/
└── specs/
    ├── README.md           # Index of all specs
    ├── overview.md         # High-level system overview
    ├── components.md       # Component architecture
    ├── data-flow.md        # Data flow diagrams
    ├── api.md              # API specifications (if applicable)
    └── decisions/          # Architecture Decision Records (ADRs)
        └── 001-*.md
```

Diagram types: **graph/flowchart** (components, logic flow), **sequenceDiagram** (interactions over time), **classDiagram** (data models), **stateDiagram-v2** (state machines), **erDiagram** (database schema). Keep diagrams focused — one concept per diagram.

Spec document template:

```markdown
# SPEC_TITLE

> Last updated: DATE
> Status: Draft | Review | Approved

## Overview
One or two paragraphs.

## Diagram
A fenced mermaid block with the appropriate diagram.

## Components

### COMPONENT_NAME

- **Purpose**: what it does
- **Location**: `path/to/code`
- **Dependencies**: what it depends on

## Key Decisions

- **DECISION**: rationale
```

Arch Mode rules: always read the relevant source before creating/updating; specs describe what IS, not what should be; use `1.` for ordered lists, backtick generic types, and blank lines around blocks so markdownlint stays green.

## Notes

- **The store is private.** `my-work/` is git-ignored on purpose — it is the
  user's plate, not a shared board. Never commit it; never push it.
- **Emit, don't implement.** This skill produces understanding and work-items.
  Handing off to implementation (e.g. `hero-skills:one-shot` on a ready item) is
  a separate, deliberate step the user takes.
- **Discovered work goes back in.** If grilling one item surfaces new work, write
  it as its own item with a `depends_on` link rather than smuggling it into the
  current one.
- **Update status as you go.** A stale store is worse than none — mark items
  `in-progress` and `done` so the readiness query stays honest.

## Anti-Patterns

| Smell                                            | Why it's wrong                                                   |
| ------------------------------------------------ | --------------------------------------------------------------- |
| Asking three questions in one message            | Destroys design-tree order; overwhelms. One at a time.          |
| Asking without proposing an answer               | Makes the user do all the work. Always recommend.               |
| Asking what the codebase already answers         | Wastes attention. Go read it first.                             |
| Declaring "we're aligned" yourself               | The user signals shared understanding, not you.                 |
| Emitting work-items before the gate              | Violates the Prime Directive. Wait for the yes.                 |
| A work-item with an empty `success`              | If you can't state done, you don't understand it yet.           |
| Skipping the one-way-door question               | The most expensive mistakes hide behind unasked reversibility.  |

## Next steps

Pick exactly one, based on `my-work/`'s current state:

- **A READY item exists**: `Next step: hero-skills:one-shot — drive it ticket-to-merge` (print only — model-invocation-restricted, cannot auto-run).
- **No READY item** (everything's still blocked, or there's another piece to grill): `Next step: hero-skills:think-it-through — think the next piece through, or re-grill a blocked item` (print only — re-invoking this same skill right after it finishes isn't auto-chained).
