"""``ghcounts``: stars and outside contributions, read-only, from scripted
responses (radiusred/www#105, M12-R2 and M12-R4). No test touches the network."""

import json
from datetime import date

import pytest

from ghcounts import cli
from ghcounts.counts import Window
from ghcounts.github import GitHub, ReadOnlyViolation

TODAY = date(2026, 10, 30)  # default window: 2026-10-23 .. 2026-10-29
ENV = {"GH_TOKEN": "ghs_test"}
REPO = "acme/widget"


def _repo(stars=5, discussions=True, owner_type="Organization"):
    return {"stargazers_count": stars, "has_discussions": discussions, "owner": {"login": "acme", "type": owner_type}}


def _issue(n, login, created, association="NONE", kind="User", pull=False):
    issue = {
        "html_url": f"https://github.com/{REPO}/{'pull' if pull else 'issues'}/{n}",
        "user": {"login": login, "type": kind},
        "author_association": association,
        "created_at": created,
    }
    if pull:
        issue["pull_request"] = {"url": "…"}
    return issue


def _star(login, when):
    return {"starred_at": when, "user": {"login": login, "html_url": f"https://github.com/{login}"}}


def _discussions(nodes, next_cursor=None):
    return {"data": {"repository": {"discussions": {
        "pageInfo": {"hasNextPage": next_cursor is not None, "endCursor": next_cursor},
        "nodes": nodes,
    }}}}


def _discussion(n, login, created, association="NONE", kind="User"):
    return {"url": f"https://github.com/{REPO}/discussions/{n}", "createdAt": created,
            "authorAssociation": association, "author": {"login": login, "__typename": kind}}


def _script(transport, *, repo=None, members=None, members_status=200, stars=(), issues=(), discussions=None):
    transport.expect("GET", f"/repos/{REPO}", body=repo or _repo())
    if (repo or _repo())["owner"]["type"] == "Organization":
        transport.expect("GET", "/orgs/acme/members", status=members_status, body=members if members is not None else [])
    transport.expect("GET", f"/repos/{REPO}/issues", body=list(issues))
    if discussions is not None:
        transport.expect("POST", "/graphql", body=_discussions(discussions))
    transport.expect("GET", f"/repos/{REPO}/stargazers", body=list(stars))
    return transport


def _run(transport, *args, environ=ENV):
    return cli.main(["--repo", REPO, *args], transport=transport, environ=environ, today=TODAY)


def _json(capsys):
    return json.loads(capsys.readouterr().out)


# --- the window -----------------------------------------------------------


def test_default_window_is_the_last_seven_full_days():
    args = cli.build_parser().parse_args([])
    window = cli.window_from(args, TODAY)
    assert (window.since, window.until) == (date(2026, 10, 23), date(2026, 10, 29))


def test_until_alone_keeps_seven_days_and_since_alone_runs_to_yesterday():
    w = cli.window_from(cli.build_parser().parse_args(["--until", "2026-10-10"]), TODAY)
    assert (w.since, w.until) == (date(2026, 10, 4), date(2026, 10, 10))
    w = cli.window_from(cli.build_parser().parse_args(["--since", "2026-10-01"]), TODAY)
    assert (w.since, w.until) == (date(2026, 10, 1), date(2026, 10, 29))


def test_both_days_of_the_window_are_included():
    from ghcounts.counts import parse_ts

    window = Window(date(2026, 10, 23), date(2026, 10, 29))
    assert parse_ts("2026-10-23T00:00:00Z") in window
    assert parse_ts("2026-10-29T23:59:59Z") in window
    assert parse_ts("2026-10-22T23:59:59Z") not in window
    assert parse_ts("2026-10-30T00:00:00Z") not in window


def test_since_after_until_is_refused_before_any_call(refusing_transport, capsys):
    rc = _run(refusing_transport, "--since", "2026-10-10", "--until", "2026-10-01")
    assert rc == 2
    assert "after --until" in capsys.readouterr().err


