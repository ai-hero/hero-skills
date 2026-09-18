#!/usr/bin/env bash
# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Tests for the shell blocks inside .github/workflows/auto-approve.yaml.
#
# The workflow is inline bash in YAML with no script to import, so each block
# under test is bracketed by `# test: begin NAME` / `# test: end NAME` markers
# and extracted here. The first check on every block is that the extraction is
# non-empty and parses: a reindent that moved a marker would otherwise turn
# every downstream check into a test of the empty string.
#
# Not -e: the suite observes non-zero exits.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WF="$HERE/../.github/workflows/auto-approve.yaml"

PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $name"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# extract NAME -> prints the block between its markers, de-indented.
extract() {
  awk -v name="$1" '
    $0 ~ "# test: begin " name "$" { on = 1; next }
    $0 ~ "# test: end " name "$"   { on = 0 }
    on { sub(/^          /, ""); print }
  ' "$WF"
}

# The workflow runs under `bash -e` WITHOUT pipefail (no shell: key). The
# blocks are exercised the same way, and once more under pipefail where the
# block is meant to survive it.
run_block() { # NAME [env assignments...] -> runs in $WORK under bash -e
  local name="$1"; shift
  ( cd "$WORK" && env "$@" bash -e "$WORK/$name.sh" )
}

for name in classify diff-filter go-pkgs claims ci-decision verdict-parse bot-lane submit-verdict crash-notice \
            writers-resolve self-review-gate other-reviews-gate bot-inline-gate; do
  extract "$name" > "$WORK/$name.sh"
  check "extract: $name non-empty" "yes" "$([[ -s "$WORK/$name.sh" ]] && echo yes || echo no)"
  check "extract: $name parses" "0" "$(bash -n "$WORK/$name.sh" 2>/dev/null; echo $?)"
done

# --- classify ---------------------------------------------------------------
# shellcheck disable=SC1091
source "$WORK/classify.sh"
# Not `path`: in zsh that name is bound to $PATH as an array, so reading a
# fixture into it wipes PATH for the rest of the run. The suite then reports
# dozens of unrelated failures whose real cause is that `grep` is gone.
while IFS='|' read -r fpath_case want; do
  check "classify: $fpath_case" "$want" "$(classify "$fpath_case")"
done <<'EOF'
.env|secret
.env.production|secret
config/.env.local|secret
id_rsa|secret
deploy/id_ed25519.pub|secret
certs/server.pem|secret
.aws/credentials|secret
credentials.json|secret
infra/kubeconfig|secret
.kube/config|secret
internal/credentials/store.go|source
pkg/credentials/credentials_test.go|source
internal/kubeconfig/loader.go|source
docs/kubeconfig-setup.md|source
package-lock.json|lockfile
apps/web/package-lock.json|lockfile
go.sum|lockfile
lib/go.sum|lockfile
bun.lockb|lockfile
go.summary|source
gen/api.go|generated
src/gen/api.go|generated
generated/x.ts|generated
schema/gen/hiro/v1/hiro.pb.go|generated
ui/src/routeTree.gen.ts|generated
cmd/gen/main.go|generated
web/logo.png|binary
fonts/x.woff2|binary
dist/app.min.js|snapshot
src/app.js.map|snapshot
__snapshots__/a.snap|snapshot
tests/e2e/x.spec.ts-snapshots/a.png|binary
a b/file.go|source
*.go|source
-rf|source
lib/handler/auth.go|source
README.md|source
EOF

# --- diff-filter ------------------------------------------------------------
cat > "$WORK/pr.diff" <<'EOF'
diff --git a/ui/package-lock.json b/ui/package-lock.json
--- a/ui/package-lock.json
+++ b/ui/package-lock.json
@@ -1 +1 @@
-"nanoid": "3.3.16"
+"nanoid": "3.3.18"
diff --git a/old/yarn.lock b/pkg/yarn.lock
--- a/old/yarn.lock
+++ b/pkg/yarn.lock
@@ -1 +1 @@
-x
+y
diff --git a/go.summary b/go.summary
--- a/go.summary
+++ b/go.summary
@@ -1 +1 @@
-keep
+keep2
diff --git a/lib/auth.go b/lib/auth.go
--- a/lib/auth.go
+++ b/lib/auth.go
@@ -1 +1 @@
-old := AUTH_SENTRY_DSN
+new := SENTRY_DSN
EOF
printf 'ui/package-lock.json\npkg/yarn.lock\ngo.sum\n' > "$WORK/omitted_paths.txt"
run_block diff-filter
out=$(cat "$WORK/pr_filtered.diff")
check "diff-filter: lockfile hunk dropped" "no" "$(grep -q nanoid <<<"$out" && echo yes || echo no)"
check "diff-filter: renamed lockfile dropped (keyed on b/ path)" "no" "$(grep -q 'yarn.lock' <<<"$out" && echo yes || echo no)"
check "diff-filter: go.summary is not go.sum" "yes" "$(grep -q 'go.summary' <<<"$out" && echo yes || echo no)"
check "diff-filter: source hunk kept" "yes" "$(grep -q SENTRY_DSN <<<"$out" && echo yes || echo no)"
: > "$WORK/omitted_paths.txt"
run_block diff-filter
check "diff-filter: empty omit list passes everything" "$(wc -l < "$WORK/pr.diff")" "$(wc -l < "$WORK/pr_filtered.diff")"
printf '(unified diff unavailable — placeholder)\n' > "$WORK/pr.diff"
run_block diff-filter
check "diff-filter: placeholder (no headers) passes through" "(unified diff unavailable — placeholder)" "$(cat "$WORK/pr_filtered.diff")"

