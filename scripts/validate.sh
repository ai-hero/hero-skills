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
