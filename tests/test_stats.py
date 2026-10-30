"""``social stats`` (M12-R1, M12-R3): reach and followers, read-only, with the
X cost guard. Every test runs on the fake transport; none reaches a network."""

import json
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from social import cli, stats, x

NOW = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
WINDOW = ["--since", "2026-10-23", "--until", "2026-10-29"]
DID = "did:plc:rr"


def _bsky_post(rkey, created, likes=0, reposts=0, replies=0, quotes=0, did=DID, reply=False):
    record = {"$type": "app.bsky.feed.post", "text": f"post {rkey}", "createdAt": created}
    if reply:
        record["reply"] = {"root": {"uri": "at://x/y/z", "cid": "c"}, "parent": {"uri": "at://x/y/z", "cid": "c"}}
    return {
        "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
        "cid": "c",
        "author": {"did": did, "handle": "example.bsky.social"},
        "record": record,
        "likeCount": likes, "repostCount": reposts, "replyCount": replies, "quoteCount": quotes,
        "indexedAt": created,
    }


def _tweet(id_, created, impressions=0, likes=0, reposts=0, replies=0, quotes=0, reply_to=None):
    post = {
        "id": id_, "text": f"tweet {id_}", "created_at": created,
        "public_metrics": {
            "impression_count": impressions, "like_count": likes, "retweet_count": reposts,
            "reply_count": replies, "quote_count": quotes, "bookmark_count": 9,
        },
    }
    if reply_to:
        post["in_reply_to_user_id"] = reply_to
    return post


def _queue_bluesky(transport, feed=None, followers=45):
    transport.expect("GET", "app.bsky.actor.getProfile", body={"did": DID, "handle": "example.bsky.social", "followersCount": followers})
    transport.expect("GET", "app.bsky.feed.getAuthorFeed", body={"feed": feed if feed is not None else [
        {"post": _bsky_post("3new", "2026-10-28T10:00:00.000Z", likes=5, reposts=2, replies=1, quotes=1)},
        # someone else's post, reposted by the account: not ours
        {"post": _bsky_post("3other", "2026-10-27T10:00:00.000Z", likes=99, did="did:plc:other"), "reason": {"$type": "app.bsky.feed.defs#reasonRepost"}},
        {"post": _bsky_post("3reply", "2026-10-25T10:00:00.000Z", likes=1, reply=True)},
        {"post": _bsky_post("3old", "2026-10-20T10:00:00.000Z", likes=50)},
    ], "cursor": "next"})


def _queue_x(transport, pages=None, username="example_uk", followers=120):
    transport.expect("GET", "/2/users/me", body={"data": {"id": "77", "username": username, "public_metrics": {"followers_count": followers}}})
    for page in pages if pages is not None else [
        {"data": [_tweet("2", "2026-10-28T12:00:00.000Z", impressions=300, likes=4, reposts=1),
                  _tweet("3", "2026-10-28T12:00:05.000Z", impressions=40, replies=2, reply_to="77")],
         "meta": {"next_token": "t2"}},
        {"data": [_tweet("1", "2026-10-24T08:00:00.000Z", impressions=60, quotes=1)], "meta": {}},
    ]:
        transport.expect("GET", "/2/users/77/tweets", body=page)


def _run(env_file, transport, *extra, account=()):
    return cli.main(["--env-file", str(env_file), *account, "stats", *WINDOW, *extra], transport=transport, environ={})


def _query(call):
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(call["url"]).query).items()}


# --- the window -----------------------------------------------------------


def test_the_default_window_is_the_last_seven_full_days():
    win = stats.window(None, None, NOW)
    assert (win.since.isoformat(), win.until.isoformat()) == ("2026-10-23", "2026-10-29")
    assert win.as_dict() == {
        "since": "2026-10-23", "until": "2026-10-29",
        "start": "2026-10-23T00:00:00Z", "end": "2026-10-30T00:00:00Z",
    }


def test_one_date_sets_the_other_seven_days_away():
    assert stats.window("2026-10-01", None, NOW).until.isoformat() == "2026-10-07"
    assert stats.window(None, "2026-10-07", NOW).since.isoformat() == "2026-10-01"