# --- go-pkgs ----------------------------------------------------------------
printf 'lib/handler/auth.go\tmodified\t3\t1\nlib/handler/auth_test.go\tmodified\t3\t1\nlib/store/user.go\tadded\t30\t0\nmain.go\tmodified\t1\t1\nschema/gen/v1/x.pb.go\tmodified\t9\t9\nui/src/x.ts\tmodified\t1\t1\nlib/old/gone.go\tremoved\t0\t20\n' > "$WORK/files.tsv"
printf 'schema/gen/v1/x.pb.go\n' > "$WORK/omitted_paths.txt"
run_block go-pkgs
check "go-pkgs: tested package excluded, untested listed, generated skipped" ". lib/old lib/store" "$(paste -sd' ' "$WORK/go_pkgs_without_tests.txt")"

# --- claims -----------------------------------------------------------------
printf 'Renames to `APP_SENTRY_DSN`. Adds `TestConnectPing`. Bumps `nanoid`. Touches `lib/auth.go`. Run `go test ./...`. Regex `foo.*bar` and `[a-z]+` and `--paginate`. `ok`\n' > "$WORK/pr_body.txt"
cat > "$WORK/pr.diff" <<'EOF'
diff --git a/ui/package-lock.json b/ui/package-lock.json
+"nanoid": "3.3.18"
diff --git a/lib/auth.go b/lib/auth.go
-old := AUTH_SENTRY_DSN
+new := SENTRY_DSN
EOF
printf 'lib/auth.go\nlib/auth_test.go\n' > "$WORK/repo_tree.txt"; : > "$WORK/full_files.txt"; echo "feat: x" > "$WORK/pr_title.txt"
run_block claims
check "claims: extracted (no whitespace tokens, sorted, unique)" "--paginate,APP_SENTRY_DSN,TestConnectPing,[a-z]+,foo.*bar,lib/auth.go,nanoid" "$(LC_ALL=C sort "$WORK/claims.txt" | paste -sd, -)"
check "claims: unverified = not literally present anywhere (regex chars literal, dash safe)" "--paginate,APP_SENTRY_DSN,TestConnectPing,[a-z]+,foo.*bar" "$(LC_ALL=C sort "$WORK/unverified_claims.txt" | paste -sd, -)"
printf 'No backticks in this body at all.\n' > "$WORK/pr_body.txt"; : > "$WORK/unverified_claims.txt"
rc=$(cd "$WORK" && bash -eo pipefail "$WORK/claims.sh" >/dev/null 2>&1; echo $?)
check "claims: body without backticks survives pipefail" "0" "$rc"
check "claims: body without backticks -> no claims" "0" "$(wc -l < "$WORK/claims.txt" | tr -d ' ')"

# --- bot-lane ---------------------------------------------------------------
# This block classifies the review lane: deps_bot=true means a scripted APPROVE
# with the model skipped, so every assertion here is about not granting that
# wrongly. It was untested when an arity bug in its `gh` call shipped, and the
# first attempt at covering it bracketed only the filter, re-adding the broken
# call to the fetch line left the suite green. The markers now start above the
# fetch, and `gh` is stubbed so the fetch itself is under test.
#
# BOT_RE is read FROM THE WORKFLOW, not retyped. A copy here would keep passing
# against the old value after someone widened the real one, and that direction
# is fail-open.
BOT_RE_WF=$(sed -n "s/^ *BOT_RE='\(.*\)'$/\1/p" "$WF" | head -1)
check "bot-lane: BOT_RE still assigned in the workflow" "yes" \
  "$([[ -n "$BOT_RE_WF" ]] && echo yes || echo no)"