def test_no_token_is_refused_before_any_call(refusing_transport, capsys):
    rc = _run(refusing_transport, environ={})
    assert rc == 2
    assert "GH_TOKEN is not set" in capsys.readouterr().err


def test_a_repo_that_is_not_owner_name_is_refused():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--repo", "widget"])


def test_default_repos_are_the_four_product_repos():
    assert cli.DEFAULT_REPOS == (
        "radiusred/tradedesk",
        "radiusred/tradedesk-marketdata",
        "radiusred/tradedesk-miner",
        "radiusred/ha-sinkhole",
    )


# --- what is counted --------------------------------------------------------


def test_stars_now_and_new_stars_from_starred_at_across_pages(transport, capsys):
    transport.expect("GET", f"/repos/{REPO}", body=_repo(stars=3))
    transport.expect("GET", "/orgs/acme/members", body=[])
    transport.expect("GET", f"/repos/{REPO}/issues", body=[])
    transport.expect("POST", "/graphql", body=_discussions([]))
    transport.expect("GET", f"/repos/{REPO}/stargazers", body=[_star("old", "2026-01-01T00:00:00Z"), _star("a", "2026-10-23T08:00:00Z")],
                     headers={"link": f'<https://api.github.com/repos/{REPO}/stargazers?page=2>; rel="next"'})
    transport.expect("GET", f"/repos/{REPO}/stargazers?page=2", body=[_star("b", "2026-10-29T23:00:00Z"), _star("late", "2026-10-30T01:00:00Z")])
    assert _run(transport, "--json") == 0
    row = _json(capsys)["repos"][0]
    assert row["stars"] == 3
    assert row["new_stars"]["count"] == 2
    assert [i["author"] for i in row["new_stars"]["items"]] == ["a", "b"]
    assert row["new_stars"]["items"][0] == {"url": "https://github.com/a", "author": "a", "date": "2026-10-23T08:00:00Z"}
    star_call = next(c for c in transport.calls if "stargazers" in c["url"])
    assert star_call["headers"]["Accept"] == "application/vnd.github.star+json"


def test_issues_and_prs_are_split_and_bots_and_members_are_not_outside(transport, capsys):
    _script(transport, issues=[
        _issue(9, "stranger", "2026-10-28T10:00:00Z"),
        _issue(8, "helper", "2026-10-27T10:00:00Z", association="CONTRIBUTOR", pull=True),
        _issue(7, "renovate[bot]", "2026-10-27T09:00:00Z", pull=True),
        _issue(6, "some-app", "2026-10-26T09:00:00Z", kind="Bot"),
        _issue(5, "boss", "2026-10-26T08:00:00Z", association="OWNER"),
        _issue(4, "staff", "2026-10-25T08:00:00Z", association="MEMBER", pull=True),
        _issue(3, "early", "2026-10-20T08:00:00Z"),
    ], discussions=[])
    assert _run(transport, "--json") == 0
    row = _json(capsys)["repos"][0]
    assert [i["author"] for i in row["issues"]["items"]] == ["stranger"]
    assert [i["author"] for i in row["pull_requests"]["items"]] == ["helper"]
    assert row["pull_requests"]["items"][0]["url"] == f"https://github.com/{REPO}/pull/8"
    assert (row["issues"]["count"], row["pull_requests"]["count"]) == (1, 1)


def test_the_member_list_adds_to_author_association(transport, capsys):
    _script(transport, members=[{"login": "quiet-member"}], issues=[
        _issue(2, "quiet-member", "2026-10-28T10:00:00Z", association="CONTRIBUTOR"),
        _issue(1, "stranger", "2026-10-27T10:00:00Z"),
    ], discussions=[])
    assert _run(transport, "--json") == 0
    row = _json(capsys)["repos"][0]
    assert [i["author"] for i in row["issues"]["items"]] == ["stranger"]
    assert row["member_list"] == "read"


