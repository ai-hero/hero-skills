#!/usr/bin/env bash
# Validate hero-skills plugin structure against Claude Code official requirements.
# Usage: ./scripts/validate.sh [--verbose]

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0
WARNINGS=0
VERBOSE="${1:-}"

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
dim()    { printf "\033[2m%s\033[0m\n" "$*"; }
bold()   { printf "\033[1m%s\033[0m\n" "$*"; }

error() {
  red "  ERROR: $1"
  if [[ -n "${2:-}" ]]; then
    dim "         File: $2"
  fi
  if [[ -n "${3:-}" ]]; then
    dim "         Line: $3"
  fi
  if [[ -n "${4:-}" ]]; then
    printf "\033[36m         Fix:  %s\033[0m\n" "$4"
  fi
  ERRORS=$((ERRORS + 1))
}

warn() {
  yellow "  WARN:  $1"
  if [[ -n "${2:-}" ]]; then
    dim "         File: $2"
  fi
  if [[ -n "${3:-}" ]]; then
    printf "\033[36m         Fix:  %s\033[0m\n" "$3"
  fi
  WARNINGS=$((WARNINGS + 1))
}

pass() {
  if [[ "$VERBOSE" == "--verbose" ]]; then
    green "  OK:    $*"
  fi
}

echo ""
bold "Hero Skills Plugin Validator"
echo "────────────────────────────"
echo ""

# ─── Plugin Manifest ──────────────────────────────────────────────

bold "1. Plugin Manifest"

MANIFEST="$PLUGIN_ROOT/.claude-plugin/plugin.json"
MANIFEST_REL=".claude-plugin/plugin.json"

if [[ ! -f "$MANIFEST" ]]; then
  error "Missing plugin manifest" \
    "$MANIFEST_REL" \
    "" \
    "Create .claude-plugin/plugin.json with at minimum: { \"name\": \"your-plugin-name\" }"
