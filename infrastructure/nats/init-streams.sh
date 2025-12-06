#!/bin/bash
# =============================================================================
# NATS JetStream Stream Initialization Script
# Run this after NATS server is up to create streams and consumers
# =============================================================================

set -e

NATS_URL="${NATS_URL:-nats://admin:nats_password@localhost:4222}"

echo "Waiting for NATS server to be ready..."
until nats server ping --server="$NATS_URL" 2>/dev/null; do
    echo "NATS server is not ready yet. Retrying in 2 seconds..."
    sleep 2
done

echo "NATS server is ready. Initializing JetStream streams..."

# Create main events stream
echo "Creating FTMS_EVENTS stream..."
nats stream add FTMS_EVENTS \
    --server="$NATS_URL" \
    --subjects="ftms.>" \
    --storage=file \
    --retention=limits \
    --max-msgs=1000000 \
    --max-bytes=1073741824 \
    --max-age=7d \
    --max-msg-size=1048576 \
    --discard=old \
    --dupe-window=2m \
    --replicas=1 \
    --no-allow-rollup \
    --deny-delete \
    --deny-purge || echo "Stream may already exist, continuing..."

# Create dead letter stream for failed messages
echo "Creating FTMS_DLQ stream (Dead Letter Queue)..."
nats stream add FTMS_DLQ \
    --server="$NATS_URL" \
    --subjects="ftms.dlq.>" \
    --storage=file \
    --retention=limits \
    --max-msgs=100000 \
    --max-bytes=536870912 \
    --max-age=30d \
    --replicas=1 || echo "DLQ stream may already exist, continuing..."

echo "Creating consumers for each service..."

# User Service Consumer
nats consumer add FTMS_EVENTS user-service \
    --server="$NATS_URL" \
    --filter="ftms.user.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

# Notification Service Consumer (subscribes to all events for notifications)
nats consumer add FTMS_EVENTS notification-service \
    --server="$NATS_URL" \
    --filter="ftms.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

# Organization Service Consumer
nats consumer add FTMS_EVENTS organization-service \
    --server="$NATS_URL" \
    --filter="ftms.organization.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

# Flight Service Consumer
nats consumer add FTMS_EVENTS flight-service \
    --server="$NATS_URL" \
    --filter="ftms.flight.>,ftms.booking.>,ftms.aircraft.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

# Training Service Consumer
nats consumer add FTMS_EVENTS training-service \
    --server="$NATS_URL" \
    --filter="ftms.training.>,ftms.user.>,ftms.flight.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

# Finance Service Consumer
nats consumer add FTMS_EVENTS finance-service \
    --server="$NATS_URL" \
    --filter="ftms.finance.>,ftms.booking.>,ftms.flight.>" \
    --ack=explicit \
    --deliver=all \
    --max-deliver=5 \
    --ack-wait=30s \
    --replay=instant \
    --pull || echo "Consumer may already exist, continuing..."

echo ""
echo "=== JetStream Setup Complete ==="
echo ""
echo "Stream info:"
nats stream info FTMS_EVENTS --server="$NATS_URL" 2>/dev/null || true
echo ""
echo "Consumers:"
nats consumer list FTMS_EVENTS --server="$NATS_URL" 2>/dev/null || true
