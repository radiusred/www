"""``python -m social`` — check credentials, post, or re-consent LinkedIn."""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from . import bluesky, linkedin
from .config import Credentials, MissingCredential, load_credentials
from .transport import ApiError, UrllibTransport

NETWORKS = ("bluesky", "linkedin")
REFRESH_AHEAD = 7 * 24 * 3600  # refresh when the access token has under a week left


def _stamp(epoch: int | float) -> str:
    return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%d")


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


# --- LinkedIn token care ------------------------------------------------


def linkedin_client(creds: Credentials, transport) -> linkedin.LinkedIn:
    return linkedin.LinkedIn(
        transport,
        creds.require("LINKEDIN_CLIENT_ID"),
        creds.require("LINKEDIN_CLIENT_SECRET"),
        creds.get("LINKEDIN_ACCESS_TOKEN"),
        creds.get("LINKEDIN_VERSION", linkedin.DEFAULT_VERSION),
    )


def store_tokens(creds: Credentials, tokens: dict, now: float) -> None:
    updates = {
        "LINKEDIN_ACCESS_TOKEN": tokens["access_token"],
        "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT": str(int(now + tokens.get("expires_in", 0))),
    }
    if tokens.get("refresh_token"):
        updates["LINKEDIN_REFRESH_TOKEN"] = tokens["refresh_token"]
        updates["LINKEDIN_REFRESH_TOKEN_EXPIRES_AT"] = str(
            int(now + tokens.get("refresh_token_expires_in", 0))
        )
    skipped = creds.persist(updates)
    if skipped:
        _say(
            "warning: rotated LinkedIn tokens were NOT persisted for "
            + ", ".join(skipped)
            + " (they came from the environment) — update your orchestrator's copy"
        )
    _say(f"LinkedIn access token refreshed; valid to {_stamp(now + tokens.get('expires_in', 0))}")


def ensure_linkedin_token(creds: Credentials, client: linkedin.LinkedIn, now: float | None = None) -> str:
    """Return a usable access token, refreshing when it is expired, unknown,
    or within REFRESH_AHEAD of expiry."""
    now = time.time() if now is None else now
    token = creds.get("LINKEDIN_ACCESS_TOKEN")
    expires_at = creds.get("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT")
    fresh = False
    if token and expires_at and expires_at.isdigit():
        fresh = int(expires_at) - now > REFRESH_AHEAD
    elif token:
        info = client.introspect(token)
        fresh = bool(info.get("active")) and int(info.get("expires_at", 0)) - now > REFRESH_AHEAD
    if fresh:
        client.access_token = token
        return token
    refresh_token = creds.require("LINKEDIN_REFRESH_TOKEN")
    tokens = client.refresh(refresh_token)
    store_tokens(creds, tokens, now)
    return tokens["access_token"]


# --- commands -----------------------------------------------------------


def cmd_check(args, creds: Credentials, transport) -> int:
    failures = 0
    try:
        client = bluesky.Bluesky(
            transport, creds.require("BSKY_HANDLE"), creds.require("BSKY_APP_PASSWORD"),
            creds.get("BSKY_PDS", bluesky.DEFAULT_PDS),
        )
        session = client.login()
        print(f"bluesky: ok — {session.get('handle')} ({session.get('did')})")
    except (MissingCredential, ApiError) as err:
        failures += 1
        print(f"bluesky: FAILED — {err}")

    try:
        client = linkedin_client(creds, transport)
        ensure_linkedin_token(creds, client)
        info = client.introspect(client.access_token)
        scopes = info.get("scope", "").replace(",", " ")
        print(
            f"linkedin: token {info.get('status', '?')}, expires {_stamp(info.get('expires_at', 0))}"
            f"; scopes: {scopes}"
        )
        refresh_exp = creds.get("LINKEDIN_REFRESH_TOKEN_EXPIRES_AT")
        if refresh_exp and refresh_exp.isdigit():
            print(f"linkedin: refresh token expires {_stamp(refresh_exp)} — re-consent before then")
        acls = client.organization_acls()
        urns = [a.get("organization") for a in acls]
        configured = creds.get("LINKEDIN_ORG_URN")
        for urn in urns:
            org = client.organization(urn)
            mark = " (configured)" if urn == configured else ""
            print(f"linkedin: administers {urn} — {org.get('localizedName')} / {org.get('vanityName')}{mark}")
        if configured and configured not in urns:
            failures += 1
            print(f"linkedin: FAILED — LINKEDIN_ORG_URN {configured} is not among the administered pages")
        elif not configured and len(urns) == 1:
            creds.persist({"LINKEDIN_ORG_URN": urns[0]})
            print(f"linkedin: LINKEDIN_ORG_URN set to {urns[0]}")
        elif not configured:
            failures += 1
            print("linkedin: FAILED — set LINKEDIN_ORG_URN to one of the pages above")
    except (MissingCredential, ApiError) as err:
        failures += 1
        print(f"linkedin: FAILED — {err}")
    return 1 if failures else 0


def _read_text(args, network: str) -> str:
    override = getattr(args, f"{network}_text_file", None)
    if override:
        return Path(override).read_text()
    if args.text_file:
        return Path(args.text_file).read_text()
    if args.text:
        return args.text
    raise SystemExit("error: give --text, --text-file, or a per-network --<network>-text-file")


