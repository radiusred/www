"""One seam between the clients and the network, so tests never touch it."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Response:
    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)

    def json(self):
        return json.loads(self.body.decode("utf-8") or "null")

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class ApiError(Exception):
    def __init__(self, what: str, response: Response):
        detail = response.body.decode("utf-8", "replace")[:500]
        super().__init__(f"{what}: HTTP {response.status} {detail}".rstrip())
        self.response = response


class UrllibTransport:
    """``transport(method, url, headers, body) -> Response``. Error statuses
    come back as responses, not exceptions — the caller decides."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> Response:
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return Response(resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()})
        except urllib.error.HTTPError as err:
            return Response(err.code, err.read(), {k.lower(): v for k, v in err.headers.items()})
