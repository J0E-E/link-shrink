"""Unit tests for linkshrink_shared.validation (no database, no real DNS required)."""

from __future__ import annotations

import socket

import pytest

from linkshrink_shared.validation import (
    REASON_ALIAS_GRAMMAR,
    REASON_ALIAS_HYPHEN,
    REASON_ALIAS_LENGTH,
    REASON_ALIAS_RESERVED,
    REASON_URL_LENGTH,
    REASON_URL_MALFORMED,
    REASON_URL_NO_HOST,
    REASON_URL_PRIVATE_ADDRESS,
    REASON_URL_SCHEME,
    REASON_URL_SELF_REFERENTIAL,
    REASON_URL_UNRESOLVABLE,
    RESERVED_WORDS,
    ValidationError,
    default_host_resolver,
    default_public_host,
    proxy_served_paths,
    validate_alias,
    validate_url,
)

#: A public, non-disallowed address used as the resolver result for accept cases.
PUBLIC_IP = "93.184.216.34"

#: A public host to compare against for self-reference tests.
PUBLIC_HOST = "link-shrink.org"


def public_resolver(_hostname: str) -> list[str]:
    """Resolver stub that always resolves to a single public IP."""
    return [PUBLIC_IP]


# --- validate_alias -------------------------------------------------------------


def test_validate_alias_accepts_valid_alias():
    assert validate_alias("my-link") == "my-link"


def test_validate_alias_normalizes_uppercase():
    assert validate_alias("My-Link") == "my-link"


def test_validate_alias_strips_surrounding_whitespace():
    assert validate_alias("  my-link  ") == "my-link"


@pytest.mark.parametrize("alias", ["abc", "a" * 32])
def test_validate_alias_accepts_length_bounds(alias):
    assert validate_alias(alias) == alias


@pytest.mark.parametrize("alias", ["ab", "a" * 33])
def test_validate_alias_rejects_out_of_bounds_length(alias):
    with pytest.raises(ValidationError) as error:
        validate_alias(alias)
    assert error.value.reason == REASON_ALIAS_LENGTH


@pytest.mark.parametrize("alias", ["bad_alias", "bad.alias", "bad alias", "cafélink"])
def test_validate_alias_rejects_bad_grammar(alias):
    with pytest.raises(ValidationError) as error:
        validate_alias(alias)
    assert error.value.reason == REASON_ALIAS_GRAMMAR


@pytest.mark.parametrize("alias", ["-abc", "abc-"])
def test_validate_alias_rejects_leading_or_trailing_hyphen(alias):
    with pytest.raises(ValidationError) as error:
        validate_alias(alias)
    assert error.value.reason == REASON_ALIAS_HYPHEN


#: Reserved words that are also valid-length aliases (>= 3 chars), so they reach the
#: reserved-word check. Shorter ones (e.g. ``qr``) are rejected by the length guard
#: first and can never be claimed as an alias anyway.
ALIAS_LENGTH_RESERVED_WORDS = sorted(word for word in RESERVED_WORDS if len(word) >= 3)


@pytest.mark.parametrize("word", ALIAS_LENGTH_RESERVED_WORDS)
def test_validate_alias_rejects_reserved_words(word):
    with pytest.raises(ValidationError) as error:
        validate_alias(word)
    assert error.value.reason == REASON_ALIAS_RESERVED


@pytest.mark.parametrize("word", ALIAS_LENGTH_RESERVED_WORDS)
def test_validate_alias_rejects_reserved_words_case_insensitively(word):
    with pytest.raises(ValidationError) as error:
        validate_alias(word.upper())
    assert error.value.reason == REASON_ALIAS_RESERVED


@pytest.mark.parametrize("word", sorted(RESERVED_WORDS))
def test_validate_alias_always_rejects_every_reserved_word(word):
    """Every reserved word is rejected for some reason (length-short ones too)."""
    with pytest.raises(ValidationError):
        validate_alias(word)


# --- validate_url ---------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://example.com/path?q=1",
        "https://EXAMPLE.com/Path",
    ],
)
def test_validate_url_accepts_public_http_urls(url):
    assert validate_url(url, public_host=PUBLIC_HOST, resolver=public_resolver) == url


def test_validate_url_rejects_over_length():
    long_url = "https://example.com/" + "a" * 2048
    with pytest.raises(ValidationError) as error:
        validate_url(long_url, public_host=PUBLIC_HOST, resolver=public_resolver)
    assert error.value.reason == REASON_URL_LENGTH


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "ftp://example.com", "data:text/plain,hi", "example.com"],
)
def test_validate_url_rejects_disallowed_scheme(url):
    with pytest.raises(ValidationError) as error:
        validate_url(url, public_host=PUBLIC_HOST, resolver=public_resolver)
    assert error.value.reason == REASON_URL_SCHEME


