import json

import pytest

from social import x
from social.transport import ApiError, Response

# --- OAuth 1.0a: the worked example from X's "Creating a signature" page -----
# https://docs.x.com/resources/fundamentals/authentication/oauth-1-0a/creating-a-signature

DOCS_PARAMS = {
    "status": "Hello Ladies + Gentlemen, a signed OAuth request!",
    "include_entities": "true",
    "oauth_consumer_key": "xvz1evFS4wEEPTGEFPHBog",
    "oauth_nonce": "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg",
    "oauth_signature_method": "HMAC-SHA1",
    "oauth_timestamp": "1318622958",
    "oauth_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
    "oauth_version": "1.0",
}
DOCS_URL = "https://api.x.com/1.1/statuses/update.json"
DOCS_CONSUMER_SECRET = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
DOCS_TOKEN_SECRET = "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"


def test_signature_base_string_matches_the_docs_example():
    assert x.signature_base_string("post", DOCS_URL, DOCS_PARAMS) == (
        "POST&https%3A%2F%2Fapi.x.com%2F1.1%2Fstatuses%2Fupdate.json&include_entities%3Dtrue"
        "%26oauth_consumer_key%3Dxvz1evFS4wEEPTGEFPHBog"
        "%26oauth_nonce%3DkYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"
        "%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1318622958"
        "%26oauth_token%3D370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb"
        "%26oauth_version%3D1.0"
        "%26status%3DHello%2520Ladies%2520%252B%2520Gentlemen%252C%2520a%2520signed%2520OAuth%2520request%2521"
    )


def test_signature_known_answer_from_the_docs_example():
    assert x.sign("POST", DOCS_URL, DOCS_PARAMS, DOCS_CONSUMER_SECRET, DOCS_TOKEN_SECRET) == "Ls93hJiZbQ3akF3HF3x1Bz8/zU4="


def test_percent_encode_keeps_only_unreserved_characters():
    assert x.percent_encode("Ladies + Gentlemen, é!~-_.") == "Ladies%20%2B%20Gentlemen%2C%20%C3%A9%21~-_."


def test_authorization_header_carries_the_signature_over_sorted_encoded_fields():
    header = x.authorization_header(
        "POST", DOCS_URL, DOCS_PARAMS["oauth_consumer_key"], DOCS_CONSUMER_SECRET,
        DOCS_PARAMS["oauth_token"], DOCS_TOKEN_SECRET,
        query={"status": DOCS_PARAMS["status"], "include_entities": "true"},
        nonce=DOCS_PARAMS["oauth_nonce"], timestamp=1318622958,
    )
    assert header == (
        'OAuth oauth_consumer_key="xvz1evFS4wEEPTGEFPHBog", '
        'oauth_nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", '
        'oauth_signature="Ls93hJiZbQ3akF3HF3x1Bz8%2FzU4%3D", '
        'oauth_signature_method="HMAC-SHA1", oauth_timestamp="1318622958", '
        'oauth_token="370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", oauth_version="1.0"'
    )


def test_a_fresh_header_has_a_new_nonce_and_the_current_time():
    a = x.authorization_header("GET", "https://api.x.com/2/users/me", "k", "s", "t", "ts")
    b = x.authorization_header("GET", "https://api.x.com/2/users/me", "k", "s", "t", "ts")
    assert a.startswith("OAuth ") and a != b
    assert 'oauth_timestamp="1' in a and 'oauth_version="1.0"' in a


# --- the weighted count (twitter-text config v3) ----------------------------


def test_plain_text_boundary_is_280():
    assert x.weighted_len("a" * 280) == 280
    x.build_post("a" * 280)
    with pytest.raises(ValueError, match=r"281 weighted characters; X allows 280"):
        x.build_post("a" * 281)


def test_every_url_counts_as_23_whatever_its_length():
    long_url = "https://www.radiusred.uk/blog/posts/2026-09-26-protocol-2-1/"  # 60
    assert len(long_url) == 60 and x.weighted_len(long_url) == 23
    assert x.weighted_len("https://a.b/") == 23  # 12 characters, still 23
    assert x.weighted_len("see https://a.b/, then https://c.d/e.") == len("see , then .") + 46


