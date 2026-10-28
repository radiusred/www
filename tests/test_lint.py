"""``social lint``: the guide's mechanical rules (radiusred/www#92, M10-R4).

One failing and one passing example per rule, the command's output and exit
codes, and ``post`` refusing a failing text unless ``--skip-lint`` is given.
"""

import json

import pytest

from social import cli, lint

CLEAN = (
    "gh-codecrew v2.1.2 is out. The merge command now refuses while a reviewer has an open "
    "question on the task. 7 fixes from the fleet, 9 PRs."
)


def rules(text, network="bluesky"):
    return [f.rule for f in lint.lint(text, network)]


# --- one rule at a time ---------------------------------------------------------


def test_clean_text_passes_on_every_network():
    for network in lint.NETWORKS:
        assert lint.lint(CLEAN, network) == []


def test_em_dash_fails_and_shows_where():
    failures = lint.lint("The merge command checks first — and refuses.", "x")
    assert [f.rule for f in failures] == ["em dash"]
    assert "checks first — and refuses" in failures[0].fragment


def test_hyphens_and_en_dashes_are_not_em_dashes():
    assert rules("A second-model review, 2026-10-28, pages 3-4.") == []


def test_first_sentence_question_fails():
    failures = lint.lint("Who reviews your coding agent's pull requests? We do.", "bluesky")
    assert [f.rule for f in failures] == ["the first sentence is a question"]
    assert failures[0].fragment == "Who reviews your coding agent's pull requests?"


def test_question_later_in_the_text_passes():
    assert rules("The reviewer is a second model. Why a second one? The first wrote the code.") == []


def test_first_sentence_ends_at_a_word_not_inside_a_version_or_a_url():
    assert lint.first_sentence("gh-codecrew v2.1.2 is out. Next sentence?") == "gh-codecrew v2.1.2 is out."
    assert lint.first_sentence("See https://codecrew.works/why/gates-in-code/ for the rule? No.") == (
        "See https://codecrew.works/why/gates-in-code/ for the rule?"
    )
    assert lint.first_sentence("Is $0.200 a post worth it? Yes.") == "Is $0.200 a post worth it?"
    assert lint.first_sentence("No terminator at all") == "No terminator at all"


def test_question_in_closing_quotes_still_counts():
    assert rules('"Who reviews the agent?" we asked.') == ["the first sentence is a question"]


@pytest.mark.parametrize(
    "text, word",
    [
        ("A seamless hand-off to the reviewer.", "seamless"),
        ("Seamlessly handed off.", "seamless"),
        ("We leverage the GitHub API.", "leverage"),
        ("It leverages the GitHub API.", "leverage"),
        ("Leveraging the GitHub API.", "leverage"),
        ("Delving into the record.", "delve"),
        ("A GAME CHANGER for small teams.", "game-changer"),
        ("A game-changer for small teams.", "game-changer"),
        ("Here’s the thing about agents.", "here's the thing"),
        ("Here's the  thing about agents.", "here's the thing"),
        ("The best part is the price.", "the best part"),
        ("We are thrilled to announce v2.", "thrilled to announce"),
        ("Excited to announce v2.", "excited to announce"),
        ("Unlocking a new landscape.", "unlock"),
    ],
)
def test_banned_words_fail_case_insensitively_with_inflections(text, word):
    assert f"banned word {word!r}" in rules(text)


def test_banned_words_match_whole_words_only():
    assert rules("Robustness tests, the robot and a journeyman are not the words.") == []
    assert rules("The unlockable door, elevator music, landscaper.") == []


def test_banned_word_failure_names_the_word_and_the_fragment():
    failures = lint.lint("We leverage GitHub.", "x")
    assert failures == [lint.Failure("banned word 'leverage'", "We leverage GitHub.")]
    long = lint.lint("a" * 40 + " leverage " + "b" * 40, "x")
    assert long[0].fragment == "…" + "a" * 19 + " leverage " + "b" * 19 + "…"  # 20 characters of context each side


# --- call-to-action labels (www#96) ---------------------------------------------

M24_REPLY = "What changed and how it was checked: https://github.com/radiusred/gh-codecrew/blob/main/docs/milestones/24-x.md"


