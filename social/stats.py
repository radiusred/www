"""``social stats``: per-post reach and follower counts on X and Bluesky for
one account over a window of UTC days. Read-only: every request is a GET.

X bills each read (pay-per-use: $0.005 per post read, $0.010 per user read),
so the most a run can cost is known before the first read, and the CLI stops
when it is over the budget. Bluesky's public AppView is free and needs no
credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from . import bluesky, x
from .config import Credentials, MissingCredential
from .transport import ApiError

DEFAULT_DAYS = 7
X_POST_READ = Decimal("0.005")
X_USER_READ = Decimal("0.010")
DEFAULT_X_BUDGET = Decimal("0.50")
DEFAULT_X_MAX_POSTS = 50
# X refuses an end_time later than 10 seconds before the request.
X_END_MARGIN = timedelta(seconds=30)
X_METRICS = {
    "impressions": "impression_count",
    "likes": "like_count",
    "reposts": "retweet_count",
    "replies": "reply_count",
    "quotes": "quote_count",
}
BLUESKY_METRICS = {"likes": "likeCount", "reposts": "repostCount", "replies": "replyCount", "quotes": "quoteCount"}


@dataclass(frozen=True)
class Window:
    since: date
    until: date  # included

    @property
    def start(self) -> datetime:
        return datetime(self.since.year, self.since.month, self.since.day, tzinfo=timezone.utc)

    @property
    def end(self) -> datetime:
        """The first instant after the window: ``until`` + 1 day, 00:00 UTC."""
        return datetime(self.until.year, self.until.month, self.until.day, tzinfo=timezone.utc) + timedelta(days=1)

    def as_dict(self) -> dict:
        return {"since": self.since.isoformat(), "until": self.until.isoformat(), "start": _rfc3339(self.start), "end": _rfc3339(self.end)}


def _rfc3339(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(value: str, flag: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{flag} {value!r} is not a date (YYYY-MM-DD)") from None


def window(since: str | None, until: str | None, now: datetime) -> Window:
    """Both dates UTC and included. With neither, the last ``DEFAULT_DAYS``
    full days before today; with one, the other is ``DEFAULT_DAYS`` away."""
    today = now.astimezone(timezone.utc).date()
    end = _day(until, "--until") if until else None
    begin = _day(since, "--since") if since else None
    if end is None:
        end = begin + timedelta(days=DEFAULT_DAYS - 1) if begin else today - timedelta(days=1)
    if begin is None:
        begin = end - timedelta(days=DEFAULT_DAYS - 1)
    if begin > end:
        raise ValueError(f"--since {begin} is after --until {end}")
    if begin > today:
        raise ValueError(f"--since {begin} is in the future")
    return Window(begin, end)


def max_x_cost(max_posts: int) -> Decimal:
    """The most an X read can cost: ``max_posts`` post reads and one user read."""
    return max_posts * X_POST_READ + X_USER_READ


def cost_line(max_posts: int, budget: Decimal) -> str:
    return (
        f"x: this run reads at most {max_posts} posts and 1 user: at most ${max_x_cost(max_posts):.3f} "
        f"(posts ${X_POST_READ} each, the user ${X_USER_READ}; --x-budget ${budget:.2f})"
    )


def _totals(posts: list[dict], metrics) -> dict:
    return {"posts": len(posts), **{m: sum(p[m] for p in posts) for m in metrics}}


def x_report(client: x.X, win: Window, max_posts: int, now: datetime, spend: dict) -> dict:
    """One user read (followers, and the tokens' owner checked against the
    handle), then the posts in the window. ``spend`` counts the reads that
    came back, page by page, for the cost estimate: a failure on a later page
    keeps the reads before it."""
    me = client.me_metrics()
    spend["users_read"] += 1
    username = me.get("username", "")
    if username.lower() != client.handle.lower():
        raise ValueError(f"the X tokens belong to @{username}, not @{client.handle}")
    end = min(win.end, now - X_END_MARGIN)

    def counted(n: int) -> None:
        spend["posts_read"] += n

    found, truncated = client.posts(me["id"], _rfc3339(win.start), _rfc3339(end), max_posts, on_page=counted)
    posts = []
    for post in found:
        metrics = post.get("public_metrics") or {}
        posts.append({
            "id": post["id"],
            "url": client.status_url(post["id"]),
            "created_at": post.get("created_at", ""),
            "reply": bool(post.get("in_reply_to_user_id")),
            "text": post.get("text", ""),
            **{name: int(metrics.get(key, 0)) for name, key in X_METRICS.items()},
        })
    return {
        "handle": client.handle,
        "followers": int((me.get("public_metrics") or {}).get("followers_count", 0)),
        "posts": posts,
        "totals": _totals(posts, X_METRICS),
        "truncated": truncated,
    }


def bluesky_report(transport, handle: str, win: Window) -> dict:
    who = bluesky.profile(transport, handle)
    found, truncated = bluesky.author_posts(transport, who["did"], win.start, win.end)
    posts = []
    for post in found:
        record = post.get("record") or {}
        rkey = post["uri"].rsplit("/", 1)[-1]
        posts.append({
            "uri": post["uri"],
            "url": f"https://bsky.app/profile/{who.get('handle', handle)}/post/{rkey}",
            "created_at": record.get("createdAt", ""),
            "reply": "reply" in record,
            "text": record.get("text", ""),
            **{name: int(post.get(key, 0)) for name, key in BLUESKY_METRICS.items()},
        })
    return {
        "handle": who.get("handle", handle),
        "followers": int(who.get("followersCount", 0)),
        "posts": posts,
        "totals": _totals(posts, BLUESKY_METRICS),
        "truncated": truncated,
    }


def report(creds: Credentials, transport, win: Window, max_posts: int, budget: Decimal, now: datetime, x_client) -> dict:
    """The whole report. A network that fails carries ``error`` in place of
    its numbers; the other network still reports. ``x_client`` builds the X
    client from the credentials (the CLI's own builder)."""
    networks: dict[str, dict] = {}
    try:
        networks["bluesky"] = bluesky_report(transport, creds.require("BSKY_HANDLE"), win)
    except (MissingCredential, ApiError, ValueError, KeyError) as err:
        networks["bluesky"] = {"handle": creds.get("BSKY_HANDLE", ""), "error": str(err)}
    spend = {"users_read": 0, "posts_read": 0}
    try:
        networks["x"] = x_report(x_client(creds, transport), win, max_posts, now, spend)
    except (MissingCredential, ApiError, ValueError, KeyError) as err:
        networks["x"] = {"handle": creds.get("X_HANDLE", ""), "error": str(err)}
    spent = spend["users_read"] * X_USER_READ + spend["posts_read"] * X_POST_READ
    return {
        "account": creds.account,
        "window": win.as_dict(),
        "networks": networks,
        "x_cost": {
            "max_posts": max_posts,
            "max_usd": float(max_x_cost(max_posts)),
            "budget_usd": float(budget),
            "users_read": spend["users_read"],
            "posts_read": spend["posts_read"],
            "spent_usd": float(spent),
        },
    }


def _row(label: str, values: dict, metrics) -> str:
    return f"  {label:<20}" + "  ".join(f"{m} {values[m]}" for m in metrics)


def render(rep: dict) -> str:
    """The report as text for a person: a block per network, a row per post
    and one for the totals, then the X cost."""
    win = rep["window"]
    lines = [f"{rep['account']}: {win['since']} to {win['until']} (UTC, both days included)"]
    for network, metrics, at in (("bluesky", BLUESKY_METRICS, ""), ("x", X_METRICS, "@")):
        part = rep["networks"][network]
        lines.append("")
        if "error" in part:
            lines.append(f"{network} {at}{part['handle']}: FAILED — {part['error']}")
            continue
        totals = part["totals"]
        lines.append(f"{network} {at}{part['handle']}: {part['followers']} followers, {totals['posts']} posts")
        for post in part["posts"]:
            label = post["created_at"][:16].replace("T", " ") + (" reply" if post["reply"] else "")
            lines.append(_row(label, post, metrics) + f"  {post['url']}")
        lines.append(_row("total", totals, metrics))
        if part["truncated"]:
            lines.append("  (more posts in the window were not read)")
    cost = rep["x_cost"]
    lines.append("")
    lines.append(
        f"x cost: about ${cost['spent_usd']:.3f} ({cost['users_read']} user read, {cost['posts_read']} post reads); "
        f"at most ${cost['max_usd']:.3f}"
    )
    return "\n".join(lines)