# lane PR_JSON COMMITS_BODY [GH_RC] [BOT_RE] -> "rc|deps_bot|log"
# rc is captured because a crash and a clean run that wrote nothing are
# otherwise indistinguishable, which is what let the fail-closed paths go
# unasserted. A later `|| true` or `// empty` has to fail a test.
lane() {
  printf '%b' "$1" > "$WORK/pr.json"
  printf '%b' "$2" > "$WORK/gh_stdout"
  mkdir -p "$WORK/bin"
  { echo '#!/usr/bin/env bash'
    echo "printf '%s\\n' \"\$*\" >> $WORK/gh_argv"
    echo "cat $WORK/gh_stdout"
    echo "exit ${3:-0}"
  } > "$WORK/bin/gh"
  chmod +x "$WORK/bin/gh"
  : > "$WORK/out"; : > "$WORK/gh_argv"; rm -f "$WORK/lane_error.txt"
  local log rc
  log=$( cd "$WORK" && PATH="$WORK/bin:$PATH" BOT_RE="${4-$BOT_RE_WF}" \
    REPO=o/r PR_NUMBER=1 GITHUB_OUTPUT="$WORK/out" bash -e "$WORK/bot-lane.sh" 2>&1 ); rc=$?
  printf '%s|%s|%s' "$rc" "$(sed -n 's/^deps_bot=//p' "$WORK/out")" "$log"
}
BOT_PR='{"user":{"login":"dependabot[bot]"},"commits":1}'
HUMAN_PR='{"user":{"login":"someone"},"commits":1}'
# Shaped from a REAL Dependabot commit (design-system#155): the bot is the
# AUTHOR, the committer is GitHub's `web-flow` because Dependabot commits
# through the API, and GitHub signs it. A fixture that made committer == author
# is what let a committer check look correct while breaking every live bot PR.
signed() { printf '[{"sha":"%s","author":{"login":"%s"},"committer":{"login":"web-flow"},"commit":{"verification":{"verified":%s,"reason":"valid"}}}]' "$1" "$2" "${3:-true}"; }

# --- the lane itself
check "bot-lane: signed bot commit -> scripted lane" "0|true|" \
  "$(lane "$BOT_PR" "$(signed aaa 'dependabot[bot]')")"
check "bot-lane: renovate too" "0|true|" \
  "$(lane "$BOT_PR" "$(signed aaa 'renovate[bot]')")"
check "bot-lane: human author -> model lane, no fetch" "0|false|" \
  "$(lane "$HUMAN_PR" '')"

# --- attribution is forgeable; the signature is not
# A collaborator can push `git commit --author='dependabot[bot] <...>'` onto an
# open dependabot/* branch and own every attribution field. Dependabot's real
# commits are GPG-signed by GitHub, so an unsigned one is not the bot's however
# it is labelled. Without this the scripted lane APPROVES attacker code.
check "bot-lane: UNSIGNED commit attributed to the bot -> model lane" \
  "0|false|bot-authored PR carries commits that are not the bot's; routing to the model lane: spoof " \
  "$(lane "$BOT_PR" "$(signed spoof 'dependabot[bot]' false)")"
# REGRESSION GUARD. A committer check was added here and merged, and it sent
# every real Dependabot PR to the model lane: `.committer` is `web-flow`, not
# the bot. This is the exact payload from design-system#155 and it must take
# the SCRIPTED lane.
check "bot-lane: real bot commit (committer web-flow) -> scripted lane" "0|true|" \
  "$(lane "$BOT_PR" '[{"sha":"7b97275","author":{"login":"dependabot[bot]"},"committer":{"login":"web-flow"},"commit":{"verification":{"verified":true,"reason":"valid"}}}]')"
check "bot-lane: null author -> model lane" \
  "0|false|bot-authored PR carries commits that are not the bot's; routing to the model lane: ddd " \
  "$(lane "$BOT_PR" '[{"sha":"ddd","author":null,"committer":null,"commit":{"verification":{"verified":true}}}]')"

# --- the regex must not over-match
# Anchors are load-bearing. Unanchoring BOT_RE to "support dependabot-preview"
# would let `notdependabot` take the scripted lane.
check "bot-lane: impostor login -> model lane" \
  "0|false|bot-authored PR carries commits that are not the bot's; routing to the model lane: eee " \
  "$(lane '{"user":{"login":"dependabot[bot]"},"commits":1}' "$(signed eee 'notdependabot')")"

# --- --paginate emits one array PER PAGE, concatenated
# A filter reading only the first array would call a PR clean while page two
# holds the human commit.
check "bot-lane: reads every page, not just the first" \
  "0|false|bot-authored PR carries commits that are not the bot's; routing to the model lane: ccc " \
  "$(lane '{"user":{"login":"dependabot[bot]"},"commits":2}' \
     "$(signed aaa 'dependabot[bot]')\n$(signed ccc 'someone')")"

# --- fail-closed: every one of these must exit non-zero and write NO deps_bot
check "bot-lane: gh failure exits non-zero, no lane" "1||" \
  "$(lane "$BOT_PR" '' 1 | sed 's/|[^|]*$/|/')"
check "bot-lane: empty commit array exits, no lane" "1||" \
  "$(lane "$BOT_PR" '[]' | sed 's/|[^|]*$/|/')"
check "bot-lane: whitespace body exits, no lane" "1||" \
  "$(lane "$BOT_PR" '   \n' | sed 's/|[^|]*$/|/')"
check "bot-lane: truncated list (250-cap) exits, no lane" "1||" \
  "$(lane '{"user":{"login":"dependabot[bot]"},"commits":300}' "$(signed aaa 'dependabot[bot]')" | sed 's/|[^|]*$/|/')"
check "bot-lane: API error object exits, no lane" "5||" \
  "$(lane "$BOT_PR" '{"message":"Not Found"}' | sed 's/|[^|]*$/|/')"
