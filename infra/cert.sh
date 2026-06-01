#!/usr/bin/env bash
#
# Issue or renew the Let's Encrypt certificate for LinkShrink and hand it to nginx.
#
#   bash infra/cert.sh issue   # issue if missing, keep an existing valid cert (default)
#   bash infra/cert.sh renew   # renew if within 30 days of expiry
#
# Uses certbot's DNS-01 challenge via Route 53, authenticating with the instance
# role (no AWS keys). The cert lands in the same Docker volumes nginx serves from,
# so the compose project name (linkshrink) is what keeps the paths stable.
#
# Replaces the hand-written ~/renew-cert.sh from manual-deploy.md 3.6. Run by
# deploy-on-host.sh (issue) and the linkshrink-cert systemd timer (renew).

set -euo pipefail

MODE="${1:-issue}"
AWS_REGION="us-east-1"
DOMAIN="${PUBLIC_HOST:-link-shrink.org}"
EMAIL="${LETSENCRYPT_EMAIL:-joeyiglesias83@gmail.com}"
NGINX_CONTAINER="linkshrink-nginx-1"

# Copies the live cert into the volume nginx reads from. certbot only runs this
# when a cert is actually obtained or renewed, so it's a no-op otherwise.
DEPLOY_HOOK="cp -L /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /nginx-certs/fullchain.pem && cp -L /etc/letsencrypt/live/${DOMAIN}/privkey.pem /nginx-certs/privkey.pem"

run_certbot() {
  docker run --rm \
    -e "AWS_DEFAULT_REGION=${AWS_REGION}" \
    -v linkshrink_letsencrypt:/etc/letsencrypt \
    -v linkshrink_nginx-certs:/nginx-certs \
    certbot/dns-route53 "$@"
}

case "$MODE" in
  issue)
    # certonly with --keep-until-expiring leaves a still-valid cert untouched.
    run_certbot certonly \
      --dns-route53 \
      --non-interactive --agree-tos --no-eff-email \
      --keep-until-expiring \
      -m "$EMAIL" \
      -d "$DOMAIN" \
      -d "www.${DOMAIN}" \
      --deploy-hook "$DEPLOY_HOOK"
    ;;
  renew)
    run_certbot renew --deploy-hook "$DEPLOY_HOOK"
    ;;
  *)
    echo "usage: cert.sh [issue|renew]" >&2
    exit 2
    ;;
esac

# Reload nginx so it picks up a new cert — but only if it's actually running
# (on a fresh box the cert may be issued before the stack is up).
if docker ps --format '{{.Names}}' | grep -qx "$NGINX_CONTAINER"; then
  docker exec "$NGINX_CONTAINER" nginx -s reload
  echo "Reloaded $NGINX_CONTAINER"
else
  echo "$NGINX_CONTAINER not running — nginx will read the cert on next start"
fi

echo "cert.sh $MODE complete for $DOMAIN"
