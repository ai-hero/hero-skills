# Skill Audit & Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the hero-skills plugin from 20 skills to 15 by removing/merging low-use skills, rename one, and give every surviving skill a multi-option "Next steps" self-recommendation block so the dev loop is tight and discoverable.

**Architecture:** Fold four skills' logic into three survivors (`push-pr`, `test-changes`, `ship-pr`), delete the merged-away directories plus `plan-work`, rename `respond-to-pr` → `respond-to-comments`, then rewrite every cross-reference across skills + docs + scripts. Finish with a discoverability pass adding "Next steps" blocks everywhere.

**Tech Stack:** Markdown SKILL.md files, bash snippets inside them, `.claude-plugin/*.json` manifests, pre-commit (prettier + JSON/YAML/plugin validation).

## Global Constraints

- **No angle-bracket placeholders in any SKILL.md** — use `UPPER_CASE` tokens instead (pre-commit `prettier` treats `<...>` as broken HTML). (Memory: `feedback_angle_brackets`.)
- **Never silently stash** — the merged `push-pr` commits dirty trees rather than stashing; if any stash path is ever added it needs explicit confirmation + named stash + restore tracking. (Memory: `feedback_stash_guardrails`.)
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (repo convention; the existing `commit-changes` used `Claude <noreply@anthropic.com>` — carry the repo's Opus form into `push-pr`).
- **Customer-facing de-branding (skill-generated output only).** These skills run inside *customer* repos, so anything a skill writes to a customer's git/GitHub must not brand "Hero"/"hero-skills" in any **title, subject, or heading** (customers don't know what "Hero" is). Rules:
  - No `Hero`/`hero-skills` in a generated commit subject, PR title, or PR-comment heading.
  - The visible marker heading `## Hero Self-Review` / `## Hero Self-Review Improvements` becomes neutral (`## Self-Review` / `## Self-Review — Improvements`). The machine marker moves to a **hidden HTML comment** `<!-- ai-hero:self-review -->` (invisible on GitHub) so the grep stays stable while the customer sees nothing branded.
  - Each generated **PR body and PR review comment** ends with exactly one subtle attribution last-line: `_Done with AI Hero skills._` — body/comment only, never a title/heading.
  - This applies to skill *output templates*, **not** to this plugin repo's own commit messages (the tasks in this plan use `feat(push-pr): …` scopes freely — that is internal).
- **Skill names are kebab-case** and must match their directory name and `name:` frontmatter.
- **Final skill set (15):** `init-hero`, `preflight`, `setup-dev`, `create-project`, `create-skill`, `document-arch`, `audit-plugin`, `test-changes`, `push-pr`, `review-pr`, `respond-to-comments`, `ship-pr`, `scan-vulns`, `one-shot`, `reset-branch`.
- **Removed (5):** `commit-changes`, `plan-work`, `check-ci`, `create-branch`, `smoke-ui`.
- **Decisions locked with the user:**
  - `commit-changes` logic → folds into `push-pr` (push now commits-then-pushes).
  - `create-branch` logic → folds into `push-pr` (branch-off-default when needed).
  - `check-ci` **CI-status mode** → folds into `push-pr` (report CI after push).
  - `check-ci` **cluster mode** → folds into `ship-pr` as a **platform-agnostic post-merge deployment-health check** (k8s *or* VM *or* serverless — driven by HERO.md deployment platform).
  - `smoke-ui` → folds into `test-changes` (its frontend smoke step).
  - `plan-work` → removed; `one-shot` plans inline via Plan Mode.
  - `respond-to-pr` → renamed `respond-to-comments`.
  - Self-recommendation = **multiple** next-step options per skill, not a single forced next step.

---

## File Structure

**Skills rewritten (logic absorbed):**

- `skills/push-pr/SKILL.md` — becomes the "finish my work" skill: branch-if-needed → smart-commit → push → draft PR → CI status.
- `skills/test-changes/SKILL.md` — its frontend smoke step absorbs `smoke-ui`'s route-derivation + console allowlist + dev-server lifecycle.
- `skills/ship-pr/SKILL.md` — gains a post-merge deployment-health check.
- `skills/one-shot/SKILL.md` — pipeline shrinks 12 → 10 steps; `plan`/`implement` become inline, `commit`+`push-draft` collapse to `push`, `e2e` folds into `test`.

**Skill renamed:**

- `skills/respond-to-pr/` → `skills/respond-to-comments/` (directory + `name:` field + heading).

**Skills deleted:**

- `skills/commit-changes/`, `skills/plan-work/`, `skills/check-ci/`, `skills/create-branch/`, `skills/smoke-ui/`.

**Docs/scripts touched:**