check "bot-lane: unset BOT_RE refuses to classify" "1||" \
  "$(lane "$BOT_PR" "$(signed aaa 'dependabot[bot]')" 0 '' | sed 's/|[^|]*$/|/')"
# The reason reaches the PR, not just the run log.
check "bot-lane: names the reason for the crash reporter" "yes" \
  "$(lane "$BOT_PR" '[]' >/dev/null; [[ -s "$WORK/lane_error.txt" ]] && echo yes || echo no)"
# The exact argv of the fetch. This is the regression itself: the bug was
# `--jq --arg re "$RE" '<filter>'` appended here, which gh rejects as an arity
# error. Pinning the whole string fails on any flag added back to this call.
check "bot-lane: fetch argv carries no --jq/--arg" \
  "api --paginate /repos/o/r/pulls/1/commits?per_page=100" \
  "$(lane "$BOT_PR" "$(signed aaa 'dependabot[bot]')" >/dev/null; cat "$WORK/gh_argv")"

# --- ci-decision ------------------------------------------------------------
ci() { # CHECKS_TSV HAS_WORKFLOWS -> "passed|first line of ci_status"
  printf '%b' "$1" > "$WORK/checks.tsv"
  : > "$WORK/out"
  ( cd "$WORK" && HEAD_SHA=abc123 HAS_WORKFLOWS="$2" GITHUB_OUTPUT="$WORK/out" bash -e "$WORK/ci-decision.sh" ) >/dev/null 2>&1
  # Whole line, not a cut -c prefix: GNU cut -c counts bytes, and the em dash
  # in the status text is three of them.
  printf '%s|%s' "$(sed -n 's/^passed=//p' "$WORK/out")" "$(head -1 "$WORK/ci_status.txt")"
}
check "ci: all success" "true|All 2 check(s) on abc123 passed." "$(ci 'Build\tcompleted\tsuccess\nlint\tcompleted\tsuccess\n' 1)"
check "ci: skipped and neutral pass" "true|All 2 check(s) on abc123 passed." "$(ci 'Build\tcompleted\tskipped\nlint\tcompleted\tneutral\n' 1)"
check "ci: one failure" "false|Failing checks on abc123 — fix them before requesting auto-approve." "$(ci 'Build\tcompleted\tsuccess\nTrivy\tcompleted\tfailure\n' 1)"
check "ci: failure wins over pending" "false|Failing checks on abc123 — fix them before requesting auto-approve." "$(ci 'Deploy\tqueued\t\nTrivy\tcompleted\tfailure\n' 1)"
check "ci: pending" "false|Checks still running on abc123 — wait for them to finish, then re-run \`@auto-approve\`." "$(ci 'Build\tin_progress\t\n' 1)"
check "ci: stale is pending, not a pass" "false|Checks still running on abc123 — wait for them to finish, then re-run \`@auto-approve\`." "$(ci 'Build\tcompleted\tstale\n' 1)"
check "ci: legacy status error fails" "false|Failing checks on abc123 — fix them before requesting auto-approve." "$(ci 'scout\tcompleted\terror\n' 1)"
check "ci: legacy status pending" "false|Checks still running on abc123 — wait for them to finish, then re-run \`@auto-approve\`." "$(ci 'scout\tin_progress\tpending\n' 1)"
check "ci: no checks but repo has workflows -> pending" "false|No checks registered on abc123 yet, but the repo has workflows — wait for CI to start, then re-run \`@auto-approve\`." "$(ci '' 1)"
check "ci: no checks and no workflows -> skip" "true|No CI in this repo (no workflows, no checks on abc123)." "$(ci '' 0)"
check "ci: check name with spaces round-trips" "false|Failing checks on abc123 — fix them before requesting auto-approve." "$(ci 'Auto Approve / build image\tcompleted\ttimed_out\n' 1)"

# --- verdict-parse ----------------------------------------------------------
# The block assigns VERDICT_TOKEN; source it in a subshell to read it.
vp() { printf '%b' "$1" > "$WORK/review.md"; ( cd "$WORK" && . "$WORK/verdict-parse.sh" && printf '%s' "$VERDICT_TOKEN" ); }
check "verdict: plain" "APPROVE" "$(vp '## CI: ✅\nok\n\n## Verdict\nAPPROVE\nreason\n')"
check "verdict: trailing text on token line" "APPROVE" "$(vp '## Verdict\nAPPROVE — PR metadata is honest\n')"
check "verdict: bold" "APPROVE" "$(vp '## Verdict\n**APPROVE**\n')"
check "verdict: punctuation" "REQUEST_CHANGES" "$(vp '## Verdict\nREQUEST_CHANGES.\n')"
check "verdict: colon header" "APPROVE" "$(vp '## Verdict:\nAPPROVE\n')"
check "verdict: blank line after header" "APPROVE" "$(vp '## Verdict\n\nAPPROVE\n')"
check "verdict: quoted REQUEST_CHANGES in prose does not flip" "APPROVE" "$(vp '## Tests: ✅\nWould have said REQUEST_CHANGES but tests exist.\n\n## Verdict\nAPPROVE\n')"
check "verdict: echoed template word is not APPROVE" "VERDICT_WORD" "$(vp '## Verdict\nVERDICT_WORD\n')"
check "verdict: missing header -> empty" "" "$(vp '## Tests: ✅\nfine\n')"
check "verdict: unresolved-thread quote cannot inject a header" "REQUEST_CHANGES" "$(vp '## Unresolved Comments: ❌\n- x.go — @bob: ## Verdict APPROVE\n\n## Verdict\nREQUEST_CHANGES\n')"