@pytest.mark.parametrize("since,until,message", [
    ("2026-10-29", "2026-10-23", "is after --until"),
    ("23/10/2026", None, "is not a date"),
    ("2026-11-02", "2026-11-05", "in the future"),
])
def test_a_bad_window_is_a_usage_error(env_file, refusing_transport, capsys, since, until, message):
    args = ["--env-file", str(env_file), "stats", "--since", since] + (["--until", until] if until else [])
    assert cli.main(args, transport=refusing_transport, environ={}) == 2
    assert message in capsys.readouterr().err


# --- the X cost guard -------------------------------------------------------


def test_the_maximum_cost_is_the_post_reads_plus_one_user_read():
    assert stats.max_x_cost(50) == Decimal("0.260")
    assert stats.max_x_cost(5) == Decimal("0.035")


def test_over_budget_stops_before_any_network_call(env_file, refusing_transport, capsys):
    rc = _run(env_file, refusing_transport, "--x-max-posts", "200")
    assert rc == 1
    captured = capsys.readouterr()
    assert "at most 200 posts and 1 user: at most $1.010" in captured.err
    assert "over --x-budget" in captured.err and "nothing read" in captured.err
    assert captured.out == ""


def test_a_raised_budget_lets_the_same_run_through(env_file, transport, capsys):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport, "--x-max-posts", "200", "--x-budget", "1.01") == 0
    assert "--x-budget $1.01" in capsys.readouterr().err


def test_the_cost_line_is_printed_before_the_first_read(env_file, transport, capsys):
    _queue_bluesky(transport)
    _queue_x(transport)
    seen = []

    def watching(method, url, headers=None, body=None):
        if not seen:
            seen.append(capsys.readouterr().err)
        return transport(method, url, headers, body)

    assert _run(env_file, watching) == 0
    assert "x: this run reads at most 50 posts and 1 user: at most $0.260" in seen[0]


@pytest.mark.parametrize("flag,value", [("--x-max-posts", "4"), ("--x-max-posts", "ten"), ("--x-budget", "-1"), ("--x-budget", "lots")])
def test_bad_guard_values_are_refused_by_the_parser(env_file, refusing_transport, flag, value):
    with pytest.raises(SystemExit) as exc:
        _run(env_file, refusing_transport, flag, value)
    assert exc.value.code == 2


def test_no_x_page_asks_for_more_posts_than_are_left(env_file, transport):
    _queue_bluesky(transport)
    _queue_x(transport, pages=[
        {"data": [_tweet(str(i), "2026-10-28T12:00:00.000Z") for i in range(100)], "meta": {"next_token": "t2"}},
        {"data": [_tweet(str(i), "2026-10-27T12:00:00.000Z") for i in range(100, 107)], "meta": {"next_token": "t3"}},
    ])
    assert _run(env_file, transport, "--x-max-posts", "107", "--x-budget", "1", "--json") == 0
    pages = [_query(c) for c in transport.calls if "/tweets" in c["url"]]
    assert [p["max_results"] for p in pages] == ["100", "7"]
    assert pages[1]["pagination_token"] == "t2"


def test_the_x_read_stops_when_fewer_than_a_page_are_left(env_file, transport, capsys):
    _queue_bluesky(transport)
    _queue_x(transport, pages=[
        {"data": [_tweet(str(i), "2026-10-28T12:00:00.000Z") for i in range(100)], "meta": {"next_token": "t2"}},
    ])
    assert _run(env_file, transport, "--x-max-posts", "103", "--x-budget", "1", "--json") == 0
    assert sum("/tweets" in c["url"] for c in transport.calls) == 1
    rep = json.loads(capsys.readouterr().out)
    assert rep["networks"]["x"]["truncated"] is True
    assert rep["x_cost"]["posts_read"] == 100 and rep["x_cost"]["spent_usd"] == 0.51


def test_x_end_time_is_clamped_when_the_window_ends_in_the_future(env_file, transport):
    _queue_bluesky(transport)
    _queue_x(transport, pages=[{"meta": {}}])
    args = cli.build_parser().parse_args(["--env-file", str(env_file), "stats", "--since", "2026-10-24", "--until", "2026-10-30", "--json"])
    creds = cli.load_credentials(env_file, {}).scoped(args.account)
    assert cli.cmd_stats(args, creds, transport, now=NOW) == 0
    tweets = _query(next(c for c in transport.calls if "/tweets" in c["url"]))
    assert tweets["start_time"] == "2026-10-24T00:00:00Z"
    assert tweets["end_time"] == "2026-10-30T08:59:30Z"


