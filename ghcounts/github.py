"""A read-only GitHub client: REST GETs, and GraphQL queries for what REST
cannot list (a repository's discussions). It refuses to send anything else."""

from __future__ import annotations

import json
import re
import urllib.parse

from social.transport import ApiError, Response

API = "https://api.github.com"
JSON = "application/vnd.github+json"
# The stargazers list carries ``starred_at`` only under this media type.
STAR_JSON = "application/vnd.github.star+json"
NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class ReadOnlyViolation(Exception):
    """A call that is not a read never reaches the transport."""


class GraphQLError(Exception):
    pass


def next_link(response: Response) -> str | None:
    """The ``rel="next"`` URL of a paged response, if there is one."""
    match = NEXT_RE.search(response.headers.get("link", ""))
    return match.group(1) if match else None


def _is_query(document: str) -> bool:
    """A GraphQL document that holds operations of type ``query`` only. An
    anonymous ``{ … }`` is a query too."""
    text = re.sub(r"#[^\n]*", "", document).strip()
    return not re.search(r"\b(mutation|subscription)\b", text) and (text.startswith("{") or text.startswith("query"))


class GitHub:
    def __init__(self, transport, token: str, api: str = API):
        self.transport = transport
        self.token = token
        self.api = api.rstrip("/")

    def _headers(self, accept: str = JSON) -> dict[str, str]:
        return {
            "Accept": accept,
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "radiusred-ghcounts",
        }

    def _url(self, path: str, params: dict[str, str] | None = None) -> str:
        url = path if path.startswith("https://") else f"{self.api}{path}"
        return f"{url}?{urllib.parse.urlencode(params)}" if params else url

    def get(self, path: str, params: dict[str, str] | None = None, accept: str = JSON) -> Response:
        """One GET. An error status comes back as a response: the caller
        decides whether it is fatal."""
        return self.transport("GET", self._url(path, params), self._headers(accept), None)

    def get_json(self, what: str, path: str, params: dict[str, str] | None = None, accept: str = JSON):
        resp = self.get(path, params, accept)
        if not resp.ok:
            raise ApiError(what, resp)
        return resp.json()

    def pages(self, what: str, path: str, params: dict[str, str] | None = None, accept: str = JSON):
        """Each page of a paged list, in order, following ``Link: rel="next"``.
        The caller may stop early."""
        url = self._url(path, {"per_page": "100", **(params or {})})
        while url:
            resp = self.get(url, accept=accept)
            if not resp.ok:
                raise ApiError(what, resp)
            yield resp.json()
            url = next_link(resp)

    def graphql(self, what: str, query: str, variables: dict) -> dict:
        if not _is_query(query):
            raise ReadOnlyViolation("ghcounts sends GraphQL queries only, never a mutation")
        body = json.dumps({"query": query, "variables": variables}).encode()
        headers = {**self._headers(), "Content-Type": "application/json"}
        resp = self.transport("POST", f"{self.api}/graphql", headers, body)
        if not resp.ok:
            raise ApiError(what, resp)
        data = resp.json()
        if data.get("errors"):
            raise GraphQLError(f"{what}: " + "; ".join(e.get("message", "?") for e in data["errors"]))
        return data["data"]