- `PIPELINES.md` — Pipeline 2 DAG + mapping table.
- `README.md` — prerequisites, quickstart, catalog table.
- `skills/init-hero/SKILL.md` — field-to-skill attribution tables + ASCII summaries.
- `skills/preflight/SKILL.md`, `skills/create-project/SKILL.md`, `skills/setup-dev/SKILL.md` — Next-steps refs.
- `scripts/check-hero-staleness.sh` — the "daily-flow skills" comment.
- Stale-HERO snippet "keep aligned with" comments inside `push-pr`, `test-changes`, `one-shot`.

**Discoverability pass:** every surviving SKILL.md gets/refreshes a "Next steps" block.

---

## Task 1: Rewrite `push-pr` to commit-then-push, branch-if-needed, and report CI

**Files:**

- Modify: `skills/push-pr/SKILL.md` (whole file)
- Source material to lift: `skills/commit-changes/SKILL.md` (Steps 1–10), `skills/create-branch/SKILL.md` (Steps 2–3 branch-from-default), `skills/check-ci/SKILL.md` (CI Mode Steps 1–6)

**Interfaces:**

- Produces: `hero-skills:push-pr` — no-arg default now means *branch-if-on-default → smart-commit any dirty tree → push → draft PR → report CI*. `ready` and target-branch args unchanged. Downstream skills (`review-pr`, `ship-pr`, `one-shot`) still call `hero-skills:push-pr` with the same arg contract.

- [ ] **Step 1: Update frontmatter description**

Replace the `description:` line (keep the `# prettier-ignore` above it) with:

```
description: Commit your work and push it — smart conventional commit, branch off the default branch if needed, then open a draft PR and report CI. Pass `ready` for a non-draft PR, or a branch name to merge into a target.
```

Keep `argument-hint: [ready|target-branch]` and `disable-model-invocation: true`.

- [ ] **Step 2: Add a "Branch if on default" step before push**

Insert a new step after "Step 0: Load Hero Configuration" that reproduces `create-branch` Step 2–3 + `commit-changes` Step 1 branch-guard: if `git branch --show-current` equals the HERO.md `default-branch` (fallback `main`), derive a `{type}/{slug}` branch name from the diff (rules from `create-branch` Step 3), present it, and `git checkout -b` on confirm. Do **not** stash — uncommitted changes follow the checkout. This replaces the old Step 1 "STOP if uncommitted changes exist" gate.

- [ ] **Step 3: Add the smart-commit step (from commit-changes)**

Insert a "Commit dirty changes" step that runs only when `git status --porcelain` is non-empty. Lift `commit-changes` Steps 2–9 verbatim in spirit: pre-commit run, invoke the `simplify` skill (with the inline-checklist fallback), ruthless review, group changesets, conventional commits with the **Opus** `Co-Authored-By` trailer, `Fixes:`/`Relates to:` issue trailers, post-commit pre-push dry-run. If the tree is already clean, skip straight to push.

- [ ] **Step 4: Keep the existing push + PR-creation workflow (A1–A4, B1–B5)**

Leave Workflow A and Workflow B largely intact. Remove the old "run hero-skills:commit-changes first" STOP prompt (Step 3 now handles committing).

- [ ] **Step 5: Append CI-status reporting after a successful push (from check-ci CI Mode)**

After A4 (PR created), add a "Report CI status" step: lift `check-ci` CI-Mode Steps 1–3 (identify repo/branch, `gh run list --branch`, analyze + surface failures) and print a compact CI summary. Poll only briefly (do not block); if runs are still queued, say so and point to re-running. Skip gracefully if `gh` is unavailable.

- [ ] **Step 6: Rewrite the "Next steps" block (multi-option)**

Update the A4 summary's Next steps to the new skill set:

```
Next steps:
  hero-skills:review-pr        # self-review — runs pr-review-toolkit agents, applies fixes, marks ready
  hero-skills:scan-vulns       # if this PR touched dependencies
  hero-skills:ship-pr          # once green — @auto-approve, merge, verify deploy, reset
```

Also, in the generated PR body template (A3, the `gh pr create ... --body` heredoc): keep the title un-branded and append `_Done with AI Hero skills._` as the final body line (per the customer-facing de-branding constraint). Leave the commit-message template with only the `Co-Authored-By` trailer — no "hero" word in commit subjects/bodies.

- [ ] **Step 7: Verify no dangling refs and lint**

Run: `grep -nE "commit-changes|create-branch|check-ci" skills/push-pr/SKILL.md`
Expected: no matches (all folded, not referenced).
Run: `pre-commit run --files skills/push-pr/SKILL.md`
Expected: PASS (prettier clean, no angle brackets).

- [ ] **Step 8: Commit**

