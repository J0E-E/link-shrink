"""Epic 3 — short-code generation unit tests (no database).

Verifies the acceptance criteria from the epic plan:

* encode is deterministic per sequence value;
* decode round-trips;
* generated codes match the alias grammar ``[a-z0-9-]`` (single case) with length >= 6;
* the bounded retry loop advances on a simulated conflict and gives up after the cap.

The retry-loop tests inject plain async callables (no DB), so the whole module runs
without Docker and ``pytest`` stays green on a Docker-less machine.
"""

from __future__ import annotations

import re

import pytest

from linkshrink_shared.shortcode import (
    SHORT_CODE_MIN_LENGTH,
    ShortCodeCollisionError,
    ShortCodeGenerator,
    default_short_code_generator,
    generate_unique_short_code,
)

TEST_SALT = "test-salt"
ALIAS_GRAMMAR = re.compile(r"[a-z0-9-]+")
SAMPLE_VALUES = [1, 2, 5, 10, 1000, 999_999_999]


def make_generator(salt: str = TEST_SALT) -> ShortCodeGenerator:
    return ShortCodeGenerator(salt)


def test_encode_deterministic() -> None:
    """The same value encodes to the same code across same-salt generators."""
    first = make_generator()
    second = make_generator()
    for n in SAMPLE_VALUES:
        assert first.encode(n) == second.encode(n)
        assert first.encode(n) == first.encode(n)


def test_decode_round_trips() -> None:
    generator = make_generator()
    for n in SAMPLE_VALUES:
        assert generator.decode(generator.encode(n)) == n


def test_output_matches_alias_grammar() -> None:
    generator = make_generator()
    for n in range(1, 500):
        assert ALIAS_GRAMMAR.fullmatch(generator.encode(n))


def test_no_uppercase_or_hyphen() -> None:
    """Generated codes are strictly [a-z0-9] — tighter than the alias grammar."""
    generator = make_generator()
    for n in range(1, 500):
        code = generator.encode(n)
        assert code == code.lower()
        assert "-" not in code


def test_min_length_padding() -> None:
    generator = make_generator()
    for n in range(1, 6):
        assert len(generator.encode(n)) >= SHORT_CODE_MIN_LENGTH


def test_salt_affects_output() -> None:
    one = make_generator("salt-one")
    two = make_generator("salt-two")
    assert one.encode(1) != two.encode(1)


def test_decode_invalid_returns_none() -> None:
    generator = make_generator()
    assert generator.decode("!!!") is None
    assert generator.decode("ABCDEF") is None
    assert generator.decode("") is None


def test_encode_rejects_non_positive() -> None:
    generator = make_generator()
    with pytest.raises(ValueError):
        generator.encode(0)
    with pytest.raises(ValueError):
        generator.encode(-1)


def test_empty_salt_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError):
        ShortCodeGenerator(salt="")
    # Set to "" (not delenv): an env var overrides the dev `.env` dotenv source, so the
    # "salt unset" path is exercised deterministically whether or not a local .env exists.
    monkeypatch.setenv("HASHIDS_SALT", "")
    with pytest.raises(RuntimeError):
        default_short_code_generator()


class SequenceValues:
    """Yields increasing sequence values and records how many were taken."""

    def __init__(self, start: int = 1) -> None:
        self.next_value = start
        self.call_count = 0

    async def __call__(self) -> int:
        self.call_count += 1
        value = self.next_value
        self.next_value += 1
        return value


async def test_retry_advances_on_conflict() -> None:
    """A single conflict advances the sequence and the second value is used."""
    generator = make_generator()
    sequence = SequenceValues(start=1)
    attempts: list[str] = []

    async def try_persist(code: str) -> bool:
        attempts.append(code)
        return len(attempts) > 1  # first attempt collides, second succeeds

    code = await generate_unique_short_code(
        sequence, try_persist, generator=generator
    )

    assert sequence.call_count == 2
    assert code == generator.encode(2)  # second sequence value, not a re-encode of the first
    assert attempts == [generator.encode(1), generator.encode(2)]


async def test_gives_up_after_exactly_max_attempts() -> None:
    generator = make_generator()
    sequence = SequenceValues(start=1)
    persist_calls = 0

    async def try_persist(code: str) -> bool:
        nonlocal persist_calls
        persist_calls += 1
        return False  # never succeeds

    with pytest.raises(ShortCodeCollisionError):
        await generate_unique_short_code(
            sequence, try_persist, generator=generator, max_attempts=3
        )

    assert sequence.call_count == 3
    assert persist_calls == 3


async def test_success_on_last_attempt() -> None:
    generator = make_generator()
    sequence = SequenceValues(start=1)
    persist_calls = 0

    async def try_persist(code: str) -> bool:
        nonlocal persist_calls
        persist_calls += 1
        return persist_calls == 3  # succeeds only on the final allowed attempt

    code = await generate_unique_short_code(
        sequence, try_persist, generator=generator, max_attempts=3
    )

    assert code == generator.encode(3)
    assert persist_calls == 3