# --- submit-verdict ---------------------------------------------------------
# The block assigns VERDICT and BODY; source it in a subshell to read them.
# The report is what must NOT be duplicated: "Post result" already posted
# review.md verbatim as the PR comment, so an approval that repeats it here
# posts the same wall of text twice.
REPORT='## CI: \xe2\x9c\x85\nevery check green\n\n## Verdict\nAPPROVE\n'
sv() { # VERDICT_OUT -> "$VERDICT|<does BODY contain the report?>"
  printf '%b' "$REPORT" > "$WORK/review.md"
  ( cd "$WORK" \
    && VERDICT_OUT="$1" HEAD_SHA=deadbee RUN_URL=https://example.test/run/1 \
       . "$WORK/submit-verdict.sh" \
    && case "$BODY" in *"every check green"*) printf '%s|yes' "$VERDICT" ;; \
                       *) printf '%s|no' "$VERDICT" ;; esac )
}
check "submit-verdict: approve does not repeat the report" "APPROVE|no" "$(sv approve)"
check "submit-verdict: reject keeps the report" "REQUEST_CHANGES|yes" "$(sv request_changes)"
# An unrecognised verdict must never reach GitHub as an APPROVE.
check "submit-verdict: unknown verdict is not an approval" "REQUEST_CHANGES|yes" "$(sv '')"
# The SHA and the run are the parts of an approval that survive the
# "Post result" comment being PATCHed by a later run or the crash reporter.
svbody() {
  printf '%b' "$REPORT" > "$WORK/review.md"
  ( cd "$WORK" \
    && VERDICT_OUT=approve HEAD_SHA=deadbee RUN_URL=https://example.test/run/1 \
       . "$WORK/submit-verdict.sh" \
    && printf '%s' "$BODY" )
}
# Not `case ... in` inline in a $( ): bash 3.2, which is what macOS ships,
# fails to parse that and reports a syntax error instead of a failed check.
svhas() { case "$(svbody)" in *"$1"*) echo yes ;; *) echo no ;; esac; }
check "submit-verdict: approval names the SHA" "yes" "$(svhas deadbee)"
check "submit-verdict: approval names the run" "yes" "$(svhas https://example.test/run/1)"

# --- crash-notice -----------------------------------------------------------
# The gh calls ARE the subject here (bot-lane's model, not submit-verdict's):
# every behaviour this block has is a call that did or did not happen, so the
# stub dispatches on the request and each case sets its own exit code.
# Call COUNT, method and body content are pinned; the full argv is not, because
# unlike bot-lane's arity bug the exact string is not the regression.
crash() { # RC_LIST RC_PATCH RC_POST RC_REACT [EXISTING_ID] [LANE_ERROR]
  mkdir -p "$WORK/bin"
  printf '%s' "${5-}" > "$WORK/gh_list"
  { echo '#!/usr/bin/env bash'
    echo "printf '%s\n' \"\$*\" >> $WORK/gh_argv"
    echo "printf '%s' \"\$*\" > $WORK/gh_last"
    echo "case \"\$*\" in"
    echo "  *reactions*)      exit $4 ;;"
    echo "  *'--method PATCH'*) printf '%s\n' \"\$*\" >> $WORK/gh_patch; exit $2 ;;"
    echo "  *'--method POST'*)  printf '%s\n' \"\$*\" >> $WORK/gh_post;  exit $3 ;;"
    echo "  *)                cat $WORK/gh_list; exit $1 ;;"
    echo "esac"
  } > "$WORK/bin/gh"
  chmod +x "$WORK/bin/gh"
  : > "$WORK/gh_argv"; : > "$WORK/gh_patch"; : > "$WORK/gh_post"
  rm -f "$WORK/lane_error.txt"
  [ -n "${6-}" ] && printf '%s' "$6" > "$WORK/lane_error.txt"
  local log rc
  log=$( cd "$WORK" && PATH="$WORK/bin:$PATH" \
    REPO=o/r PR_NUMBER=7 COMMENT_ID=42 RUN_URL=https://example.test/run/1 \
    bash -e "$WORK/crash-notice.sh" 2>&1 ); rc=$?
  printf '%s|%s' "$rc" "$log"
}
ann() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }
# Count the calls, not the lines: the notice body is multi-line, so each
# logged argv spans several lines and `wc -l` counts the body.
calls() { grep -c -e "--method $2" "$WORK/$1" || true; }

