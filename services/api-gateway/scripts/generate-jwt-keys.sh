#!/bin/bash
# services/api-gateway/scripts/generate-jwt-keys.sh
# Generate RS256 JWT key pair for Kong authentication

set -e

KEYS_DIR="$(dirname "$0")/../kong/jwt-keys"
mkdir -p "$KEYS_DIR"

echo "Generating RS256 JWT key pair..."

# Generate private key
openssl genrsa -out "$KEYS_DIR/private.pem" 2048

# Generate public key from private key
openssl rsa -in "$KEYS_DIR/private.pem" -pubout -out "$KEYS_DIR/public.pem"

# Set permissions
chmod 600 "$KEYS_DIR/private.pem"
chmod 644 "$KEYS_DIR/public.pem"

echo "Keys generated successfully!"
echo "Private key: $KEYS_DIR/private.pem"
echo "Public key: $KEYS_DIR/public.pem"
echo ""
echo "IMPORTANT: Keep private.pem secure and NEVER commit it to version control!"
echo "Copy private.pem to your User Service for JWT signing."
echo "Copy public.pem to Kong for JWT verification."
