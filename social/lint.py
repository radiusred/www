"""The guide's mechanical rules, checked before a post goes out.

``announcements/README.md`` is the writing guide; this module is the part of
it a program can check. The banned list and the hashtag limits live here and
nowhere else: the guide lists them identically, and a test pins the two
copies to each other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import x
from .bluesky import TAG_RE, URL_RE

NETWORKS = ("bluesky", "linkedin", "x")

# The guide's "Use these words" list, lower case. A phrase matches with any
# run of whitespace between its words, a hyphen as a hyphen or a space, and
# a straight or curly apostrophe. A word matches as a whole word, with the
# common inflections (``leverages``, ``unlocking``, ``seamlessly``).
BANNED = (
    "seamless",
    "robust",
    "leverage",
    "unlock",
    "game-changer",
    "delve",
    "elevate",
    "empower",
    "journey",
    "landscape",
    "supercharge",
    "here's the thing",
    "the best part",
    "excited to announce",
    "thrilled to announce",
)

# Hashtags each network allows. None on X: they read as spam there. Two on
# Bluesky, both specific. LinkedIn keeps its five.
HASHTAG_LIMITS = {"x": 0, "bluesky": 2, "linkedin": 5}

# Where a URL may not sit in a post's body: on X it goes in the reply. A
# reply is where the link lives, so the rule does not apply to one.
URL_IN_REPLY = ("x",)

EM_DASH = "—"
_SUFFIX = r"(?:e?s|e?d|ing|ly)?"
_TERMINATOR_RE = re.compile(r"[.!?]+(?=[\s\"')”’]|$)")
_CLOSERS = "\"')”’"
_AGENT_HYPHEN_RE = re.compile(r"agent[‐‑‒–—-]staffed", re.IGNORECASE)
_AGENT_STAFFED_RE = re.compile(r"agent staffed(?!, human moderated)", re.IGNORECASE)


@dataclass(frozen=True)
class Failure:
    rule: str
    fragment: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.fragment}"


def _banned_pattern(phrase: str) -> re.Pattern:
    parts = []
    for ch in phrase:
        if ch == " ":
            parts.append(r"\s+")
        elif ch == "-":
            parts.append(r"[-\s]")
        elif ch == "'":
            parts.append("['’]")
        else:
            parts.append(re.escape(ch))
    body = "".join(parts)
    if phrase.endswith("e"):  # delve/delving, leverage/leveraging drop the e
        body = body[:-1] + "e?"
    return re.compile(rf"(?<!\w){body}{_SUFFIX}(?!\w)", re.IGNORECASE)


BANNED_PATTERNS = tuple((phrase, _banned_pattern(phrase)) for phrase in BANNED)


def _around(text: str, start: int, end: int, margin: int = 20) -> str:
    """The match with a little context either side, on one line."""
    lo, hi = max(0, start - margin), min(len(text), end + margin)
    piece = text[lo:hi].replace("\n", " ")
    return ("…" if lo else "") + piece + ("…" if hi < len(text) else "")


def _mask_urls(text: str) -> str:
    """URLs replaced by same-length runs of ``x``: their dots and ``#`` are
    not sentence ends or hashtags."""
    return URL_RE.sub(lambda m: "x" * len(m.group()), text)


def first_sentence(text: str) -> str:
    """Up to and including the first ``.``, ``!`` or ``?`` that ends a word
    (so ``v2.1.2`` and ``$0.200`` do not end it); the whole text when there
    is none."""
    masked = _mask_urls(text)
    match = _TERMINATOR_RE.search(masked)
    end = match.end() if match else len(text)
    return text[:end].strip()


def hashtags(text: str) -> list[str]:
    """Every ``#tag`` in the body, URLs skipped, as the networks would see them."""
    masked = _mask_urls(text)
    return [m.group() for m in TAG_RE.finditer(masked) if not m.group(1).isdigit()]


def urls(text: str) -> list[str]:
    """Every URL in the body: with a scheme, or a bare domain X autolinks."""
    found = [m.group().rstrip(x.TRAILING_PUNCT) for m in URL_RE.finditer(text)]
    masked = _mask_urls(text)
    found.extend(masked[s:e] for s, e in x.bare_domains(masked))
    return found


def emojis(text: str) -> list[str]:
    """Every emoji sequence in the body, as X's weighted count sees them."""
    return [text[s:e] for s, e in x.emoji_spans(text)]


def lint(text: str, network: str, reply: bool = False) -> list[Failure]:
    """Every failure of the guide's mechanical rules in ``text`` for
    ``network``; empty when the text passes. ``reply`` marks a reply, which
    carries the link and so may hold a URL on X."""
    if network not in NETWORKS:
        raise ValueError(f"unknown network {network!r}; one of {', '.join(NETWORKS)}")
    text = text.strip()
    failures: list[Failure] = []

    for match in re.finditer(EM_DASH, text):
        failures.append(Failure("em dash", _around(text, match.start(), match.end())))

    opening = first_sentence(text)
    if opening.rstrip(_CLOSERS).endswith("?"):
        failures.append(Failure("the first sentence is a question", opening))

    for phrase, pattern in BANNED_PATTERNS:
        for match in pattern.finditer(text):
            failures.append(Failure(f"banned word {phrase!r}", _around(text, match.start(), match.end())))

    tags = hashtags(text)
    limit = HASHTAG_LIMITS[network]
    if len(tags) > limit:
        failures.append(Failure(f"{len(tags)} hashtags; {network} allows {limit}", " ".join(tags)))

    if network in URL_IN_REPLY and not reply:
        for url in urls(text):
            failures.append(Failure(f"a URL in the body; on {network} it goes in the reply", url))

    for emoji in emojis(text):
        failures.append(Failure("emoji", emoji))

    for match in _AGENT_HYPHEN_RE.finditer(text):
        failures.append(Failure('"agent-staffed" with a hyphen; write "agent staffed, human moderated"', _around(text, match.start(), match.end())))
    for match in _AGENT_STAFFED_RE.finditer(text):
        failures.append(Failure('"agent staffed" without ", human moderated"', _around(text, match.start(), match.end())))

    return failures
