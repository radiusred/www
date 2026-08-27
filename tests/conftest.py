import json

import pytest

from social.transport import Response


class FakeTransport:
    """Scripted transport: responses are matched by (method, URL substring)
    in the order they were queued; every call is recorded."""

    def __init__(self):
        self.calls = []
        self.queue = []

    def expect(self, method, url_part, status=200, body=None, headers=None):
        payload = body if isinstance(body, bytes) else json.dumps(body or {}).encode()
        self.queue.append((method, url_part, Response(status, payload, headers or {})))
        return self

    def __call__(self, method, url, headers=None, body=None):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "body": body})
        for i, (m, part, resp) in enumerate(self.queue):
            if m == method and part in url:
                del self.queue[i]
                return resp
        raise AssertionError(f"unexpected request {method} {url}")

    def bodies(self):
        return [json.loads(c["body"]) if c["body"] and c["headers"].get("Content-Type", "").startswith("application/json") else c["body"] for c in self.calls]


@pytest.fixture
def transport():
    return FakeTransport()


@pytest.fixture
def refusing_transport():
    def refuse(method, url, headers=None, body=None):
        raise AssertionError(f"network touched: {method} {url}")

    return refuse


@pytest.fixture
def env_file(tmp_path):
    path = tmp_path / "social.env"
    path.write_text(
        "# test creds\n"
        "BSKY_HANDLE=example.bsky.social\n"
        "BSKY_APP_PASSWORD=app-pass\n"
        "LINKEDIN_CLIENT_ID=cid\n"
        "LINKEDIN_CLIENT_SECRET=csecret\n"
        "LINKEDIN_ACCESS_TOKEN=old-access\n"
        "LINKEDIN_REFRESH_TOKEN=old-refresh\n"
        "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT=9999999999\n"
        "LINKEDIN_ORG_URN=urn:li:organization:42\n"
    )
    return path
