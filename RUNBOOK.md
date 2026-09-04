# Operations runbook — www.radiusred.uk

How the site is hosted, how TLS works, and what to do when something needs
attention. The site itself is a static build (Zensical) — see `README.md`
for authoring; this file is only about serving it.

## How the site is served

- A Debian VPS runs nginx, serving the built site from
  `/var/www/www.radiusred.uk`.
- `https://www.radiusred.uk` is the canonical host. The apex
  `radiusred.uk` and all `http://` requests 301-redirect to it.
- Deploys come from this repo's CI (`.github/workflows/docs.yml`): every
  push to `main` (and a daily scheduled run) builds the site and publishes
  `site/` to GitHub Pages through `actions/upload-pages-artifact` and
  `actions/deploy-pages` (the `github-pages` environment). The default
  Pages URL is https://radiusred.github.io/www/; the VPS no longer receives
  deploys and is retired under radiusred/ops#4 — until then the sections
  below still describe it. The repo's Pages build type must be `workflow`
  (`gh api repos/radiusred/www/pages --jq .build_type`); on `legacy`
  GitHub's own Jekyll build of the repo root races the deploy.

## TLS certificates

Since 2026-08-03 the certificate comes from **Let's Encrypt** (it was
ZeroSSL before, whose free plan stopped allowing renewals). Setup:

- One certificate lineage, `www.radiusred.uk`, covering
  `www.radiusred.uk` + `radiusred.uk`, at
  `/etc/letsencrypt/live/www.radiusred.uk/`.
- Issued and renewed by `certbot` using webroot HTTP-01 validation from
  the dedicated webroot `/var/www/letsencrypt` (deliberately outside the
  document root, which CI rsyncs with `--delete`).
- **Renewal is automatic**: the Debian `certbot.timer` systemd unit runs
  twice daily and renews ~30 days before expiry. A deploy hook
  (`/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`) reloads nginx
  after each renewal. No cron jobs, no manual steps.
- Other services on the same host manage their certificates under the same
  certbot timer; they are out of scope for this repo.

### Checking certificate health

From anywhere:

```sh
echo | openssl s_client -connect www.radiusred.uk:443 -servername www.radiusred.uk 2>/dev/null \
  | openssl x509 -noout -issuer -enddate -ext subjectAltName
```

On the server:

```sh
sudo certbot certificates          # lineages, domains, expiry
systemctl list-timers certbot.timer
sudo certbot renew --dry-run       # full staging rehearsal (slow, several minutes)
```

### Forcing a renewal

Normally never needed. If a cert is close to expiry and the timer hasn't
renewed it, check `journalctl -u certbot.service` first, then:

```sh
sudo certbot renew
```

## Rebuilding the server from scratch

Prerequisites:

1. DNS A records for `radiusred.uk` and `www.radiusred.uk` pointing at the
   new host (nameservers are at the domain registrar).
2. Ports 80 and 443 reachable from the internet.
3. A `live` user whose `~/.ssh/authorized_keys` contains the public half of
   the `WWW_SSH_DEPLOY_KEY` repo secret; update the `WWW_VPS_HOST_KEY`
   secret (or the fallback host keys in `docs.yml`) for the new host.

Then run [`ops/provision-vps.sh`](ops/provision-vps.sh) as root on the
host. It is idempotent: installs nginx + certbot, writes the nginx config
(HTTP-only first on a fresh host so `nginx -t` never references a
certificate that doesn't exist yet), obtains the certificate, enables the
HTTPS config, and installs the renewal hook. Finally, trigger the CI
workflow (or push to `main`) to deploy the site content.

## History

- **2026-09-04** — the CI deploy moved from rsync over SSH to GitHub
  Pages actions (radiusred/www#62, milestone radiusred/ops#4). DNS still
  points at the VPS until radiusred/infrastructure#251 lands.
- **2026-08-03** — migrated from ZeroSSL (expired, free plan couldn't
  renew) to Let's Encrypt; added the `radiusred.uk` apex DNS record and
  included it in the certificate with an apex→www redirect. Server config
  was previously managed by Ansible in the (now archived)
  `radiusred/infrastructure` repo; the essentials were captured here as
  `ops/provision-vps.sh` and that repo should not be reused — its roles
  still describe the pre-Let's-Encrypt setup.