def test_url_boundary_with_text():
    url = "https://www.radiusred.uk/blog/posts/2026-09-26-protocol-2-1/"
    x.build_post("a" * 256 + " " + url)  # 257 + 23
    with pytest.raises(ValueError, match="281 weighted"):
        x.build_post("a" * 257 + " " + url)


def test_cjk_counts_2_each():
    assert x.weighted_len("日" * 140) == 280
    x.build_post("日" * 140)
    with pytest.raises(ValueError, match="282 weighted"):
        x.build_post("日" * 141)


@pytest.mark.parametrize(
    "emoji",
    ["👍", "👍🏽", "👨‍👩‍👧", "1️⃣", "🇬🇧", "☀️", "©️", "❤️"],
)
def test_an_emoji_sequence_counts_2_as_one(emoji):
    assert x.weighted_len(emoji) == 2
    assert x.weighted_len(f"a{emoji}b") == 4


def test_punctuation_ranges_and_currency():
    assert x.weighted_len("—") == 1  # em dash, U+2014, in the light ranges
    assert x.weighted_len("•") == 2  # bullet, U+2022, is just outside them
    assert x.weighted_len("€") == 2  # U+20AC is outside them
    assert x.weighted_len("©") == 1  # text presentation stays 1


def test_input_is_normalised_to_nfc():
    assert x.weighted_len("café") == 4
    assert x.build_post("café")["text"] == "café"


def test_build_post_strips_and_refuses_empty():
    assert x.build_post("  hi  ") == {"text": "hi"}
    with pytest.raises(ValueError, match="empty"):
        x.build_post("   ")


# --- the client ---------------------------------------------------------------


def _client(transport):
    return x.X(transport, "@example_uk", "xkey", "xsecret", "xtoken", "xtokensecret")


def test_me_signs_a_get_with_the_consumer_key_and_token(transport):
    transport.expect("GET", "/2/users/me", body={"data": {"id": "1", "name": "Example", "username": "example_uk"}})
    assert _client(transport).me()["username"] == "example_uk"
    call = transport.calls[0]
    assert call["url"] == "https://api.x.com/2/users/me" and call["body"] is None
    auth = call["headers"]["Authorization"]
    assert auth.startswith("OAuth ") and 'oauth_consumer_key="xkey"' in auth and 'oauth_token="xtoken"' in auth
    assert "xsecret" not in auth and "xtokensecret" not in auth


def test_post_sends_the_json_body_unsigned_and_returns_the_url(transport):
    transport.expect("POST", "/2/tweets", status=201, body={"data": {"id": "1970", "text": "hi"}})
    result = _client(transport).post(x.build_post("hi"))
    assert result == {"id": "1970", "url": "https://x.com/example_uk/status/1970"}
    call = transport.calls[0]
    assert call["headers"]["Content-Type"] == "application/json"
    assert json.loads(call["body"]) == {"text": "hi"}
    # the header is verifiable from its own fields: the body is not part of the base string
    fields = dict(
        (k, v.strip('"')) for k, v in (part.split("=", 1) for part in call["headers"]["Authorization"][6:].split(", "))
    )
    signature = fields.pop("oauth_signature")
    assert x.percent_encode(x.sign("POST", call["url"], fields, "xsecret", "xtokensecret")) == signature


def test_402_with_the_credits_depleted_problem_is_out_of_credits(transport):
    transport.expect("POST", "/2/tweets", status=402, body={
        "detail": "credits depleted", "status": 402, "title": "Payment Required",
        "type": "https://api.x.com/2/problems/credits-depleted",
    })
    with pytest.raises(x.OutOfCredits, match=r"X post failed: out of credits — .*buy credits in the X Developer Console") as info:
        _client(transport).post(x.build_post("hi"))
    assert "HTTP 402" in str(info.value)


def test_402_with_the_credits_depleted_type_alone_is_out_of_credits(transport):
    transport.expect("POST", "/2/tweets", status=402, body={"type": "https://api.x.com/2/problems/credits-depleted", "status": 402})
    with pytest.raises(x.OutOfCredits):
        _client(transport).post(x.build_post("hi"))


