# Operations runbook — www.radiusred.uk

How the site is hosted, how TLS works, and what to do when something needs
attention. The site itself is a static build (Zensical) — see `README.md`
for authoring; this file is only about serving it.

## How the site is served

- **Build and publish: GitHub Pages.** This repo's CI
  (`.github/workflows/docs.yml`) builds the site on every push to `main`
  and on a daily scheduled run, then publishes `site/` through
  `actions/upload-pages-artifact` and `actions/deploy-pages` into the
  `github-pages` environment. The default Pages URL is
  https://radiusred.github.io/www/ and the site's custom domain is
  `www.radiusred.uk` (`gh api repos/radiusred/www/pages --jq .cname`).
  The repo's Pages build type must be `workflow`
  (`gh api repos/radiusred/www/pages --jq .build_type`); on `legacy`
  GitHub's own Jekyll build of the repo root races the deploy.
- **Front: Cloudflare.** The `radiusred.uk` zone lives on Cloudflare and
  `www` is a proxied CNAME to `radiusred.github.io`. A redirect rule sends
  the apex (`https://radiusred.uk/*`) to `https://www.radiusred.uk/*` with
  a 301, path and query preserved, and the zone enforces HTTPS at the
  edge: Always Use HTTPS on, minimum TLS 1.2, SSL mode Full to the Pages
  origin. All of it is OpenTofu in `radiusred/infrastructure`
  (`tofu/cloudflare/radiusred-uk`, applied with `scripts/tofu-r2.sh`);
  DNS, redirect and TLS changes go through that repo, not this one.
- `https://www.radiusred.uk` is the canonical host. Nothing is served from
  a server of our own any more; there is no host to log in to for this
  site.

## TLS

- The certificate a browser sees is Cloudflare's edge certificate for the
  zone (Universal SSL). Cloudflare issues and renews it; there is nothing
  to renew here.
- Between Cloudflare and GitHub Pages the connection uses GitHub's own
  certificate for `radiusred.github.io` (SSL mode Full). GitHub cannot
  issue a Pages certificate for a domain that is a proxied Cloudflare
  CNAME, so the Pages **Enforce HTTPS** setting stays off and HTTPS is
  enforced at the Cloudflare edge instead — the decision is recorded on
  radiusred/ops#4 (M4-R1 as amended).

### Checking the site is healthy

From anywhere:

```sh
curl -sI https://www.radiusred.uk/ | grep -iE '^(HTTP|server|cf-ray)'     # 200, server: cloudflare
curl -sI http://www.radiusred.uk/about/ | grep -iE '^(HTTP|location)'     # 301 to https
curl -sI 'https://radiusred.uk/about/?x=1' | grep -iE '^(HTTP|location)'  # 301 to www, query kept
echo | openssl s_client -connect www.radiusred.uk:443 -servername www.radiusred.uk 2>/dev/null \
  | openssl x509 -noout -issuer -enddate -ext subjectAltName
dog www.radiusred.uk radiusred.uk    # Cloudflare edge addresses, proxied
```

On the GitHub side:

```sh
gh run list -R radiusred/www --workflow docs.yml --limit 5
gh api repos/radiusred/www/pages --jq '{build_type, cname, https_enforced, status}'
```

## When something needs attention

- **The site is stale.** Check the latest `CI Build` run; a failed build
  never reaches `deploy`, so the previous deploy keeps serving. Re-run it
  with `gh workflow run docs.yml -R radiusred/www` once the cause is fixed.
- **www does not resolve, or the apex does not redirect.** That is the
  Cloudflare zone: `tofu plan` in
  `radiusred/infrastructure/tofu/cloudflare/radiusred-uk` shows drift, and
  `infrastructure/scripts/check-dns.sh` verifies the records.
- **Pages says the custom domain is unverified or missing.** Re-set it:
  `gh api -X PUT repos/radiusred/www/pages -f cname=www.radiusred.uk`
  (needs a token with Pages admin; the implementer App does not have it).

## Rebuilding from scratch

There is no server to rebuild. If Pages is ever disabled on the repo:

1. `gh api -X POST repos/radiusred/www/pages -f build_type=workflow`, then
   the `cname` PUT above.
2. Run the `CI Build` workflow (or push to `main`) to deploy the content.
3. Apply the Cloudflare root in `radiusred/infrastructure` if the zone was
   touched.

## History

- **2026-09-04** — the VPS www nginx vhost was decommissioned
  (radiusred/www#64): `/etc/nginx/sites-enabled/www` and
  `/etc/nginx/sites-available/www` removed, `nginx -t`, nginx reloaded;
  hooks.radiusred.uk and the Paperclip proxy (zoo.radiusred.uk) verified
  to answer the same before and after. The Let's Encrypt lineage
  `www.radiusred.uk` under `/etc/letsencrypt`, the `live` deploy user and
  its keys, and the served directory `/var/www/www.radiusred.uk` were
  deliberately left on the VPS for the operator (operator decisions on
  radiusred/www#64). `ops/provision-vps.sh` was deleted from this repo
  (last present at 7e6985b — re-provisioning, should it ever be wanted,
  starts from that commit). The `WWW_SSH_DEPLOY_KEY` and
  `WWW_VPS_HOST_KEY` repo secrets were deleted by the operator on
  2026-09-04 (the implementer App's token cannot touch Actions secrets);
  the repo has no Actions secrets left.
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
