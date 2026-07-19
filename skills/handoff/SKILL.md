---
name: handoff
# prettier-ignore
description: Distill the current conversation into one self-contained work-item — context, decisions, remaining work, acceptance criteria — for a downstream agent with zero context from this session.
argument-hint: "[TITLE_OR_FOCUS] [--issue]"
---

# Handoff — Package This Conversation for a Downstream Agent

Turn whatever this conversation has established — the goal, the decisions made and why, the work already done, the work still open — into a single work-item in the `my-work/` store that a downstream agent (a fresh session, a cheaper model, `hero-skills:one-shot`, or a teammate) can execute **without asking anything this conversation already answered**.

The receiving agent has zero context from this session. That is the quality bar: if the item would make its reader scroll back through this chat, it is not a handoff yet.

## Arguments

- `$ARGUMENTS` — Optional:
  - `TITLE_OR_FOCUS` — what to hand off, when the conversation covered several threads (e.g., `handoff the migration follow-ups`). Default: the conversation's current primary goal.
  - `--issue` — also file the work-item to the tracker configured in HERO.md (`github-issues` via `gh issue create`, or Linear via its MCP tools) and cross-link the two.

## Instructions

### Step 0: Load Hero Configuration and the my-work Store

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Same git-ignored store think-it-through and harden use.
mkdir -p "$ROOT/my-work"
EXCLUDE_FILE=$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)
case "$EXCLUDE_FILE" in
  /*) ;;
  *)  EXCLUDE_FILE="$ROOT/$EXCLUDE_FILE" ;;
esac
mkdir -p "$(dirname "$EXCLUDE_FILE")"
grep -qxF 'my-work/' "$EXCLUDE_FILE" 2>/dev/null \
  || printf '\nmy-work/\n' >> "$EXCLUDE_FILE"
ls "$ROOT/my-work"/*.md 2>/dev/null || echo "my-work/ is empty"
```

Read existing items — the handoff may depend on one, supersede one, or already exist in stale form (update it rather than duplicating).

### Step 1: Distill the Conversation

Walk back through this session and extract, in your own words:

1. **Goal** — what the work is ultimately for, as background, not as the solution.
2. **Decisions made** — each choice that was settled, *with its why* (including options that were rejected and the reason). These are the most expensive thing to lose in a handoff.
3. **Done so far** — what already landed: files changed, commits/PRs opened (with numbers/SHAs), verifications that passed.
4. **Remaining work** — the concrete next actions, in dependency order.
5. **Gotchas** — anything discovered the hard way this session: failing approaches, environment quirks, hooks/gates that bit, naming constraints.
6. **Acceptance criteria** — how the downstream agent proves it is done.

Also capture the mechanical state a fresh session needs: repo, branch, PR number, tracker issue, and any commands that must run before work starts.

If `$ARGUMENTS` names a focus, scope the distillation to that thread and note the neighboring threads in one line each so they aren't silently lost.

### Step 2: Confirm the Shape

Show the user a 3–6 line synthesis (goal, key decisions, remaining work, acceptance criteria) and ask one question: "Hand this off as written?" Fix anything they correct. Do not write the item before the yes — a wrong handoff multiplies downstream.

### Step 3: Write the Work-Item

One file at `my-work/NNN-slug.md`, id continuing from the highest existing id (think-it-through's numbering rules: integer `id`, zero-padded filename only). Use the shared format plus the handoff sections:

```markdown
---
id: 9
title: Finish the payment-retry migration
status: ready # ready | blocked | in-progress | done
depends_on: []
one_way_door: false
success: "Retries drain the backlog in staging; alert AL-42 stays green for 24h"
---

## Context

The goal and its background — why this work exists.

## Decisions made

- DECISION — why; what was rejected and why.

## Done so far

- Branch `feat/...`, PR #NN (state), commits SHAs; verifications that passed.

## Remaining work

1. Ordered, concrete next actions.

## Gotchas

Hard-won session knowledge: failed approaches, environment quirks, gate/hook behavior.

## Verification

How the downstream agent proves completion (commands, tests, observable behavior).
```

### Step 4: Optionally File to the Tracker (`--issue`)

When `--issue` is passed (or the user asks): read **Project Management** from HERO.md. For `github-issues`, `gh issue create --title TITLE --body-file THE_ITEM` (the body is the work-item minus frontmatter, plus a line noting the `my-work/` path). For Linear, create the issue via the Linear MCP tools. Then add the issue URL to the work-item's Context so the two stay cross-linked.

Filing to a tracker is outward-facing — do it only on the explicit flag or an explicit ask, never by default.

### Step 5: Report

```
Handoff written: my-work/009-finish-payment-retry-migration.md
Status: ready (no blocking dependencies)
Tracker: #123 filed (or: not filed)

Downstream pickup:
  hero-skills:one-shot         # execute it ticket-to-merge in a fresh session
  # or point any agent at the my-work/ file — it is self-contained by design
```

## Notes

- **Self-containment is the contract.** Write for a reader with zero session context; decisions without their why are the first thing to rot.
- **One item per handoff.** If the conversation holds several independent threads, hand off the named one and list the rest as candidates — or run `hero-skills:think-it-through` to decompose properly.
- **The store is private.** `my-work/` is git-ignored; never commit or push it. The `--issue` path is the deliberate way to make a handoff shared.
- **Update, don't duplicate.** Re-running handoff on the same thread updates the existing item and bumps its sections, keeping the id stable.