@pytest.mark.parametrize("status, body", [(403, {"message": "Resource not accessible by integration"}), (200, [])])
def test_an_unreadable_member_list_is_not_an_error(transport, capsys, status, body):
    _script(transport, members=body, members_status=status, issues=[
        _issue(2, "staff", "2026-10-28T10:00:00Z", association="MEMBER"),
        _issue(1, "stranger", "2026-10-27T10:00:00Z"),
    ], discussions=[])
    assert _run(transport) == 0
    out = capsys.readouterr().out
    assert "issues by outside people: 1" in out
    assert "org member list: not readable with this token; outside is judged from author_association" in out


def test_a_user_owned_repo_reads_no_member_list(transport, capsys):
    _script(transport, repo=_repo(owner_type="User"), issues=[_issue(1, "stranger", "2026-10-27T10:00:00Z")], discussions=[])
    assert _run(transport, "--json") == 0
    assert _json(capsys)["repos"][0]["member_list"] == "not an org"
    assert not any("/orgs/" in c["url"] for c in transport.calls)


def test_the_issues_list_stops_at_the_page_that_reaches_before_the_window(transport, capsys):
    transport.expect("GET", f"/repos/{REPO}", body=_repo(discussions=False))
    transport.expect("GET", "/orgs/acme/members", body=[])
    transport.expect("GET", f"/repos/{REPO}/issues", body=[_issue(2, "a", "2026-10-28T10:00:00Z"), _issue(1, "b", "2026-10-01T10:00:00Z")],
                     headers={"link": f'<https://api.github.com/repos/{REPO}/issues?page=2>; rel="next"'})
    transport.expect("GET", f"/repos/{REPO}/stargazers", body=[])
    assert _run(transport, "--json") == 0
    assert _json(capsys)["repos"][0]["issues"]["count"] == 1
    assert not any("page=2" in c["url"] for c in transport.calls)
    issue_call = next(c for c in transport.calls if "/issues" in c["url"])
    assert "state=all" in issue_call["url"] and "sort=created" in issue_call["url"] and "direction=desc" in issue_call["url"]


def test_discussions_count_outside_authors_and_page_until_the_window(transport, capsys):
    transport.expect("GET", f"/repos/{REPO}", body=_repo())
    transport.expect("GET", "/orgs/acme/members", body=[])
    transport.expect("GET", f"/repos/{REPO}/issues", body=[])
    transport.expect("POST", "/graphql", body=_discussions([
        _discussion(5, "asker", "2026-10-29T10:00:00Z"),
        _discussion(4, "radiusred-wordy", "2026-10-28T10:00:00Z", kind="Bot"),
    ], next_cursor="c1"))
    transport.expect("POST", "/graphql", body=_discussions([
        _discussion(3, "staff", "2026-10-27T10:00:00Z", association="MEMBER"),
        _discussion(2, "other", "2026-10-24T10:00:00Z"),
        _discussion(1, "old", "2026-09-01T10:00:00Z"),
    ], next_cursor="c2"))
    transport.expect("GET", f"/repos/{REPO}/stargazers", body=[])
    assert _run(transport, "--json") == 0
    block = _json(capsys)["repos"][0]["discussions"]
    assert block["enabled"] is True
    assert [i["author"] for i in block["items"]] == ["other", "asker"]
    queries = [json.loads(c["body"]) for c in transport.calls if c["method"] == "POST"]
    assert [q["variables"]["after"] for q in queries] == [None, "c1"]


def test_a_repo_with_discussions_off_counts_zero_and_says_so(transport, capsys):
    _script(transport, repo=_repo(discussions=False))
    assert _run(transport) == 0
    assert "discussions by outside people: 0 (Discussions are off)" in capsys.readouterr().out
    assert not any(c["method"] == "POST" for c in transport.calls)


