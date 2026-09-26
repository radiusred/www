import json
import re

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


# --- the weighted count: bare domains, mirrored from twitter-text (checky's reviews) ---
# js/src/extractUrlsWithIndices.js and js/src/regexp/*.js at twitter/twitter-text master.


def test_a_bare_domain_is_weighed_as_a_url():
    assert x.weighted_len("radiusred.uk") == 23
    assert x.weighted_len("see codecrew.works now") == len("see  now") + 23
    assert x.weighted_len("(radiusred.uk).") == 26
    assert x.weighted_len("a" * 260 + " radiusred.uk") == 284
    with pytest.raises(ValueError, match="284 weighted"):
        x.build_post("a" * 260 + " radiusred.uk")


def test_combining_marks_in_a_label_are_latin_accent_chars():
    # checky's case: NFC keeps U+1EA1 U+0301, both in latinAccentChars.js
    token = "ạ́.com"
    assert x.weighted_len(token) == 23
    assert x.weighted_len("a" * 257 + " " + token) == 281
    with pytest.raises(ValueError, match="281 weighted"):
        x.build_post("a" * 257 + " " + token)
    assert x.weighted_len("á.com") == 23  # composes to á, still in the class


def test_punycode_and_the_unicode_tld_list():
    assert x.weighted_len("foo.xn--p1ai") == 23
    assert x.weighted_len("a" * 260 + " foo.xn--p1ai") == 284
    with pytest.raises(ValueError, match="284 weighted"):
        x.build_post("a" * 260 + " foo.xn--p1ai")
    assert x.weighted_len("foo.рф") == 23  # a Latin label with the ccTLD рф
    assert x.weighted_len("münchen.de/rathaus") == 23 + len("/rathaus")  # the path is weighed literally: over, never under
    assert x.weighted_len("xn--mnchen-3ya.de") == 23
    assert x.weighted_len("foo.中国人") == 25  # TLD 中国, then 人 on its own


def test_case_is_folded_as_twitter_texts_i_flag_does():
    # extractUrl.js and validAsciiDomain.js carry the ``i`` flag; the composed sub-patterns inherit it.
    assert x.weighted_len("a" * 273 + " foo.\u0420\u0424") == 297  # foo.РФ
    with pytest.raises(ValueError, match="297 weighted"):
        x.build_post("a" * 273 + " foo.\u0420\u0424")
    assert x.weighted_len("a" * 267 + " foo.XN--P1AI") == 291
    with pytest.raises(ValueError, match="291 weighted"):
        x.build_post("a" * 267 + " foo.XN--P1AI")
    for token in ("foo.COM", "Foo.Uk", "FOO.XN--P1AI", "foo.Xn--P1aI", "foo.\u0420\u0444", "M\u00dcNCHEN.DE", "FOO.\u4e2d\u56fd"):
        assert x.weighted_len(token) == 23, token
        assert x.bare_domains(token) == [(0, len(token))], token


def test_python_ignorecase_does_not_widen_the_ascii_classes():
    # JavaScript's non-Unicode ``i`` never folds a non-ASCII letter into [a-z]; Python's would fold
    # İ, ı, ſ and K, so the ASCII classes are scoped (?-i:) — and NFC turns K into K first anyway.
    assert x.weighted_len("foo.com\u017f") == 24  # TLD com, then ſ on its own: the lookahead lets it through
    assert x.bare_domains("@\u017ffoo.com") == [(2, 9)]  # ſ is a valid preceding character, so foo.com links
    assert x.bare_domains("foo.co\u0131") == [(0, 6)] and x.weighted_len("foo.co\u0131") == 24
    assert x.weighted_len("\u212afoo.com") == 23  # NFC: KELVIN SIGN is K, and Kfoo.com is one link


def test_labels_outside_the_latin_class_are_not_linked_without_a_scheme():
    # validAsciiDomain: a protocol-less domain links only through Latin labels, as twitter-text does.
    assert x.weighted_len("пример.рф") == 9  # пример.рф, literal
    assert x.bare_domains("пример.рф") == []
    assert x.weighted_len("https://пример.рф") == 23  # with a scheme it is a URL


def test_a_non_latin_prefix_is_weighed_on_its_own_and_the_latin_part_is_the_link():
    # twitter-text extracts the ASCII domain inside a wider validDomain match.
    assert x.bare_domains("日本example.com") == [(2, 13)]
    assert x.weighted_len("日本example.com") == 4 + 23
    assert x.weighted_len("example.com日本") == 23 + 4
    assert x.weighted_len("€foo.com") == 2 + 23


