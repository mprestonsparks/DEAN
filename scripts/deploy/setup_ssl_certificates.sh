#!/bin/bash
# scripts/deploy/setup_ssl_certificates.sh

CERT_DIR="${CERT_DIR:-./certs}"
CERT_VALIDITY_DAYS="${CERT_VALIDITY_DAYS:-365}"
DOMAIN="${DOMAIN:-localhost}"

setup_ssl_certificates() {
    echo "Setting up SSL certificates..."
    
    mkdir -p "$CERT_DIR"
    
    # Check if certificates already exist
    if [[ -f "$CERT_DIR/server.crt" ]] && [[ -f "$CERT_DIR/server.key" ]]; then
        echo "SSL certificates already exist. Skipping generation."
        return 0
    fi
    
    # Generate self-signed certificate for development/testing
    if [[ "$ENVIRONMENT" == "development" ]] || [[ "$USE_SELF_SIGNED" == "true" ]]; then
        echo "Generating self-signed certificate..."
        openssl req -x509 -nodes -days "$CERT_VALIDITY_DAYS" -newkey rsa:2048 \
            -keyout "$CERT_DIR/server.key" \
            -out "$CERT_DIR/server.crt" \
            -subj "/C=US/ST=State/L=City/O=DEAN/CN=$DOMAIN" \
            2>/dev/null
        
        # Create copies with alternative names for compatibility
        cp "$CERT_DIR/server.crt" "$CERT_DIR/localhost.crt"
        cp "$CERT_DIR/server.key" "$CERT_DIR/localhost.key"
        cp "$CERT_DIR/server.crt" "$CERT_DIR/nginx.crt"
        cp "$CERT_DIR/server.key" "$CERT_DIR/nginx.key"
        
        chmod 600 "$CERT_DIR"/*.key
        chmod 644 "$CERT_DIR"/*.crt
        
        echo "✓ Self-signed certificates generated successfully"
    else
        echo "ERROR: Production certificates not found!"
        echo "Please place your SSL certificates at:"
        echo "  - $CERT_DIR/server.crt"
        echo "  - $CERT_DIR/server.key"
        return 1
    fi
}

# Run the function
setup_ssl_certificates