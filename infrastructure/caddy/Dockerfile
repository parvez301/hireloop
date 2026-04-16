# Caddy 2 with github.com/caddy-dns/route53 for DNS-01 (Let's Encrypt).
# Build context: this directory. Push to ECR as hireloop-caddy:2-route53 (see build-and-push.sh).
FROM caddy:2-builder AS xcaddy
RUN xcaddy build \
  --with github.com/caddy-dns/route53

FROM caddy:2-alpine
COPY --from=xcaddy /usr/bin/caddy /usr/bin/caddy
