#!/bin/bash
# =============================================================================
# Redis Cluster Creation Script
# Creates a 6-node Redis cluster (3 masters + 3 replicas)
# =============================================================================

set -e

echo "Waiting for all Redis nodes to be ready..."
sleep 10

# Check if cluster already exists
CLUSTER_INFO=$(redis-cli -h redis-node-1 -p 7000 cluster info 2>/dev/null || echo "")

if echo "$CLUSTER_INFO" | grep -q "cluster_state:ok"; then
    echo "Redis cluster already exists and is running."
    exit 0
fi

echo "Creating Redis cluster..."

# Create the cluster with 3 masters and 3 replicas
redis-cli --cluster create \
    redis-node-1:7000 \
    redis-node-2:7001 \
    redis-node-3:7002 \
    redis-node-4:7003 \
    redis-node-5:7004 \
    redis-node-6:7005 \
    --cluster-replicas 1 \
    --cluster-yes

echo "Redis cluster created successfully!"

# Verify cluster status
echo ""
echo "Cluster Status:"
redis-cli -h redis-node-1 -p 7000 cluster info

echo ""
echo "Cluster Nodes:"
redis-cli -h redis-node-1 -p 7000 cluster nodes

echo ""
echo "Cluster Slots:"
redis-cli -h redis-node-1 -p 7000 cluster slots
