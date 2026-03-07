---
name: hero-plan
# prettier-ignore
description: Plan implementation for a ticket. Fetches issue details from Linear, creates feature branch, analyzes codebase, and drafts implementation approach for approval. Works with any project structure (single repo or monorepo).
argument-hint: <issue-id> [additional-context]
disable-model-invocation: true
---

# Hero Plan - Issue Implementation Planning

Plan the implementation for a Linear issue by fetching details, analyzing the codebase, and drafting an implementation approach for user approval.

## Arguments

- `$ARGUMENTS` - The Linear issue identifier (e.g., `PROJ-123`) and optional additional context

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Project Management** → which tool/MCP to fetch issues from (Linear, Jira, Asana, GitHub Issues)
- **Repository** → branch naming convention, default branch
- **Projects** → which subproject the issue relates to

If `HERO.md` is missing, suggest `/hero-init` but proceed with defaults (Linear MCP, conventional branches).

### Step 1: Parse Arguments

Extract from `$ARGUMENTS`:

- **Issue ID** (required): First argument, e.g., `PROJ-123`
- **Additional context** (optional): Remaining text provides extra requirements

If no issue ID provided, ask the user for one.

### Step 2: Fetch Issue from Linear

Use the Linear MCP tools to get full issue details:

```
mcp__linear-server__get_issue with id: <issue-id>
```

Extract and summarize:

- **Title**: What the issue is about
- **Description**: Full requirements and context
- **Acceptance criteria**: What "done" looks like
- **Labels/Priority**: Any categorization
- **Related issues**: Linked issues or blockers

Also fetch comments for additional context:

```
mcp__linear-server__list_comments with issueId: <issue-id>
```

Present a summary of the issue to the user.

### Step 3: Prepare Workspace

```bash
git branch --show-current
git status --porcelain
```

**Branch logic:**

| Current Branch | Action |
|----------------|--------|
| `main` or `master` | Pull latest, create feature branch |
| Sprint/cycle branch | Ask user: stay or create feature branch |
| Other feature branch | Ask user if they want to stay or create new |

**If creating feature branch:**

```bash
git checkout main && git pull
git checkout -b <issue-id>-<short-description>
```

Use the issue ID and 2-3 descriptive words from the title.

### Step 4: Enter Plan Mode

```
Entering plan mode for issue <issue-id>.

In this mode I will:
- Analyze the codebase
- Identify affected files and systems
- Draft an implementation approach
- Ask clarifying questions

I will NOT write any code until the plan is approved.
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
## Implementation Plan for <issue-id>

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
2. **Present final plan** for approval
3. **Remind user**:

```
Plan is ready for review.

- To approve and start implementation: "implement" or "let's go"
- To modify the plan: provide feedback
- To cancel: "cancel planning"
```

## Integration

```
/hero-plan PROJ-123    # Plan the work
# ... implement ...
/hero-commit review           # Review and commit
/hero-push             # Push and create PR
```

## Notes

- Plan mode is analysis-only - no code modifications
- Always fetch full issue details from Linear
- Create branches with consistent naming: `<issue-id>-<short-description>`
- Ask questions rather than assume
- The plan should be specific enough that implementation is straightforward
- Include testing approach in every plan
