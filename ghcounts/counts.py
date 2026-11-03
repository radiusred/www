"""What ``ghcounts`` counts, per repository: stars now, new stars in the
window when the token may read the stargazers, and the issues, pull requests
and discussions outside people opened in it."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from social.transport import ApiError

from .github import STAR_JSON, GitHub, next_link

# Inside, as ``author_association`` says: an owner or member of the owner org,
# or a collaborator with direct access to the repository. An App installation
# token cannot see private org membership, so a private member shows as
# COLLABORATOR or even CONTRIBUTOR (access through the org), and the member
# list is often unreadable. So an author left over is inside too when their
# permission on the repository is one of INSIDE_PERMISSIONS; that read works
# with the App token. GitHub gives the maintain role as ``write`` there.
INSIDE_ASSOCIATIONS = ("OWNER", "MEMBER", "COLLABORATOR")
INSIDE_PERMISSIONS = ("admin", "write")
KINDS = ("new_stars", "issues", "pull_requests", "discussions")

DISCUSSIONS_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    discussions(first: 100, after: $after, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { url createdAt authorAssociation author { login __typename } }
    }
  }
}
"""


@dataclass(frozen=True)
class Window:
    """UTC dates, both days included."""

    since: date
    until: date

    @classmethod
    def last_full_days(cls, today: date, days: int = 7) -> Window:
        until = today - timedelta(days=1)
        return cls(until - timedelta(days=days - 1), until)

    @property
    def start(self) -> datetime:
        return datetime.combine(self.since, time(), timezone.utc)

    @property
    def end(self) -> datetime:
        """The first instant after the window."""
        return datetime.combine(self.until + timedelta(days=1), time(), timezone.utc)

    def __contains__(self, stamp: datetime) -> bool:
        return self.start <= stamp < self.end


