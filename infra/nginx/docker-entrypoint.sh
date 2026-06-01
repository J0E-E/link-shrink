#!/bin/sh
# infra/nginx/docker-entrypoint.sh — Epic 18b TLS bootstrap (local self-signed).
#
# Mounted into the nginx:alpine image's /docker-entrypoint.d/ so the stock
# launcher runs it before starting nginx. It must NOT exec nginx itself — the
# launcher does that after the .d scripts finish.
#
# Generates a self-signed cert into the nginx-certs volume ONLY if one is absent.
# In prod, mount Let's Encrypt fullchain.pem/privkey.pem at these same paths (or
# run certbot into the volume): the files then already exist, this script skips,
# and the same default.conf serves the real cert with no config change.
set -e

CERT_DIR=/etc/nginx/certs
HOST="${PUBLIC_HOST:-localhost}"

if [ ! -s "$CERT_DIR/fullchain.pem" ] || [ ! -s "$CERT_DIR/privkey.pem" ]; then
    echo "[nginx] no certificate found — generating a self-signed pair for $HOST"
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/CN=$HOST" \
        -addext "subjectAltName=DNS:$HOST,DNS:localhost,IP:127.0.0.1"
else
    echo "[nginx] existing certificate found — using it (prod / Let's Encrypt)"
fi
