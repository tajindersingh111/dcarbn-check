#!/usr/bin/env bash
set -Eeuo pipefail

namespace="${1:?Namespace is required}"
rollout="${2:?Rollout name is required}"

kubectl argo rollouts abort "$rollout" -n "$namespace"
kubectl argo rollouts undo "$rollout" -n "$namespace"
kubectl argo rollouts status "$rollout" -n "$namespace" --timeout 10m