```bash
git add skills/push-pr/SKILL.md
git commit -m "$(cat <<'EOF'
feat(push-pr): absorb commit, branch-off-default, and CI-status reporting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Fold `smoke-ui` into `test-changes`

**Files:**

- Modify: `skills/test-changes/SKILL.md` (Step 4 "Frontend App" subsection + Notes)
- Source material: `skills/smoke-ui/SKILL.md` (Steps 1–6)

**Interfaces:**

- Consumes: nothing new.
- Produces: `hero-skills:test-changes frontend [routes...]` now does the full smoke-ui recipe (route derivation from diff, dev-server lifecycle under `.test-output/`, console-error allowlist, screenshots, failure rules). The old thin "navigate + snapshot" Frontend block is replaced.

- [ ] **Step 1: Replace the "Frontend App" smoke subsection**

In Step 4, replace the current Frontend App block (lines ~210–219) with `smoke-ui`'s richer logic: detect UI project heuristically (known-UI / known-non-UI framework lists), confirm/start dev server with PID + `.test-output/dev-server.log` + `.git/info/exclude` handling, derive ≤5 routes from the diff, drive via Playwright MCP, apply the console-noise allowlist, save screenshots under `.test-output/playwright-mcp/`, and apply the failure rules. Preserve `test-changes`'s existing full-stack orchestration (backend-before-frontend).

- [ ] **Step 2: Accept optional routes after `frontend`**

Update the Arguments section: `frontend [routes...]` — trailing tokens are explicit routes (verbatim), matching smoke-ui's `$ARGUMENTS` contract. Update the Examples block accordingly.

- [ ] **Step 3: Merge the relevant Notes**

Fold smoke-ui's Notes about `.test-output/`, never-modifying-tracked-files, and console filtering into `test-changes` Notes. Remove any duplicate.

- [ ] **Step 4: Rewrite the "Next steps" block**

Replace the current block (which points to `smoke-ui` and `commit-changes`) with:

```
Next steps:
  /simplify                    # tidy the dirty diff before committing
  hero-skills:push-pr          # commit and push — opens a draft PR
```

- [ ] **Step 5: Verify and lint**

Run: `grep -nE "smoke-ui|commit-changes" skills/test-changes/SKILL.md`
Expected: no matches.
Run: `pre-commit run --files skills/test-changes/SKILL.md`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/test-changes/SKILL.md
git commit -m "$(cat <<'EOF'
feat(test-changes): absorb smoke-ui into the frontend smoke step

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add platform-agnostic post-merge deployment-health check to `ship-pr`

**Files:**

- Modify: `skills/ship-pr/SKILL.md` (add a step after Step 7b reset; update Step 0 config reads + Next steps)
- Source material: `skills/check-ci/SKILL.md` (Cluster Mode Steps 1–7)

**Interfaces:**

- Consumes: HERO.md **Deployment** section (platform, namespaces, health-check endpoints).
- Produces: `hero-skills:ship-pr` gains a "verify deployment health" phase that runs after a successful merge+reset, generalized beyond Kubernetes.

- [ ] **Step 1: Extend Step 0 config reads**

Add to the "This skill uses" list: `Deployment → platform (kubernetes | vm | serverless | paas | none), namespaces/hosts, health endpoints`.

- [ ] **Step 2: Add "Step 7e: Verify Deployment Health (post-merge)"**

After the reset (7b), add a step that reads the HERO.md deployment platform and dispatches:

- `kubernetes` → lift `check-ci` Cluster Mode (nodes/pods/deployments/ArgoCD) as-is.
- `vm` / `paas` / `serverless` → curl the configured health endpoint(s) and report status; if HERO.md lists none, print a one-line "no health check configured — skipping" and continue.
- `none` or missing → skip silently with `(–)`.

This is **advisory** — a failing health check surfaces loudly but never un-merges. Gate the whole step on a successful merge (`MERGED == true`).

- [ ] **Step 3: Add the health line to the DAG + Summary**

Extend the internal DAG `gates → trigger → verdict → merge → reset` to `... → reset → verify-deploy`. Add a "Deployment: HEALTHY | DEGRADED | skipped" line to the Ship Summary.

- [ ] **Step 4: Update Prerequisites**

Add: "`kubectl`/`argocd` (k8s deploys) or `curl`-reachable health endpoints (VM/PaaS) — only needed if HERO.md declares a deployment platform."

- [ ] **Step 5: Update the "Next steps" block**

Replace `hero-skills:plan-work` (Step 608) and update:

```
Next steps:
  /clear                       # fresh context before the next task (recommended)
  hero-skills:one-shot         # start the next small task ticket-to-merge
  hero-skills:reset-branch     # if you abandoned work mid-flight instead of merging