def test_totals_add_up_across_repos(transport, capsys):
    for name, stars, starred in (("acme/one", 4, "2026-10-24T00:00:00Z"), ("acme/two", 6, "2026-10-25T00:00:00Z")):
        transport.expect("GET", f"/repos/{name}", body={**_repo(stars=stars, discussions=False)})
        if name == "acme/one":
            transport.expect("GET", "/orgs/acme/members", body=[])
        transport.expect("GET", f"/repos/{name}/issues", body=[_issue(1, "stranger", "2026-10-27T10:00:00Z")])
        transport.expect("GET", f"/repos/{name}/stargazers", body=[_star("fan", starred)])
    rc = cli.main(["--repo", "acme/one", "--repo", "acme/two", "--json"], transport=transport, environ=ENV, today=TODAY)
    assert rc == 0
    data = _json(capsys)
    assert data["totals"] == {"stars": 10, "new_stars": 2, "issues": 2, "pull_requests": 0, "discussions": 0}
    # one member-list read per org, not per repo
    assert sum("/orgs/acme/members" in c["url"] for c in transport.calls) == 1


def test_json_schema_is_pinned(transport, capsys):
    _script(transport, issues=[_issue(1, "stranger", "2026-10-27T10:00:00Z")], discussions=[], stars=[_star("fan", "2026-10-24T00:00:00Z")])
    assert _run(transport, "--json") == 0
    data = _json(capsys)
    assert set(data) == {"window", "inside", "repos", "totals"}
    assert data["window"] == {"since": "2026-10-23", "until": "2026-10-29"}
    assert data["inside"] == {"author_association": ["OWNER", "MEMBER"], "bots": "excluded"}
    row = data["repos"][0]
    assert set(row) == {"repo", "stars", "new_stars", "issues", "pull_requests", "discussions", "member_list"}
    for kind in ("new_stars", "issues", "pull_requests"):
        assert set(row[kind]) == {"count", "items"}
    assert set(row["discussions"]) == {"count", "items", "enabled"}
    assert set(row["issues"]["items"][0]) == {"url", "author", "date"}
    assert set(data["totals"]) == {"stars", "new_stars", "issues", "pull_requests", "discussions"}


def test_text_output_lists_each_counted_item(transport, capsys):
    _script(transport, issues=[_issue(1, "stranger", "2026-10-27T10:00:00Z")], discussions=[])
    assert _run(transport) == 0
    out = capsys.readouterr().out
    assert "ghcounts 2026-10-23 to 2026-10-29 (UTC, both days included)" in out
    assert f"    2026-10-27  stranger  https://github.com/{REPO}/issues/1" in out
    assert "\ntotal\n" in out


def test_an_api_error_is_reported_not_raised(transport, capsys):
    transport.expect("GET", f"/repos/{REPO}", status=404, body={"message": "Not Found"})
    assert _run(transport) == 1
    assert "acme/widget lookup: HTTP 404" in capsys.readouterr().err


# --- read-only ----------------------------------------------------------------


def test_a_full_run_sends_only_gets_and_graphql_queries(transport, capsys):
    _script(transport, issues=[_issue(1, "stranger", "2026-10-27T10:00:00Z")], discussions=[], stars=[_star("fan", "2026-10-24T00:00:00Z")])
    assert _run(transport, "--json") == 0
    for call in transport.calls:
        assert call["headers"]["Authorization"] == "Bearer ghs_test"
        if call["method"] == "GET":
            assert call["body"] is None
            continue
        assert (call["method"], call["url"]) == ("POST", "https://api.github.com/graphql")
        assert json.loads(call["body"])["query"].lstrip().startswith("query(")
    assert transport.queue == []


@pytest.mark.parametrize("document", [
    "mutation { addStar(input: {starrableId: \"x\"}) { clientMutationId } }",
    "query { viewer { login } } mutation { addStar(input: {}) { clientMutationId } }",
    "subscription { x }",
])
def test_the_client_refuses_anything_but_a_query(refusing_transport, document):
    with pytest.raises(ReadOnlyViolation):
        GitHub(refusing_transport, "t").graphql("x", document, {})


# --- who runs it (M12-R3) -------------------------------------------------------


def test_help_says_who_runs_it_in_one_line(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert "Run by the chief of staff, with its own GitHub App token in GH_TOKEN." in out.splitlines()