@pytest.mark.parametrize("url", ["http://[::1", "https://::1]/x"])
def test_validate_url_rejects_malformed_url(url):
    with pytest.raises(ValidationError) as error:
        validate_url(url, public_host=PUBLIC_HOST, resolver=public_resolver)
    assert error.value.reason == REASON_URL_MALFORMED


def test_validate_url_rejects_missing_host():
    with pytest.raises(ValidationError) as error:
        validate_url("http:///path", public_host=PUBLIC_HOST, resolver=public_resolver)
    assert error.value.reason == REASON_URL_NO_HOST


@pytest.mark.parametrize(
    "url",
    ["https://link-shrink.org/abc", "https://LINK-SHRINK.ORG/abc"],
)
def test_validate_url_rejects_self_referential_host(url):
    with pytest.raises(ValidationError) as error:
        validate_url(url, public_host=PUBLIC_HOST, resolver=public_resolver)
    assert error.value.reason == REASON_URL_SELF_REFERENTIAL


@pytest.mark.parametrize(
    "public_host",
    [PUBLIC_HOST, f"{PUBLIC_HOST}:8443", f"https://{PUBLIC_HOST}:8443"],
)
def test_validate_url_self_reference_tolerates_scheme_and_port_in_public_host(public_host):
    with pytest.raises(ValidationError) as error:
        validate_url(
            f"https://{PUBLIC_HOST}/abc",
            public_host=public_host,
            resolver=public_resolver,
        )
    assert error.value.reason == REASON_URL_SELF_REFERENTIAL


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.1",
        "192.168.1.1",
        "172.16.0.1",
        "127.0.0.1",
        "169.254.1.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "0.0.0.0",
        "::ffff:10.0.0.1",
    ],
)
def test_validate_url_rejects_private_addresses(address):
    with pytest.raises(ValidationError) as error:
        validate_url(
            "https://internal.example.com",
            public_host=PUBLIC_HOST,
            resolver=lambda _host: [address],
        )
    assert error.value.reason == REASON_URL_PRIVATE_ADDRESS


def test_validate_url_rejects_when_any_address_is_private():
    with pytest.raises(ValidationError) as error:
        validate_url(
            "https://mixed.example.com",
            public_host=PUBLIC_HOST,
            resolver=lambda _host: [PUBLIC_IP, "10.0.0.1"],
        )
    assert error.value.reason == REASON_URL_PRIVATE_ADDRESS


def test_validate_url_rejects_unparseable_resolver_output():
    with pytest.raises(ValidationError) as error:
        validate_url(
            "https://bad.example.com",
            public_host=PUBLIC_HOST,
            resolver=lambda _host: ["not-an-ip"],
        )
    assert error.value.reason == REASON_URL_PRIVATE_ADDRESS


def test_validate_url_rejects_unresolvable_host():
    with pytest.raises(ValidationError) as error:
        validate_url(
            "https://nowhere.example.com",
            public_host=PUBLIC_HOST,
            resolver=lambda _host: [],
        )
    assert error.value.reason == REASON_URL_UNRESOLVABLE


def test_validate_url_uses_default_public_host_from_env(monkeypatch):
    monkeypatch.setenv("PUBLIC_HOST", PUBLIC_HOST)
    with pytest.raises(ValidationError) as error:
        validate_url(f"https://{PUBLIC_HOST}/abc", resolver=public_resolver)
    assert error.value.reason == REASON_URL_SELF_REFERENTIAL


# --- default_host_resolver ------------------------------------------------------


def test_default_host_resolver_dedupes_addresses(monkeypatch):
    def fake_getaddrinfo(_host, _port):
        return [
            (socket.AF_INET, None, None, "", ("93.184.216.34", 0)),
            (socket.AF_INET, None, None, "", ("93.184.216.34", 0)),
            (socket.AF_INET6, None, None, "", ("2606:2800:220:1::1", 0, 0, 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert default_host_resolver("example.com") == [
        "93.184.216.34",
        "2606:2800:220:1::1",
    ]


def test_default_host_resolver_returns_empty_on_failure(monkeypatch):
    def fake_getaddrinfo(_host, _port):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert default_host_resolver("nowhere.invalid") == []


# --- default_public_host --------------------------------------------------------


def test_default_public_host_reads_env(monkeypatch):
    monkeypatch.setenv("PUBLIC_HOST", PUBLIC_HOST)
    assert default_public_host() == PUBLIC_HOST


def test_default_public_host_raises_when_unset(monkeypatch):
    monkeypatch.delenv("PUBLIC_HOST", raising=False)
    with pytest.raises(RuntimeError):
        default_public_host()


# --- proxy_served_paths anti-drift ----------------------------------------------


def test_reserved_words_superset_of_proxy_paths():
    assert proxy_served_paths() <= RESERVED_WORDS


def test_proxy_served_paths_have_no_dotted_entries():
    assert all("." not in path for path in proxy_served_paths())


def test_proxy_served_paths_expected_contents():
    assert proxy_served_paths() == frozenset(
        {"api", "health", "metrics", "assets", "static", "dashboard", "how-it-works"}
    )