```

- [ ] **Step 6: Verify and lint**

Run: `grep -nE "check-ci|plan-work|create-branch" skills/ship-pr/SKILL.md`
Expected: no matches (Step 437's `plan-work / create-branch` comment must become `push-pr`).
Run: `pre-commit run --files skills/ship-pr/SKILL.md`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/ship-pr/SKILL.md
git commit -m "$(cat <<'EOF'
feat(ship-pr): add platform-agnostic post-merge deployment-health check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Rename `respond-to-pr` → `respond-to-comments`

**Files:**

- Rename: `skills/respond-to-pr/` → `skills/respond-to-comments/`
- Modify: the renamed `SKILL.md` (`name:` field + `# ...` heading + any self-reference)

**Interfaces:**

- Produces: `hero-skills:respond-to-comments`. Every caller (`one-shot` Step 11, `ship-pr` 7c, `PIPELINES.md`, `README.md`) must switch to the new name (handled in later tasks).

- [ ] **Step 1: Move the directory**

```bash
git mv skills/respond-to-pr skills/respond-to-comments
```

- [ ] **Step 2: Update frontmatter + heading**

In `skills/respond-to-comments/SKILL.md`: set `name: respond-to-comments`; update the H1 heading and any inline `hero-skills:respond-to-pr` self-mentions to `respond-to-comments`. Refresh its "Next steps" block to the new skill set (point to `hero-skills:ship-pr`).

- [ ] **Step 3: Verify and lint**

Run: `grep -rn "respond-to-pr" skills/respond-to-comments/`
Expected: no matches.
Run: `pre-commit run --files skills/respond-to-comments/SKILL.md`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A skills/respond-to-comments skills/respond-to-pr
git commit -m "$(cat <<'EOF'
refactor: rename respond-to-pr to respond-to-comments

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Delete the five removed skills

**Files:**

- Delete: `skills/commit-changes/`, `skills/plan-work/`, `skills/check-ci/`, `skills/create-branch/`, `skills/smoke-ui/`

**Interfaces:**

- Produces: nothing. This task only removes. **It must run AFTER Tasks 6–10** (all reference-fixups) so the repo has zero dangling `hero-skills:*` refs — otherwise the `audit` pre-commit hook blocks the deletion commit. Run the guard grep first.

- [ ] **Step 1: Confirm logic has been absorbed**

Run: `grep -rln "commit-changes\|plan-work\|check-ci\|create-branch\|smoke-ui" skills/push-pr skills/test-changes skills/ship-pr`
Expected: no matches (Tasks 1–3 removed them).

- [ ] **Step 2: Delete the directories**

```bash
git rm -r skills/commit-changes skills/plan-work skills/check-ci skills/create-branch skills/smoke-ui
```

- [ ] **Step 3: Verify remaining references are only in files scheduled for Tasks 6–10**

Run: `grep -rln "commit-changes\|plan-work\|check-ci\|create-branch\|smoke-ui" . --include=*.md --include=*.sh | grep -v node_modules`
Expected: only `README.md`, `PIPELINES.md`, `skills/one-shot/SKILL.md`, `skills/init-hero/SKILL.md`, `skills/preflight/SKILL.md`, `skills/create-project/SKILL.md`, `skills/setup-dev/SKILL.md`, `scripts/check-hero-staleness.sh`. If any *other* file appears, stop and handle it.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: remove merged-away and unused skills (commit-changes, plan-work, check-ci, create-branch, smoke-ui)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Restructure `one-shot` to the new 10-step pipeline

**Files:**

- Modify: `skills/one-shot/SKILL.md`

**Interfaces:**

- Consumes: `hero-skills:test-changes` (now includes e2e), `hero-skills:push-pr` (now commits+pushes), `hero-skills:review-pr`, `hero-skills:respond-to-comments`, `hero-skills:ship-pr`.
- Produces: new DAG `plan → implement → test → simplify → push → self-review → mark-ready → await-review → respond → ship` (10 nodes). `plan`/`implement` are inline; `test` absorbs `e2e`; `push` absorbs `commit`+`push-draft`.

- [ ] **Step 1: Rewrite the Pipeline DAG + progress line**

Change the DAG string everywhere in the file from the 12-node form to:
`plan → implement → test → simplify → push → self-review → mark-ready → await-review → respond → ship`
Update all `[N/12]` markers to `[N/10]` and re-number.

- [ ] **Step 2: Rewrite the step→skill mapping table**

| # | Step | Skill |
|---|------|-------|
| 1 | plan | inline (Plan Mode) |
| 2 | implement | inline |
| 3 | test | `hero-skills:test-changes` (includes UI smoke) |
| 4 | simplify | `/simplify` (external) |
| 5 | push | `hero-skills:push-pr` (commits + pushes draft) |
| 6 | self-review | `hero-skills:review-pr --no-mark-ready` |
| 7 | mark-ready | `hero-skills:review-pr` (Step 9 gate) or `gh pr ready` |
| 8 | await-review | inline poll |
| 9 | respond | `hero-skills:respond-to-comments` |
| 10 | ship | `hero-skills:ship-pr` |