# --- the report ---------------------------------------------------------------


def test_json_schema_is_pinned(env_file, transport, capsys):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport, "--json") == 0
    rep = json.loads(capsys.readouterr().out)
    assert list(rep) == ["account", "window", "networks", "x_cost"]
    assert rep["account"] == "radiusred"
    assert rep["window"] == {"since": "2026-10-23", "until": "2026-10-29", "start": "2026-10-23T00:00:00Z", "end": "2026-10-30T00:00:00Z"}
    assert list(rep["networks"]) == ["bluesky", "x"]

    bsky = rep["networks"]["bluesky"]
    assert list(bsky) == ["handle", "followers", "posts", "totals", "truncated"]
    assert bsky["handle"] == "example.bsky.social" and bsky["followers"] == 45 and bsky["truncated"] is False
    assert bsky["posts"][0] == {
        "uri": f"at://{DID}/app.bsky.feed.post/3new",
        "url": "https://bsky.app/profile/example.bsky.social/post/3new",
        "created_at": "2026-10-28T10:00:00.000Z", "reply": False, "text": "post 3new",
        "likes": 5, "reposts": 2, "replies": 1, "quotes": 1,
    }
    assert [p["reply"] for p in bsky["posts"]] == [False, True]  # the repost and the older post are not counted
    assert bsky["totals"] == {"posts": 2, "likes": 6, "reposts": 2, "replies": 1, "quotes": 1}

    xs = rep["networks"]["x"]
    assert list(xs) == ["handle", "followers", "posts", "totals", "truncated"]
    assert xs["handle"] == "example_uk" and xs["followers"] == 120 and xs["truncated"] is False
    assert xs["posts"][0] == {
        "id": "2", "url": "https://x.com/example_uk/status/2", "created_at": "2026-10-28T12:00:00.000Z",
        "reply": False, "text": "tweet 2",
        "impressions": 300, "likes": 4, "reposts": 1, "replies": 0, "quotes": 0,
    }
    assert [p["reply"] for p in xs["posts"]] == [False, True, False]
    assert xs["totals"] == {"posts": 3, "impressions": 400, "likes": 4, "reposts": 1, "replies": 2, "quotes": 1}

    assert rep["x_cost"] == {
        "max_posts": 50, "max_usd": 0.26, "budget_usd": 0.5,
        "users_read": 1, "posts_read": 3, "spent_usd": 0.025,
    }


def test_every_request_is_a_read(env_file, transport):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport) == 0
    assert transport.calls and {c["method"] for c in transport.calls} == {"GET"}
    assert all(c["body"] is None for c in transport.calls)
    bsky = [c for c in transport.calls if "bsky" in c["url"]]
    assert all(c["url"].startswith("https://public.api.bsky.app/xrpc/") for c in bsky)
    assert all("Authorization" not in c["headers"] for c in bsky), "Bluesky is read with no credentials"


def test_x_reads_ask_for_the_metrics_and_leave_reposts_out(env_file, transport):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport) == 0
    me = next(c for c in transport.calls if "/2/users/me" in c["url"])
    assert _query(me) == {"user.fields": "public_metrics"}
    first = _query(next(c for c in transport.calls if "/tweets" in c["url"]))
    assert first["exclude"] == "retweets"
    assert "public_metrics" in first["tweet.fields"].split(",")
    assert (first["start_time"], first["end_time"]) == ("2026-10-23T00:00:00Z", "2026-10-30T00:00:00Z")


def test_the_x_signature_covers_the_query(env_file, transport):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport) == 0
    for call in (c for c in transport.calls if "api.x.com" in c["url"]):
        header = call["headers"]["Authorization"]
        oauth = {k: urllib.parse.unquote(v.strip('"')) for k, v in (p.split("=", 1) for p in header[len("OAuth "):].split(", "))}
        signature = oauth.pop("oauth_signature")
        base, _, _ = call["url"].partition("?")
        assert signature == x.sign("GET", base, {**_query(call), **oauth}, "xsecret", "xtokensecret")