def cmd_post(args, creds: Credentials, transport) -> int:
    targets = list(dict.fromkeys(args.to))
    if not targets:
        raise SystemExit("error: --to bluesky and/or --to linkedin is required")

    requests: dict[str, dict] = {}
    clients: dict[str, object] = {}
    if "bluesky" in targets:
        record = bluesky.build_post(_read_text(args, "bluesky"), args.link, args.title, args.description)
        if args.dry_run:
            client = bluesky.Bluesky(transport, creds.get("BSKY_HANDLE", "<handle>"), "", creds.get("BSKY_PDS", bluesky.DEFAULT_PDS))
            requests["bluesky"] = client.create_record_request(record)
        else:
            client = bluesky.Bluesky(
                transport, creds.require("BSKY_HANDLE"), creds.require("BSKY_APP_PASSWORD"),
                creds.get("BSKY_PDS", bluesky.DEFAULT_PDS),
            )
            clients["bluesky"] = (client, record)
    if "linkedin" in targets:
        org = creds.get("LINKEDIN_ORG_URN") if args.dry_run else creds.require("LINKEDIN_ORG_URN")
        body = linkedin.build_post(org or "urn:li:organization:<id>", _read_text(args, "linkedin"), args.link, args.title, args.description)
        if args.dry_run:
            client = linkedin.LinkedIn(transport, "", "", version=creds.get("LINKEDIN_VERSION", linkedin.DEFAULT_VERSION))
            requests["linkedin"] = client.post_request(body)
        else:
            client = linkedin_client(creds, transport)
            clients["linkedin"] = (client, body)

    if args.dry_run:
        for network in targets:
            print(json.dumps({"network": network, "dry_run": True, "request": requests[network]}, indent=2, ensure_ascii=False))
        return 0

    failures = 0
    for network in targets:
        client, payload = clients[network]
        try:
            if network == "linkedin":
                ensure_linkedin_token(creds, client)
            result = client.post(payload)
            print(json.dumps({"network": network, **result}))
        except ApiError as err:
            failures += 1
            print(json.dumps({"network": network, "error": str(err)}))
    return 1 if failures else 0


class _CodeCatcher(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    state: str | None = None

    def do_GET(self):  # noqa: N802 — http.server's name
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        type(self).code = query.get("code", [None])[0]
        type(self).state = query.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Consent received; you can close this tab.")

    def log_message(self, *_):
        pass


def cmd_auth_linkedin(args, creds: Credentials, transport) -> int:
    """The re-consent playbook: consent URL → code → exchange → write-back.
    Needs a human signed in to LinkedIn as a Page admin. Run it when the
    refresh token expires or when the app's scopes change."""
    client = linkedin_client(creds, transport)
    redirect_uri = args.redirect_uri or creds.get("LINKEDIN_REDIRECT_URI") or "http://localhost:8765/callback"
    url, state = client.auth_url(redirect_uri, tuple(args.scope) if args.scope else linkedin.DEFAULT_SCOPES)
    print("1. Make sure this redirect URI is registered on the app's Auth tab:", redirect_uri)
    print("2. Signed in as the Page admin, open:\n\n   " + url + "\n")

    parsed = urllib.parse.urlparse(redirect_uri)
    code = None
    if parsed.hostname in ("localhost", "127.0.0.1") and not args.paste:
        print(f"3. Waiting for LinkedIn to redirect to {redirect_uri} …")
        with http.server.HTTPServer((parsed.hostname, parsed.port or 80), _CodeCatcher) as server:
            while _CodeCatcher.code is None:
                server.handle_request()
        if _CodeCatcher.state != state:
            print("error: state mismatch on the callback — refusing the code")
            return 1
        code = _CodeCatcher.code
    else:
        pasted = input("3. Paste the redirected URL (or just the code): ").strip()
        query = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
        code = query.get("code", [pasted])[0]

    tokens = client.exchange_code(code, redirect_uri)
    store_tokens(creds, tokens, time.time())
    print("4. Granted scopes:", tokens.get("scope", "?").replace(",", " "))
    return 0


# --- entry --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m social", description=__doc__)
    parser.add_argument("--env-file", type=Path, help="credentials file (default ~/.config/codecrew/social.env)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="prove the credentials work without posting")

    post = sub.add_parser("post", help="publish one post to one or more networks")
    post.add_argument("--to", action="append", choices=NETWORKS, default=[], help="repeatable")
    post.add_argument("--text")
    post.add_argument("--text-file")
    post.add_argument("--bluesky-text-file", help="override the text for Bluesky (300 graphemes)")
    post.add_argument("--linkedin-text-file", help="override the text for LinkedIn")
    post.add_argument("--link", help="URL to attach as a link card / article")
    post.add_argument("--title", help="title for the link card")
    post.add_argument("--description", help="description for the link card")
    post.add_argument("--dry-run", action="store_true", help="print the requests; send nothing")

    auth = sub.add_parser("auth", help="re-consent a network (browser leg for a human)")
    auth_sub = auth.add_subparsers(dest="network", required=True)
    li = auth_sub.add_parser("linkedin")
    li.add_argument("--redirect-uri", help="registered redirect URI (default LINKEDIN_REDIRECT_URI or http://localhost:8765/callback)")
    li.add_argument("--scope", action="append", help="repeatable; default is the app's known scope set")
    li.add_argument("--paste", action="store_true", help="paste the code instead of listening on localhost")
    return parser


def main(argv: list[str] | None = None, transport=None, environ: dict[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    creds = load_credentials(args.env_file, environ)
    transport = transport or UrllibTransport()
    try:
        if args.command == "check":
            return cmd_check(args, creds, transport)
        if args.command == "post":
            return cmd_post(args, creds, transport)
        if args.command == "auth":
            return cmd_auth_linkedin(args, creds, transport)
    except MissingCredential as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    return 2