- [ ] **Step 3: Rewrite Step 1 "plan" to be inline**

`plan-work` is gone. Rewrite Step 1 to plan inline: if `$ARGUMENTS` is a Linear/issue ID, fetch it via the Linear MCP (lift `plan-work` Step 2); otherwise treat as a description. Then EnterPlanMode, draft, ExitPlanMode on approval. Keep the existing scope-check-after-planning gate.

- [ ] **Step 4: Collapse old Steps 4/6/7**

Delete the standalone `e2e` step (Step 4) — its behavior now lives inside `test-changes`; note in Step 3 that `test-changes` skips UI smoke with `(–)` on backend-only PRs. Collapse old Step 6 (`commit`) and Step 7 (`push-draft`) into a single `push` step calling `hero-skills:push-pr` (no args → commits + draft PR). Renumber self-review/mark-ready/await-review/respond/ship to 6–10.

- [ ] **Step 5: Update Step 0.5 resume decision tree**

The resume table references step numbers and the `commit`/`e2e` nodes. Re-map: "mid-implement, UNCOMMITTED>0" → resume at Step 3 (test); "committed but not pushed" → resume at Step 5 (push). Update every `Step N` label and DAG render in the table + examples to the 10-step numbering. Update the `respond-to-pr` reference to `respond-to-comments`.

- [ ] **Step 6: Update prose refs + Notes**

Replace all `hero-skills:plan-work`, `hero-skills:commit-changes`, `hero-skills:smoke-ui`, `hero-skills:respond-to-pr`, `hero-skills:create-branch` mentions with their new homes/names. Update the stale-HERO snippet comment "Keep aligned with the copies in commit-changes/push-pr/plan-work/test-changes" → "...in push-pr/test-changes".

- [ ] **Step 7: Verify and lint**

Run: `grep -nE "plan-work|commit-changes|smoke-ui|create-branch|respond-to-pr|\[.*/12\]|→ e2e →|→ commit →" skills/one-shot/SKILL.md`
Expected: no matches.
Run: `pre-commit run --files skills/one-shot/SKILL.md`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add skills/one-shot/SKILL.md
git commit -m "$(cat <<'EOF'
refactor(one-shot): 12→10 step pipeline; inline plan, test absorbs e2e, push absorbs commit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Update `PIPELINES.md` Pipeline 2

**Files:**

- Modify: `PIPELINES.md` (Pipeline 2 section, lines ~55–93)

**Interfaces:**

- Consumes: the new one-shot DAG from Task 6 (must match exactly).

- [ ] **Step 1: Rewrite the Pipeline 2 DAG and mapping table**

Replace the 12-step DAG string and its 12-row table with the 10-step version from Task 6 Step 2. Update the surrounding prose: the `e2e` paragraph becomes "UI smoke runs inside `test`; backend-only PRs skip it"; the `commit`/`push-draft` split paragraph is removed; keep the `mark-ready`/`await-review` split rationale. Replace `hero-skills:respond-to-pr` → `hero-skills:respond-to-comments`, `hero-skills:plan-work` → "inline (Plan Mode)", `hero-skills:commit-changes`/`hero-skills:smoke-ui` per their merges.

- [ ] **Step 2: Verify and lint**

Run: `grep -nE "plan-work|commit-changes|smoke-ui|check-ci|create-branch|respond-to-pr" PIPELINES.md`
Expected: no matches.
Run: `pre-commit run --files PIPELINES.md`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add PIPELINES.md
git commit -m "$(cat <<'EOF'
docs(pipelines): update Pipeline 2 to the 10-step one-shot DAG

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Update `init-hero` field-to-skill attribution

**Files:**

- Modify: `skills/init-hero/SKILL.md` (lines ~50–56, ~558–568, ~580–701, ~832, ~948–953)

**Interfaces:**

- Consumes: the final skill set. init-hero documents which HERO.md fields each skill consumes; that mapping must reflect the merges.

- [ ] **Step 1: Re-attribute the field tables**

- `commit-changes` field rows (commit convention, pre-commit, issue prefix) → attribute to `push-pr`.
- `plan-work` field rows (PM tool/MCP, branch template, issue prefix, project list) → attribute to `one-shot` (planning is now inline there). Keep the fields; only the consumer name changes.
- `check-ci` CI rows (CI platform, workflow names, registry, required checks) → attribute to `push-pr`.
- `check-ci cluster` rows (deployment platform, namespaces, ArgoCD, health endpoints) → attribute to `ship-pr`.

- [ ] **Step 2: Rewrite the grouped ASCII summaries**

Update Group headings + `Used by:` lines (558–607) and the plain-text summary blocks (639–701, 948–953):

