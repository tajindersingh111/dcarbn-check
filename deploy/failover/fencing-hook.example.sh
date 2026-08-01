#!/usr/bin/env bash
set -Eeuo pipefail

# Replace with an idempotent control-plane action that prevents the old
# primary from accepting writes, such as revoking its database security group,
# stopping its compute group, or applying a write fence through the provider API.
echo "Fence the former primary before promotion."
