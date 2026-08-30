#!/usr/bin/env bash

# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# The map of which skill is driven by which config fields, and what each
# field decides for that skill. The read-only first phase of every skill's
# `recalibrate` verb — see docs/RECALIBRATE.md.
#
# Usage:
#   scripts/hero-fields.sh SKILL [ROOT]   rows for one skill, with values read
#                                         from ROOT (default: the repo root)
#   scripts/hero-fields.sh --list         skill names that have a map entry
#   scripts/hero-fields.sh --all          every row, no values read
#
# Output is TSV with a header: SECTION KEY CURRENT DECIDES.
# KEY `*` means the whole section, and CURRENT is then `present` / `absent`.
# CURRENT is `unset` for a field the file does not carry and `refused` for one
# the reader rejected as unsafe — the two are different findings, and
# collapsing them would send `recalibrate` to ask about a field that is
# actually set to something dangerous.
#
# Exit: 0 rows printed, 2 unknown skill.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$HERE/hero-lib.sh" || { echo "hero-fields: cannot source hero-lib.sh" >&2; exit 1; }

# SKILL|SECTION|KEY|DECIDES
#
# One row per field a skill actually reads. A field listed here that no skill
# reads, or read by a skill and missing here, is what audit-plugin's HERO.md
# field-coverage pass reports: this map is the claim, the skills are the truth.
#
# Emitted by a function, not assigned through `MAP=$(cat <<'ROWS' ... )`: a
# here-doc nested in a command substitution makes bash scan the body for shell
# quotes, and the first apostrophe in a prose cell ("the bot's") becomes an
# unterminated string that fails the whole script at parse time.
rows() {
  cat <<'ROWS'
init-hero|*|*|every section — the only whole-file pass
architecture|Repository|type|single or monorepo, which decides whether one DESIGN.md covers the repo
architecture|Deployment|platform|the deploy shape the boundaries and invariants must hold under
architecture|Projects|*|the project list, and in a monorepo which one the file describes
push-pr|Repository|default-branch|the branch to cut from and the PR base
push-pr|Repository|branch-convention|the shape of the branch name it creates
push-pr|Repository|commit-convention|the shape of the commit message it writes
push-pr|Project Management|issue-prefix|the ticket ID in the branch name and the PR trailers
push-pr|Code Quality|pre-commit|whether the commit step expects hooks to run and re-stage
push-pr|Code Quality|linters|the static checks the verify phase runs
push-pr|CI/CD|platform|where the post-push CI status report is read from
push-pr|Projects|*|per project: language, framework, install/test/dev commands, port — the test phase falls back to auto-detection without them
ship-pr|Repository|default-branch|what the branch resets to after the merge
ship-pr|Repository|merge-method|squash, rebase, or merge — the button this skill presses
ship-pr|Repository|auto-delete-branches|whether ship deletes the head branch itself after merging
ship-pr|CI/CD|auto-approve-installed|whether `@auto-approve` will do anything at all
ship-pr|CI/CD|auto-approve-gates|the gates the approval verdict is expected to enforce
ship-pr|Deployment|platform|whether there is a deploy to verify after the merge
ship-pr|Deployment|registry|where the built image is expected to land
ship-pr|Deployment|argocd|whether the deploy is GitOps-synced rather than pushed
one-shot|Repository|default-branch|the base for every step of the pipeline
one-shot|Repository|branch-convention|the branch the goal's work lands on
one-shot|Project Management|tool|where the ticket is fetched from
one-shot|Project Management|issue-prefix|how a plain-text argument is recognized as a ticket ID
one-shot|Project Management|issue-tracker|where the issue is closed out after the merge
one-shot|Code Review Agent|agent|which bot's review the await-review step waits for
one-shot|Code Review Agent|bot-username|whose comments count as the bot's, and whose do not
one-shot|CI/CD|auto-approve-installed|whether the ship step can complete
one-shot|Projects|*|per project: test and dev commands the build and verify steps use
review-pr|Repository|default-branch|the base the diff under review is taken against
review-pr|Code Quality|linters|the checks a finding must not simply restate
review-pr|Coding Conventions|*|the conventions a review judges the code against, instead of inventing house style
review-pr|Projects|*|per project: language and framework, which decide the review's focus
respond-to-comments|Code Review Agent|agent|which reviewer's threads this skill answers
respond-to-comments|Code Review Agent|bot-username|whose comments are the bot's, for the poll and the resolve
respond-to-comments|Code Review Agent|trigger|how the bot's review is requested
respond-to-comments|Code Review Agent|poll-method|how this skill knows the review has landed
respond-to-comments|Repository|default-branch|the base for the diff a comment is read against
respond-to-comments|Projects|*|per project: the test command run after a fix
wayfare|Wayfare|source-repo|the codebase reconciled against the design
wayfare|Wayfare|design-project|the target design substrate, or none
wayfare|Wayfare|design-transport|how design files reach the local snapshot
wayfare|Wayfare|feedback-repo|where design feedback is filed, or none for local packets
wayfare|Wayfare|ux-flow|the authoritative journey the codebase is reconciled against
wayfare|Wayfare|design-system-repo|the registry the UI work sources primitives from
wayfare|Wayfare|reconciliation|how far a sync is allowed to go on its own
wayfare|Repository|default-branch|the base for every PR the goal turns open
harden|Deployment|platform|whether there are images and manifests to scan
harden|Deployment|registry|where the image being scanned is pulled from
harden|Code Quality|linters|the security checks already in the gate, which the audit must not duplicate
harden|Projects|*|per project: language and dependency file, which decide the CVE scanners
recomponentize-ui|Design System|role|producer refuses the run; consumer is what the pass is for
recomponentize-ui|Design System|namespace|the registry prefix components are sourced under
recomponentize-ui|Design System|registry-url|where the registry is fetched from
recomponentize-ui|Design System|token-env|the env var holding the registry token
recomponentize-ui|Projects|*|per project: the framework, which decides whether there is a UI at all
abandon|Repository|default-branch|what the tree resets to once the work is discarded
abandon|Repository|branch-convention|which branches are this pipeline's to discard
preflight|Repository|default-branch|the branch every readiness check is made against
preflight|CI/CD|auto-approve-installed|whether the ship step will be a no-op
preflight|Code Quality|pre-commit|whether the gate is installed and current
setup-dev|Developer Setup|*|required tools, recommended tools, and MCP servers — the checklist this skill walks
setup-dev|Projects|*|per project: install and dev commands the setup verifies
create-project|Repository|type|single or monorepo, which decides where the new project is scaffolded
create-project|Design System|namespace|the registry a scaffolded UI is wired to
create-project|Projects|*|the existing projects a new one must not collide with
create-skill|Projects|*|per project: language and framework, which the new skill's examples follow
handoff|Project Management|tool|where the distilled work-item is filed
handoff|Project Management|issue-tracker|the tracker the item is created in
handoff|Project Management|issue-prefix|the ID shape the item is named with
ROWS
}