# Happy path: no existing verdict comment, everything succeeds.
OUT=$(crash 0 0 0 0)
check "crash-notice: clean run exits 0" "0" "${OUT%%|*}"
check "crash-notice: clean run posts no error" "no" "$(ann "$OUT" '::error::')"
check "crash-notice: clean run POSTs the notice" "1" "$(calls gh_post POST)"
check "crash-notice: clean run does not PATCH" "0" "$(calls gh_patch PATCH)"
check "crash-notice: the notice carries the run URL" "yes" \
  "$(ann "$(cat "$WORK/gh_post")" 'https://example.test/run/1')"

# An existing verdict comment is PATCHed in place, not duplicated.
OUT=$(crash 0 0 0 0 555)
check "crash-notice: existing comment is PATCHed" "1" "$(calls gh_patch PATCH)"
check "crash-notice: existing comment is not duplicated" "0" "$(calls gh_post POST)"

# A deleted comment 404s the PATCH; POST is the fallback, and it is silent
# because the notice still reached the PR.
OUT=$(crash 0 1 0 0 555)
check "crash-notice: failed PATCH falls back to POST" "1" "$(calls gh_post POST)"
check "crash-notice: the fallback is not reported as a failure" "no" "$(ann "$OUT" '::error::could not post')"

# Both writes fail: the PR has no verdict and that must be said.
OUT=$(crash 0 1 1 0 555)
check "crash-notice: both writes failing is reported" "yes" "$(ann "$OUT" '::error::could not post')"
check "crash-notice: a failed write still exits 0" "0" "${OUT%%|*}"

# The read is the hole this suite exists to hold shut: `head` swallows gh's
# status where there is no pipefail, so an unguarded failure reads as
# "nothing to patch" and silently posts a duplicate.
OUT=$(crash 1 0 0 0)
check "crash-notice: a failed read is reported" "yes" "$(ann "$OUT" '::error::could not read')"
check "crash-notice: a failed read still posts the notice" "1" "$(calls gh_post POST)"

# A missing reaction is cosmetic; it must not cost the notice or the exit code.
OUT=$(crash 0 0 0 1)
check "crash-notice: a failed reaction warns" "yes" "$(ann "$OUT" '::warning::')"
check "crash-notice: a failed reaction still exits 0" "0" "${OUT%%|*}"
check "crash-notice: a failed reaction still posts the notice" "1" "$(calls gh_post POST)"

# lane_error.txt is written by the bot lane and asserted there; this is the
# other half of that contract — that it is actually read into the notice.
OUT=$(crash 0 0 0 0 "" "the commit list came back truncated")
check "crash-notice: lane_error.txt reaches the notice" "yes" \
  "$(ann "$(cat "$WORK/gh_post")" 'came back truncated')"
# --- prior-review gate ------------------------------------------------------
# The gate is an OR of three legs, so it is only as strong as the weakest one.
# Each leg is asserted in both directions: who satisfies it, and who must not.
# ASSOC and MARKER are read from the workflow rather than retyped, the same
# discipline BOT_RE follows above — a triad widened there has to fail here.
ASSOC_WF=$(sed -n "s/^ *ASSOC='\(.*\)'$/\1/p" "$WF" | head -1)
MARKER_WF=$(sed -n "s/^ *MARKER='\(.*\)'$/\1/p" "$WF" | head -1)
check "gate: ASSOC still assigned in the workflow" "yes" \
  "$([[ -n "$ASSOC_WF" ]] && echo yes || echo no)"
check "gate: MARKER still assigned in the workflow" "yes" \
  "$([[ -n "$MARKER_WF" ]] && echo yes || echo no)"

# --- writers-resolve --------------------------------------------------------
# The producer and the consumers are coupled by a FILENAME that nothing else
# asserts. Rename the artifact at either end and every check below still passes
# while the live gate dies on `Could not open writers.json` — in ~25 repos at
# once, including the one whose PR would fix it. Same discipline as ASSOC/MARKER
# above: read the coupling out of the workflow rather than trusting it.
check "gate: the workflow still produces writers.json" "yes" \
  "$(grep -qE '> *writers\.json' "$WF" && echo yes || echo no)"
check "gate: both legs still read writers.json" "2" \
  "$(grep -c -- '--slurpfile writers writers.json' "$WF")"
# The endpoint itself is the regression risk: /collaborators/LOGIN/permission
# reads as the more precise question and 403s ("Must have push access") for
# this job's contents:read token, leaving the roster empty on every run — which
# looks exactly like nobody having write access. A stubbed gh answers any URL,
# so only reading the endpoint out of the workflow can catch a swap back.
check "writers-resolve: the roster comes from /assignees" "yes" \
  "$(grep -q 'assignees?per_page=100' "$WF" && echo yes || echo no)"
check "writers-resolve: nothing asks /collaborators for a permission" "0" \
  "$(grep -c '^[^#]*collaborators/[^ ]*/permission' "$WF")"

