"""``python -m social`` — check credentials, lint a text, post or reply, mint tokens.

``--account radiusred`` (the default) or ``--account codecrew`` picks whose
credentials every verb uses; LinkedIn is Radius Red's alone.
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from . import bluesky, linkedin, lint as lintmod, x
from .config import ACCOUNTS, DEFAULT_ACCOUNT, Credentials, MissingCredential, load_credentials
from .transport import ApiError, UrllibTransport

NETWORKS = ("bluesky", "linkedin", "x")
REPLY_NETWORKS = ("bluesky", "x")
# LinkedIn posts as the Radius Red Page; no other account has one.
LINKEDIN_ACCOUNT = DEFAULT_ACCOUNT
REFRESH_AHEAD = 7 * 24 * 3600  # refresh when the access token has under a week left


def _stamp(epoch: int | float) -> str:
    return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%d")


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


def _interactive() -> bool:
    """Whether stdin is a terminal a human can type into. The auth commands
    wait for typed input, and ``input()`` on a pipe raises EOFError after the
    request token has already been minted (www#95)."""
    stdin = sys.stdin
    return stdin is not None and stdin.isatty()


def _no_linkedin_for(creds: Credentials) -> None:
    """LinkedIn is Radius Red's only: refuse before any network call."""
    if creds.account != LINKEDIN_ACCOUNT:
        raise SystemExit(
            f"error: LinkedIn posts as the Radius Red Page only; --account {creds.account} has no LinkedIn "
            f"(drop --to linkedin, or use --account {LINKEDIN_ACCOUNT})"
        )


# --- LinkedIn token care ------------------------------------------------


def linkedin_client(creds: Credentials, transport) -> linkedin.LinkedIn:
    _no_linkedin_for(creds)
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
    # A token and its expiry are one fact: if the token itself came from the
    # environment (an orchestrator's copy), do not write its new expiry next
    # to the file's stale token — the next run would trust it and post 401.
    for token_key in ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_REFRESH_TOKEN"):
        if token_key in creds.from_env:
            creds.values[f"{token_key}_EXPIRES_AT"] = updates.pop(f"{token_key}_EXPIRES_AT", "")
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


# --- Bluesky and X clients -----------------------------------------------


def bluesky_client(creds: Credentials, transport, dry_run: bool = False) -> bluesky.Bluesky:
    if dry_run:
        return bluesky.Bluesky(transport, creds.get("BSKY_HANDLE", "<handle>"), "", creds.get("BSKY_PDS", bluesky.DEFAULT_PDS))
    return bluesky.Bluesky(
        transport, creds.require("BSKY_HANDLE"), creds.require("BSKY_APP_PASSWORD"),
        creds.get("BSKY_PDS", bluesky.DEFAULT_PDS),
    )


def x_client(creds: Credentials, transport, dry_run: bool = False) -> x.X:
    if dry_run:
        return x.X(transport, creds.get("X_HANDLE", "<handle>"), "", "", "", "")
    return x.X(
        transport,
        creds.require("X_HANDLE"),
        creds.require("X_API_KEY"),
        creds.require("X_API_SECRET"),
        creds.require("X_ACCESS_TOKEN"),
        creds.require("X_ACCESS_TOKEN_SECRET"),
    )


# --- commands -----------------------------------------------------------


def cmd_check(args, creds: Credentials, transport) -> int:
    """Prove each network's credentials belong to the account they are filed
    under: the Bluesky session's handle and the X tokens' username must be the
    account's configured handles. Another account's tokens are a failure."""
    failures = 0
    try:
        client = bluesky_client(creds, transport)
        session = client.login()
        handle = session.get("handle", "")
        if handle.lower() != client.handle.lower():
            failures += 1
            print(f"bluesky: FAILED — the session is {handle}, not {client.handle} ({creds.key('BSKY_HANDLE')})")
        else:
            print(f"bluesky: ok — {handle} ({session.get('did')})")
    except (MissingCredential, ApiError) as err:
        failures += 1
        print(f"bluesky: FAILED — {err}")

    if creds.account != LINKEDIN_ACCOUNT:
        print(f"linkedin: skipped — Radius Red's Page only; --account {creds.account} has no LinkedIn")
        return _check_x(creds, transport, failures)

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
    return _check_x(creds, transport, failures)


def _check_x(creds: Credentials, transport, failures: int) -> int:
    try:
        client = x_client(creds, transport)
        me = client.me()
        username = me.get("username", "")
        if username.lower() != client.handle.lower():
            failures += 1
            print(f"x: FAILED — the tokens belong to @{username}, not @{client.handle} ({creds.key('X_HANDLE')})")
        else:
            print(f"x: ok — @{username} ({me.get('id')})")
    except (MissingCredential, ApiError) as err:
        failures += 1
        print(f"x: FAILED — {err}")
    return 1 if failures else 0


def _read_text(args, network: str) -> str:
    override = getattr(args, f"{network}_text_file", None)
    path = override or args.text_file
    if path:
        try:
            return Path(path).read_text()
        except OSError as err:
            raise SystemExit(f"error: cannot read the {network} text: {err}") from None
    if args.text:
        return args.text
    raise SystemExit("error: give --text, --text-file, or a per-network --<network>-text-file")


def _dry_reply_refs(ref: str) -> dict:
    """What a dry run prints in place of the Bluesky reply refs it does not
    fetch: the thread is read at send time, and a dry run touches no network."""
    repo, rkey = bluesky.parse_post_ref(ref)
    parent = {"uri": ref if ref.startswith("at://") else f"at://{repo}/{bluesky.POST_COLLECTION}/{rkey}", "cid": "<fetched at send time>"}
    return {"root": {"uri": "<the thread root, fetched at send time>", "cid": "<fetched at send time>"}, "parent": parent}


def _x_reply_text(args) -> str | None:
    """The link reply's text, checked before any network call: it must fit,
    and the post it answers must carry no URL — the URL is why the reply
    exists, and a URL in the body would be billed as a URL post anyway."""
    if not args.x_reply_file:
        return None
    if args.reply_to:
        raise SystemExit("error: --x-reply-file posts a new thread; it cannot be combined with --reply-to")
    if "x" not in args.to:
        raise SystemExit("error: --x-reply-file needs --to x")
    return Path(args.x_reply_file).read_text()


def _print_lint(network: str, failures: list[lintmod.Failure]) -> None:
    for failure in failures:
        print(f"{network}: {failure}")


def cmd_lint(args, creds: Credentials, transport) -> int:
    """The guide's mechanical rules against one text for one network: each
    failure on its own line with the rule and the fragment; exit 1 on any."""
    failures = lintmod.lint(_read_text(args, args.to), args.to, reply=args.reply)
    if failures:
        _print_lint(args.to, failures)
        return 1
    print(f"{args.to}: lint ok")
    return 0


def check_texts(args, targets: list[str], x_reply_text: str | None = None) -> bool:
    """Lint every text before any network call: each target's post, and the
    X link reply. A reply is linted as one — it carries the link, so the
    URL-in-body rule does not apply to it. False, with the failures on
    stderr, when a text fails; ``--skip-lint`` passes everything through
    with one line saying so."""
    if args.skip_lint:
        _say("lint skipped (--skip-lint): sending the text as approved")
        return True
    texts = [(network, _read_text(args, network), bool(args.reply_to)) for network in targets]
    if x_reply_text is not None:
        texts.append(("x reply", x_reply_text, True))
    clean = True
    for label, text, reply in texts:
        failures = lintmod.lint(text, label.split()[0], reply=reply)
        if failures:
            clean = False
            _say(f"error: the {label} text fails lint (announcements/README.md); --skip-lint sends an approved text")
            for failure in failures:
                _say(f"{label}: {failure}")
    return clean


def cmd_post(args, creds: Credentials, transport) -> int:
    targets = list(dict.fromkeys(args.to))
    if not targets:
        raise SystemExit("error: --to bluesky, --to linkedin and/or --to x is required")
    if args.reply_to:
        if len(targets) != 1 or targets[0] not in REPLY_NETWORKS:
            raise SystemExit("error: --reply-to replies on one network per invocation: --to bluesky or --to x")
        if targets[0] == "x":
            x.parse_post_ref(args.reply_to)  # a bad ref is a usage error, not a billed call
        else:
            bluesky.parse_post_ref(args.reply_to)
    x_reply_text = _x_reply_text(args)
    if not check_texts(args, targets, x_reply_text):
        return 1

    requests: dict[str, list[dict]] = {}
    clients: dict[str, object] = {}
    if "bluesky" in targets:
        record = bluesky.build_post(_read_text(args, "bluesky"), args.link, args.title, args.description)
        client = bluesky_client(creds, transport, dry_run=args.dry_run)
        if args.dry_run:
            if args.reply_to:
                record["reply"] = _dry_reply_refs(args.reply_to)
            requests["bluesky"] = [client.create_record_request(record)]
        else:
            clients["bluesky"] = (client, record)
    if "linkedin" in targets:
        _no_linkedin_for(creds)
        org = creds.get("LINKEDIN_ORG_URN") if args.dry_run else creds.require("LINKEDIN_ORG_URN")
        body = linkedin.build_post(org or "urn:li:organization:<id>", _read_text(args, "linkedin"), args.link, args.title, args.description)
        if args.dry_run:
            client = linkedin.LinkedIn(transport, "", "", version=creds.get("LINKEDIN_VERSION", linkedin.DEFAULT_VERSION))
            requests["linkedin"] = [client.post_request(body)]
        else:
            client = linkedin_client(creds, transport)
            clients["linkedin"] = (client, body)
    if "x" in targets:
        # No card on X, and no URL in the body: the link goes in the reply
        # (announcements/README.md, "Links"); lint has already refused a body with one.
        if args.link or args.title or args.description:
            _say("x: --link/--title/--description are not applied on X; links go in the reply (--x-reply-file)")
        text = _read_text(args, "x")
        body = x.build_post(text, reply_to=args.reply_to)
        reply_body = None
        if x_reply_text is not None:
            found = x.urls_in(body["text"])
            if found:
                raise ValueError(
                    "the X post body carries a URL (" + ", ".join(found) + "); with --x-reply-file the links go "
                    "in the reply and the body must carry none"
                )
            reply_body = x.build_post(x_reply_text)
            # Filled with the post's ID once it exists; a dry run shows the slot.
            reply_body["reply"] = {"in_reply_to_tweet_id": "<the post's id>" if args.dry_run else None}
        client = x_client(creds, transport, dry_run=args.dry_run)
        if args.dry_run:
            requests["x"] = [client.post_request(body)] + ([client.post_request(reply_body)] if reply_body else [])
        else:
            clients["x"] = (client, body, reply_body)

    if args.dry_run:
        for network in targets:
            for request in requests[network]:
                print(json.dumps({"network": network, "dry_run": True, "request": request}, indent=2, ensure_ascii=False))
        return 0

    failures = 0
    for network in targets:
        client, payload, *rest = clients[network]
        try:
            if network == "linkedin":
                ensure_linkedin_token(creds, client)
            elif network == "bluesky" and args.reply_to:
                payload["reply"] = client.reply_refs(args.reply_to)
            result = client.post(payload)
            print(json.dumps({"network": network, **result}))
        except (ApiError, ValueError) as err:
            failures += 1
            print(json.dumps({"network": network, "error": str(err)}))
            continue
        reply_body = rest[0] if rest else None
        if reply_body is not None:
            reply_body["reply"]["in_reply_to_tweet_id"] = result["id"]
            try:
                reply = client.post(reply_body)
                print(json.dumps({"network": network, "reply_to": result["id"], **reply}))
            except ApiError as err:
                failures += 1
                print(json.dumps({"network": network, "reply_to": result["id"], "error": str(err)}))
                env = f"--env-file {args.env_file} " if args.env_file else ""
                _say(
                    f"x: the post is up at {result['url']} but its reply failed; retry the reply alone with:\n"
                    f"  uv run -m social {env}--account {creds.account} post --to x --reply-to {result['id']} "
                    f"--text-file {args.x_reply_file}"
                )
    return 1 if failures else 0


def cmd_comment(args, creds: Credentials, transport) -> int:
    """The first comment on a LinkedIn share — where a post's links go, since
    inline URLs cost the post reach (announcements/README.md)."""
    _no_linkedin_for(creds)
    text = Path(args.text_file).read_text() if args.text_file else args.text
    if not text:
        raise SystemExit("error: give --text or --text-file")
    org = creds.get("LINKEDIN_ORG_URN") if args.dry_run else creds.require("LINKEDIN_ORG_URN")
    body = linkedin.build_comment(org or "urn:li:organization:<id>", args.urn, text)
    if args.dry_run:
        client = linkedin.LinkedIn(transport, "", "", version=creds.get("LINKEDIN_VERSION", linkedin.DEFAULT_VERSION))
        print(json.dumps({"network": "linkedin", "dry_run": True, "request": client.comment_request(body)}, indent=2, ensure_ascii=False))
        return 0
    client = linkedin_client(creds, transport)
    try:
        ensure_linkedin_token(creds, client)
        print(json.dumps({"network": "linkedin", **client.comment(body)}))
    except ApiError as err:
        print(json.dumps({"network": "linkedin", "error": str(err)}))
        return 1
    return 0


def parse_callback(url_or_code: str) -> tuple[str | None, str | None]:
    """(code, state) from a redirected URL — or (the string itself, None)
    when a bare code was pasted."""
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url_or_code).query)
    if "code" in query:
        return query["code"][0], query.get("state", [None])[0]
    return (url_or_code or None), None