@pytest.mark.parametrize(
    "failing, passing, label",
    [
        ("What changed: the merge gate now checks CI first.", "The reviewer found what changed in the diff.", "what changed"),
        ("Here's how the gate works.", "The old post said here's how and linked the page.", "here's how"),
        ("Find out what the reviewer caught.", "The reviewer will find out when the tests run.", "find out"),
        ("Read the record to find out what changed.", "We read the record to find out what the reviewer caught.", "read the … to find out"),
        ("Learn more at the link.", "We learn more from each review.", "learn more"),
        ("Check it out: the record is on main.", "The reviewer will check it out before merging.", "check it out"),
        ("See how the gate works.", "You can see how the gate works in the record.", "see how"),
        ("Click the link for the record.", "A single click opens the record.", "click"),
        ("Link in the reply.", "The link in the reply is the record.", "link in"),
    ],
)
def test_each_call_to_action_label_fails_opening_a_phrase_and_passes_inside_one(failing, passing, label):
    assert rules(failing, "x") == [f"call-to-action label {label!r}"]
    assert rules(passing, "x") == []


def test_the_m24_reply_fails_as_an_x_reply():
    failures = lint.lint(M24_REPLY, "x", reply=True)
    assert [f.rule for f in failures] == ["call-to-action label 'what changed'"]
    assert failures[0].fragment == "What changed and how it was chec…"


def test_a_label_fails_in_a_bluesky_link_label_but_a_plain_label_passes():
    assert rules("v2 is out. [What changed](https://codecrew.works/) #CodeReview") == ["call-to-action label 'what changed'"]
    assert rules("v2 is out. [Read the record to find out why](https://codecrew.works/)") == ["call-to-action label 'read the … to find out'"]
    assert rules("v2 is out. [The M24 record](https://codecrew.works/) #CodeReview") == []


@pytest.mark.parametrize(
    "text",
    [
        "what changed: the gate.",  # lower case at the start
        "WHAT CHANGED: the gate.",
        "Here’s how the gate works.",  # curly apostrophe
        "v2 is out: here's how it works.",  # after a colon
        "v2 is out; here's how it works.",  # after a semicolon
        "v2 is out.\nHere's how it works.",  # a new line
        "v2 is out. \"Here's how\" is the label we dropped.",  # in quotes
        "v2 is out.Here's how it works.",  # no space after the sentence end
    ],
)
def test_a_label_opens_a_phrase_after_any_boundary_in_any_case(text):
    found = rules(text)
    assert len(found) == 1 and found[0].startswith("call-to-action label"), found


def test_a_label_inside_a_sentence_or_after_a_comma_is_not_a_label():
    assert rules("The record lists the tasks, what changed, and who reviewed them.") == []
    assert rules("We clicked through the console. Clicking is fine, clicks are not labels.") == []
    assert rules("Nobody asked what changed. See https://codecrew.works/ for the rule.") == []


def test_a_dot_inside_a_url_is_not_a_phrase_boundary():
    assert rules("The record is at https://codecrew.works/docs/what-changed.click here.") == []
    assert lint.cta_labels("v2.1.2 click") == []


def test_the_ellipsis_in_read_the_to_find_out_stays_inside_one_sentence():
    assert rules("Read the record. To find out more, ask.", "x") == []
    assert lint.cta_labels("Read the long and detailed milestone record to find out what shipped") == [
        ("read the … to find out", 0, 55),
    ]


@pytest.mark.parametrize(
    "network, tags, allowed",
    [
        ("x", 1, False),
        ("x", 0, True),
        ("bluesky", 3, False),
        ("bluesky", 2, True),
        ("linkedin", 6, False),
        ("linkedin", 5, True),
    ],
)
def test_hashtag_limits_per_network(network, tags, allowed):
    text = "v2 is out. " + " ".join(f"#Tag{i}" for i in range(tags))
    failures = lint.lint(text, network)
    if allowed:
        assert failures == []
    else:
        assert failures[0].rule == f"{tags} hashtags; {network} allows {lint.HASHTAG_LIMITS[network]}"
        assert failures[0].fragment == " ".join(f"#Tag{i}" for i in range(tags))


def test_a_url_fragment_and_a_number_are_not_hashtags():
    assert lint.hashtags("See https://codecrew.works/docs#gates and issue #423. #CodeReview") == ["#CodeReview"]