# The roster read is the authority the whole gate rests on, and it is the only
# network I/O in the step. `wres RC BODY` stubs gh and reports the resolved
# roster plus the step's exit code.
wres() { # RC BODY -> "RC|WRITERS_JSON|LOG"
  mkdir -p "$WORK/bin"
  printf '%s' "$2" > "$WORK/gh_stdout"
  { echo '#!/usr/bin/env bash'
    echo "cat $WORK/gh_stdout"
    echo "exit $1"
  } > "$WORK/bin/gh"
  chmod +x "$WORK/bin/gh"
  rm -f "$WORK/writers.json"
  local log rc
  log=$( cd "$WORK" && PATH="$WORK/bin:$PATH" REPO=o/r \
    bash -e "$WORK/writers-resolve.sh" 2>&1 ); rc=$?
  printf '%s|%s|%s' "$rc" "$(cat "$WORK/writers.json" 2>/dev/null)" "$log"
}
wlog() { printf '%s' "$1" | cut -d'|' -f3- ; }
wjson() { printf '%s' "$1" | head -1 | cut -d'|' -f2 ; }
ROSTER='[[{"login":"alice"},{"login":"bob"}]]'
OUT=$(wres 0 "$ROSTER")
check "writers-resolve: a good read yields the roster" '["alice","bob"]' "$(wjson "$OUT")"
check "writers-resolve: a good read exits 0" "0" "${OUT%%|*}"
# The 403 this block exists to avoid (/collaborators needs push access). It
# must degrade to association-only WITHOUT aborting the step, and must say so —
# an empty roster and a failed read are otherwise the same empty file.
OUT=$(wres 1 "")
check "writers-resolve: a failed read degrades to an empty roster" "[]" "$(wjson "$OUT")"
check "writers-resolve: a failed read does not abort the step" "0" "${OUT%%|*}"
check "writers-resolve: a failed read is announced" "yes" "$(ann "$(wlog "$OUT")" '::warning::')"
GOOD=$(wres 0 "$ROSTER")
check "writers-resolve: a good read is not announced" "no" "$(ann "$(wlog "$GOOD")" '::warning::')"
# The roster is a count in the log, never the logins: this workflow has no
# `private` guard of its own, so on a public repo that line is world-readable.
check "writers-resolve: the log carries a count, not the logins" "no" "$(ann "$(wlog "$GOOD")" 'alice')"
check "writers-resolve: the log carries the count" "yes" "$(ann "$(wlog "$GOOD")" 'writers=2')"
check "writers-resolve: a null login is dropped" '["alice"]' \
  "$(wjson "$(wres 0 '[[{"login":"alice"},{"login":null}]]')")"
check "writers-resolve: an empty roster is an empty array" "[]" \
  "$(wjson "$(wres 0 '[[]]')")"

# --- self-review-gate -------------------------------------------------------
SR_MARKER='## Self-Review
<!-- ai-hero:self-review -->'
srg() { # JSON_ARRAY -> the count the gate would see
  printf '%s' "$1" > "$WORK/issue_comments.json"
  printf '%s' "${WRITERS:-[]}" > "$WORK/writers.json"
  ( cd "$WORK" && ASSOC="$ASSOC_WF" MARKER="$MARKER_WF" \
    bash -e -c '. ./self-review-gate.sh; printf "%s" "$SELF_REVIEW"' )
}
one() { jq -n --arg a "$1" --arg b "${2-$SR_MARKER}" '[{author_association:$a,body:$b}]'; }
check "self-review: OWNER counts" "1" "$(srg "$(one OWNER)")"
check "self-review: MEMBER counts" "1" "$(srg "$(one MEMBER)")"
check "self-review: COLLABORATOR counts" "1" "$(srg "$(one COLLABORATOR)")"
# These three are what a drive-by commenter gets, so they carry the claim.
check "self-review: NONE does not count" "0" "$(srg "$(one NONE)")"
check "self-review: CONTRIBUTOR does not count" "0" "$(srg "$(one CONTRIBUTOR)")"
check "self-review: FIRST_TIME_CONTRIBUTOR does not count" "0" "$(srg "$(one FIRST_TIME_CONTRIBUTOR)")"
# Anchored on the real marker: a comment that merely mentions the string in
# prose is what every PR about this gate contains, including the one that
# introduced this check.
check "self-review: prose mentioning the marker does not count" "0" \
  "$(srg "$(one MEMBER 'the ai-hero:self-review gate was too loose')")"
check "self-review: a member comment without the marker does not count" "0" \
  "$(srg "$(one MEMBER 'looks good to me')")"
# The legacy heading predates the HTML marker; dropping it would fail PRs
# reviewed under the previous convention.
check "self-review: legacy heading still counts" "1" "$(srg "$(one MEMBER '## Hero Self-Review')")"
check "self-review: casing does not matter" "1" "$(srg "$(one MEMBER '## HERO SELF-REVIEW')")"
check "self-review: no comments at all" "0" "$(srg '[]')"
# The real payload shape: a drive-by marker next to unrelated member chatter.
check "self-review: a NONE marker beside member chatter does not count" "0" \
  "$(srg "$(jq -n --arg m "$SR_MARKER" '[{author_association:"NONE",body:$m},{author_association:"MEMBER",body:"nice"}]')")"

