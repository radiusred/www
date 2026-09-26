"""Credential resolution: environment first, then the operator's env file.

The env file is ``~/.config/radiusred/social.env`` by default — the posting
accounts are Radius Red's, not CodeCrew's — and is written back to when a
token rotates and that is where it came from. Values that arrive through the
environment (an orchestrator's doing) are never written anywhere.

Transitional (www#70): when the default file is absent, the old
``~/.config/codecrew/social.env`` is still read, with one stderr line telling
the operator to move it. It is never written to; a rotation seeds the new file
from it instead. The fallback goes once the operator confirms the move.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ENV_FILE = Path.home() / ".config" / "radiusred" / "social.env"
LEGACY_ENV_FILE = Path.home() / ".config" / "codecrew" / "social.env"

KEYS = (
    "BSKY_HANDLE",
    "BSKY_APP_PASSWORD",
    "BSKY_PDS",
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
    "LINKEDIN_ACCESS_TOKEN",
    "LINKEDIN_REFRESH_TOKEN",
    "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT",
    "LINKEDIN_REFRESH_TOKEN_EXPIRES_AT",
    "LINKEDIN_ORG_URN",
    "LINKEDIN_VERSION",
    "LINKEDIN_REDIRECT_URI",
)


class MissingCredential(Exception):
    def __init__(self, key: str, env_file: Path | None):
        where = f" or {env_file}" if env_file else ""
        super().__init__(f"{key} is not set in the environment{where}")
        self.key = key


def parse_env_file(text: str) -> dict[str, str]:
    """Parse KEY=value lines. Blank lines and ``#`` comments are ignored;
    a single layer of matching quotes around the value is stripped."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


@dataclass
class Credentials:
    values: dict[str, str] = field(default_factory=dict)
    from_env: set[str] = field(default_factory=set)
    env_file: Path | None = None
    # The legacy file the values were read from, when ``env_file`` does not
    # exist yet: the first write copies it whole so nothing is left behind.
    seed_from: Path | None = None

    def get(self, key: str, default: str | None = None) -> str | None:
        value = self.values.get(key)
        return value if value else default

    def require(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise MissingCredential(key, self.env_file)
        return value

    def persist(self, updates: dict[str, str]) -> list[str]:
        """Write ``updates`` back to the env file. Returns the keys that could
        not be persisted: those that came from the environment, or all of them
        when there is no env file to write to."""
        self.values.update(updates)
        skipped = [k for k in updates if k in self.from_env]
        writable = {k: v for k, v in updates.items() if k not in self.from_env}
        if not writable:
            return skipped
        if self.env_file is None:
            return list(updates)
        if self.env_file.exists():
            existing = self.env_file.read_text()
        elif self.seed_from is not None and self.seed_from.exists():
            existing = self.seed_from.read_text()
        else:
            existing = ""
        lines = existing.splitlines()
        seen: set[str] = set()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in writable:
                lines[i] = f"{key}={writable[key]}"
                seen.add(key)
        for key, value in writable.items():
            if key not in seen:
                lines.append(f"{key}={value}")
        self.env_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = self.env_file.with_suffix(self.env_file.suffix + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.env_file)
        return skipped


def load_credentials(
    env_file: Path | None = None, environ: dict[str, str] | None = None
) -> Credentials:
    """Environment wins over the file, key by key. A missing file is fine —
    whatever the environment lacks is simply absent.

    With no explicit ``env_file`` the default path is read; if it is absent
    and the legacy path exists, the legacy file is read instead and one line
    on stderr names both. Either way the returned ``env_file`` is the default
    path: it is the only one ever written. An explicit ``env_file`` is read
    alone, with no fallback and no hint."""
    environ = os.environ if environ is None else environ
    path = env_file or DEFAULT_ENV_FILE
    seed_from = None
    values: dict[str, str] = {}
    if path.exists():
        values.update(parse_env_file(path.read_text()))
    elif env_file is None and LEGACY_ENV_FILE.exists():
        seed_from = LEGACY_ENV_FILE
        values.update(parse_env_file(seed_from.read_text()))
        print(
            f"social: {path} is absent, reading the old {seed_from} instead — "
            f"move it to {path}; only the new path is ever written, and this fallback is temporary",
            file=sys.stderr,
        )
    from_env = {k for k in KEYS if environ.get(k)}
    for key in from_env:
        values[key] = environ[key]
    return Credentials(values=values, from_env=from_env, env_file=path, seed_from=seed_from)