def test_402_with_the_camel_case_title_is_out_of_credits(transport):
    transport.expect("GET", "/2/users/me", status=402, body={"title": "CreditsDepleted", "status": 402, "type": "about:blank"})
    with pytest.raises(x.OutOfCredits, match="X check failed: out of credits"):
        _client(transport).me()


def test_a_problem_naming_credits_is_out_of_credits_whatever_the_status(transport):
    transport.expect("POST", "/2/tweets", status=403, body={
        "title": "CreditsDepleted", "detail": "Your enrolled account does not have any credits to fulfill this request",
        "type": "about:blank", "status": 403,
    })
    with pytest.raises(x.OutOfCredits, match="out of credits"):
        _client(transport).post(x.build_post("hi"))


def test_other_errors_stay_generic_api_errors(transport):
    transport.expect("POST", "/2/tweets", status=403, body={
        "title": "Forbidden", "detail": "You are not permitted to perform this action.", "type": "about:blank",
    })
    with pytest.raises(ApiError, match="X post failed: HTTP 403") as info:
        _client(transport).post(x.build_post("hi"))
    assert not isinstance(info.value, x.OutOfCredits)
    assert "out of credits" not in str(info.value)


def test_402_saying_something_else_stays_a_generic_api_error_with_its_status(transport):
    transport.expect("POST", "/2/tweets", status=402, body={"title": "Payment Required", "detail": "billing profile incomplete", "type": "about:blank", "status": 402})
    with pytest.raises(ApiError, match="X post failed: HTTP 402 .*billing profile incomplete") as info:
        _client(transport).post(x.build_post("hi"))
    assert not isinstance(info.value, x.OutOfCredits) and "out of credits" not in str(info.value)


def test_402_with_no_parseable_body_stays_a_generic_api_error(transport):
    transport.expect("GET", "/2/users/me", status=402, body=b"")
    with pytest.raises(ApiError, match="X check failed: HTTP 402$") as info:
        _client(transport).me()
    assert not isinstance(info.value, x.OutOfCredits)


def test_a_credit_card_problem_is_not_out_of_credits(transport):
    transport.expect("POST", "/2/tweets", status=403, body={"title": "Forbidden", "detail": "credit card verification failed", "type": "about:blank"})
    with pytest.raises(ApiError, match="HTTP 403") as info:
        _client(transport).post(x.build_post("hi"))
    assert not isinstance(info.value, x.OutOfCredits)


@pytest.mark.parametrize(
    "body",
    [
        {"type": "credits-depleted"},
        {"title": "Payment Required", "detail": "credits depleted"},
        {"title": "Payment Required", "detail": "Your enrolled account does not have any credits to fulfill this request"},
        {"errors": [{"message": "Insufficient credits"}]},
        {"errors": [{"title": "No credits remaining"}]},
        {"detail": "Credit balance is negative"},
        {"detail": "credits exhausted"},
    ],
)
def test_credit_depletion_phrases_match(body):
    assert x.out_of_credits(Response(402, json.dumps(body).encode()))
    assert x.out_of_credits(Response(403, json.dumps(body).encode()))


@pytest.mark.parametrize(
    "body",
    [
        b"", b"not json", b"[1, 2]",
        b'{"detail": "no credit card on file"}',
        b'{"detail": "credit card verification failed"}',
        b'{"title": "Payment Required", "detail": "billing profile incomplete"}',
        b'{"detail": "You are not permitted to perform this action."}',
        b'{"type": "https://api.x.com/2/problems/usage-capped"}',
    ],
)
def test_unrelated_bodies_do_not_match_whatever_the_status(body):
    assert not x.out_of_credits(Response(402, body))
    assert not x.out_of_credits(Response(403, body))


# --- the weighted count: bare domains and the light ranges (checky's review) ---


def test_a_bare_domain_is_weighed_as_a_url():
    assert x.weighted_len("radiusred.uk") == 23
    assert x.weighted_len("see codecrew.works/blog now") == len("see  now") + 23
    assert x.weighted_len("(radiusred.uk).") == 26
    assert x.weighted_len("a" * 260 + " radiusred.uk") == 284
    with pytest.raises(ValueError, match="284 weighted"):
        x.build_post("a" * 260 + " radiusred.uk")


