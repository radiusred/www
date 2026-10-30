"""Social posts live outside the repository; announcements/ is a writing guide.

The operator's Decision on radiusred/ops#37 retired the per-post trail: no
dated record, no committed text file, no per-network checkpoint, no captured
check or --dry-run output (radiusred/www#89). The 2026-10-28 voice rules then
rewrote the guide (radiusred/www#92, M10-R3): these tests pin that the trail
does not drift back, that the rules the rewrite replaced stay gone, and that
the guide's mechanical list agrees with ``social/lint.py``.
"""

import os
import re
from pathlib import Path

from social import lint

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

# What the 2026-10-28 rules replaced: five hashtags, measured tags, inline X
# links and the 2026-09-26 Decision for them, approval of every post.
REPLACED_RULES = (
    "Five relevant hashtags",
    "Tags are measured, not guessed",
    "hours for a tag to accumulate",
    "links inline in the body",
    "the URLs go in the body",
    "issuecomment-5846341962",
    "approval is the only check",
    "nothing goes out without it",
    # The "every close" clause, superseded on 2026-10-28 by the scope Decision
    # (gh-codecrew#423, issuecomment-6469436459): a website-only milestone gets
    # no post (www#96).
    "every close, the small milestones included",
)


def _social_section(readme_text):
    """The main README's social runbook, from its heading to the next H2."""
    _, _, rest = readme_text.partition("## Posting to social accounts")
    assert rest, "README.md has no 'Posting to social accounts' section"
    return rest.split("\n## ", 1)[0]


def _flat(text):
    """The guide with its line wrapping undone, so a phrase matches wherever it breaks."""
    return re.sub(r"\s+", " ", text)


def _banned_words_in_the_guide(text):
    """The backticked items of the Don't list's 'Use these words' entry."""
    match = re.search(r"Use these words:(.*?)(?=\n\d+\.|\n\n)", text, re.S)
    assert match, "the guide has no 'Use these words' entry"
    return re.findall(r"`([^`]+)`", match.group(1))


def _cta_labels_in_the_guide(text):
    """The backticked items of the Don't list's 'Use call-to-action labels' entry."""
    match = re.search(r"Use call-to-action labels:(.*?)(?=\n\d+\.|\n\n)", text, re.S)
    assert match, "the guide has no 'Use call-to-action labels' entry"
    return re.findall(r"`([^`]+)`", match.group(1))


def test_announcements_holds_only_the_guide():
    assert sorted(os.listdir("announcements")) == ["README.md"]


def test_guide_documents_both_measuring_commands():
    text = GUIDE.read_text()
    assert "from social.bluesky import grapheme_len, facets" in text
    assert "from social.x import weighted_len" in text
    assert "300 graphemes" in text
    assert "280 weighted characters" in text


def test_guide_describes_posting_and_the_record():
    text = _flat(GUIDE.read_text())
    assert "the operator approves, the exact text" in text
    assert "uv run -m social lint" in text and "uv run -m social post" in text
    assert "Every post's links go in one comment on the milestone issue the post belongs to" in text
    assert "radiusred/ops/issues/37" in text, "the guide cites the Decision that moved posts out of the tree"
    assert "issuecomment-6467856741" in text, "the guide cites the Decision that reshaped the close post"


def test_guide_keeps_its_sections():
    text = GUIDE.read_text()
    for heading in (
        "## Accounts",
        "## What CodeCrew posts about",
        "## The voice",
        "### Do",
        "### Don't",
        "### Before and after",
        "## Hashtags",
        "## Links",
        "## Approval",
        "## Before you post",
        "## The check: `social lint`",
        "## Milestone-close posts",
        "## Bluesky budget",
        "## X budget",
        "## Credentials",
        "## Measuring reach",
    ):
        assert heading in text, f"{heading!r} is missing from the guide"


def test_guide_names_both_account_sets():
    text = GUIDE.read_text()
    for handle in ("radiusred.uk", "radiusred_uk", "codecrew.works", "codecrewworks"):
        assert f"`{handle}`" in text


def test_guide_carries_the_voice_rules():
    text = _flat(GUIDE.read_text())
    assert "Write like a developer telling another developer what shipped" in text
    assert "Write for someone who has never heard of us" in text
    assert '"agent staffed, human moderated" (no hyphen)' in text
    assert "Open with a rhetorical question" in text
    assert "Use call-to-action labels" in text
    assert "Use em dashes or colon reveals" in text
    assert "Hashtags: none on X. On Bluesky, at most two, and specific" in text
    assert "On X, the link goes in a reply" in text


def test_guide_has_no_em_dash_of_its_own():
    assert lint.EM_DASH not in GUIDE.read_text()