else
  if ! jq empty "$MANIFEST" 2>/dev/null; then
    error "Invalid JSON syntax" \
      "$MANIFEST_REL" \
      "" \
      "Run: jq . $MANIFEST_REL to see the parse error, then fix the JSON"
  else
    pass "plugin.json is valid JSON"

    NAME=$(jq -r '.name // empty' "$MANIFEST")
    if [[ -z "$NAME" ]]; then
      error "Missing required 'name' field" \
        "$MANIFEST_REL" \
        "" \
        "Add a \"name\" field: { \"name\": \"my-plugin\" } — must be kebab-case"
    elif [[ ! "$NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
      error "Plugin name '$NAME' is not kebab-case" \
        "$MANIFEST_REL" \
        "$(grep -n '"name"' "$MANIFEST" | head -1 | cut -d: -f1)" \
        "Use lowercase letters and hyphens only, e.g. \"my-plugin-name\""
    else
      pass "name: $NAME"
    fi

    VERSION=$(jq -r '.version // empty' "$MANIFEST")
    if [[ -n "$VERSION" && ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      warn "Version '$VERSION' is not valid semver" \
        "$MANIFEST_REL" \
        "Use format X.Y.Z, e.g. \"1.0.0\""
    else
      pass "version: ${VERSION:-not set}"
    fi

    DESC=$(jq -r '.description // empty' "$MANIFEST")
    if [[ -z "$DESC" ]]; then
      warn "No description in plugin manifest" \
        "$MANIFEST_REL" \
        "Add a \"description\" field to help users understand what this plugin does"
    else
      pass "description present"
    fi
  fi
fi

echo ""

# ─── Marketplace Manifest ─────────────────────────────────────────

bold "2. Marketplace Manifest"

MARKETPLACE="$PLUGIN_ROOT/.claude-plugin/marketplace.json"
MARKETPLACE_REL=".claude-plugin/marketplace.json"

if [[ ! -f "$MARKETPLACE" ]]; then
  pass "marketplace.json not found (optional — only needed for publishing)"
else
  if ! jq empty "$MARKETPLACE" 2>/dev/null; then
    error "Invalid JSON syntax" \
      "$MARKETPLACE_REL" \
      "" \
      "Run: jq . $MARKETPLACE_REL to see the parse error"
  else
    pass "marketplace.json is valid JSON"
  fi
fi

echo ""

# ─── Skills ───────────────────────────────────────────────────────

bold "3. Skills"

SKILLS_DIR="$PLUGIN_ROOT/skills"

if [[ ! -d "$SKILLS_DIR" ]]; then
  error "Missing skills/ directory" \
    "" \
    "" \
    "Create a skills/ directory and add skill subdirectories, each with a SKILL.md"
else
  SKILL_COUNT=0
  SKILL_PASS=0

  for skill_dir in "$SKILLS_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    SKILL_NAME=$(basename "$skill_dir")
    SKILL_COUNT=$((SKILL_COUNT + 1))
    SKILL_ERRORS_BEFORE=$ERRORS

    SKILL_FILE="$skill_dir/SKILL.md"
    SKILL_REL="skills/$SKILL_NAME/SKILL.md"

    # 1. SKILL.md exists
    if [[ ! -f "$SKILL_FILE" ]]; then
      error "Missing SKILL.md" \
        "skills/$SKILL_NAME/" \
        "" \
        "Create $SKILL_REL with YAML frontmatter (--- delimited) containing 'name' and 'description'"
      continue
    fi

    # 2. Extract frontmatter
    FRONTMATTER=$(awk '/^---$/{n++; next} n==1{print} n>=2{exit}' "$SKILL_FILE")

    if [[ -z "$FRONTMATTER" ]]; then
      error "No YAML frontmatter found" \
        "$SKILL_REL" \
        "1" \
        "Add frontmatter at the top: ---\\nname: $SKILL_NAME\\ndescription: What this skill does\\n---"
      continue
    fi

    # 3. Name field
    FM_NAME=$(echo "$FRONTMATTER" | grep -E '^name:' | sed 's/^name:[[:space:]]*//' | head -1 || true)
    NAME_LINE=$(grep -n '^name:' "$SKILL_FILE" | head -1 | cut -d: -f1 || true)

    if [[ -z "$FM_NAME" ]]; then
      error "Frontmatter missing 'name' field" \
        "$SKILL_REL" \
        "2" \
        "Add 'name: $SKILL_NAME' to the frontmatter block"
    elif [[ ! "$FM_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
      error "Name '$FM_NAME' is not kebab-case (must be lowercase + hyphens)" \
        "$SKILL_REL" \
        "$NAME_LINE" \
        "Change to: name: $(echo "$FM_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')"
    elif [[ "$FM_NAME" != "$SKILL_NAME" ]]; then
      warn "Frontmatter name '$FM_NAME' doesn't match directory name '$SKILL_NAME'" \
        "$SKILL_REL" \
        "$NAME_LINE" \
        "Either rename the directory to '$FM_NAME/' or change frontmatter to 'name: $SKILL_NAME'"
    else
      pass "$SKILL_NAME: name OK"
    fi

    # 4. Description field
    FM_DESC=$(echo "$FRONTMATTER" | grep -E '^description:' | sed 's/^description:[[:space:]]*//' | head -1 || true)
    DESC_LINE=$(grep -n '^description:' "$SKILL_FILE" | head -1 | cut -d: -f1 || true)

    if [[ -z "$FM_DESC" ]]; then
      error "Frontmatter missing 'description' field" \
        "$SKILL_REL" \
        "${DESC_LINE:-3}" \
        "Add 'description: What this skill does. Use when user asks to \"trigger phrase\".' — be specific about when to trigger"
    elif [[ ${#FM_DESC} -lt 20 ]]; then
      warn "Description is only ${#FM_DESC} chars — too short to be useful" \
        "$SKILL_REL" \
        "$DESC_LINE" \
        "Expand to include what the skill does AND trigger phrases (e.g. 'Use when...'). Aim for 50+ chars."
    else
      pass "$SKILL_NAME: description (${#FM_DESC} chars)"
    fi

    # 5. Body content
    BODY=$(awk '/^---$/{n++; next} n>=2{found=1; print}' "$SKILL_FILE")
    BODY_START_LINE=$(awk '/^---$/{n++; if(n==2){print NR+1; exit}}' "$SKILL_FILE")

    if [[ -z "$BODY" ]]; then
      error "No body content after frontmatter" \
        "$SKILL_REL" \
        "$BODY_START_LINE" \
        "Add skill instructions after the closing --- delimiter"
    else
      pass "$SKILL_NAME: body content present"
    fi

    # 6. Line count
    LINE_COUNT=$(wc -l < "$SKILL_FILE" | tr -d ' ')
    if [[ $LINE_COUNT -gt 500 ]]; then
      warn "SKILL.md is $LINE_COUNT lines (recommended: under 500)" \
        "$SKILL_REL" \
        "" \
        "Move detailed content to references/ or examples/ subdirectories and link via supplementary-files"
    else
      pass "$SKILL_NAME: $LINE_COUNT lines"
    fi

    # 7. Word count
    WORD_COUNT=$(wc -w < "$SKILL_FILE" | tr -d ' ')
    if [[ $WORD_COUNT -gt 5000 ]]; then
      warn "SKILL.md is $WORD_COUNT words (recommended: under 5000)" \
        "$SKILL_REL" \
        "" \
        "Large skills consume context window. Split into references/ loaded on-demand via supplementary-files"
    else
      pass "$SKILL_NAME: $WORD_COUNT words"
    fi

    # 8. Supplementary file references
    SUPP_FILES=$(echo "$FRONTMATTER" | awk '/^supplementary-files:/,/^[^ -]/' | grep -E '^\s*-\s*' | sed 's/.*-[[:space:]]*//' || true)
    if [[ -n "$SUPP_FILES" ]]; then
      SUPP_LINE=$(grep -n 'supplementary-files:' "$SKILL_FILE" | head -1 | cut -d: -f1 || true)
      while IFS= read -r ref; do
        if [[ ! -f "$skill_dir/$ref" ]]; then
          error "Supplementary file '$ref' referenced but not found" \
            "$SKILL_REL" \
            "$SUPP_LINE" \
            "Create the file at skills/$SKILL_NAME/$ref or remove it from supplementary-files"
        else
          pass "$SKILL_NAME: $ref exists"
        fi
      done <<< "$SUPP_FILES"
    fi

    # 9. Empty subdirectories
    for subdir in references scripts examples assets; do
      if [[ -d "$skill_dir/$subdir" ]]; then
        file_count=$(find "$skill_dir/$subdir" -type f | wc -l | tr -d ' ')
        if [[ $file_count -eq 0 ]]; then
          warn "skills/$SKILL_NAME/$subdir/ exists but is empty" \
            "skills/$SKILL_NAME/$subdir/" \
            "Add files or remove the empty directory"
        else
          pass "$SKILL_NAME: $subdir/ ($file_count files)"
        fi
      fi
    done

    # Track per-skill pass/fail
    if [[ $ERRORS -eq $SKILL_ERRORS_BEFORE ]]; then
      SKILL_PASS=$((SKILL_PASS + 1))
    fi

  done

  echo ""
  echo "  Skills: $SKILL_PASS/$SKILL_COUNT passed"
fi

# ── chained-skill invocability guard ───────────────────────────────
# one-shot (skills/one-shot/SKILL.md) delegates its steps to child skills via
# the Skill tool, and wayfare next chains into think-it-through and
# one-shot the same way. A chained skill carrying
# `disable-model-invocation: true` cannot be invoked by the model, so the
# calling pipeline breaks at that step (there is no per-caller allowlist).
# Keep this list in sync with one-shot's step→skill mapping AND
# wayfare next's tiers — `one-shot` is here because re-adding its flag
# would silently break `wayfare next`. `architecture` is chained three
# ways: wayfare sync runs its review/sync in both modes, and
# think-it-through's `arch` dispatch
# delegates to it. `handoff` is deliberately NOT here: wayfare's
# design-feedback delivery files its issue directly rather than routing
# through handoff, because handoff distills the *current conversation* and
# would carry this repo's session state into a third party's tracker.
# `preflight` is intentionally absent — one-shot runs
# it via scripts/preflight.sh, not the Skill tool, so it may stay user-only.
CHAINED_SKILLS="think-it-through push-pr review-pr respond-to-comments ship-pr one-shot architecture"
for chained in $CHAINED_SKILLS; do
  chained_file="$SKILLS_DIR/$chained/SKILL.md"
  # A missing chained skill silently breaks one-shot at that step, so error
  # rather than skip — the list above must always resolve to real skills.
  if [[ ! -f "$chained_file" ]]; then
    error "the pipelines chain '$chained' but skills/$chained/SKILL.md is missing" \
      "skills/$chained/SKILL.md" \
      "" \
      "Restore the skill, or update the calling skill's step→skill mapping and this guard's CHAINED_SKILLS list to match"
    continue
  fi
  # Scope the check to the YAML frontmatter (first --- ... --- block) so a
  # `disable-model-invocation: true` line inside a body code block (e.g. a
  # scaffolding example) can't produce a false positive. Allow leading
  # whitespace on the key.
  CHAINED_FM=$(awk '/^---$/{n++; next} n==1{print} n>=2{exit}' "$chained_file")
  # Here-string, not `printf | grep -q`. Under `set -o pipefail`, grep -q exits
  # the moment it matches, which SIGPIPEs the still-writing printf; the pipeline
  # then reports 141 and the `if` takes the FAILURE branch even though the match
  # succeeded. The bigger the input, the likelier it fires — so the guard would
  # start lying precisely as a skill grew.
  if grep -qE '^[[:space:]]*disable-model-invocation:[[:space:]]*true' <<< "$CHAINED_FM"; then
    DMI_LINE=$(grep -nE '^[[:space:]]*disable-model-invocation:[[:space:]]*true' "$chained_file" | head -1 | cut -d: -f1)
    error "'$chained' is chained by a hero pipeline but is user-only (disable-model-invocation: true)" \
      "skills/$chained/SKILL.md" \
      "$DMI_LINE" \
      "Remove the 'disable-model-invocation: true' line — a hero pipeline invokes this skill via the Skill tool and cannot call a user-only skill"
  else
    pass "$chained: model-invocable (chainable by the hero pipelines)"
  fi
done

echo ""
echo "────────────────────────────"

# ── absorbed-skill dangling-reference guard ────────────────────────
# scan-vulns, test-changes, and document-arch were deleted and folded into
# harden, push-pr, and think-it-through respectively. A live reference to one
# of these names is fine ONLY as a lineage note ("absorbed the former X",
# "absorbed from X") — anything else is a leftover pointer to a skill that no
# longer exists. Scoped to tracked, non-historical docs; a plans/ retrospective
# describing what the repo looked like at the time it was written is exempt.
ABSORBED_SKILLS="scan-vulns test-changes document-arch"
for absorbed in $ABSORBED_SKILLS; do
  if [[ -d "$SKILLS_DIR/$absorbed" ]]; then
    error "'$absorbed' was supposed to be absorbed elsewhere but skills/$absorbed/ still exists" \
      "skills/$absorbed/SKILL.md" \
      "" \
      "Either this skill was reinstated (update ABSORBED_SKILLS in scripts/validate.sh to drop it) or the merge is incomplete"
    continue
  fi
  HITS=$(grep -rn "$absorbed" --include='*.md' --include='*.sh' \
    "$SKILLS_DIR" "$PLUGIN_ROOT/README.md" "$PLUGIN_ROOT/PIPELINES.md" "$PLUGIN_ROOT/scripts" 2>/dev/null \
    | grep -v "$(basename "$0")" \
    | grep -viE 'absorb' || true)
  if [[ -n "$HITS" ]]; then
    while IFS= read -r hit; do
      hit_file="${hit%%:*}"
      error "reference to deleted skill '$absorbed' without lineage context (expected 'absorbed...')" \
        "${hit_file#"$PLUGIN_ROOT"/}" \
        "" \
        "Either add lineage framing ('absorbed the former $absorbed...') or this is a stale pointer to a skill that no longer exists"
    done <<< "$HITS"
  else
    pass "no dangling references to deleted skill '$absorbed'"
  fi
done

echo ""
echo "────────────────────────────"

# ── skill-reference resolution guard ───────────────────────────────
# `hero-skills:NAME` references fan out across skills, README, and
# PIPELINES.md; a renamed or deleted skill rots every one of them silently.
# ABSORBED_SKILLS above is the hand-curated tail of that class — this is the
# generic half: every referenced name must resolve to skills/NAME/SKILL.md.
# Lineage notes ("absorbed the former hero-skills:X") are exempt, same rule
# as the absorbed guard.
REF_NAMES=$(grep -rhoE 'hero-skills:[a-z][a-z0-9-]*' --include='*.md' \
  "$SKILLS_DIR" "$PLUGIN_ROOT/README.md" "$PLUGIN_ROOT/PIPELINES.md" 2>/dev/null \
  | sort -u | cut -d: -f2)
DANGLING_REFS=0
for ref in $REF_NAMES; do
  [[ -f "$SKILLS_DIR/$ref/SKILL.md" ]] && continue
  # Trailing-boundary match so `one-shot` never swallows a hit on `one-shots`.
  HITS=$(grep -rnE "hero-skills:$ref([^a-z0-9-]|\$)" --include='*.md' \
    "$SKILLS_DIR" "$PLUGIN_ROOT/README.md" "$PLUGIN_ROOT/PIPELINES.md" 2>/dev/null \
    | grep -viE 'absorb' || true)
  [[ -z "$HITS" ]] && continue # lineage-only references are fine
  DANGLING_REFS=1
  while IFS= read -r hit; do
    hit_file="${hit%%:*}"
    hit_line=$(printf '%s' "$hit" | cut -d: -f2)
    error "'hero-skills:$ref' does not resolve to skills/$ref/SKILL.md" \
      "${hit_file#"$PLUGIN_ROOT"/}" \
      "$hit_line" \
      "Point the reference at the skill's current name, or add lineage framing ('absorbed the former $ref ...') if it is a history note"
  done <<< "$HITS"
done
if [[ "$DANGLING_REFS" = 0 ]]; then
  pass "all hero-skills:NAME references resolve to existing skills"
fi

echo ""
echo "────────────────────────────"

# ── re-inlined shared helpers ──────────────────────────────────────
# HERO.md parsing, .git/info/exclude writes, and work-item status parsing live
# in scripts/hero-lib.sh. A file that re-implements one forks the behavior
# silently, and the fork only surfaces when two skills disagree at runtime.
#
# This checks SEMANTICS, not literal byte strings. An earlier version matched
# the exact awk one-liners that existed at the time; those strings stopped
# appearing the moment hero-lib.sh was rewritten, so the guard matched nothing
# anywhere in the repo — including the canonical implementation — and reported
# clean over every possible violation. Any reworded copy (awk -F":", sed -n,
# grep|cut) escaped it too.
#
# The inverted rule: if a file TOUCHES shared state, it must also reference the
# library. That has no phrasing to evade — you cannot parse default-branch
# without naming default-branch.
#
# Format: "marker-regex|hero-lib replacement|human description"
# Match the PARSING IDIOM, not the field name. Matching field names both
# over-fired (prose mentioning "default-branch", init-hero GENERATING the
# HERO.md template, a test writing fixtures) and under-fired (it never named
# merge-method / platform / health-endpoint, so four hand-rolled parsers in
# ship-pr went unseen). Reading HERO.md through a text tool is the actual
# duplication; writing it is not.
# Match the PARSING IDIOM, not the field name. Field names both over-fired
# (prose, init-hero GENERATING the HERO.md template, tests writing fixtures)
# and under-fired (never naming merge-method / platform, so four hand-rolled
# parsers in ship-pr went unseen). Reading HERO.md through a text tool is the
# duplication; writing it is not.
#
# Fields are :: separated — the patterns contain `|` alternations.
# `.*` not `[^\n]*`: grep -E reads the latter as "not backslash or n", which
# cannot span an ordinary word like `print`. grep is line-based regardless.
# \b word boundaries are required too — without them `sed` matches inside
# "pas_sed_" and "ba_sed_", flagging ordinary prose.
SHARED_STATE=(
  "\\b(awk|sed|cut)\\b.*HERO\\.md::hero_field::hand-rolled HERO.md parsing"
  "rev-parse.*info/exclude::hero_exclude_add::.git/info/exclude resolution"
)
ALLOW_MARKER="hero-lint: allow-inline"

while IFS= read -r f; do
  case "$f" in
    */hero-lib.sh|*/validate.sh) continue ;;
  esac
  for entry in "${SHARED_STATE[@]}"; do
    marker="${entry%%::*}"
    rest="${entry#*::}"
    replacement="${rest%%::*}"
    description="${rest##*::}"
    # Report only lines that BOTH match the idiom and lack the opt-out marker.
    # Checked per line, not per file: a file may legitimately use the library
    # in one place and document the anti-pattern in another.
    hits=$(grep -nE "$marker" "$f" 2>/dev/null | grep -vF "$ALLOW_MARKER" || true)
    [ -z "$hits" ] && continue
    error "$description — use $replacement" \
      "${f#"$PLUGIN_ROOT/"}" \
      "$(printf '%s' "$hits" | head -1 | cut -d: -f1)" \
      "Source scripts/hero-lib.sh and call $replacement, or append a '$ALLOW_MARKER' comment on that line if it is deliberate"
  done
done < <(find "$SKILLS_DIR" "$PLUGIN_ROOT/scripts" -type f 2>/dev/null)

if [[ $ERRORS -eq 0 ]]; then
  pass "no file touches shared state without hero-lib.sh"
fi

# ── work-item store: producers must have a consumer ────────────────
# think-it-through, handoff, and harden all WRITE work-items into .plans/
# (and read the plate back to build on it). one-shot is the only skill that
# CONSUMES an item — resolving it to execute and marking it done. (It also
# authors Step 2a carve-outs, but it never plans one from scratch.) If that delegation
# is ever edited away, the store silently becomes write-only: items pile up,
# nothing marks them done, and one-shot goes back to planning from scratch
# while ignoring the plate. Nothing else in this repo would catch that.
ONE_SHOT="$SKILLS_DIR/one-shot/SKILL.md"
if [[ ! -f "$ONE_SHOT" ]]; then
  error "skills/one-shot/SKILL.md is missing" "skills/one-shot/SKILL.md" "" \
    "one-shot owns Pipeline 2; restore it or update this guard"
else
  # Strip HTML comments and fenced blocks before matching, and require the
  # reference in an ACTIVE position (an Invoke instruction or a table row).
  # A bare substring check was satisfied by leaving the name in a comment —
  # "this pipeline used to call hero-skills:think-it-through" passed while
  # every real delegation had been deleted, which is exactly the drift this
  # guard exists to catch.
  ONE_SHOT_ACTIVE=$(awk '
    /^```/           { fence = !fence; next }
    fence            { next }
    /<!--/           { next }
    { print }
  ' "$ONE_SHOT")
  # Here-string rather than `printf | grep -q` — see the pipefail/SIGPIPE note
  # on the chained-skill guard above. This site is the one that actually bit:
  # the match sits near the top of one-shot's Step->skill table, so grep -q
  # exited early and killed printf mid-write, and the guard reported drift that
  # had not happened.
  if grep -qE '(Invoke|Skill tool|^\|).*hero-skills:think-it-through' <<< "$ONE_SHOT_ACTIVE"; then
    pass "one-shot's plan step delegates to think-it-through"
  else
    error "one-shot no longer references think-it-through — the plan step has drifted back to planning from scratch" \
      "skills/one-shot/SKILL.md" \
      "" \
      "think-it-through is the planning skill; one-shot's Step 1 must resolve against .plans/ and delegate to it. See PIPELINES.md Pipeline 2"
  fi
  # Require several real references, not one incidental mention — "plans" is
  # a word that appears in ordinary prose, so match the literal `.plans` token.
  STORE_HITS=$(printf '%s\n' "$ONE_SHOT_ACTIVE" | grep -cF '.plans' || true)
  if [[ "${STORE_HITS:-0}" -ge 3 ]]; then
    pass "one-shot reads the .plans/ store ($STORE_HITS references)"
  else
    error "one-shot does not read .plans/ — the work-item store has no consumer" \
      "skills/one-shot/SKILL.md" \
      "" \
      "think-it-through, handoff, and harden all emit into .plans/; one-shot Step 1 must resolve against it and Step 9 must mark the merged item done"
  fi
fi

echo ""
echo "────────────────────────────"

if [[ $ERRORS -gt 0 ]]; then
  echo ""
  red "FAILED: $ERRORS error(s), $WARNINGS warning(s)"
  echo ""
  dim "Fix the errors above and re-run: ./scripts/validate.sh"
  dim "Use --verbose to also see passing checks."
  exit 1
elif [[ $WARNINGS -gt 0 ]]; then
  echo ""
  yellow "PASSED with $WARNINGS warning(s)"
  dim "Warnings won't block commits but should be addressed."
  exit 0
else
  echo ""
  green "ALL CHECKS PASSED"
  exit 0
fi