- Group 1 "committing and pushing" → `hero-skills:push-pr`, `hero-skills:ship-pr` (drop `commit-changes`).
- Group 2 "planning and tracking" → `hero-skills:one-shot` (drop `plan-work`).
- Group 4 "CI/CD and deployment" → `hero-skills:push-pr` (CI), `hero-skills:ship-pr` (deploy health), `hero-skills:scan-vulns` (drop `check-ci`/`check-ci cluster`).
- Line 832 `linear ... for hero-skills:plan-work` → `for hero-skills:one-shot issue planning`.
- Lines 948–953 example block → same substitutions.

- [ ] **Step 3: Verify and lint**

Run: `grep -nE "commit-changes|plan-work|check-ci|create-branch|smoke-ui" skills/init-hero/SKILL.md`
Expected: no matches.
Run: `pre-commit run --files skills/init-hero/SKILL.md`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add skills/init-hero/SKILL.md
git commit -m "$(cat <<'EOF'
docs(init-hero): re-attribute HERO.md fields to the consolidated skill set

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Update remaining cross-references (preflight, create-project, setup-dev, staleness script)

**Files:**

- Modify: `skills/preflight/SKILL.md:93`, `skills/create-project/SKILL.md:249,272`, `skills/setup-dev/SKILL.md:169`, `scripts/check-hero-staleness.sh:17`

**Interfaces:**

- Consumes: the final skill set.

- [ ] **Step 1: preflight**

Line 93: `hero-skills:plan-work # …or start with Step 1 alone` → `hero-skills:one-shot` (or `hero-skills:push-pr` if the comment is about pushing — choose by context; it is about starting work, so `one-shot`).

- [ ] **Step 2: create-project**

Line 249: `defer the commit to hero-skills:commit-changes` → `hero-skills:push-pr`.
Line 272: `hero-skills:plan-work # Steps 1–2 — plan and implement the first task` → `hero-skills:one-shot # plan and implement the first task`.

- [ ] **Step 3: setup-dev**

Line 169: `needed for hero-skills:plan-work to manage issues` → `needed for hero-skills:one-shot to fetch issues`.

- [ ] **Step 4: check-hero-staleness.sh**

Line 17 comment `the daily-flow skills (commit-changes / push-pr / plan-work / test-changes)` → `(push-pr / test-changes)`.

- [ ] **Step 5: Verify and lint**

Run: `grep -rnE "commit-changes|plan-work|check-ci|create-branch|smoke-ui" skills/preflight skills/create-project skills/setup-dev scripts/check-hero-staleness.sh`
Expected: no matches.
Run: `pre-commit run --files skills/preflight/SKILL.md skills/create-project/SKILL.md skills/setup-dev/SKILL.md scripts/check-hero-staleness.sh`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/preflight/SKILL.md skills/create-project/SKILL.md skills/setup-dev/SKILL.md scripts/check-hero-staleness.sh
git commit -m "$(cat <<'EOF'
docs: repoint stragglers to the consolidated skill set

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Update `README.md`

**Files:**

- Modify: `README.md` (lines ~49, ~83, ~99–111, ~139–149, ~171–197)

**Interfaces:**

- Consumes: final skill set + new one-shot DAG.

- [ ] **Step 1: Prerequisites**

Line 49: `push-pr, review-pr, respond-to-pr, and ship-pr` → `respond-to-comments`.
Line 83: `browser smoke test in hero-skills:smoke-ui (Step 4 e2e)` → `hero-skills:test-changes (frontend smoke)`.

- [ ] **Step 2: Quickstart block (99–111)**

Rewrite to the 10-step flow: drop the `plan-work`/`smoke-ui`/`commit-changes` lines, add `hero-skills:push-pr` as the commit+push line, rename `respond-to-pr` → `respond-to-comments`, renumber the step comments to match Task 6.

- [ ] **Step 3: One-shot mapping table (139–149)**

Update rows to the 10-step table (plan=inline, e2e folded into test, commit folded into push, respond=respond-to-comments).

- [ ] **Step 4: Skill catalog table (171–197)**

- Remove rows: `plan-work`, `create-branch`, `commit-changes`, `smoke-ui`, `check-ci`.
- Rename row: `respond-to-pr` → `respond-to-comments`.
- Update `push-pr` row description to "commit + push + draft PR + CI status".
- Update `test-changes` row to mention UI smoke.
- Update `ship-pr` row to mention post-merge deploy-health.
- Confirm the table lists exactly the 15 surviving skills.

- [ ] **Step 5: Verify and lint**

Run: `grep -nE "plan-work|create-branch|commit-changes|smoke-ui|check-ci|respond-to-pr" README.md`
Expected: no matches.
Run: `pre-commit run --files README.md`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(readme): reflect the consolidated 15-skill set and 10-step pipeline

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Discoverability pass — "Next steps" on every surviving skill

**Files:**