def test_a_url_in_an_x_body_fails_with_the_url():
    failures = lint.lint("v2 is out. https://codecrew.works/blog/v2/.", "x")
    assert failures == [lint.Failure("a URL in the body; on x it goes in the reply", "https://codecrew.works/blog/v2/")]


def test_a_bare_domain_x_would_autolink_fails_too():
    assert rules("Read it at codecrew.works today.", "x") == ["a URL in the body; on x it goes in the reply"]


def test_a_url_in_a_bluesky_or_linkedin_body_passes_lint():
    text = "v2 is out. [Release notes](https://codecrew.works/blog/v2/) and https://codecrew.works/."
    assert rules(text, "bluesky") == []
    assert rules("v2 is out. https://codecrew.works/", "linkedin") == []


def test_a_url_in_an_x_reply_passes_the_url_rule_but_nothing_else():
    assert lint.lint("https://codecrew.works/why/gates-in-code/", "x", reply=True) == []
    assert rules("Here\u2019s the thing: https://codecrew.works/", "x") == [
        'banned word "here\'s the thing"', "a URL in the body; on x it goes in the reply",
    ]
    assert [f.rule for f in lint.lint("Here\u2019s the thing: https://codecrew.works/", "x", reply=True)] == [
        'banned word "here\'s the thing"',
    ]


@pytest.mark.parametrize("text, emoji", [
    ("v2 is out \U0001F680", "\U0001F680"),
    ("Shipped \u2705 today.", "\u2705"),
    ("Thumbs \U0001F44D\U0001F3FD from the reviewer.", "\U0001F44D\U0001F3FD"),
    ("Flag \U0001F1EC\U0001F1E7 day.", "\U0001F1EC\U0001F1E7"),
    ("Step 1\ufe0f\u20e3 done.", "1\ufe0f\u20e3"),
    ("Made with \u00a9\ufe0f care.", "\u00a9\ufe0f"),
])
def test_emoji_fails_with_the_sequence(text, emoji):
    failures = lint.lint(text, "bluesky")
    assert failures == [lint.Failure("emoji", emoji)]


def test_symbols_digits_and_plain_copyright_are_not_emoji():
    assert rules("Costs $0.200 per post, 7 fixes, #1 priority, \u00a9 2026 Radius Red, \u2318 and \u20ac.") == []


def test_agent_staffed_with_a_hyphen_fails():
    failures = lint.lint("Yes, we are agent-staffed.", "bluesky")
    assert [f.rule for f in failures] == ['"agent-staffed" with a hyphen; write "agent staffed, human moderated"']


def test_agent_staffed_without_human_moderated_fails():
    failures = lint.lint("CodeCrew is agent staffed and open source.", "bluesky")
    assert [f.rule for f in failures] == ['"agent staffed" without ", human moderated"']
    assert "agent staffed and open" in failures[0].fragment
    assert rules("We are agent staffed, human-moderated.") == ['"agent staffed" without ", human moderated"']


def test_agent_staffed_human_moderated_passes():
    assert rules("CodeCrew is agent staffed, human moderated. v2 shipped today.") == []
    assert rules("Agent staffed, human moderated.") == []


def test_every_failure_is_reported_not_just_the_first():
    text = "Thrilled to announce? A seamless, robust release — agent-staffed. #A #B #C https://x.example/"
    found = rules(text, "x")
    assert "em dash" in found
    assert "the first sentence is a question" in found
    assert "banned word 'thrilled to announce'" in found and "banned word 'seamless'" in found
    assert "banned word 'robust'" in found
    assert "3 hashtags; x allows 0" in found
    assert "a URL in the body; on x it goes in the reply" in found
    assert '"agent-staffed" with a hyphen; write "agent staffed, human moderated"' in found


def test_unknown_network_is_refused():
    with pytest.raises(ValueError, match="unknown network"):
        lint.lint("hi", "mastodon")


# --- the command --------------------------------------------------------------


