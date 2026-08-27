"""LinkedIn: OAuth token care and one organization post via the Posts API."""

from __future__ import annotations

import json
import re
import secrets as _secrets
import urllib.parse

from .transport import ApiError, Response

API = "https://api.linkedin.com"
OAUTH = "https://www.linkedin.com/oauth/v2"
# Versions are YYYYMM and stay active for about a year; bump when LinkedIn
# retires this one (a 426 NONEXISTENT_VERSION says so). LINKEDIN_VERSION overrides.
DEFAULT_VERSION = "202608"
# What the radiusred-wordy app is entitled to (Community Management API); the
# consent screen refuses scopes the app lacks, so keep this to the known set.
DEFAULT_SCOPES = (
    "r_organization_social",
    "r_organization_social_feed",
    "rw_organization_admin",
    "w_organization_social",
    "w_organization_social_feed",
)
# "little text" reserved characters — unescaped, they format or vanish.
COMMENTARY_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


def escape_commentary(text: str) -> str:
    return COMMENTARY_RESERVED.sub(r"\\\1", text)


def build_post(
    org_urn: str,
    text: str,
    link: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("post text is empty")
    body = {
        "author": org_urn,
        "commentary": escape_commentary(text),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if link:
        article = {"source": link, "title": title or link}
        if description:
            article["description"] = description
        body["content"] = {"article": article}
    return body


class LinkedIn:
    def __init__(
        self,
        transport,
        client_id: str,
        client_secret: str,
        access_token: str | None = None,
        version: str = DEFAULT_VERSION,
    ):
        self.transport = transport
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.version = version

    # --- OAuth ---------------------------------------------------------

    def _oauth(self, what: str, path: str, form: dict[str, str]) -> dict:
        resp = self.transport(
            "POST",
            f"{OAUTH}/{path}",
            {"Content-Type": "application/x-www-form-urlencoded"},
            urllib.parse.urlencode(form).encode(),
        )
        if not resp.ok:
            raise ApiError(what, resp)
        return resp.json()

    def introspect(self, token: str) -> dict:
        return self._oauth(
            "LinkedIn introspection failed",
            "introspectToken",
            {"client_id": self.client_id, "client_secret": self.client_secret, "token": token},
        )

    def refresh(self, refresh_token: str) -> dict:
        tokens = self._oauth(
            "LinkedIn token refresh failed",
            "accessToken",
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        self.access_token = tokens["access_token"]
        return tokens

    def auth_url(self, redirect_uri: str, scopes=DEFAULT_SCOPES, state: str | None = None) -> tuple[str, str]:
        state = state or _secrets.token_urlsafe(16)
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": " ".join(scopes),
            }
        )
        return f"{OAUTH}/authorization?{query}", state

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        tokens = self._oauth(
            "LinkedIn code exchange failed",
            "accessToken",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        self.access_token = tokens["access_token"]
        return tokens

    # --- REST ----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("no LinkedIn access token")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    def _rest(self, what: str, method: str, path: str, body: dict | None = None) -> Response:
        payload = json.dumps(body).encode() if body is not None else None
        resp = self.transport(method, f"{API}/rest/{path}", self._headers(), payload)
        if not resp.ok:
            raise ApiError(what, resp)
        return resp

    def organization_acls(self) -> list[dict]:
        resp = self._rest(
            "LinkedIn organizationAcls failed",
            "GET",
            "organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
        )
        return resp.json().get("elements", [])

    def organization(self, urn: str) -> dict:
        org_id = urn.rsplit(":", 1)[-1]
        return self._rest("LinkedIn organization lookup failed", "GET", f"organizations/{org_id}").json()

    def post_request(self, body: dict) -> dict:
        return {"method": "POST", "url": f"{API}/rest/posts", "body": body}

    def post(self, body: dict) -> dict:
        resp = self._rest("LinkedIn post failed", "POST", "posts", body)
        urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id", "")
        return {"urn": urn, "url": f"https://www.linkedin.com/feed/update/{urn}/" if urn else ""}