- Modify: the SKILL.md of each of the 15 survivors that lacks a multi-option "Next steps" block (verify each): `init-hero`, `preflight`, `setup-dev`, `create-project`, `create-skill`, `document-arch`, `audit-plugin`, `reset-branch`, `scan-vulns`, `review-pr` (plus the four already edited in Tasks 1–4 if their blocks still need widening).

**Interfaces:**

- Produces: each skill ends with a `Next steps:` block offering **2–3 context-relevant** follow-ups (not one forced step), so the loop self-advances and skills stay discoverable.

- [ ] **Step 1: Audit which skills already have the block**

Run: `for f in skills/*/SKILL.md; do echo "== $f"; grep -c "Next steps" "$f"; done`
Note which are 0.

- [ ] **Step 2: Add a block to each skill missing one**

For each, append (or fold into the existing summary) a `Next steps:` block with the natural follow-ups. Suggested pairings:

- `init-hero` → `hero-skills:setup-dev`, `hero-skills:one-shot`.
- `setup-dev` → `hero-skills:one-shot`, `hero-skills:preflight`.
- `create-project` → `hero-skills:setup-dev`, `hero-skills:one-shot`.
- `preflight` → `hero-skills:one-shot`, `hero-skills:test-changes`.
- `create-skill` → `hero-skills:audit-plugin`, `hero-skills:push-pr`.
- `document-arch` → `hero-skills:push-pr`.
- `audit-plugin` → `hero-skills:push-pr`.
- `reset-branch` → `hero-skills:one-shot`.
- `scan-vulns` → `hero-skills:push-pr`, `hero-skills:ship-pr`.
- `review-pr` → `hero-skills:respond-to-comments`, `hero-skills:ship-pr`.

Keep them short (≤3 lines), use real skill names only, and match the existing "Next steps:" phrasing already used in the pipeline skills.

- [ ] **Step 3: Verify and lint**

Run: `for f in skills/*/SKILL.md; do grep -q "Next steps" "$f" || echo "MISSING: $f"; done`
Expected: no MISSING lines.
Run: `pre-commit run --files skills/*/SKILL.md`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add skills
git commit -m "$(cat <<'EOF'
feat(skills): add multi-option Next steps blocks for discoverability

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: De-brand customer-facing output & stabilize the self-review marker

**Files:**

- Modify: `skills/review-pr/SKILL.md` (comment headings ~140, ~224; the review/body templates ~208, ~265, ~382), `skills/ship-pr/SKILL.md:124` (marker grep), `skills/one-shot/SKILL.md:284,293,347` (marker grep + prose), `skills/push-pr/SKILL.md` (PR body attribution — may already be done in Task 1), `skills/respond-to-comments/SKILL.md` (comment/body attribution ~232,323,350)

**Interfaces:**

- Consumes: the final self-review marker string `<!-- ai-hero:self-review -->`.
- Produces: no customer-visible "Hero" branding in generated commits/PRs/comments; a hidden, stable marker that `ship-pr` and `one-shot` grep for; a subtle attribution last-line on generated bodies/comments.

> Run this task AFTER Tasks 1, 3, 4, and 6 have settled `push-pr`, `ship-pr`, `respond-to-comments`, and `one-shot`, so it edits their final content. All grep sites must agree on the single marker string in Global Constraints regardless of task order.

- [ ] **Step 1: Neutralize review-pr comment headings + add hidden marker**

In `skills/review-pr/SKILL.md`: change the visible heading `## Hero Self-Review` (~140) to `## Self-Review` and `## Hero Self-Review Improvements` (~224) to `## Self-Review — Improvements`. Immediately below each heading line (inside the heredoc), add the hidden marker line `<!-- ai-hero:self-review -->`. This keeps a machine-detectable anchor while the customer sees only "Self-Review".

- [ ] **Step 2: Add attribution last-line to review-pr generated comments/body**

Append `_Done with AI Hero skills._` as the final line of each `gh pr comment`/`gh pr edit --body`/`gh pr review --body` heredoc in review-pr (~139, ~223, ~265, ~382). Standardize the `Co-Authored-By` trailer to `Claude Opus 4.8 <noreply@anthropic.com>` (~208).

- [ ] **Step 3: Update the marker greps in ship-pr and one-shot**

`skills/ship-pr/SKILL.md:124` — change `test("Hero Self-Review"; "i")` to match the hidden marker: `test("ai-hero:self-review")`.
`skills/one-shot/SKILL.md:293` — same substitution. Update the comment (~284) and the reasoning prose (~347) from "Hero Self-Review marker" to "self-review marker".

- [ ] **Step 4: Add attribution to push-pr and respond-to-comments output**

