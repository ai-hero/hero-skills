---
name: handoff
# prettier-ignore
description: Distill the current conversation into one self-contained work-item — context, decisions, remaining work, acceptance criteria — for a downstream agent with zero context from this session.
argument-hint: "[TITLE_OR_FOCUS] [--issue] [--repo OWNER/NAME]"
---

# Handoff — Package This Conversation for a Downstream Agent

Turn whatever this conversation has established — the goal, the decisions made and why, the work already done, the work still open — into a single work-item in the `my-work/` store that a downstream agent (a fresh session, a cheaper model, `hero-skills:one-shot`, or a teammate) can execute **without asking anything this conversation already answered**.

The receiving agent has zero context from this session. That is the quality bar: if the item would make its reader scroll back through this chat, it is not a handoff yet.

## Arguments

- `$ARGUMENTS` — Optional:
  - `TITLE_OR_FOCUS` — what to hand off, when the conversation covered several threads (e.g., `handoff the migration follow-ups`). Default: the conversation's current primary goal.
  - `--issue` — also file the work-item to the tracker configured in HERO.md (`github-issues` via `gh issue create`, or Linear via its MCP tools) and cross-link the two.
  - `--repo OWNER/NAME` — hand the work to a **different repository**: file the item to that repo's tracker and keep a cross-linked stub locally. Implies `--issue`.

## Instructions

### Step 0: Load Hero Configuration and the my-work Store

```bash
HERO_LIB="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-lib.sh"
[ -r "$HERO_LIB" ] || HERO_LIB="$(git rev-parse --show-toplevel)/scripts/hero-lib.sh"
# shellcheck source=/dev/null
. "$HERO_LIB"

ROOT=$(hero_root)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Same git-ignored store think-it-through and harden use.
hero_ready_items "$(hero_work_store)"
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

### Step 5: Hand Off to Another Repo (`--repo`)

`my-work/` is git-ignored and repo-local — it cannot carry work to another repository, and copying a file into a sibling checkout's `my-work/` would land somewhere that never syncs and that no teammate can see. **The tracker is the transport.** `--repo` files the distilled item as an issue on the target repo and leaves a stub here so this repo still remembers it delegated the work.

Handing work to another team's repo is outward-facing and visible to people who are not in this conversation. **Confirm the target and show the body before filing** — never file to a repo the user did not name in this session.

1. **Resolve and verify the target.** Confirm it exists and you can file to it:

   ```bash
   gh repo view "OWNER/NAME" --json nameWithOwner,hasIssuesEnabled \
     -q '"\(.nameWithOwner) issues=\(.hasIssuesEnabled)"'
   ```

   If this fails, STOP — report whether it's a typo, a private repo you lack access to, or issues being disabled. Do not fall back to filing on the current repo; a handoff that silently lands in the wrong place is worse than one that fails.

2. **Rewrite for a reader in that repo.** The distillation from Step 1 assumes this repo's context, which the receiving team does not share. Before filing, strip or qualify anything repo-local:
   - Bare paths (`src/auth.ts`) become `THIS_REPO/src/auth.ts` — the target repo has its own `src/`.
   - Bare PR/issue numbers (`#42`) become full `OWNER/NAME#42` cross-links.
   - Branch names, local commands, and `my-work/` ids mean nothing there — either qualify them or drop them.
   - State plainly what the target repo has to *do*, and what this repo will do in response. A cross-repo item without that contract is just a complaint.

3. **Show the rendered body and confirm.** One question: "File this to OWNER/NAME?" Wait for the yes.

4. **File it:**

   ```bash
   gh issue create --repo "OWNER/NAME" --title "TITLE" --body-file BODY_FILE
   ```

   The target repo's labels/templates are its own — do not pass `--label` unless the user named one that exists there.

5. **Write the local stub.** Keep a `my-work/` item here with `status: blocked` and the issue URL in its Context, titled for *this* repo's side of the work (e.g. "Await rate-limit support in acme/api-service"). This repo's plate should show that it is waiting on someone, otherwise the dependency is invisible the moment this conversation ends.

If the target repo uses Linear rather than GitHub Issues, create the issue in the corresponding Linear team via the MCP tools instead, and confirm the team with the user — `--repo` names a git repo, which does not by itself identify a Linear team.

### Step 6: Report

```
Handoff written: my-work/009-finish-payment-retry-migration.md
Status: ready (no blocking dependencies)
Tracker: #123 filed (or: not filed)

Downstream pickup:
  hero-skills:one-shot         # execute it ticket-to-merge in a fresh session
  # or point any agent at the my-work/ file — it is self-contained by design
```

For a `--repo` handoff, report both sides so it's clear what left the building:

```
Handed off to: acme/api-service#88 — Add per-tenant rate limiting
                https://github.com/acme/api-service/issues/88

Local stub:    my-work/010-await-rate-limit-support.md
Status:        blocked (waiting on acme/api-service#88)

Nothing in this repo picks that issue up — the receiving team runs
hero-skills:one-shot (or anything else) against their own tracker.
```

## Notes

- **Self-containment is the contract.** Write for a reader with zero session context; decisions without their why are the first thing to rot.
- **One item per handoff.** If the conversation holds several independent threads, hand off the named one and list the rest as candidates — or run `hero-skills:think-it-through` to decompose properly.
- **The store is private.** `my-work/` is git-ignored; never commit or push it. The `--issue` and `--repo` paths are the deliberate ways to make a handoff shared — the store itself is not a transport, and never becomes one.
- **A cross-repo handoff is a request, not an assignment.** Filing an issue on someone else's repo does not schedule their work. Say what you need and by when in the item; do not assume it will be picked up.
- **Pickup is per-repo.** `hero-skills:one-shot` Step 1 resolves against the local `my-work/` store and this repo's tracker only. A `--repo` handoff is picked up by whoever runs their own tooling in the target repo.
- **Update, don't duplicate.** Re-running handoff on the same thread updates the existing item and bumps its sections, keeping the id stable.