class _CodeCatcher(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    state: str | None = None

    @classmethod
    def reset(cls):
        cls.code = cls.state = None

    def do_GET(self):  # noqa: N802 — http.server's name
        type(self).code, type(self).state = parse_callback(self.path)
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
    parsed = urllib.parse.urlparse(redirect_uri)
    listening = parsed.hostname in ("localhost", "127.0.0.1") and not args.paste
    if not listening and not _interactive():
        _say("error: auth linkedin --paste reads the code from stdin and needs an interactive terminal; run it from a shell (nothing requested, nothing stored)")
        return 1
    url, state = client.auth_url(redirect_uri, tuple(args.scope) if args.scope else linkedin.DEFAULT_SCOPES)
    print("1. Make sure this redirect URI is registered on the app's Auth tab:", redirect_uri)
    print("2. Signed in as the Page admin, open:\n\n   " + url + "\n")

    code = None
    if listening:
        print(f"3. Waiting for LinkedIn to redirect to {redirect_uri} …")
        _CodeCatcher.reset()
        with http.server.HTTPServer((parsed.hostname, parsed.port or 80), _CodeCatcher) as server:
            while _CodeCatcher.code is None:
                server.handle_request()
        if _CodeCatcher.state != state:
            print("error: state mismatch on the callback — refusing the code")
            return 1
        code = _CodeCatcher.code
    else:
        pasted = input("3. Paste the redirected URL (or just the code): ").strip()
        code, pasted_state = parse_callback(pasted)
        if pasted_state is not None and pasted_state != state:
            print("error: state mismatch on the pasted URL — refusing the code")
            return 1

    tokens = client.exchange_code(code, redirect_uri)
    store_tokens(creds, tokens, time.time())
    print("4. Granted scopes:", tokens.get("scope", "?").replace(",", " "))
    return 0


def cmd_auth_x(args, creds: Credentials, transport) -> int:
    """Mint X user tokens for the account under the shared app: the PIN-based
    OAuth 1.0a flow. Someone signed in to X as the account clicks through and
    reads the PIN back; the tokens are checked against the account's handle
    and persisted under its key names, never printed."""
    expected = creds.require("X_HANDLE").lstrip("@")
    consumer_key, consumer_secret = creds.require("X_API_KEY"), creds.require("X_API_SECRET")
    if not _interactive():
        _say("error: auth x reads the PIN from stdin and needs an interactive terminal; run it from a shell (nothing requested, nothing stored)")
        return 1
    # A token endpoint's error body may reflect what was sent to it, so an
    # ApiError from either leg is reported by step and status alone — never
    # its body, never through main's traceback.
    try:
        temporary = x.request_token(transport, consumer_key, consumer_secret)
    except ApiError as err:
        print(
            f"error: X refused the request token (HTTP {err.response.status}); check X_API_KEY and X_API_SECRET "
            "and that OAuth 1.0a is enabled on the app — nothing stored"
        )
        return 1
    print(f"1. Signed in to X as @{expected}, open:\n\n   " + x.authorize_url(temporary["oauth_token"]) + "\n")
    print("2. Approve the app; X shows a PIN.")
    pin = input("3. Enter the PIN: ").strip()
    if not pin:
        print("error: no PIN given")
        return 1
    try:
        tokens = x.access_token(transport, consumer_key, consumer_secret, temporary["oauth_token"], temporary["oauth_token_secret"], pin)
    except ApiError as err:
        print(
            f"error: X refused the PIN exchange (HTTP {err.response.status}); the PIN may be wrong or expired, "
            "run auth x again — nothing stored"
        )
        return 1
    username = tokens.get("screen_name", "")
    if username.lower() != expected.lower():
        print(f"error: the tokens belong to @{username}, not @{expected} ({creds.key('X_HANDLE')}) — nothing stored")
        return 1
    skipped = creds.persist({"X_ACCESS_TOKEN": tokens["oauth_token"], "X_ACCESS_TOKEN_SECRET": tokens["oauth_token_secret"]})
    if skipped:
        _say(
            "warning: the X tokens were NOT persisted for " + ", ".join(skipped)
            + " (they came from the environment) — update your orchestrator's copy"
        )
    stored = ", ".join(creds.key(k) for k in ("X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET") if creds.key(k) not in skipped)
    print(f"4. Tokens for @{username} ({tokens.get('user_id', '?')})" + (f" stored as {stored}" if stored else ""))
    return 0


# --- entry --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m social", description=__doc__)
    parser.add_argument("--env-file", type=Path, help="credentials file (default ~/.config/radiusred/social.env)")
    parser.add_argument(
        "--account", choices=tuple(ACCOUNTS), default=DEFAULT_ACCOUNT,
        help="whose accounts to use (default radiusred; codecrew reads the CODECREW_* keys, and has no LinkedIn)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="prove the credentials work, and belong to the account, without posting")

    post = sub.add_parser("post", help="publish one post to one or more networks")
    post.add_argument("--to", action="append", choices=NETWORKS, default=[], help="repeatable")
    post.add_argument("--text")
    post.add_argument("--text-file")
    post.add_argument("--bluesky-text-file", help="override the text for Bluesky (300 graphemes)")
    post.add_argument("--linkedin-text-file", help="override the text for LinkedIn")
    post.add_argument("--x-text-file", help="override the text for X (280 weighted characters, every URL 23)")
    post.add_argument("--link", help="URL to attach as a link card / article (Bluesky, LinkedIn; not X)")
    post.add_argument("--title", help="title for the link card")
    post.add_argument("--description", help="description for the link card")
    post.add_argument("--reply-to", help="publish as a reply: an X post ID or status URL, or a Bluesky at:// URI or bsky.app post URL (one --to)")
    post.add_argument("--x-reply-file", help="X only: post this file's text as a reply to the post, in one go (the body must then carry no URL)")
    post.add_argument("--dry-run", action="store_true", help="print the requests; send nothing")
    post.add_argument("--skip-lint", action="store_true", help="send a text the operator approved even though lint fails it")

    lint = sub.add_parser("lint", help="check a text against the guide's mechanical rules (announcements/README.md)")
    lint.add_argument("--to", choices=NETWORKS, required=True, help="the network the text is for")
    lint.add_argument("--text")
    lint.add_argument("--text-file")
    lint.add_argument("--reply", action="store_true", help="the text is a reply, which may carry the link")

    comment = sub.add_parser("comment", help="comment on a LinkedIn share (the first-comment link slot)")
    comment.add_argument("--urn", required=True, help="the share URN the post printed, e.g. urn:li:share:123")
    comment.add_argument("--text")
    comment.add_argument("--text-file")
    comment.add_argument("--dry-run", action="store_true", help="print the request; send nothing")

    auth = sub.add_parser("auth", help="mint or re-consent a network's tokens (browser leg for a human)")
    auth_sub = auth.add_subparsers(dest="network", required=True)
    auth_sub.add_parser("x", help="PIN-based OAuth 1.0a: user tokens for --account under the shared X app")
    li = auth_sub.add_parser("linkedin")
    li.add_argument("--redirect-uri", help="registered redirect URI (default LINKEDIN_REDIRECT_URI or http://localhost:8765/callback)")
    li.add_argument("--scope", action="append", help="repeatable; default is the app's known scope set")
    li.add_argument("--paste", action="store_true", help="paste the code instead of listening on localhost")
    return parser


def main(argv: list[str] | None = None, transport=None, environ: dict[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    creds = load_credentials(args.env_file, environ).scoped(args.account)
    transport = transport or UrllibTransport()
    try:
        if args.command == "check":
            return cmd_check(args, creds, transport)
        if args.command == "post":
            return cmd_post(args, creds, transport)
        if args.command == "lint":
            return cmd_lint(args, creds, transport)
        if args.command == "comment":
            return cmd_comment(args, creds, transport)
        if args.command == "auth" and args.network == "x":
            return cmd_auth_x(args, creds, transport)
        if args.command == "auth":
            return cmd_auth_linkedin(args, creds, transport)
    except MissingCredential as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    return 2