Confirm push-pr's PR body ends with `_Done with AI Hero skills._` (from Task 1 Step 6; add if missing). In `respond-to-comments`, append the same attribution last-line to its generated PR comment and PR-body-edit heredocs (~323, ~350), and standardize its `Co-Authored-By` trailer (~232) to the Opus form.

- [ ] **Step 5: Verify no customer-facing "Hero" and marker consistency**

Run: `grep -rniE "## Hero|Hero Self-Review" skills/`
Expected: no matches.
Run: `grep -rn "ai-hero:self-review" skills/review-pr skills/ship-pr skills/one-shot`
Expected: emitted once each in review-pr's two comment templates and grepped for in ship-pr + one-shot — all agree on the same string.
Run: `pre-commit run --files skills/review-pr/SKILL.md skills/ship-pr/SKILL.md skills/one-shot/SKILL.md skills/push-pr/SKILL.md skills/respond-to-comments/SKILL.md`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills
git commit -m "$(cat <<'EOF'
refactor: de-brand customer-facing skill output; hide the self-review marker

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Final validation

**Files:**

- No edits unless validation surfaces a gap.

- [ ] **Step 1: Global dangling-reference sweep**

Run: `grep -rnE "commit-changes|plan-work|check-ci|create-branch|smoke-ui|respond-to-pr" . --include=*.md --include=*.sh --include=*.json | grep -v node_modules | grep -v docs/superpowers/plans`
Expected: no matches anywhere in shipped files.
Run: `grep -rniE "## Hero|Hero Self-Review" skills/`
Expected: no matches (customer-facing de-branding, Task 12).

- [ ] **Step 2: Confirm exactly 15 skills**

Run: `ls -d skills/*/ | wc -l`
Expected: `15`.
Run: `ls skills`
Expected: the 15 names from Global Constraints, no more.

- [ ] **Step 3: Run the plugin's own audit**

Invoke `hero-skills:audit-plugin` (or the Skill tool) to check skill quality, consistency, DRY, HERO.md field coverage, and readability across the new set. Fix anything it flags.

- [ ] **Step 4: Full pre-commit + plugin validation**

Run: `pre-commit run --all-files`
Expected: PASS (prettier, JSON/YAML/plugin validation from `.github` PR check).

- [ ] **Step 5: Verify one-shot DAG consistency**

Run: `grep -o "\[[0-9]*/10\]" skills/one-shot/SKILL.md | sort -u`
Expected: only `[1/10]`..`[10/10]`, no `/12`.
Confirm the DAG node strings in `one-shot` and `PIPELINES.md` are byte-identical.

- [ ] **Step 6: Commit any validation fixes**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: final validation fixes for the skill consolidation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage:**

- Remove 5 skills → Task 5. ✓
- Merge commit-changes/create-branch/check-ci(CI) → push-pr → Task 1. ✓
- Merge smoke-ui → test-changes → Task 2. ✓
- Merge check-ci(cluster) → ship-pr, platform-agnostic → Task 3. ✓
- Rename respond-to-pr → respond-to-comments → Task 4. ✓
- one-shot restructure + PIPELINES + init-hero + README + stragglers → Tasks 6–10. ✓
- Multi-option Next steps everywhere → Task 11. ✓
- Customer-facing de-branding + hidden self-review marker + attribution → Task 12. ✓
- Validation → Task 13. ✓

**2. Placeholder scan:** Reference-swap tasks name exact files, line anchors, and old→new strings. The three content-move tasks (1–3) point to the exact source sections to lift rather than re-pasting hundreds of lines — acceptable because the source files still exist in git history at execution time (deletion is Task 5, after Tasks 1–3). Executors must Read the cited source sections.

**3. Type consistency:** Skill names are used identically throughout: `respond-to-comments` (not `respond-to-pr`), `push-pr` as the commit+push home, `test-changes` as the smoke home, `ship-pr` as the deploy-health home. The one-shot DAG node names (`plan, implement, test, simplify, push, self-review, mark-ready, await-review, respond, ship`) are identical in Tasks 6 and 7.

**Ordering note (CORRECTED after Task 5 hit the audit hook):** The `audit` pre-commit hook validates `hero-skills:*` references repo-wide on every commit, so the repo must never be committed with a dangling reference. Therefore the reference-fixup tasks run BEFORE the deletion:

- Tasks 1–4 first (lift logic into survivors; skills still present, all refs valid).
- Then Tasks 6–10 (repoint every reference away from the to-be-removed skills — valid because those skills still exist on disk).
- Then Task 5 (delete the 5 skills — now that nothing references them, the audit passes). Task 6 may still READ `plan-work`/etc. to lift inline logic, which is why deletion is last.
- Then Task 11 (Next steps), Task 12 (de-branding, after Tasks 1/3/4/6 settled their files), Task 13 (validation) last.

Execution order: **1, 2, 3, 4, 6, 7, 8, 9, 10, 5, 11, 12, 13.**
