# Hero Configuration
<!-- This file configures /hero-* skills. See /hero-init to update. -->

## Project Management
- tool: github-issues
- issue-prefix: none

## Repository
- type: single
- default-branch: main
- branch-convention: github-standard
- commit-convention: conventional

## CI/CD
- platform: none

## Deployment
- platform: none
- registry: none
- argocd: false

## Code Quality
- pre-commit: true

## Projects

### hero-skills
- path: ./
- language: markdown
- framework: claude-code-plugin
- test-command: none
- dev-command: none
