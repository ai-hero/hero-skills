# Hero Configuration
<!-- This file configures /hero-* skills. See /hero-init to update. -->

## Project Management

- tool: github-issues
- issue-prefix: none
- issue-tracker: github

## Repository

- type: single
- default-branch: main
- branch-convention: github-standard
- commit-convention: conventional

## CI/CD

- platform: github-actions
- workflows: claude-pr-approve

## Deployment

- platform: none
- registry: none
- argocd: false

## Coding Agent

- agent: claude-code
- config: .claude/

## Code Review Agent

- agent: github copilot

## Code Quality

- pre-commit: true
- linters: markdownlint, shellcheck, codespell
- hooks: detect-secrets, validate-plugin, hero-meta, hero-init-update

## Projects

### hero-skills

- path: ./
- language: markdown
- framework: claude-code-plugin
- test-command: none
- dev-command: none
