#!/usr/bin/env bash
# Regression table for check-design-tokens.sh.
#
# The seven checks are pure string -> bool functions, and three of them once
# shipped with regexes that silently matched nothing in the most common case:
# a shadow class in first position, and any class inside className={cn(...)}.
# Both read as "no findings", which is indistinguishable from a clean file.
# Every row below is a case that was, or could again be, wrong in that
# undetectable direction.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")" && pwd)/check-design-tokens.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

# case NAME hit|miss RULE_SUBSTRING CONTENT [EXT]
case_() {
  local name="$1" expect="$2" rule="$3" content="$4" ext="${5:-tsx}"
  printf '%s\n' "$content" > "$TMP/$name.$ext"
  local out got
  out="$(printf '{"tool_input":{"file_path":"%s/%s.%s"}}' "$TMP" "$name" "$ext" | bash "$HOOK" 2>&1)"
  if printf '%s' "$out" | grep -qF "$rule"; then got=hit; else got=miss; fi
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name — expected $expect, got $got"
    echo "      input:  $content"
    echo "      output: ${out:-(none)}"
  fi
}

# exit_ NAME EXPECTED_CODE PAYLOAD
exit_() {
  local name="$1" want="$2" payload="$3" rc
  printf '%s' "$payload" | bash "$HOOK" >/dev/null 2>&1
  rc=$?
  if [ "$rc" = "$want" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name — expected exit $want, got $rc"
  fi
}

# dcase_ NAME hit|miss RULE_SUBSTRING DISK_CONTENT NEW_STRING [EXT]
#
# Diff-scoped case: DISK_CONTENT is written to the file first, simulating
# pre-existing content this edit does NOT touch. The hook is then invoked
# with an Edit-shaped payload carrying NEW_STRING as tool_input.new_string —
# that field is what makes the scan diff-scoped instead of whole-file.
dcase_() {
  local name="$1" expect="$2" rule="$3" disk="$4" new="$5" ext="${6:-tsx}"
  printf '%s\n' "$disk" > "$TMP/$name.$ext"
  local payload out got
  payload="$(jq -n --arg fp "$TMP/$name.$ext" --arg ns "$new" \
    '{tool_input:{file_path:$fp, old_string:"x", new_string:$ns}}')"
  out="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)"
  if printf '%s' "$out" | grep -qF "$rule"; then got=hit; else got=miss; fi
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name — expected $expect, got $got"
    echo "      disk: $disk"
    echo "      new:  $new"
    echo "      output: ${out:-(none)}"
  fi
}

# wcase_ NAME hit|miss RULE_SUBSTRING CONTENT [EXT]
#
# Write-shaped diff-scoped case: CONTENT is the full new file, carried as
# tool_input.content (what a Write call's payload looks like) rather than
# file_path alone — proves the content field is also diff/content-scoped,
# not just new_string. The file is also written to disk first, matching
# real PostToolUse timing (the write has already landed by the time the
# hook runs).
wcase_() {
  local name="$1" expect="$2" rule="$3" content="$4" ext="${5:-tsx}"
  printf '%s\n' "$content" > "$TMP/$name.$ext"
  local payload out got
  payload="$(jq -n --arg fp "$TMP/$name.$ext" --arg c "$content" \
    '{tool_input:{file_path:$fp, content:$c}}')"
  out="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)"
  if printf '%s' "$out" | grep -qF "$rule"; then got=hit; else got=miss; fi
  if [ "$got" = "$expect" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name — expected $expect, got $got"
    echo "      output: ${out:-(none)}"
  fi
}

# --- shadow: the house rule with no legitimate exception ---------------------
case_ shadow_first hit  Shadow '<div className="shadow-md rounded" />'
case_ shadow_mid   hit  Shadow '<div className="rounded shadow-md" />'
case_ shadow_cn    hit  Shadow '<div className={cn("shadow-lg", x)} />'
case_ shadow_bare  hit  Shadow '<div className="shadow rounded" />'
case_ shadow_none  miss Shadow '<div className="shadow-none rounded" />'
# Tailwind v4 added shadow-2xs/shadow-xs below shadow-sm; an earlier draft's
# alternation only carried the v3-era suffix set, so the single most common
# small-elevation utility in a v4 codebase silently passed.
case_ shadow_xs    hit  Shadow '<div className="shadow-xs rounded" />'
case_ shadow_2xs   hit  Shadow '<div className="shadow-2xs rounded" />'

# --- className={cn(...)} is the form the rules file mandates ----------------
case_ cn_margin   hit Margin      '<div className={cn("mb-4", x)} />'
case_ cn_zindex   hit z-index     '<div className={cn("z-50", x)} />'
case_ cn_arb      hit Arbitrary   '<div className={cn("rounded-[10px]", x)} />'
# ${x} below is literal fixture content (a JS template literal being tested
# as-is), not a shell variable. Switching to double quotes to satisfy a
# lint hint about it would make bash actually expand $x (undefined, empty),
# silently changing what this case exercises.
# shellcheck disable=SC2016
case_ tmpl_margin hit Margin      '<div className={`mb-4 ${x}`} />'
case_ sq_margin   hit Margin      "<div className='mb-4' />"

# --- arbitrary values: the bracket need not follow the first hyphen ---------
case_ arb_w    hit Arbitrary '<div className="w-[300px]" />'
case_ arb_h    hit Arbitrary '<div className="h-[48px]" />'
case_ arb_maxw hit Arbitrary '<div className="max-w-[65ch]" />'
case_ arb_grid hit Arbitrary '<div className="grid-cols-[240px_1fr]" />'
case_ arb_calc hit Arbitrary '<div className="min-h-[calc(100vh-4rem)]" />'

# --- Tailwind's own bracket variants are not arbitrary values ---------------
case_ fp_data miss Arbitrary '<div className="data-[state=open]:bg-muted" />'
case_ fp_aria miss Arbitrary '<div className="aria-[current]:underline" />'

# --- classes that merely start like a margin --------------------------------
case_ fp_maxw miss Margin '<div className="max-w-md" />'
case_ fp_minh miss Margin '<div className="min-h-0" />'
case_ fp_mask miss Margin '<div className="mask-radial" />'
case_ fp_mix  miss Margin '<div className="mix-blend-multiply" />'

case_ fp_ztoken miss z-index   '<div className="z-dropdown" />'
case_ fp_size   miss Arbitrary '<div className="size-4 gap-4" />'

# --- the remaining rules ----------------------------------------------------
case_ palette hit  "Raw palette"    '<div className="bg-zinc-100" />'
case_ hex     hit  "Color literal"  '<div style={{color:"#ff0000"}} />'
case_ darkvar hit  "dark: color"    '<div className="dark:bg-muted" />'
case_ clean   miss "  - "           '<div className="bg-background gap-4" />'

# --- a URL fragment is not a color literal ---------------------------------
case_ href_hex   miss "Color literal" '<a href="#feed" className="underline">Feed</a>'
case_ href_hex2  miss "Color literal" '<a href="#decade">D</a>'
case_ style_hex  hit  "Color literal" '<div style={{color:"#abc123"}} />'

# --- CSS: hex belongs in the token layer and nowhere else -------------------
case_ css_plain hit  "Color literal" 'a{color:#ff0000}'          css
case_ css_theme miss "Color literal" '@theme{--color-x:#ff0000;}' css

# --- prose is not a colour literal, and neither is a whole-line comment -----
#
# Both once false-positived: a colour in JSX is always inside a value context
# (a quoted string, a template literal, Tailwind's bracket notation) and prose
# never is, so requiring one of ["'`[ immediately before # drops these without
# guessing at hex length. The comment case is stripped as a whole-line comment
# before the hex check ever sees it — see the hook's own comment-stripping
# note for why that strip is line-anchored rather than to-end-of-line.
case_ prose_hex    miss "Color literal" '<p>Visit us at Ste #1100 downtown.</p>'
case_ prose_hex2   miss "Color literal" '<p>See issue #1234 for details.</p>'
case_ comment_hex  miss "Color literal" '// #aabbcc is the old brand colour, kept for reference
export const A = () => <div className="p-4">hi</div>;'

# --- the bracket-notation regression this refinement almost introduced -----
#
# Requiring a QUOTE before # (the first draft of the fix above) silently
# stopped catching this: Tailwind's own bracket syntax puts a real colour
# literal after `[`, never a quote, and it is a common real way one enters a
# component. Caught by re-running the fixed hook against every existing case
# before vendoring it anywhere.
case_ bracket_hex hit "Color literal" '<div className={cn("text-[#3D4AB8]")} />'

# --- a broken hook must not look like a clean file --------------------------
exit_ malformed_payload 2 'not json at all'
exit_ empty_payload     2 ''
exit_ no_file_path      0 '{"tool_input":{"other":"x"}}'
exit_ notebook_payload  0 '{"tool_input":{"notebook_path":"/a/b.ipynb"}}'

# An `edits` field that isn't an array makes `.[]` a jq error. Both DIFF_SCAN
# and HAS_DIFF_FIELD extraction must fail loud (exit 2) here, not swallow the
# error and silently degrade to a whole-file scan with no signal that
# diff-scoping stopped working. Needs a real, readable file on disk (this is
# the whole-file-fallback failure path, reached only after the diff-scoped
# extraction itself errors), so build the payload with jq rather than a
# literal string.
printf '%s\n' 'export const A = () => <div className="clean" />;' > "$TMP/bad_edits.tsx"
BAD_EDITS_PAYLOAD="$(jq -n --arg fp "$TMP/bad_edits.tsx" '{tool_input:{file_path:$fp,edits:"not-an-array"}}')"
exit_ malformed_edits_field 2 "$BAD_EDITS_PAYLOAD"

# ---------- multi-line className ------------------------------------------
#
# Prettier wraps className={cn(...)} across lines whenever it exceeds the print
# width, which for real components is most of the time. grep is line-based, so
# every className-anchored rule once matched NOTHING here while the same
# violation on one line reported correctly. The whole table was single-line, so
# it attested to far more coverage than it had.

case_ ml_margin hit "Margin in a component" 'export const A = () => (
  <div
    className={cn(
      "mb-4 rounded",
    )}
  />
)'
case_ ml_arb hit "Arbitrary value" 'export const B = () => (
  <div
    className={cn(
      "w-[300px]",
    )}
  />
)'
case_ ml_shadow hit "Shadow class" 'export const C = () => (
  <div
    className={cn(
      "shadow-lg",
    )}
  />
)'
case_ ml_zindex hit "Numeric z-index" 'export const D = () => (
  <div
    className={cn(
      "z-50",
    )}
  />
)'

