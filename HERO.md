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
- target-repo: none # set to OWNER/NAME, a local path, or a git URL to enable the target substrate
- target-branch: main
- target-path: none # optional subtree holding the target design

## Projects

### hero-skills

- path: ./
- language: markdown
- framework: claude-code-plugin
- test-command: none
- dev-command: none
