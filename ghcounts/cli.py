"""``python -m ghcounts`` — stars now, new stars, and the issues, pull requests
and discussions outside people opened, per repository and in total.

Outside means not a bot and not a member of the repository's owner org.
Read-only: GETs and GraphQL queries, nothing else.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

from social.transport import ApiError, UrllibTransport

from .counts import KINDS, Window, report
from .github import GitHub, GraphQLError

DEFAULT_REPOS = (
    "radiusred/tradedesk",
    "radiusred/tradedesk-marketdata",
    "radiusred/tradedesk-miner",
    "radiusred/ha-sinkhole",
)
WHO_RUNS_IT = "Run by the chief of staff, with its own GitHub App token in GH_TOKEN."
REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")
LABELS = {
    "new_stars": "new stars",
    "issues": "issues by outside people",
    "pull_requests": "pull requests by outside people",
    "discussions": "discussions by outside people",
}


def _repo(value: str) -> str:
    if not REPO_RE.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not owner/name")
    return value


def _day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a date (YYYY-MM-DD)") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ghcounts",
        description=__doc__,
        epilog=WHO_RUNS_IT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", action="append", type=_repo, metavar="OWNER/NAME",
                        help="a repository to count (repeatable; default: " + ", ".join(DEFAULT_REPOS) + ")")
    parser.add_argument("--since", type=_day, help="first day of the window, UTC (default: 7 days before --until)")
    parser.add_argument("--until", type=_day, help="last day of the window, UTC, included (default: yesterday)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    return parser


def window_from(args, today: date) -> Window:
    """The last 7 full days by default; ``--until`` alone keeps 7 days,
    ``--since`` alone runs to yesterday."""
    until = args.until or Window.last_full_days(today).until
    since = args.since or Window.last_full_days(until + timedelta(days=1)).since
    return Window(since, until)


def render(data: dict) -> str:
    window = data["window"]
    lines = [f"ghcounts {window['since']} to {window['until']} (UTC, both days included)"]
    for row in data["repos"]:
        lines += ["", row["repo"], f"  stars now: {row['stars']}"]
        for kind in KINDS:
            block = row[kind]
            note = " (Discussions are off)" if kind == "discussions" and not block["enabled"] else ""
            lines.append(f"  {LABELS[kind]}: {block['count']}{note}")
            lines += [f"    {i['date'][:10]}  {i['author']}  {i['url']}" for i in block["items"]]
        if row["member_list"] == "not readable":
            lines.append("  org member list: not readable with this token; outside is judged from author_association")
    totals = data["totals"]
    lines += ["", "total", f"  stars now: {totals['stars']}"]
    lines += [f"  {LABELS[kind]}: {totals[kind]}" for kind in KINDS]
    return "\n".join(lines)


def main(argv: list[str] | None = None, transport=None, environ: dict[str, str] | None = None,
         today: date | None = None) -> int:
    args = build_parser().parse_args(argv)
    environ = os.environ if environ is None else environ
    today = today or datetime.now(timezone.utc).date()
    window = window_from(args, today)
    if window.since > window.until:
        print(f"error: --since {window.since} is after --until {window.until}", file=sys.stderr)
        return 2
    token = environ.get("GH_TOKEN")
    if not token:
        print("error: GH_TOKEN is not set; mint the App token first: "
              "export GH_TOKEN=$(gh codecrew identity token <slug>)", file=sys.stderr)
        return 2
    gh = GitHub(transport or UrllibTransport(), token)
    try:
        data = report(gh, args.repo or list(DEFAULT_REPOS), window)
    except (ApiError, GraphQLError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0