# The false-positive twins must survive newline collapsing too: [^>]* stops at
# the first `>`, so a class-looking word in one element's BODY must not be
# attributed to a previous element's className.
case_ ml_fp_cross miss "Margin in a component" 'export const E = () => (
  <div className={cn("flex")}>
    <span>mb-4 is prose here</span>
  </div>
)'
case_ ml_fp_maxw miss "Arbitrary value" 'export const F = () => (
  <div
    className={cn(
      "max-w-md",
    )}
  />
)'

# ---------- no-jq fallback -------------------------------------------------
#
# Without jq the hook parses the payload with grep. That path once could not
# tell an unparsable payload from one carrying no file_path — both yielded
# empty and exited 0, so a schema change would silently disable the hook on
# every jq-less machine. CI has jq, so nothing else exercises this.

# Shadow jq with a stub that FAILS. Stripping PATH does not work: jq commonly
# lives in /usr/bin, so the fallback would never be reached and these rows would
# pass for the wrong reason. The hook probes that jq works, so a broken stub is
# what actually routes it down the grep path.
NOJQ_BIN="$TMP/nojq-bin"
mkdir -p "$NOJQ_BIN"
printf '#!/bin/sh\nexit 127\n' > "$NOJQ_BIN/jq"
chmod +x "$NOJQ_BIN/jq"