def parse_ts(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def is_bot(login: str, kind: str | None) -> bool:
    return kind == "Bot" or login.endswith("[bot]")


def org_members(gh: GitHub, org: str) -> set[str] | None:
    """The org's member logins, or None when the token cannot read them. An
    installation token without the Members permission gets a refusal or an
    empty list; an org always has a member, so empty means unreadable too."""
    logins: set[str] = set()
    url = f"/orgs/{org}/members"
    params = {"per_page": "100"}
    while url:
        resp = gh.get(url, params)
        if not resp.ok:
            return None
        logins.update(m["login"] for m in resp.json())
        url, params = next_link(resp), None
    return logins or None


def _item(url: str, author: str, stamp: str) -> dict:
    return {"url": url, "author": author, "date": stamp}


def _counted(items: list[dict], **extra) -> dict:
    return {"count": len(items), "items": sorted(items, key=lambda i: i["date"]), **extra}


def repo_permission(gh: GitHub, repo: str, login: str) -> str | None:
    """The author's permission on the repository (``admin``, ``write``,
    ``read`` or ``none``), or None for an account GitHub does not know. Any
    other refusal is an error: a guess would move the count."""
    resp = gh.get(f"/repos/{repo}/collaborators/{urllib.parse.quote(login)}/permission")
    if resp.status == 404:
        return None
    if not resp.ok:
        raise ApiError(f"{repo} permission of {login}", resp)
    return resp.json().get("permission")


class Outside:
    """Whether an author is outside the repo owner's org. The permission read
    runs only for an author that nothing else marks inside, once per author."""

    def __init__(self, members: set[str] | None, permission=lambda login: None):
        self.members = members or set()
        self.permission = permission
        self.seen: dict[str, bool] = {}

    def __call__(self, login: str, kind: str | None, association: str | None) -> bool:
        if is_bot(login, kind):
            return False
        if (association or "").upper() in INSIDE_ASSOCIATIONS or login in self.members:
            return False
        if login not in self.seen:
            self.seen[login] = self.permission(login) not in INSIDE_PERMISSIONS
        return self.seen[login]


def new_stars(gh: GitHub, repo: str, window: Window) -> list[dict] | None:
    """Every star given in the window, or None when the token may not read
    the stargazers: GitHub can refuse the list to an App token (HTTP 403).
    A 403 for a spent rate limit is an error, not a refusal. The list runs
    oldest first, so it is read to the end."""
    found = []
    url = f"/repos/{repo}/stargazers"
    params = {"per_page": "100"}
    while url:
        resp = gh.get(url, params, accept=STAR_JSON)
        if resp.status == 403 and resp.headers.get("x-ratelimit-remaining") != "0":
            return None
        if not resp.ok:
            raise ApiError(f"{repo} stargazers", resp)
        for star in resp.json():
            if parse_ts(star["starred_at"]) in window:
                user = star.get("user") or {}
                login = user.get("login", "ghost")
                found.append(_item(user.get("html_url", f"https://github.com/{login}"), login, star["starred_at"]))
        url, params = next_link(resp), None
    return found


def _stars_block(stars: list[dict] | None) -> dict:
    if stars is None:
        return {"count": None, "items": [], "available": False}
    return _counted(stars, available=True)


def opened_issues(gh: GitHub, repo: str, window: Window, outside: Outside) -> tuple[list[dict], list[dict]]:
    """``(issues, pull_requests)`` outside people opened in the window. The
    issues list holds pull requests too; it is read newest first and stops at
    the first page that reaches back before the window."""
    issues, pulls = [], []
    params = {"state": "all", "sort": "created", "direction": "desc"}
    for page in gh.pages(f"{repo} issues", f"/repos/{repo}/issues", params):
        for issue in page:
            created = parse_ts(issue["created_at"])
            user = issue.get("user") or {}
            login = user.get("login", "ghost")
            if created in window and outside(login, user.get("type"), issue.get("author_association")):
                item = _item(issue["html_url"], login, issue["created_at"])
                (pulls if "pull_request" in issue else issues).append(item)
        if not page or parse_ts(page[-1]["created_at"]) < window.start:
            break
    return issues, pulls


def opened_discussions(gh: GitHub, repo: str, window: Window, outside: Outside) -> list[dict]:
    owner, name = repo.split("/", 1)
    found, after = [], None
    while True:
        data = gh.graphql(f"{repo} discussions", DISCUSSIONS_QUERY, {"owner": owner, "name": name, "after": after})
        block = data["repository"]["discussions"]
        nodes = block["nodes"]
        for node in nodes:
            author = node.get("author") or {}
            login = author.get("login", "ghost")
            if parse_ts(node["createdAt"]) in window and outside(login, author.get("__typename"), node.get("authorAssociation")):
                found.append(_item(node["url"], login, node["createdAt"]))
        if not nodes or not block["pageInfo"]["hasNextPage"] or parse_ts(nodes[-1]["createdAt"]) < window.start:
            return found
        after = block["pageInfo"]["endCursor"]


def count_repo(gh: GitHub, repo: str, window: Window, members_cache: dict[str, set[str] | None]) -> dict:
    meta = gh.get_json(f"{repo} lookup", f"/repos/{repo}")
    owner = meta["owner"]
    if owner.get("type") == "Organization":
        if owner["login"] not in members_cache:
            members_cache[owner["login"]] = org_members(gh, owner["login"])
        members = members_cache[owner["login"]]
        member_list = "read" if members is not None else "not readable"
    else:
        members, member_list = None, "not an org"
    outside = Outside(members, lambda login: repo_permission(gh, repo, login))
    issues, pulls = opened_issues(gh, repo, window, outside)
    enabled = bool(meta.get("has_discussions"))
    discussions = opened_discussions(gh, repo, window, outside) if enabled else []
    return {
        "repo": repo,
        "stars": meta["stargazers_count"],
        "new_stars": _stars_block(new_stars(gh, repo, window)),
        "issues": _counted(issues),
        "pull_requests": _counted(pulls),
        "discussions": _counted(discussions, enabled=enabled),
        "member_list": member_list,
    }


def report(gh: GitHub, repos: list[str], window: Window) -> dict:
    cache: dict[str, set[str] | None] = {}
    rows = [count_repo(gh, repo, window, cache) for repo in repos]
    totals = {"stars": sum(r["stars"] for r in rows)}
    # A null count anywhere makes the total null: a sum over only the
    # readable repos would look like a full one.
    totals.update({kind: None if any(r[kind]["count"] is None for r in rows) else sum(r[kind]["count"] for r in rows)
                   for kind in KINDS})
    return {
        "window": {"since": window.since.isoformat(), "until": window.until.isoformat()},
        "inside": {
            "author_association": list(INSIDE_ASSOCIATIONS),
            "repo_permission": list(INSIDE_PERMISSIONS),
            "bots": "excluded",
        },
        "repos": rows,
        "totals": totals,
    }