def test_a_bare_domain_longer_than_23_keeps_its_literal_weight():
    long_bare = "www.radiusred.uk/blog/posts/2026-09-26-protocol-2-1/"
    assert x.weighted_len(long_bare) == len(long_bare)  # never under 23, never under literal
    assert x.weighted_len("https://" + long_bare) == 23  # a scheme makes it a certain URL


def test_things_that_are_not_bare_domains_are_weighed_literally():
    for text in ("v2.1.0", "e.g. this", "i.e.", "2026-09-26", "darren@radiusred.uk", "a.b", "x/y.z"):
        assert x.weighted_len(text) == len(text), text
    assert x.weighted_len("darren@radiusred.uk") == 19  # an address is not autolinked


def test_light_range_symbols_weigh_1_and_their_neighbours_2():
    # twitter-text config v3 ranges: 0-4351, 8192-8205, 8208-8223, 8242-8247
    assert x.weighted_len("Ω") == 1  # Omega, in 0-4351
    assert x.weighted_len("‍") == 1  # a lone ZWJ, U+200D
    assert x.weighted_len("‐–—‘’“”‟") == 8  # dashes and quotes
    assert x.weighted_len("′‷") == 2  # primes
    assert x.weighted_len("…") == 2  # the ellipsis, U+2026, is just past 8223
    assert x.weighted_len("‰‸") == 4  # per mille and caret, either side of the primes
    assert x.weighted_len("™") == 2 and x.weighted_len("™️") == 2  # TM (8482) alone, and as one emoji
    assert x.weighted_len("©") == 1 and x.weighted_len("©️") == 2  # (c): text 1, emoji presentation 2
    assert x.weighted_len("®️") == 2


def test_command_key_is_outside_the_light_ranges_and_weighs_2():
    # U+2318 is 8984: not in any v3 range, so twitter-text weighs it 2 as well.
    assert ord("⌘") == 8984 and not any(a <= 8984 <= b for a, b in x.LIGHT_RANGES)
    assert x.weighted_len("⌘") == 2
    assert x.weighted_len("⌘" * 140) == 280
    x.build_post("⌘" * 140)
    with pytest.raises(ValueError, match="282 weighted"):
        x.build_post("⌘" * 141)
    assert x.weighted_len("⌘" * 280) == 560


def test_only_a_real_emoji_absorbs_its_modifiers():
    assert x.weighted_len("a️") == 3  # 1 + 2: a letter is not an emoji base
    assert x.weighted_len("⌘️") == 4  # the command key is not an emoji: twitter-text gives 2 + 2
    assert x.weighted_len("☐️") == 4 and x.weighted_len("☑️") == 2  # ballot box is not, checked one is
    assert x.weighted_len("⌘‍\U0001f44d") == 5  # 2 + 1 + 2: a ZWJ joins nothing to a non-emoji
    assert x.weighted_len("⌚️") == 2 and x.weighted_len("⌚") == 2  # the block's real emoji collapse


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hi http://test.co", 26),
        ("http://test.co", 23),
        ("ÁB", 2),
        ("H🐱☺👨‍👩‍👧‍👦", 7),
        ("😷👾😡🔥💩", 10),
        ("🙋🏽👨‍🎤", 4),
        ("1⃣", 2),
        ("Unicode 10.0 emoji: 🤪; 🧕; 🧕🏾; 🏴󠁧󠁢󠁥󠁮󠁧󠁿", 34),
        ("Unicode 9.0 emoji: 🤠; 💃; 💃🏾", 29),
        ("randomurlrandomurlrandomurlrandomurlrandomurlrandomurlrandomurls.com", 68),
        ("故人西辞黄鹤楼" * 20 + "故人", 284),
    ],
)
def test_twitter_text_conformance_fixtures(text, expected):
    # https://github.com/twitter/twitter-text/blob/master/conformance/validate.yml,
    # WeightedTweetsWithDiscountedEmojiCounterTest (the v3 config).
    assert x.weighted_len(text) == expected
