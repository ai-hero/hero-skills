---
name: hero-setup
# prettier-ignore
description: Set up a developer's local environment for a project. Reads HERO.md for required tools, checks what's installed, guides through git config, CLI auth, and missing dependencies. Per-developer — does not modify shared files.
argument-hint: [--check]
---

# Hero Setup - Developer Environment Setup

Guide an individual developer through setting up their local environment based on the team's `HERO.md` configuration. This skill handles everything that is per-developer and should NOT be committed to the repo.

## Arguments

- `$ARGUMENTS`:
  - (none) — Full guided setup
  - `--check` — Just verify current setup, report what's missing

## Prerequisites

`HERO.md` must exist. If it doesn't, tell the user:

```
No HERO.md found. Run /hero-init first to configure the project.
```

## Instructions

### Step 1: Read HERO.md

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md"
```

Parse the `## Developer Setup` section for required tools, recommended tools, and MCP servers. Also read other sections for implicit requirements (e.g., CI platform → `gh`, deployment platform → `kubectl`).

### Step 2: Check Git Configuration

```bash
# Local git config
git config --local user.name
git config --local user.email

# Global fallback
git config --global user.name
git config --global user.email

# Signing
git config --local commit.gpgsign
git config --global commit.gpgsign
git config --local gpg.format

# Remote
git remote -v
```

**Present findings:**

```
GIT CONFIGURATION
─────────────────
[OK] user.name: "Jane Doe" (global)
[OK] user.email: "jane@company.com" (global)
[--] No local git config — using global values
     → Set local config for this repo? (useful if you use a different
       email for work vs personal projects)
[--] Commit signing: not configured
     → Set up GPG/SSH signing? (recommended for verified commits)
```

**If local config is missing**, offer to set it:

```bash
git config --local user.name "<name>"
git config --local user.email "<email>"
```

Ask the user — never auto-set identity config without confirmation.

### Step 3: Check Required CLI Tools

For each tool in HERO.md `## Developer Setup → Required Tools`:

```bash
which <tool> 2>/dev/null && <tool> --version 2>/dev/null
```

**Present findings:**

```
REQUIRED TOOLS
──────────────
[OK] node: v20.11.0 (required: >=20) ✓
[OK] pnpm: 9.1.0 ✓
[OK] docker: 24.0.7 ✓
[!!] gh: not installed
     → Required for PR workflows. Install: brew install gh
[!!] tofu: not installed
     → Required for infrastructure. Install: brew install opentofu
     ⚠ Do NOT install terraform — this project uses OpenTofu
```

For missing tools, provide **platform-appropriate install commands**:

- macOS: `brew install <tool>`
- Linux: distro-appropriate (apt, dnf, pacman) or official install script
- Suggest the user's package manager if detectable

### Step 4: Check Authentication & Access

For each installed CLI tool that requires auth:

```bash
# GitHub
gh auth status 2>&1

# AWS
aws sts get-caller-identity 2>&1

# GCP
gcloud auth list 2>&1

# kubectl
kubectl cluster-info 2>&1

# Docker registry
docker info 2>&1 | grep -i registry

# Linear
linear whoami 2>&1 || linear auth status 2>&1
```

**Present findings:**

```
AUTHENTICATION
──────────────
[OK] gh: authenticated as jane-doe (github.com)
[!!] aws: not authenticated
     → Run: aws configure (or aws sso login)
[OK] kubectl: connected to staging-cluster
[--] linear: CLI not installed (recommended, not required)
```

Only check auth for tools that are actually installed AND relevant to HERO.md.

### Step 5: Check Recommended Tools

Same as Step 3 but for `## Developer Setup → Recommended Tools`. Use `[--]` instead of `[!!]` for missing recommended tools — they're nice to have, not blockers.

```
RECOMMENDED TOOLS
─────────────────
[OK] pre-commit: 3.6.0 ✓
[--] linear: not installed
     → Optional CLI for issue management. Install: npm i -g @linear/cli
```

### Step 6: Check MCP Servers

If HERO.md lists MCP servers:

```
MCP SERVERS
───────────
[??] linear (mcp__linear): listed in HERO.md
     → Is the Linear MCP server configured in your Claude settings?
     → This is needed for /hero-plan to manage issues
[??] slack (mcp__slack): listed in HERO.md
     → Is the Slack MCP server configured in your Claude settings?
```

MCP server setup is done in Claude's settings, not via CLI — just inform the user what's expected and why.

### Step 7: Summary & Next Steps

**If `--check` was passed**, just show the summary and exit.

**For full setup**, after each section offer to fix what's missing. Then show final summary:

```
SETUP SUMMARY
═════════════
Git config:     ✓ local user.name and user.email set
Required tools: ✓ all 5 installed
Authentication: ⚠ 1 issue — aws not authenticated
Recommended:    ✓ 2/2 installed
MCP servers:    ? 1 to verify — linear

Remaining action items:
  1. Run: aws sso login
  2. Verify Linear MCP server is configured in Claude settings

Your environment is ready for development! 🎉
Run /hero-init --update if the project setup has changed.
```

## Key Principles

- **Never modify shared files.** This skill only touches local git config and suggests installs — it never writes to HERO.md, CLAUDE.md, or any committed file.
- **Always ask before changing config.** Git identity, signing keys, and auth are personal — confirm before setting.
- **Platform-aware.** Detect macOS vs Linux and suggest the right install commands.
- **Idempotent.** Running `/hero-setup` twice should be safe — skip what's already done.
- **Reference HERO.md.** Every check should tie back to why it's needed: "Required by HERO.md for /hero-push" or "Used by CI (GitHub Actions)".

## Examples

```
/hero-setup          # Full guided setup
/hero-setup --check  # Just verify, don't change anything
```
