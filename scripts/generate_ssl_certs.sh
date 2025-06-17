#!/bin/bash
# Generate self-signed SSL certificates for local development

CERT_DIR="${1:-./certs}"
mkdir -p "$CERT_DIR"

# Generate a self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/localhost.key" \
    -out "$CERT_DIR/localhost.crt" \
    -subj "/C=US/ST=State/L=City/O=DEAN/CN=localhost" \
    2>/dev/null

# Also create nginx.crt/key as fallback
cp "$CERT_DIR/localhost.crt" "$CERT_DIR/nginx.crt"
cp "$CERT_DIR/localhost.key" "$CERT_DIR/nginx.key"

echo "SSL certificates generated in $CERT_DIR"
echo "- localhost.crt / localhost.key"
echo "- nginx.crt / nginx.key (fallback)"