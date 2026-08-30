---
name: audit-plugin
# prettier-ignore
description: Audit the hero-skills plugin. Checks skill quality, consistency, DRY violations, HERO.md field coverage, and readability. Use before releasing changes to the plugin.
argument-hint: [--fix]
disable-model-invocation: true
---

# Audit — Plugin Self-Audit

Audit the hero-skills plugin for quality, consistency, and maintainability. This skill is specific to the hero-skills repo itself — it reviews the skills that make up the plugin.

## Arguments

- `$ARGUMENTS`:
  - (none) — Audit and report findings
  - `--fix` — Audit and auto-fix what can be fixed (formatting, ordering, etc.)

## Instructions

### Step 1: Inventory All Skills

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls -1 "$ROOT/skills/"
```

Read every `skills/*/SKILL.md` file. For each, extract:

- Name (from frontmatter)
- Description (from frontmatter)
- Line count, word count
- Heading structure (h1, h2, h3 hierarchy)
- Whether it references HERO.md fields
- Arguments it supports

### Step 2: Run Audit Checks

#### 2a: Structure Consistency

All skills should follow a consistent structure. Check for:

- **Frontmatter fields**: Every skill must have `name` and `description`. Flag missing or inconsistent fields.
- **Heading hierarchy**: Skills should follow a predictable pattern. Flag skills with wildly different structures.
- **Argument documentation**: If a skill has `argument-hint`, it should document arguments in the body.
- **Step numbering**: Steps should be sequential, no gaps or duplicates.
- **Sub-step numbering within a step**: If a step has sub-steps like `2a`, `2b`, `2c`, verify they're sequential with no gaps or duplicates.

Report template:

```
STRUCTURE CONSISTENCY
─────────────────────
[OK] commit: standard structure (frontmatter, args, instructions, principles)
[!!] plan: missing argument documentation for --dry-run
[!!] init: step sub-numbering gap (2a, 2b, 2d — missing 2c)
```

#### 2b: Size & Complexity

Flag skills that are too large or too small:

- **Over 500 lines**: Should split into supplementary files
- **Over 5000 words**: Consuming too much context window
- **Under 20 lines** (body only): Probably too thin to be useful
- **Deep nesting** (h4+ headings beyond investigation sub-steps): May need restructuring

Report template:

```
SIZE & COMPLEXITY
─────────────────
[OK] commit: 180 lines, 1200 words
[!!] init: 830 lines, 6200 words — consider splitting investigation steps into references/
[OK] respond: 200 lines, 1500 words
```

#### 2c: DRY Violations

Look for instructions that are repeated across multiple skills. Common patterns:

- "Read HERO.md" boilerplate — should each skill repeat how to read it, or should there be a shared pattern?
- "Check for git repo" — appears in many skills
- Similar investigation bash blocks
- Repeated formatting patterns for output (the `[OK]`/`[??]`/`[--]` format)

Flag when the **same substantive instruction** (not just similar phrasing) appears in 3+ skills.

Report template:

```
DRY VIOLATIONS
──────────────
[!!] "Read HERO.md and parse sections" — repeated in 8 skills
     Suggestion: This is expected — each skill needs to independently read HERO.md.
     No action needed (skills run independently, not as a pipeline).

[!!] "Present findings in [OK]/[??]/[--] format" — in init, setup
     Suggestion: Consistent by design. No action needed.

[??] Investigation bash blocks in init are 40+ lines each
     Suggestion: Consider moving to references/ if init exceeds 500 lines
```

**Important:** Not all repetition is bad. Skills run independently — they can't share runtime state. Only flag repetition that could be eliminated via supplementary files or shared references.

#### 2d: HERO.md Field Coverage

`scripts/hero-fields.sh --all` is the declared map — which skill reads which
field, and what it decides there (its CURRENT column is always `-`; the map
reads no repo). It is a claim, not evidence: cross-reference
it against the HERO.md template in init-hero and against what the skills
actually read, and report both directions of drift.

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/hero-skills}/scripts/hero-fields.sh" --all
```

A field the map omits is a field no `recalibrate` will ever ask about, which
is how a skill keeps misbehaving after the user has run the verb that was
supposed to fix it. A field in the map that no skill reads sends the user to
answer a question that changes nothing.

```
HERO.MD FIELD COVERAGE
──────────────────────
Field                          | Produced by  | Consumed by
───────────────────────────────|──────────────|────────────────────
Coding Agent → primary         | init    | setup
Repository → hosting           | init    | push
Repository → branch-template   | init    | plan
Projects → lint-command         | init    | test
Projects → dependency-file     | init    | scan, test
...

[!!] Coding Agent → self-review: produced by init, consumed by NO skill
     → Is this field actually used? Remove or wire up.

[OK] All fields consumed by at least one skill
```

#### 2e: Description Quality

Check every skill's frontmatter `description` for:

- **Trigger clarity**: Does it say when to use the skill? ("Use when...", "Use for...", "Use before...")
- **Length**: Should be 50-200 chars. Too short = unclear triggers. Too long = wastes context.
- **Specificity**: Vague descriptions like "helps with code" are useless for Claude's skill matching.

Report template:

```
DESCRIPTION QUALITY
───────────────────
[OK] commit: "Create a smart git commit..." (85 chars, clear trigger)
[!!] audit: description is 190 chars — consider trimming
[??] create-skill: no trigger phrase — add "Use when..." or "Use for..."
```

#### 2f: Alphabetical & Organizational Checks

- Are skills listed alphabetically when referenced in tables (e.g., init-hero's "What each skill needs" table)?
- Are HERO.md sections in a logical order?
- Are frontmatter fields in a consistent order across skills?

### Step 3: Report Summary

```
Plugin Audit
═════════════════════════
Skills audited: 17
Total lines: 4,200 | Total words: 28,000

MUST FIX
────────
critical issues: broken references, missing fields, structural errors

SHOULD FIX
──────────
quality issues: size, DRY violations, descriptions

INFO
────
OBSERVATIONS_WITH_NO_ACTION_NEEDED

Overall health: Good / Needs Attention / Critical

Next step: hero-skills:push-pr — commit and push the plugin changes (offer to auto-run: ask "Run it now? [y/N]", invoke via Skill tool on yes)
```

### Step 4: Auto-Fix (if `--fix`)

If `--fix` is passed, automatically fix:

- Alphabetical ordering in tables
- Frontmatter field ordering (name, description, argument-hint, disable-model-invocation)
- Step renumbering gaps
- Trailing whitespace, inconsistent newlines

**Never auto-fix:** Content changes, description rewrites, structural reorganization — these need human review.

## Key Principles

- **This skill is for the hero-skills repo only.** It audits the plugin, not user projects.
- **DRY is not always better.** Skills run independently — some repetition is by design.
- **Field coverage matters.** Every HERO.md field should be produced by init-hero and consumed by at least one skill.
- **Size awareness.** Skills consume context window. Large skills slow down every invocation.
- **Be specific.** File, line, what's wrong, how to fix.
