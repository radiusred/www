#!/bin/bash
# Provision (or re-provision) the nginx + Let's Encrypt setup for
# www.radiusred.uk on a Debian VPS. Idempotent — safe to re-run.
#
# Prerequisites (see RUNBOOK.md):
#   - DNS A records for radiusred.uk and www.radiusred.uk point at this host
#   - ports 80/443 reachable from the internet
#   - the `live` deploy user exists (site content arrives via CI rsync)
#
# Usage: sudo ./provision-vps.sh
set -euo pipefail

DOMAIN="www.radiusred.uk"
APEX="radiusred.uk"
DOCROOT="/var/www/${DOMAIN}"
ACME_WEBROOT="/var/www/letsencrypt"
LE_EMAIL="hello@radiusred.uk"
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
DEPLOY_USER="live"

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)" >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y nginx certbot

mkdir -p "$DOCROOT"
chown "$DEPLOY_USER:$DEPLOY_USER" "$DOCROOT"
chmod 755 "$DOCROOT"

# ACME challenges are served from a dedicated webroot so site deploys
# (rsync --delete into the document root) can never remove an in-flight
# challenge.
mkdir -p "$ACME_WEBROOT"
chmod 755 "$ACME_WEBROOT"

write_config() {
    # $1 = "http-only" | "full"
    cat > /etc/nginx/sites-available/www <<EOF
# Managed by ops/provision-vps.sh in the radiusred/www repo
server {
    listen 80;
    server_name ${DOMAIN} ${APEX};

    # ACME challenges for Let's Encrypt certificate validation
    location /.well-known/acme-challenge/ {
        root ${ACME_WEBROOT};
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}
EOF
    [ "$1" = "http-only" ] && return 0
    cat >> /etc/nginx/sites-available/www <<EOF

# Canonical host is ${DOMAIN}; the apex redirects there.
server {
    listen 443 ssl;
    server_name ${APEX};

    ssl_certificate     ${CERT};
    ssl_certificate_key ${KEY};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:WWW_SSL:10m;
    ssl_session_timeout 1d;

    return 301 https://${DOMAIN}\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate     ${CERT};
    ssl_certificate_key ${KEY};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:WWW_SSL:10m;
    ssl_session_timeout 1d;

    root ${DOCROOT};
    index index.html;

    error_page 404 /404.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location = /404.html {
        internal;
    }
}
EOF
}

# On a fresh host the certificate doesn't exist yet, so the HTTPS server
# blocks would fail nginx -t. Deploy HTTP-only first, obtain the cert over
# port 80, then deploy the full config.
if [ -f "$CERT" ]; then
    write_config full
else
    write_config http-only
fi
ln -sf /etc/nginx/sites-available/www /etc/nginx/sites-enabled/www
nginx -t
systemctl reload nginx
systemctl enable --now nginx

# Idempotent: certbot exits 0 without reissuing while the existing cert is
# still valid; --expand covers adding a domain to an existing lineage.
certbot certonly --webroot -w "$ACME_WEBROOT" \
    --cert-name "$DOMAIN" \
    -d "$DOMAIN" -d "$APEX" \
    --email "$LE_EMAIL" --agree-tos --no-eff-email --non-interactive \
    --expand --keep-until-expiring

write_config full
nginx -t
systemctl reload nginx

# Reload nginx whenever the certbot systemd timer renews the certificate.
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

echo
echo "Done. Certificate status:"
certbot certificates --cert-name "$DOMAIN"