def test_guide_banned_list_matches_the_code():
    assert _banned_words_in_the_guide(GUIDE.read_text()) == list(lint.BANNED)


def test_guide_call_to_action_labels_match_the_code():
    labels = _cta_labels_in_the_guide(GUIDE.read_text())
    assert [label.lower() for label in labels] == list(lint.CTA_LABELS)
    assert "What changed" in labels and "Here's how" in labels, "the M24 tells are listed as written"


def test_guide_lists_the_label_rule_among_the_checks():
    text = _flat(GUIDE.read_text())
    assert "a call-to-action label from the list in Don't 5" in text
    assert "as the start of a Bluesky `[label](url)` label" in text


def test_guide_limits_codecrew_posts_to_gh_codecrew():
    text = _flat(GUIDE.read_text())
    assert "post about gh-codecrew itself or how it is used" in text
    for subject in ("the CLI", "the protocol", "the role contracts", "releases", "the docs a user follows"):
        assert subject in text, f"{subject!r} is missing from the scope"
    assert "Never a change that only touches the codecrew.works website" in text
    assert "issuecomment-6469436459" in text, "the guide cites the scope Decision"
    close = text.partition("## Milestone-close posts")[2].partition("## Bluesky budget")[0]
    assert "only for a milestone about gh-codecrew" in close
    assert "gets no post, however small" in close
    assert "issuecomment-6469436459" in close, "the close section cites the Decision that narrowed it"


def test_guide_asks_the_drafter_to_re_read_before_lint():
    text = _flat(GUIDE.read_text())
    step = text.partition("## Before you post")[2].partition("## The check")[0]
    assert "Re-read every draft against the Don't list" in step
    for tell in ("fragment opener", "set-up-and-knock-down", "slogan", "rhythmic three"):
        assert tell in step, f"the step does not say lint cannot judge a {tell}"


def test_guide_hashtag_limits_match_the_code():
    text = GUIDE.read_text()
    match = re.search(r"X (\d+), Bluesky (\d+), LinkedIn (\d+)", text)
    assert match, "the guide states the three limits in one line"
    assert tuple(int(n) for n in match.groups()) == (
        lint.HASHTAG_LIMITS["x"], lint.HASHTAG_LIMITS["bluesky"], lint.HASHTAG_LIMITS["linkedin"],
    )


def test_guide_no_longer_asks_for_a_per_post_trail():
    text = GUIDE.read_text()
    for rule in PER_POST_RULES:
        assert rule not in text, f"{rule!r} is a per-post rule the Decision retired"


def test_guide_no_longer_carries_the_rules_the_voice_review_replaced():
    text = GUIDE.read_text()
    for rule in REPLACED_RULES:
        assert rule not in text, f"{rule!r} was replaced on 2026-10-28, not kept beside the new rule"


def test_readme_no_longer_says_posted_texts_are_kept_in_the_tree():
    section = _social_section(README.read_text())
    assert "kept in `announcements/`" not in section
    assert "announcements/README.md" in section, "the runbook still points at the guide"


def test_readme_runbook_covers_both_accounts_auth_x_and_replies():
    section = _social_section(README.read_text())
    for needle in (
        "--account codecrew", "CODECREW_X_ACCESS_TOKEN", "CODECREW_BSKY_HANDLE",
        "auth x", "--reply-to", "--x-reply-file", "$0.215",
    ):
        assert needle in section, f"{needle!r} is missing from the social runbook"
    assert "there is no reply command" not in section


def test_readme_lists_lint():
    section = _social_section(README.read_text())
    assert "uv run -m social lint" in section
    assert "--skip-lint" in section
    assert "a call-to-action label opening a sentence" in _flat(section)


def test_readme_says_auth_needs_a_terminal():
    section = _flat(_social_section(README.read_text()))
    assert "when stdin is not a terminal" in section and "before requesting any token" in section
    assert "`--paste` reads the code from the terminal" in section


def test_guide_measures_github_counts_and_names_who_runs_them():
    """M12-R3: the ``ghcounts`` part of "Measuring reach" says what the
    ``--help`` line says."""
    from ghcounts import cli as ghcounts_cli

    text = _flat(GUIDE.read_text())
    _, _, section = text.partition("## Measuring reach")
    assert "uv run -m ghcounts" in section
    assert "`ghcounts` is run by the chief of staff, with its own GitHub App token in `GH_TOKEN`" in section
    assert ghcounts_cli.WHO_RUNS_IT == "Run by the chief of staff, with its own GitHub App token in GH_TOKEN."
    for repo in ghcounts_cli.DEFAULT_REPOS:
        assert f"`{repo}`" in section