nojq_() { # NAME EXPECTED_CODE PAYLOAD
  local name="$1" want="$2" payload="$3" rc
  printf '%s' "$payload" | PATH="$NOJQ_BIN:$PATH" bash "$HOOK" >/dev/null 2>&1
  rc=$?
  if [ "$rc" = "$want" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name — expected exit $want, got $rc"
  fi
}

nojq_ nojq_garbage     2 'not json at all'
nojq_ nojq_no_filepath 0 '{"tool_input":{"other":"x"}}'

# ---------- diff-scoped scanning (new_string / content) ---------------------
#
# Scoping the scan to what the payload says was WRITTEN, rather than always
# reading the whole file, is what keeps this check reporting only what an
# edit introduced — a whole-file scan fired on 27 of 49 files in one real,
# partially-migrated repo, making nearly every edit return findings the model
# did not cause. The margin/arbitrary/z-index/shadow checks anchor on
# className= for the whole-file path, but that anchor is WRONG for a diff
# snippet: an Edit very commonly replaces just the class-list string inside
# className="...", so className= itself never appears in new_string, and an
# anchored check against just that string would silently stop catching what
# it always caught — the same undetectable-false-negative shape as the
# multi-line bug above, one layer further in.

# The anchor-drop itself: none of these new_strings contain `className=`, so
# an anchored pattern run against just the string would MISS every one.
dcase_ diff_bare_margin hit "Margin in a component" \
  '<div className="gap-4" />' 'mb-4'
dcase_ diff_bare_shadow hit "Shadow class" \
  '<div className="rounded" />' 'shadow-lg'
dcase_ diff_bare_arb hit "Arbitrary value" \
  '<div className="rounded" />' 'w-[300px]'
dcase_ diff_bare_zindex hit "Numeric z-index" \
  '<div className="rounded" />' 'z-50'

# shadow-none must stay excluded even unanchored — same false-positive twin
# as the whole-file suite, now proven under diff-scoping too.
dcase_ diff_shadow_none_excluded miss "Shadow class" \
  '<div className="rounded" />' 'shadow-none'
dcase_ diff_bare_shadow_xs hit "Shadow class" \
  '<div className="rounded" />' 'shadow-xs'

# The reason diff-scoping exists at all: a REAL violation sitting untouched
# elsewhere in the file must not surface just because this edit touched a
# different, clean part of the same file.
dcase_ diff_preexisting_not_flagged miss "Margin in a component" \
  '<div className="mb-4 shadow-lg" /><div className="gap-4" />' 'gap-6'

# Hex/palette/dark: checks are unanchored in both modes already — confirm
# they still fire and still exempt prose under diff-scoping too.
dcase_ diff_component_hex_hit hit "Color literal" \
  '<div className="rounded" />' 'style={{color:"#3D4AB8"}}'
dcase_ diff_prose_hex_excluded miss "Color literal" \
  '<div className="rounded" />' 'Visit us at Ste #1100 downtown.'

# CSS: @theme presence is a FILE-level fact a diff snippet cannot answer, so
# it must still be read from disk regardless of diff-scoping — these two
# prove that path independently of the JSX cases above.
dcase_ diff_css_theme_on_disk_suppresses miss "Color literal" \
  '@theme{--color-x:#ff0000;} .btn{color:blue}' 'color:#112233' css
dcase_ diff_css_no_theme_still_hits hit "Color literal" \
  '.btn{color:blue}' 'color:#112233' css

# Write-shaped (tool_input.content) diff-scoping, not just Edit's new_string.
wcase_ write_diff_scoped_shadow hit "Shadow class" \
  'export const A = () => <div className="shadow-md rounded" />;'
wcase_ write_diff_scoped_clean miss "  - " \
  'export const A = () => <div className="bg-background gap-4" />;'

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "check-design-tokens: $PASS passed"
  exit 0
fi
echo "check-design-tokens: $PASS passed, $FAIL FAILED"
exit 1
