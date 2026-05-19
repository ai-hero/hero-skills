---
name: plan-work
# prettier-ignore
description: Plan and implement a task. Accepts a Linear issue ID or plain description, creates a feature branch, drafts the approach in Plan Mode, then implements on approval.
argument-hint: ISSUE_ID_OR_DESCRIPTION [additional-context]
disable-model-invocation: true
---

# Plan — Plan and Implement

Plan an implementation by analyzing the codebase and drafting an approach in Plan Mode. When the user approves, Plan Mode exits and Claude implements the plan directly in the same conversation.

This is the single entry point for "I have a task to do." Plan Mode handles plan-and-approve, and the natural exit from Plan Mode is implementation.

## Arguments

- `$ARGUMENTS` - Either a Linear issue identifier (e.g., `PROJ-123`) or a plain-text description of the task, plus optional additional context

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"

# Stale-HERO check — fast subset of the plugin's check-hero-staleness.sh.
# Keep aligned with the copies in commit-changes/push-pr/test-changes.
HERO_TIME=$(git -C "$ROOT" log -1 --format=%ct -- HERO.md 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
CONFIG_TIME=$(git -C "$ROOT" log -1 --format=%ct -- \
  pyproject.toml ':(glob)**/pyproject.toml' \
  package.json ':(glob)**/package.json' \
  go.mod ':(glob)**/go.mod' \
  Cargo.toml ':(glob)**/Cargo.toml' \
  .github/workflows .pre-commit-config.yaml \
  CLAUDE.md Makefile justfile Taskfile.yml 2>/dev/null | grep -E '^[0-9]+$' || echo 0)
if [ "${CONFIG_TIME:-0}" -gt "${HERO_TIME:-0}" ]; then
  echo "note: HERO.md may be out of date — run hero-skills:init-hero --update to refresh."
fi
```

Read `HERO.md` if it exists. This skill uses:

- **Project Management** → which tool/MCP to fetch issues from (Linear, Jira, Asana, GitHub Issues)
- **Repository** → branch naming convention, default branch
- **Projects** → which subproject the issue relates to

If `HERO.md` is missing, suggest `hero-skills:init-hero` but proceed with defaults (Linear MCP, conventional branches). If the stale-HERO hint fired, mention it once to the user but do not block.

### Step 1: Parse Arguments

Extract from `$ARGUMENTS`:

- **Issue ID** (optional): If the first token matches a pattern like `PROJ-123` (letters, dash, digits), treat it as a Linear issue ID
- **Description** (alternative): If no issue ID pattern is found, treat the entire argument as a plain-text task description
- **Additional context** (optional): Any remaining text after the issue ID provides extra requirements

If `$ARGUMENTS` is empty, ask the user what they want to plan.

### Step 2: Gather Context

**If an issue ID was provided**, fetch from Linear:

Use the Linear MCP tools to get full issue details:

```
mcp__linear-server__get_issue with id: ISSUE_ID
```

Extract and summarize:

- **Title**: What the issue is about
- **Description**: Full requirements and context
- **Acceptance criteria**: What "done" looks like
- **Labels/Priority**: Any categorization
- **Related issues**: Linked issues or blockers

Also fetch comments for additional context:

```
mcp__linear-server__list_comments with issueId: ISSUE_ID
```

Present a summary of the issue to the user.

**If a plain-text description was provided**, use it directly as the task context. Summarize what you understand the task to be and confirm with the user.

### Step 3: Prepare Workspace

```bash
CURRENT=$(git branch --show-current)
git status --porcelain
```

**If uncommitted changes exist, STOP and show:**

```
You have uncommitted changes on '$CURRENT':

  (list changed files from git status)

These will follow you into the new branch via `git checkout -b` if we branch from $CURRENT, but if we need to fetch the default branch first they cannot follow safely.

Options:
1. Run hero-skills:commit-changes to commit first (recommended)
2. Cancel — handle changes manually
```

**STOP and wait for user to choose.** Do NOT silently stash, and do NOT switch branches with uncommitted changes when fetching the default branch first.

**Branch logic:**

| Current Branch | Action |
|----------------|--------|
| `main` or `master` | Pull latest, create feature branch |
| Sprint/cycle branch | Ask user: stay or create feature branch |
| Other feature branch | Ask user if they want to stay or create new |

**If creating feature branch:**

```bash
git fetch origin $DEFAULT_BRANCH
git checkout $DEFAULT_BRANCH && git pull origin $DEFAULT_BRANCH
git checkout -b "BRANCH_NAME"
```

Branch naming:

- **If issue ID exists**: `{issue-id}-short-description` (e.g., `PROJ-123-add-auth`)
- **If description only**: `feat/short-description` or `fix/short-description` based on context (e.g., `feat/add-dark-mode`)

### Step 4: Enter Plan Mode

**IMPORTANT: Use the `EnterPlanMode` tool to switch into Plan Mode.** This ensures Claude cannot modify files while planning and the user must approve the plan before implementation begins.

After entering Plan Mode, announce:

```
Now in Plan Mode for: TASK_SUMMARY

I will:
- Analyze the codebase
- Identify affected files and systems
- Draft an implementation approach
- Ask clarifying questions

I will NOT write any code until the plan is approved.
To exit Plan Mode and start implementing, say "implement" or "let's go".
```

### Step 5: Analyze the Codebase

Based on the issue, explore relevant areas:

1. **Identify affected systems** from issue description
2. **Search for related code**:
   - Use Glob to find relevant files
   - Use Grep to find related functions/classes
   - Read key files to understand current implementation
3. **Note existing patterns**:
   - How similar features are implemented
   - Naming conventions
   - File organization
4. **Identify dependencies**:
   - What this change depends on
   - What might break

### Step 6: Draft Implementation Plan

```markdown
## Implementation Plan for TASK_TITLE

### Summary
[1-2 sentence description of what will be built]

### Files to Modify
- `path/to/file.py` - [what changes]

### Files to Create
- `path/to/new_file.py` - [purpose]

### Implementation Steps
1. [First step with details]
2. [Second step with details]
3. [Third step with details]

### Testing Approach
- [How to verify the implementation works]

### Risks & Considerations
- [Potential issues to watch for]

### Open Questions
- [Question 1 that needs clarification]
```

### Step 7: Ask Clarifying Questions

Before finalizing, ask targeted questions about:

- **Unclear requirements**: Anything ambiguous in the issue
- **Edge cases**: How to handle unusual situations
- **Architectural decisions**: When multiple approaches exist
- **Scope boundaries**: What's in/out of scope

### Step 8: Refine and Present Plan

After getting answers:

1. **Incorporate feedback** into the plan
2. **Present final plan** for approval via the `ExitPlanMode` tool — this is the standard Plan Mode handoff. The user either approves (Plan Mode exits, implementation begins) or rejects (stay in Plan Mode and revise).

### Step 9: Implement the Approved Plan

Once Plan Mode exits with user approval, implement each step from the plan in order. Follow these rules during implementation:

- **Read before edit** — Always Read a file before modifying it.
- **Match existing patterns** — Follow naming, structure, and style already in the codebase. Don't introduce new conventions.
- **One step at a time** — Announce each step briefly, make the change, then move on. No commentary between steps unless something blocks you.
- **Stop and ask on ambiguity** — If a step is unclear or the codebase state contradicts the plan, stop and ask the user rather than guess.
- **No commits, no pushes** — Implementation only writes code. `hero-skills:commit-changes` and `hero-skills:push-pr` handle git operations.

Verification (running tests, linters, type checkers, smoke tests) is not part of this skill. Once implementation is complete, the user runs `hero-skills:test-changes` to verify the changes work end-to-end.

### Step 10: Summary

When all steps are implemented, report:

```
Plan Summary
=================
Task: {plan summary}
Branch: {branch-name}
Steps completed: N/N

Files Modified:
  - path/to/file1.py
  - path/to/file2.ts

Files Created:
  - path/to/new_file.py

Next steps:
  hero-skills:test-changes     # Step 3 — verify lint/typecheck/unit tests
  hero-skills:smoke-ui         # Step 4 — Playwright smoke (UI projects only)
  /simplify                    # Step 5 — tidy the dirty diff before commit
  hero-skills:commit-changes   # Step 6 — review and commit
  hero-skills:push-pr          # Step 7 — push and open a draft PR
```

## Integration

```
hero-skills:plan-work PROJ-123              # Plan from a Linear issue, then implement
hero-skills:plan-work add dark mode toggle  # Plan from a description, then implement
# ... user approves plan in Plan Mode, implementation runs ...
hero-skills:test-changes                       # Verify the implementation
hero-skills:commit-changes                     # Review and commit
hero-skills:push-pr                       # Push and open a draft PR
hero-skills:review-pr                # Run an automated review and address findings
```

## Notes

- Uses the `EnterPlanMode` tool to enforce read-only analysis — no code modifications until the user approves
- Uses the `ExitPlanMode` tool to hand the plan to the user for approval; on approval Plan Mode exits and implementation begins in the same conversation
- Accepts either a Linear issue ID or a plain-text description
- If an issue ID is provided, fetches full details from Linear
- Create branches with consistent naming: `{issue-id}-{short-description}` or `feat/{short-description}`
- Ask questions rather than assume
- The plan should be specific enough that implementation is straightforward
- Include testing approach in every plan, but actual verification happens in `hero-skills:test-changes`
- Do NOT commit or push from this skill — that's `hero-skills:commit-changes` and `hero-skills:push-pr`
