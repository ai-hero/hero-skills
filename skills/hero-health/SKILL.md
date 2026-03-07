---
name: hero-health
# prettier-ignore
description: Health check a Kubernetes cluster. Inspects nodes, pods, deployments, services, ingress, recent events, resource usage, and optionally ArgoCD app sync status. Use when connected to a cluster and need a quick status overview.
argument-hint: [namespace|all] [--argocd]
disable-model-invocation: true
---

# Hero Health - Kubernetes Cluster Health Check

Comprehensive health check for a connected Kubernetes cluster.

## Arguments

- `$ARGUMENTS` - Optional scope and flags:
  - `<namespace>` - Check a specific namespace (default: all non-system namespaces)
  - `all` - Include system namespaces (kube-system, etc.)
  - `--argocd` - Also check ArgoCD application sync status

## Prerequisites

- `kubectl` configured with valid kubeconfig
- Cluster access (at least read permissions)
- `argocd` CLI (optional, for `--argocd` flag)

## Instructions

### Step 0: Load Hero Configuration

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cat "$ROOT/HERO.md" 2>/dev/null || echo "NO_HERO_CONFIG"
```

Read `HERO.md` if it exists. This skill uses:
- **Deployment** → platform (kubernetes, ecs, etc.), namespaces, argocd flag

If `HERO.md` is missing, suggest `/hero-init` but proceed with auto-detection.

### Step 1: Verify Cluster Connection

```bash
kubectl config current-context
kubectl cluster-info --request-timeout=5s
```

If connection fails, report the error and stop.

### Step 2: Node Health

```bash
kubectl get nodes -o wide
kubectl top nodes 2>/dev/null || echo "Metrics server not available"
```

Check for:
- Nodes in `NotReady` state
- High resource utilization (>85% CPU or memory)
- Node conditions (MemoryPressure, DiskPressure, PIDPressure)

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.conditions[*]}{.type}={.status}{"\t"}{end}{"\n"}{end}'
```

### Step 3: Pod Health

```bash
# Get unhealthy pods across target namespaces
kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide 2>/dev/null

# CrashLooping pods
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | "\(.metadata.namespace)/\(.metadata.name) restarts=\(.status.containerStatuses[0].restartCount)"'

# Pending pods
kubectl get pods --all-namespaces --field-selector=status.phase=Pending -o wide
```

### Step 4: Deployment Health

```bash
# Deployments not at desired replica count
kubectl get deployments --all-namespaces -o json | jq -r '.items[] | select(.status.readyReplicas != .status.replicas) | "\(.metadata.namespace)/\(.metadata.name) ready=\(.status.readyReplicas // 0)/\(.status.replicas)"'

# Recent rollouts
kubectl get deployments --all-namespaces -o json | jq -r '.items[] | select(.status.conditions[]? | select(.type=="Progressing" and .status=="True")) | "\(.metadata.namespace)/\(.metadata.name)"'
```

### Step 5: Services and Ingress

```bash
# Services without endpoints
kubectl get endpoints --all-namespaces -o json | jq -r '.items[] | select((.subsets == null) or (.subsets | length == 0)) | "\(.metadata.namespace)/\(.metadata.name) - NO ENDPOINTS"'

# Ingress status
kubectl get ingress --all-namespaces -o wide 2>/dev/null
```

### Step 6: Recent Events (Warnings)

```bash
# Warning events in the last hour
kubectl get events --all-namespaces --field-selector type=Warning --sort-by='.lastTimestamp' | tail -20
```

### Step 7: Resource Utilization

```bash
kubectl top pods --all-namespaces --sort-by=cpu 2>/dev/null | head -15
kubectl top pods --all-namespaces --sort-by=memory 2>/dev/null | head -15
```

### Step 8: ArgoCD Status (if --argocd)

```bash
# Try argocd CLI first
argocd app list -o json 2>/dev/null | jq -r '.[] | "\(.metadata.name)\t\(.status.sync.status)\t\(.status.health.status)"'

# Fallback: check ArgoCD CRDs directly
kubectl get applications -n argocd -o json 2>/dev/null | jq -r '.items[] | "\(.metadata.name)\tsync=\(.status.sync.status)\thealth=\(.status.health.status)"'
```

Flag any apps that are:
- `OutOfSync`
- `Degraded` or `Missing` health
- `Unknown` status

### Step 9: Summary Report

```
Hero Health Check
=================
Cluster: <context-name>
Time: <timestamp>

Nodes: 3/3 Ready
  - node-1: Ready (CPU 45%, Mem 62%)
  - node-2: Ready (CPU 38%, Mem 55%)
  - node-3: Ready (CPU 52%, Mem 71%)

Pods: 42/42 Running
  CrashLooping: 0
  Pending: 0

Deployments: 15/15 Ready

Services: 18 total, 0 missing endpoints

Warnings (last hour): 3
  - <namespace>/<resource>: <message>

[ArgoCD Apps: 12 Synced, 1 OutOfSync]
  - <app-name>: OutOfSync (Degraded)

Overall: HEALTHY | DEGRADED | CRITICAL
```

**Status classification:**

| Status | Condition |
|--------|-----------|
| HEALTHY | All nodes ready, no crashloops, no pending pods, all deployments at desired count |
| DEGRADED | Some warnings, pods restarting, or deployments scaling |
| CRITICAL | Nodes not ready, multiple crashloops, or ArgoCD apps degraded |

## Examples

```
/hero-health                    # Check all non-system namespaces
/hero-health production         # Check only production namespace
/hero-health all                # Include system namespaces
/hero-health --argocd           # Include ArgoCD sync status
/hero-health production --argocd # Namespace + ArgoCD
```

## Notes

- Requires read access to the cluster (ClusterRole or namespace-scoped)
- Metrics server must be installed for `kubectl top` commands
- ArgoCD checks require either `argocd` CLI or access to argocd namespace
- Does not modify any cluster resources - read-only operation