usage() { sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; }

case "${1:-}" in
  ''|-h|--help) usage; exit 0 ;;
  --list) rows | cut -d'|' -f1 | sort -u; exit 0 ;;
  --all)
    printf 'SKILL\tSECTION\tKEY\tDECIDES\n'
    rows | tr '|' '\t'
    exit 0 ;;
esac

SKILL="$1"
ROOT="${2:-$(hero_root)}"

SKILL_ROWS=$(rows | grep "^$SKILL|" || true)
if [ -z "$SKILL_ROWS" ]; then
  echo "hero-fields: no map entry for '$SKILL' — run --list for the skills that have one" >&2
  exit 2
fi

printf 'SECTION\tKEY\tCURRENT\tDECIDES\n'
printf '%s\n' "$SKILL_ROWS" | while IFS='|' read -r _skill section key decides; do
  target="$ROOT/HERO.md"

  if [ ! -r "$target" ]; then
    current="no-file"
  elif [ "$key" = '*' ]; then
    if [ "$section" = '*' ] || grep -q "^## ${section}[[:space:]]*$" "$target"; then
      current="present"
    else
      current="absent"
    fi
  else
    current=$(hero_md_field "$target" "$key" "## $section" 2>/dev/null)
    case "$?" in
      0) : ;;
      2) current="refused" ;;
      *) current="unset" ;;
    esac
    [ -n "$current" ] || current="unset"
  fi

  printf '%s\t%s\t%s\t%s\n' "$section" "$key" "$current" "$decides"
done
