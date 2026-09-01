# Hero Configuration
<!-- This file configures hero-skills. See hero-skills:init-hero to update. -->

## Project Management

- tool: github-issues
- issue-prefix: none
- issue-tracker: github

## Repository

- type: single
- default-branch: main
- branch-convention: github-standard
- commit-convention: conventional
- merge-method: squash
- auto-delete-branches: true
- task-runner: just

## CI/CD

- platform: github-actions
- workflows: auto-approve
- auto-approve-installed: true
- auto-approve-gates: prior-review-required, all-threads-resolved, claude-metadata-check

## Deployment

- platform: none
- registry: none
- argocd: false

## Coding Agent

- agent: claude-code
- config: .claude/

## Code Review Agent

<!-- No external review bot posts to PRs here (checked #68-#72: only
     github-actions[bot], which is this repo's own auto-approve workflow).
     `agent: none` — not a made-up value — is what tells one-shot's Step 7
     to skip the bot-await poll; self-review already runs as one-shot's own
     Step 5 via hero-skills:review-pr regardless of this field. -->
- agent: none
- trigger: none
- poll-method: none
- bot-username: none

## Code Quality

- pre-commit: true
- linters: markdownlint, shellcheck, codespell
- hooks: detect-secrets, validate-plugin, audit, shell-unit-tests, agents-md, agents-md-commit-msg

## Wayfare

- source-repo: .
- design-project: none # PERMANENT — hero-skills is a plugin repo with no product and no UI (per AGENTS.md); it will never have a claude.ai/design app-design project. Do not re-propose at sync
- design-transport: auto # auto | designsync | manual — unused while design-project is permanently none, but still validated by sync's config gate, so keep it one of the three valid words
- feedback-repo: none # OWNER/NAME GitHub repo where design-feedback issues are filed; none keeps feedback in local packets
- ux-flow: none # no design-project (permanent) — no UX flow path to point at
- design-system-repo: none # no fleet folder or sibling checkout with `role: producer` under `## Design System` found
- reconciliation: none # no design-project (permanent)

## Projects

### hero-skills

- path: ./
- language: markdown
- framework: claude-code-plugin
- test-command: none
- dev-command: none