def test_lint_command_prints_each_failure_and_exits_1(tmp_path, refusing_transport, capsys):
    draft = tmp_path / "x.txt"
    draft.write_text("Who reviews your agent? We leverage GitHub — see https://codecrew.works/\n")
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), "lint", "--to", "x", "--text-file", str(draft)], transport=refusing_transport, environ={})
    assert rc == 1
    out = capsys.readouterr().out.splitlines()
    assert [line.split(": ", 2)[:2] for line in out] == [
        ["x", "em dash"],
        ["x", "the first sentence is a question"],
        ["x", "banned word 'leverage'"],
        ["x", "a URL in the body; on x it goes in the reply"],
    ]
    assert out[0].endswith("GitHub — see https://codecre…")  # the fragment, with context
    assert out[1].endswith(": Who reviews your agent?")
    assert out[3].endswith(": https://codecrew.works/")


def test_lint_command_reply_flag_allows_the_link(tmp_path, refusing_transport, capsys):
    base = ["--env-file", str(tmp_path / "none.env"), "lint", "--to", "x", "--text", "https://codecrew.works/why/gates-in-code/"]
    assert cli.main(base, transport=refusing_transport, environ={}) == 1
    assert cli.main([*base, "--reply"], transport=refusing_transport, environ={}) == 0
    assert capsys.readouterr().out.endswith("x: lint ok\n")


def test_lint_command_exits_0_when_clean(tmp_path, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(tmp_path / "none.env"), "lint", "--to", "bluesky", "--text", CLEAN], transport=refusing_transport, environ={})
    assert rc == 0
    assert capsys.readouterr().out == "bluesky: lint ok\n"


def test_lint_command_needs_a_network_and_a_text(tmp_path, refusing_transport):
    with pytest.raises(SystemExit):
        cli.main(["--env-file", str(tmp_path / "none.env"), "lint", "--text", "hi"], transport=refusing_transport, environ={})
    with pytest.raises(SystemExit, match="give --text, --text-file"):
        cli.main(["--env-file", str(tmp_path / "none.env"), "lint", "--to", "x"], transport=refusing_transport, environ={})
    with pytest.raises(SystemExit, match="cannot read the x text: .*missing.txt"):
        cli.main(["--env-file", str(tmp_path / "none.env"), "lint", "--to", "x", "--text-file", str(tmp_path / "missing.txt")], transport=refusing_transport, environ={})


# --- post runs lint -------------------------------------------------------------


def test_post_refuses_a_failing_text_before_any_network_call(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "x", "--text", "Shipped: https://codecrew.works/ — enjoy"], transport=refusing_transport, environ={})
    assert rc == 1
    out, err = capsys.readouterr()
    assert out == ""
    lines = err.splitlines()
    assert lines[0] == "error: the bluesky text fails lint (announcements/README.md); --skip-lint sends an approved text"
    assert lines[1].startswith("bluesky: em dash: ")
    assert "error: the x text fails lint" in err
    assert "x: a URL in the body; on x it goes in the reply: https://codecrew.works/" in lines


def test_post_lints_each_network_against_its_own_text(env_file, refusing_transport, tmp_path, capsys):
    xtext = tmp_path / "x.txt"
    xtext.write_text("v2 is out. The link is in the reply. #CodeReview\n")
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "bluesky", "--to", "x", "--text", "v2 is out. [Notes](https://codecrew.works/) #CodeReview", "--x-text-file", str(xtext), "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 1
    err = capsys.readouterr().err
    assert "the bluesky text fails lint" not in err
    assert "x: 1 hashtags; x allows 0: #CodeReview" in err


def test_dry_run_runs_lint_too(env_file, refusing_transport, capsys):
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "We are excited to announce v2.", "--dry-run"], transport=refusing_transport, environ={})
    assert rc == 1
    out, err = capsys.readouterr()
    assert out == "" and "banned word 'excited to announce'" in err


def test_skip_lint_sends_the_text_and_says_so_once(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "1970"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", "Shipped — https://codecrew.works/", "--skip-lint"], transport=transport, environ={})
    assert rc == 0
    out, err = capsys.readouterr()
    assert json.loads(out)["url"] == "https://x.com/example_uk/status/1970"
    assert err == "lint skipped (--skip-lint): sending the text as approved\n"
    assert json.loads(transport.calls[0]["body"])["text"] == "Shipped — https://codecrew.works/"


def test_a_clean_text_posts_without_a_lint_line(env_file, transport, capsys):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "1"}})
    rc = cli.main(["--env-file", str(env_file), "post", "--to", "x", "--text", CLEAN], transport=transport, environ={})
    assert rc == 0
    assert capsys.readouterr().err == ""
