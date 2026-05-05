---
name: check
# prettier-ignore
description: Check CI/CD pipeline status (default) or Kubernetes cluster health (cluster subcommand). Use after pushing to verify builds pass, debug pipelines, or get a cluster status overview.
argument-hint: [ci [branch|#pr|run-id] | cluster [namespace] [--argocd]]
disable-model-invocation: true
---

# Check — CI/CD and Cluster Status

Check pipeline status or cluster health. Default is CI/CD for the current branch.

## Arguments

- `$ARGUMENTS` — Optional mode and scope:
  - (none) or `ci` — CI/CD status for the current branch
  - `ci BRANCH` — CI/CD for a specific branch
  - `ci #PR` — CI/CD checks for a PR
  - `ci RUN_ID` — A specific workflow run
  - `cluster [namespace] [--argocd]` — Kubernetes cluster health

## Prerequisites

- `gh` CLI (for CI mode) or `kubectl` (for cluster mode), installed and authenticated

## Instructions

### Step 0: Load Configuration and Detect Mode

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` for:

- **CI/CD** → platform, workflow names (CI mode)
- **Deployment** → platform, namespaces, argocd flag (cluster mode)

If `HERO.md` is missing, suggest `hero-skills:init` but proceed: assume GitHub Actions for CI, auto-detect namespace for cluster.

Parse the first token of `$ARGUMENTS` to determine mode. Default is `ci`.

---

## CI Mode

### Step 1: Identify Context

```bash
gh repo view --json nameWithOwner -q .nameWithOwner
BRANCH=$(git branch --show-current)
gh workflow list
```

### Step 2: Check Workflow Runs

**Current branch (default):**

```bash
gh run list --branch "$BRANCH" --limit 5 \
  --json databaseId,name,status,conclusion,headBranch,createdAt,url
```

**Specific PR:**

```bash
gh pr checks PR_NUMBER
```

**Specific run:**

```bash
gh run view RUN_ID
```

### Step 3: Analyze Results

For each run report: workflow name, status (queued/in_progress/completed), conclusion (success/failure/cancelled/skipped), duration, branch.

If any run failed:

```bash
gh run view RUN_ID --json jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | {name, steps: [.steps[] | select(.conclusion=="failure") | .name]}'
gh run view RUN_ID --log-failed
```

### Step 4: Image and Deployment Status (if applicable)

```bash
# Container images
gh api repos/{owner}/{repo}/packages?package_type=container \
  --jq '.[].name' 2>/dev/null
gh api repos/{owner}/{repo}/packages/container/{package}/versions \
  --jq '.[0] | {tags: .metadata.container.tags, created: .created_at}' 2>/dev/null

# Deployments
gh api repos/{owner}/{repo}/deployments \
  --jq '.[:3] | .[] | {environment: .environment, ref: .ref, created: .created_at}' 2>/dev/null
```

### Step 5: Watch In-Progress Runs (optional)

If runs are `in_progress`, offer:

```bash
gh run watch RUN_ID
```

Use `run_in_background: true` and report on completion.

### Step 6: CI Summary

```
CI Status
=========
Repo: owner/repo
Branch: feature/my-change

Workflow Runs (latest 5):
  1. Build & Test   SUCCESS   2m 15s
  2. Lint           SUCCESS   45s
  3. Docker Build   FAILURE   1m 48s

Failed Run Details:
  Job: build-image
  Step: docker push
  Error: ...

Images:
  ghcr.io/owner/repo:main - pushed 2h ago

Overall: PASSING | FAILING | IN PROGRESS | STALE
```

Status classification: PASSING (all succeeded), FAILING (any failed), IN PROGRESS (still running), STALE (no runs in 24h).

---

## Cluster Mode

### Step 1: Verify Connection

```bash
kubectl config current-context
kubectl cluster-info --request-timeout=5s
```

Stop if connection fails.

### Step 2: Node Health

```bash
kubectl get nodes -o wide
kubectl top nodes 2>/dev/null || echo "Metrics server not available"
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.conditions[*]}{.type}={.status}{"\t"}{end}{"\n"}{end}'
```

Flag: NotReady nodes, >85% CPU/memory, MemoryPressure/DiskPressure/PIDPressure.

### Step 3: Pod Health

```bash
kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide 2>/dev/null
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | "\(.metadata.namespace)/\(.metadata.name) restarts=\(.status.containerStatuses[0].restartCount)"'
kubectl get pods --all-namespaces --field-selector=status.phase=Pending -o wide
```

### Step 4: Deployment Health

```bash
kubectl get deployments --all-namespaces -o json | \
  jq -r '.items[] | select(.status.readyReplicas != .status.replicas) | "\(.metadata.namespace)/\(.metadata.name) ready=\(.status.readyReplicas // 0)/\(.status.replicas)"'
```

### Step 5: Services, Ingress, Events

```bash
# Services without endpoints
kubectl get endpoints --all-namespaces -o json | \
  jq -r '.items[] | select((.subsets == null) or (.subsets | length == 0)) | "\(.metadata.namespace)/\(.metadata.name) - NO ENDPOINTS"'
kubectl get ingress --all-namespaces -o wide 2>/dev/null

# Warning events (last hour)
kubectl get events --all-namespaces --field-selector type=Warning --sort-by='.lastTimestamp' | tail -20

# Top consumers
kubectl top pods --all-namespaces --sort-by=cpu 2>/dev/null | head -15
```

### Step 6: ArgoCD Status (if --argocd)

```bash
argocd app list -o json 2>/dev/null | \
  jq -r '.[] | "\(.metadata.name)\t\(.status.sync.status)\t\(.status.health.status)"'
# Fallback via kubectl
kubectl get applications -n argocd -o json 2>/dev/null | \
  jq -r '.items[] | "\(.metadata.name)\tsync=\(.status.sync.status)\thealth=\(.status.health.status)"'
```

Flag: OutOfSync, Degraded, Missing, Unknown.

### Step 7: Cluster Summary

```
Cluster Status
==============
Context: CLUSTER_NAME
Time: TIMESTAMP

Nodes: 3/3 Ready
  - node-1: Ready (CPU 45%, Mem 62%)

Pods: 42/42 Running
  CrashLooping: 0 | Pending: 0

Deployments: 15/15 Ready

Services: 18 total, 0 missing endpoints

Warnings (last hour): 3
  - NAMESPACE/RESOURCE: MESSAGE

[ArgoCD: 12 Synced, 1 OutOfSync]
  - APP_NAME: OutOfSync (Degraded)

Overall: HEALTHY | DEGRADED | CRITICAL
```

Status: HEALTHY (all nodes ready, no crashloops, all deployments at count), DEGRADED (some warnings), CRITICAL (nodes not ready, multiple crashloops).

## Notes

- CI mode is read-only — never triggers or modifies workflows.
- Cluster mode is read-only — requires at minimum read access.
- For ArgoCD, requires `argocd` CLI or access to the `argocd` namespace.