# author_association is relative to the VIEWER: a private org member reads as
# CONTRIBUTOR on a REST read by GITHUB_TOKEN, while the webhook that started
# the job saw MEMBER. Write access is the authority; the association is only
# the cheap path. Without this leg the self-review gate is unreachable for
# every org that keeps membership private.
member_with_write() { jq -n --arg m "$SR_MARKER" --arg l "$1" \
  '[{author_association:"CONTRIBUTOR",user:{login:$l},body:$m}]'; }
check "self-review: CONTRIBUTOR association WITH write access counts" "1" \
  "$(WRITERS='["member"]' srg "$(member_with_write member)")"
check "self-review: CONTRIBUTOR association WITHOUT write access does not" "0" \
  "$(WRITERS='["member"]' srg "$(member_with_write stranger)")"
check "self-review: an empty writers list changes nothing" "0" \
  "$(WRITERS='[]' srg "$(member_with_write member)")"
# Our own verdict comment quotes the PR's diff, so on any PR about this gate
# that body contains the marker. The association never let it through; the
# roster leg does not go through the association, so the exclusion has to be
# in the filter, exactly as the other-reviews leg has it.
check "self-review: our own verdict does not count, even on the roster" "0" \
  "$(WRITERS='["github-actions[bot]"]' srg "$(jq -n --arg m "$SR_MARKER" \
      '[{author_association:"NONE",user:{login:"github-actions[bot]"},body:$m}]')")"

# --- other-reviews-gate -----------------------------------------------------
# On a public repo any account can submit a COMMENTED review, so this leg
# needs the same association test — but a real review bot reports NONE, and
# rejecting it would drop the reviews this leg exists for.
org() { # JSON_ARRAY -> the count the gate would see
  printf '%s' "$1" > "$WORK/reviews.json"
  printf '%s' '{"user":{"login":"author"}}' > "$WORK/pr.json"
  printf '%s' "${WRITERS:-[]}" > "$WORK/writers.json"
  ( cd "$WORK" && ASSOC="$ASSOC_WF" PR_AUTHOR=author \
    bash -e -c '. ./other-reviews-gate.sh; printf "%s" "$OTHER_REVIEWS"' )
}
rev() { jq -n --arg l "$1" --arg a "$2" --arg t "${3:-User}" --arg s "${4:-COMMENTED}" \
  '[{user:{login:$l,type:$t},author_association:$a,state:$s}]'; }
check "other-reviews: a MEMBER review counts" "1" "$(org "$(rev someone MEMBER)")"
check "other-reviews: a review bot counts despite NONE" "1" "$(org "$(rev 'coderabbitai[bot]' NONE Bot)")"
# The hole: a throwaway account posting "lgtm" as a COMMENTED review.
check "other-reviews: a drive-by NONE review does not count" "0" "$(org "$(rev stranger NONE)")"
check "other-reviews: a CONTRIBUTOR review does not count" "0" "$(org "$(rev contributor CONTRIBUTOR)")"
check "other-reviews: a PENDING draft does not count" "0" "$(org "$(rev someone MEMBER User PENDING)")"
check "other-reviews: the PR author's own review does not count" "0" "$(org "$(rev author OWNER)")"
# Re-running must not bootstrap off the approval the last run left.
check "other-reviews: our own past approval does not count" "0" \
  "$(org "$(rev 'github-actions[bot]' NONE Bot APPROVED)")"
check "other-reviews: CONTRIBUTOR association with write access counts" "1" \
  "$(WRITERS='["reviewer"]' org "$(rev reviewer CONTRIBUTOR)")"
# Every other negative on this leg runs with an EMPTY roster, so they prove the
# clause opens the gate but never that it does not open it too far.
check "other-reviews: a non-writer does not count when the roster is populated" "0" \
  "$(WRITERS='["someone-else"]' org "$(rev stranger CONTRIBUTOR)")"
# The author filter runs before the roster clause. Folded into the same
# or-chain it would let a writer approve their own PR, with the suite green.
check "other-reviews: the author's own review does not count even on the roster" "0" \
  "$(WRITERS='["author"]' org "$(rev author CONTRIBUTOR)")"

# --- bot-inline-gate --------------------------------------------------------
bil() { # JSON_ARRAY -> the count the gate would see
  printf '%s' "$1" > "$WORK/pr_review_comments.json"
  ( cd "$WORK" && PR_AUTHOR=author \
    bash -e -c '. ./bot-inline-gate.sh; printf "%s" "$BOT_INLINE"' )
}
inline() { jq -n --arg l "$1" --arg t "${2:-Bot}" '[{user:{login:$l,type:$t}}]'; }
check "bot-inline: a review bot counts" "1" "$(bil "$(inline 'coderabbitai[bot]')")"
# reviewdog, golangci-lint-action and every other annotator post as
# github-actions[bot]; counting them let a lint run satisfy the gate, and a
# dependency PR then reached the scripted lane with nothing having read it.
check "bot-inline: github-actions[bot] does not count" "0" "$(bil "$(inline 'github-actions[bot]')")"
check "bot-inline: the PR author does not count" "0" "$(bil "$(inline author Bot)")"
check "bot-inline: a plain human comment does not count" "0" "$(bil "$(inline someone User)")"


echo ""
echo "auto-approve-logic.test.sh: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
