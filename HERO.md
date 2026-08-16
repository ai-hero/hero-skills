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

- agent: copilot

## Code Quality

- pre-commit: true
- linters: markdownlint, shellcheck, codespell
- hooks: detect-secrets, validate-plugin, audit, init-update

## Wayfare

- source-repo: .
- design-project: none # set to a claude.ai/design link or project UUID to enable the target substrate; `ask` prompts for the link each session; under design-transport manual, none is allowed (the snapshot you fill is the target)
- design-transport: auto # auto | designsync | manual — manual = you carry exported design files into the local snapshot (two-account setups)
- feedback-repo: none # OWNER/NAME GitHub repo where design-feedback issues are filed; none keeps feedback in local packets

## Projects

### hero-skills

- path: ./
- language: markdown
- framework: claude-code-plugin
- test-command: none
- dev-command: none