def test_the_preceding_character_rules_are_twitter_texts():
    assert x.bare_domains("darren@radiusred.uk") == []  # after @ nothing links: every start is preceded by [A-Za-z0-9@]
    assert x.weighted_len("darren@radiusred.uk") == 19
    assert x.bare_domains("darren@münchen.de") == [(9, 17)]  # ...but a start after ü is allowed: twitter-text links nchen.de
    assert x.bare_domains("#foo.com") == [] and x.bare_domains("$foo.com") == []
    # fullwidth ＠ and ＃ are not in punct.js: they are domain chars, the match starts at them, and foo.com links
    assert x.bare_domains("＠foo.com") == [(1, 8)] and x.bare_domains("＃foo.com") == [(1, 8)]
    for text in ("-foo.com", "_foo.com", ".foo.com", "x/y.com"):
        assert x.bare_domains(text) == [], text  # invalidUrlWithoutProtocolPrecedingChars skips the match
    assert x.bare_domains('"foo.com"') == [(1, 8)]  # a double quote is not in punct.js, so it is a domain char


def test_a_bare_domain_longer_than_23_keeps_its_literal_weight():
    long_bare = "www.radiusred.uk/blog/posts/2026-09-26-protocol-2-1/"
    assert x.weighted_len(long_bare) == 23 + len("/blog/posts/2026-09-26-protocol-2-1/")
    assert x.weighted_len("https://" + long_bare) == 23  # a scheme makes the whole thing 23
    assert x.weighted_len("randomurlrandomurlrandomurlrandomurlrandomurlrandomurlrandomurls.com") == 68


def test_things_that_are_not_bare_domains_are_weighed_literally():
    for text in ("v2.1.0", "e.g. this", "i.e.", "2026-09-26", "a.b", "1.5x", "foo.123", "c.d", "foo.com1"):
        assert x.weighted_len(text) == len(text), text
        assert x.bare_domains(text) == [], text


def test_the_ascii_domain_class_is_letters_marks_digits_and_hyphen():
    import unicodedata

    chars = [chr(c) for c in range(0x10000) if re.fullmatch(f"[\\-a-zA-Z0-9{x.LATIN_ACCENT}]", chr(c))]
    assert chars, "the class is not empty"
    categories = {unicodedata.category(ch)[0] for ch in chars} - {"P"}  # the hyphen
    assert categories == {"L", "M", "N"}
    assert all(unicodedata.category(chr(c)) == "Mn" for c in range(0x0300, 0x0370))  # every combining diacritical is in


def _linkable_tokens():
    """Bare-domain tokens built from each character category twitter-text's
    validAsciiDomain accepts, with a seeded generator for reproducibility."""
    import random

    rng = random.Random(71)
    pools = {
        "ascii lower": "abcdefghijklmnopqrstuvwxyz",
        "ascii upper": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "digits": "0123456789",
        "latin-1": [chr(c) for c in range(0xC0, 0x100) if c not in (0xD7, 0xF7)],
        "latin extended a/b": [chr(c) for c in range(0x100, 0x250)],
        "ipa singletons": [chr(c) for c in (0x253, 0x254, 0x256, 0x257, 0x259, 0x25B, 0x263, 0x268, 0x26F, 0x272, 0x289, 0x28B, 0x2BB)],
        "combining marks": [chr(c) for c in range(0x300, 0x370)],
        "latin extended additional": [chr(c) for c in range(0x1E00, 0x1F00)],
    }
    tlds = ["com", "uk", "works", "xn--p1ai", "рф", "中国", "info"]
    tokens = []
    for name, pool in pools.items():
        for _ in range(12):
            label = "".join(rng.choice(pool) for _ in range(rng.randint(1, 8)))
            if rng.random() < 0.3 and len(label) >= 2:
                label = label[: len(label) // 2] + "-" + label[len(label) // 2 :]  # a hyphen only inside a label
            if rng.random() < 0.3:
                label = "a" + label  # a combining mark needs something to sit on
            tokens.append((name, label + "." + rng.choice(tlds)))
    return tokens


@pytest.mark.parametrize("before", ["", " ", "(", "日本", "\U0001f44d", "€", "\n", "‍", "«", "—"])
def test_every_linkable_token_weighs_at_least_a_url(before):
    # Property: for each token twitter-text may autolink, in a context that allows it, the guard's
    # count is at least the count with that token replaced by a scheme URL (exactly 23).
    for after in ("", " and more", ".", ")", "日本", "\U0001f44d"):
        for name, token in _linkable_tokens():
            for variant in (token, token.upper(), token.swapcase(), token.title()):
                text = before + variant + after
                floor = x.weighted_len(before + "https://x.co/ ") - 1 + x.weighted_len(after)
                assert x.weighted_len(text) >= floor, (name, repr(text), x.weighted_len(text), floor)


def test_excluded_contexts_stay_literal_like_twitter_text():
    # (fullwidth ＠ and ＃ are domain chars, not excluders, and a letter or digit merges into the label:
    # see the preceding-character test)
    for before in ("@", "$", "#"):
        for _, token in _linkable_tokens()[::7]:
            if re.search(f"[{x.LATIN_ACCENT}]", token.split(".")[0]):
                continue  # a non-ASCII label character is a valid start position for twitter-text too
            assert x.bare_domains(before + token) == [], repr(before + token)

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
