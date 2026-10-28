"""Social posts live outside the repository; announcements/ is a writing guide.

The operator's Decision on radiusred/ops#37 retired the per-post trail: no
dated record, no committed text file, no per-network checkpoint, no captured
check or --dry-run output. What stays is the guide. These tests pin that the
trail does not drift back and that the guide still carries what the Decision
kept (radiusred/www#89).
"""

import os
from pathlib import Path

GUIDE = Path("announcements/README.md")
README = Path("README.md")

PER_POST_RULES = (
    "cc:needs-decision",
    "Result section",
    "dated file",
    "x-<date>.txt",
    "announcements/<file>",
    "captured into the announcement file",
    "the table goes in the announcement file",
)


def _social_section(readme_text):
    """The main README's social runbook, from its heading to the next H2."""
    _, _, rest = readme_text.partition("## Posting to social accounts")
    assert rest, "README.md has no 'Posting to social accounts' section"
    return rest.split("\n## ", 1)[0]


def test_announcements_holds_only_the_guide():
    assert sorted(os.listdir("announcements")) == ["README.md"]


def test_guide_documents_both_measuring_commands():
    text = GUIDE.read_text()
    assert "from social.bluesky import grapheme_len, facets" in text
    assert "from social.x import weighted_len" in text
    assert "300 graphemes" in text
    assert "280 weighted characters" in text


def test_guide_describes_the_four_step_process():
    text = GUIDE.read_text()
    assert "operator approves the exact text" in text
    assert "uv run -m social post" in text
    assert "comment with the post links on the CodeCrew milestone issue" in text
    assert "radiusred/ops/issues/37" in text, "the guide cites the Decision it follows"


def test_guide_keeps_the_writing_rules():
    text = GUIDE.read_text()
    for heading in (
        "## Write for someone who has never heard of us",
        "## Links",
        "## Bluesky budget",
        "## X budget",
        "## Tags are measured, not guessed",
        "## Milestone-close posts",
        "## Credentials",
    ):
        assert heading in text, f"{heading!r} is missing from the guide"


def test_guide_no_longer_asks_for_a_per_post_trail():
    text = GUIDE.read_text()
    for rule in PER_POST_RULES:
        assert rule not in text, f"{rule!r} is a per-post rule the Decision retired"


def test_readme_no_longer_says_posted_texts_are_kept_in_the_tree():
    section = _social_section(README.read_text())
    assert "kept in `announcements/`" not in section
    assert "announcements/README.md" in section, "the runbook still points at the guide"