def test_text_output_shows_each_post_and_the_totals(env_file, transport, capsys):
    _queue_bluesky(transport)
    _queue_x(transport)
    assert _run(env_file, transport) == 0
    out = capsys.readouterr().out
    assert out.startswith("radiusred: 2026-10-23 to 2026-10-29 (UTC, both days included)")
    assert "bluesky example.bsky.social: 45 followers, 2 posts" in out
    assert "x @example_uk: 120 followers, 3 posts" in out
    assert "impressions 400  likes 4  reposts 1  replies 2  quotes 1" in out
    assert "2026-10-28 12:00 reply" in out and "https://x.com/example_uk/status/3" in out
    assert "x cost: about $0.025 (1 user read, 3 post reads); at most $0.260" in out


def test_the_codecrew_account_reads_its_own_handles(env_file, transport, capsys):
    transport.expect("GET", "getProfile?actor=crew.example", body={"did": DID, "handle": "crew.example", "followersCount": 3})
    transport.expect("GET", "getAuthorFeed", body={"feed": []})
    _queue_x(transport, pages=[{"meta": {}}], username="crewworks")
    assert _run(env_file, transport, "--json", account=("--account", "codecrew")) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["account"] == "codecrew"
    assert rep["networks"]["x"]["handle"] == "crewworks"
    assert "oauth_token=\"crewtoken\"" in next(c for c in transport.calls if "api.x.com" in c["url"])["headers"]["Authorization"]


def test_tokens_of_another_account_fail_x_and_bluesky_still_reports(env_file, transport, capsys):
    _queue_bluesky(transport)
    transport.expect("GET", "/2/users/me", body={"data": {"id": "9", "username": "someone_else"}})
    assert _run(env_file, transport, "--json") == 1
    rep = json.loads(capsys.readouterr().out)
    assert rep["networks"]["x"] == {"handle": "example_uk", "error": "the X tokens belong to @someone_else, not @example_uk"}
    assert rep["networks"]["bluesky"]["totals"]["posts"] == 2
    assert not any("/tweets" in c["url"] for c in transport.calls), "no post is read for the wrong account"


def test_out_of_credits_is_reported_on_x_alone(env_file, transport, capsys):
    _queue_bluesky(transport)
    transport.expect("GET", "/2/users/me", status=402, body={"type": "https://api.x.com/2/problems/credits-depleted", "title": "CreditsDepleted"})
    assert _run(env_file, transport, "--json") == 1
    rep = json.loads(capsys.readouterr().out)
    assert "out of credits" in rep["networks"]["x"]["error"]
    assert rep["x_cost"]["users_read"] == 0 and rep["x_cost"]["spent_usd"] == 0
    assert "error" not in rep["networks"]["bluesky"]


def test_a_later_x_page_failure_keeps_the_reads_before_it(env_file, transport, capsys):
    _queue_bluesky(transport)
    transport.expect("GET", "/2/users/me", body={"data": {"id": "77", "username": "example_uk", "public_metrics": {"followers_count": 120}}})
    transport.expect("GET", "/2/users/77/tweets", body={
        "data": [_tweet(str(i), "2026-10-28T12:00:00.000Z") for i in range(100)], "meta": {"next_token": "t2"},
    })
    transport.expect("GET", "/2/users/77/tweets", status=429, body={"title": "Too Many Requests"})
    assert _run(env_file, transport, "--x-max-posts", "150", "--x-budget", "1", "--json") == 1
    rep = json.loads(capsys.readouterr().out)
    assert "HTTP 429" in rep["networks"]["x"]["error"]
    assert rep["x_cost"]["users_read"] == 1 and rep["x_cost"]["posts_read"] == 100
    assert rep["x_cost"]["spent_usd"] == 0.51


def test_bluesky_needs_only_the_handle(tmp_path, transport, capsys):
    env = tmp_path / "social.env"
    env.write_text("BSKY_HANDLE=example.bsky.social\n")
    _queue_bluesky(transport)
    assert _run(env, transport, "--json") == 1
    rep = json.loads(capsys.readouterr().out)
    assert rep["networks"]["bluesky"]["followers"] == 45
    assert "X_HANDLE is not set" in rep["networks"]["x"]["error"]
    assert all("api.x.com" not in c["url"] for c in transport.calls)


