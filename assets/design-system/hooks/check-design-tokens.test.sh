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

# --- shadow: the house rule with no legitimate exception ---------------------
case_ shadow_first hit  Shadow '<div className="shadow-md rounded" />'
case_ shadow_mid   hit  Shadow '<div className="rounded shadow-md" />'
case_ shadow_cn    hit  Shadow '<div className={cn("shadow-lg", x)} />'
case_ shadow_bare  hit  Shadow '<div className="shadow rounded" />'
case_ shadow_none  miss Shadow '<div className="shadow-none rounded" />'

# --- className={cn(...)} is the form the rules file mandates ----------------
case_ cn_margin   hit Margin      '<div className={cn("mb-4", x)} />'
case_ cn_zindex   hit z-index     '<div className={cn("z-50", x)} />'
case_ cn_arb      hit Arbitrary   '<div className={cn("rounded-[10px]", x)} />'
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

# --- a broken hook must not look like a clean file --------------------------
exit_ malformed_payload 2 'not json at all'
exit_ empty_payload     2 ''
exit_ no_file_path      0 '{"tool_input":{"other":"x"}}'
exit_ notebook_payload  0 '{"tool_input":{"notebook_path":"/a/b.ipynb"}}'

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

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "check-design-tokens: $PASS passed"
  exit 0
fi
echo "check-design-tokens: $PASS passed, $FAIL FAILED"
exit 1
