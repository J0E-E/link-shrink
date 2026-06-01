# Edge proxy image (Epic 18b).
#
# Stock nginx:alpine plus openssl, which the base image does NOT include. The
# docker-entrypoint.sh drop-in needs openssl to generate the local self-signed
# cert on first boot; baking it in keeps that step offline and instant rather
# than installing a package at container start.
#
# The nginx config, conf.d, and the entrypoint script are bind-mounted by the
# compose service (not COPYed) so edits + `nginx -s reload` work without a rebuild.
FROM nginx:alpine

RUN apk add --no-cache openssl