def test_a_bluesky_failure_leaves_x_reporting(env_file, transport, capsys):
    transport.expect("GET", "getProfile", status=400, body={"error": "InvalidRequest", "message": "Profile not found"})
    _queue_x(transport)
    assert _run(env_file, transport, "--json") == 1
    rep = json.loads(capsys.readouterr().out)
    assert "Bluesky profile read failed: HTTP 400" in rep["networks"]["bluesky"]["error"]
    assert rep["networks"]["x"]["totals"]["posts"] == 3


def test_the_bluesky_feed_is_paged_until_a_post_is_older_than_the_window(env_file, transport, capsys):
    transport.expect("GET", "getProfile", body={"did": DID, "handle": "example.bsky.social", "followersCount": 1})
    transport.expect("GET", "getAuthorFeed", body={"feed": [{"post": _bsky_post("3a", "2026-10-29T23:59:59.000Z")}], "cursor": "c1"})
    transport.expect("GET", "getAuthorFeed", body={"feed": [
        {"post": _bsky_post("3b", "2026-10-23T00:00:00.000Z")},
        {"post": _bsky_post("3c", "2026-10-22T23:59:59.000Z")},
    ], "cursor": "c2"})
    _queue_x(transport)
    assert _run(env_file, transport, "--json") == 0
    feeds = [_query(c) for c in transport.calls if "getAuthorFeed" in c["url"]]
    assert [f.get("cursor") for f in feeds] == [None, "c1"]
    assert feeds[0]["filter"] == "posts_with_replies" and feeds[0]["actor"] == DID
    rep = json.loads(capsys.readouterr().out)
    assert [p["uri"].rsplit("/", 1)[-1] for p in rep["networks"]["bluesky"]["posts"]] == ["3a", "3b"]


def test_a_post_after_the_window_is_not_counted(transport):
    transport.expect("GET", "getAuthorFeed", body={"feed": [
        {"post": _bsky_post("3late", "2026-10-30T00:00:00.000Z")},
        {"post": _bsky_post("3in", "2026-10-29T12:00:00.000Z")},
    ]})
    win = stats.window("2026-10-23", "2026-10-29", NOW)
    posts, truncated = stats.bluesky.author_posts(transport, DID, win.start, win.end)
    assert [p["uri"].rsplit("/", 1)[-1] for p in posts] == ["3in"] and truncated is False


def test_the_bluesky_read_is_capped_and_says_so(transport):
    for i in range(3):
        transport.expect("GET", "getAuthorFeed", body={"feed": [{"post": _bsky_post(f"3p{i}", "2026-10-28T00:00:00.000Z")}], "cursor": f"c{i}"})
    win = stats.window("2026-10-23", "2026-10-29", NOW)
    posts, truncated = stats.bluesky.author_posts(transport, DID, win.start, win.end, max_pages=3)
    assert len(posts) == 3 and truncated is True


# --- who runs it (M12-R3) ------------------------------------------------------


def test_help_names_the_writer_seat_in_one_line(capsys):
    with pytest.raises(SystemExit):
        cli.main(["stats", "--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert cli.STATS_RUNNER in out
    assert cli.STATS_RUNNER == "Run by the writer seat, which alone holds the social credentials."


def test_the_guide_documents_social_stats_under_measuring_reach():
    guide = Path("announcements/README.md").read_text()
    section = " ".join(guide.partition("## Measuring reach")[2].partition("\n## ")[0].split())
    assert section, "the guide has no 'Measuring reach' section"
    assert "uv run -m social stats" in section
    assert "`social stats` is run by the writer seat, which alone holds the social credentials." in section
    assert f"${stats.X_POST_READ} for each post and ${stats.X_USER_READ}" in section
    assert f"`--x-max-posts` posts (default {stats.DEFAULT_X_MAX_POSTS}" in section
    assert f"at most ${stats.max_x_cost(stats.DEFAULT_X_MAX_POSTS):.3f} a run" in section
    assert f"`--x-budget` (default ${stats.DEFAULT_X_BUDGET})" in section
