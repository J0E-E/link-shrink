"""Unit tests for the load-test Nginx p95 parser (Epic 20, no Docker required).

The load-test analyzer (``infra/loadtest/parse_nginx_p95.py``) is not an installed package,
so it is loaded from its path here. These tests cover the pure parsing/percentile logic — the
log-line filtering, the ``rt=`` extraction, the nearest-rank percentile math, and the
``< 50 ms`` budget pass/fail — so the harness stays correct without bringing up the stack.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PARSER_PATH = Path(__file__).resolve().parents[1] / "infra" / "loadtest" / "parse_nginx_p95.py"
_spec = importlib.util.spec_from_file_location("parse_nginx_p95", _PARSER_PATH)
assert _spec is not None and _spec.loader is not None
parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parser)


def _line(method: str, path: str, status: str, request_time: str) -> str:
    """Build one Nginx ``main``-format access-log line (see infra/nginx/nginx.conf)."""
    return (
        f'203.0.113.7 real=203.0.113.7 "{method} {path} HTTP/2.0" '
        f"{status} rt={request_time} cache=-"
    )


class TestParseRequestTimes:
    def test_keeps_only_matching_redirect_302_lines(self) -> None:
        lines = [
            _line("GET", "/abc123", "302", "0.004"),  # match
            _line("GET", "/abc123", "302", "0.006"),  # match
            _line("GET", "/other1", "302", "0.009"),  # wrong code
            _line("GET", "/abc123", "404", "0.002"),  # wrong status (negative/unknown)
            _line("POST", "/abc123", "302", "0.003"),  # wrong method
            _line("GET", "/api/links", "200", "0.011"),  # API, not a redirect
        ]
        assert parser.parse_request_times(lines, "abc123") == [0.004, 0.006]

    def test_query_string_on_the_code_still_matches(self) -> None:
        # `?source=qr` redirects share the bare-code hot path; the query string is ignored.
        lines = [_line("GET", "/abc123?source=qr", "302", "0.005")]
        assert parser.parse_request_times(lines, "abc123") == [0.005]

    def test_a_prefix_of_the_code_does_not_match(self) -> None:
        # `/abc1234` must not match `--code abc123` (exact path compare, not a prefix).
        lines = [_line("GET", "/abc1234", "302", "0.005")]
        assert parser.parse_request_times(lines, "abc123") == []

    def test_ignores_unparseable_lines(self) -> None:
        lines = ["garbage", "", _line("GET", "/abc123", "302", "0.004")]
        assert parser.parse_request_times(lines, "abc123") == [0.004]


class TestPercentile:
    def test_nearest_rank_on_one_to_one_hundred(self) -> None:
        values = [n / 1000 for n in range(1, 101)]  # 0.001 .. 0.100
        assert parser.percentile(values, 50) == pytest.approx(0.050)
        assert parser.percentile(values, 95) == pytest.approx(0.095)
        assert parser.percentile(values, 99) == pytest.approx(0.099)

    def test_unsorted_input_is_handled(self) -> None:
        assert parser.percentile([0.030, 0.010, 0.020], 50) == pytest.approx(0.020)

    def test_single_sample(self) -> None:
        assert parser.percentile([0.042], 95) == pytest.approx(0.042)

    def test_empty_sample_raises(self) -> None:
        with pytest.raises(ValueError):
            parser.percentile([], 95)


class TestSummarizeAndBudget:
    def test_summary_fields(self) -> None:
        values = [0.001 * n for n in range(1, 21)]  # 0.001 .. 0.020
        summary = parser.summarize(values)
        assert summary["count"] == 20
        assert summary["min"] == pytest.approx(0.001)
        assert summary["max"] == pytest.approx(0.020)
        assert summary["p95"] == pytest.approx(0.019)

    def test_p95_well_under_budget_passes(self) -> None:
        # All requests at ~4 ms -> p95 far under the 50 ms budget.
        assert parser.summarize([0.004] * 100)["p95"] < parser.P95_BUDGET_SECONDS

    def test_p95_over_budget_is_detectable(self) -> None:
        # A tail of 80 ms responses pushes p95 over budget.
        values = [0.004] * 90 + [0.080] * 10
        assert parser.summarize(values)["p95"] >= parser.P95_BUDGET_SECONDS


class TestMain:
    def test_main_passes_when_under_budget(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        log = "\n".join(_line("GET", "/abc123", "302", "0.004") for _ in range(50))
        monkeypatch.setattr("sys.stdin", _StringStdin(log))
        assert parser.main(["--code", "abc123"]) == 0
        assert "PASS" in capsys.readouterr().out

    def test_main_fails_when_over_budget(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        fast = [_line("GET", "/abc123", "302", "0.004") for _ in range(90)]
        slow = [_line("GET", "/abc123", "302", "0.080") for _ in range(10)]
        monkeypatch.setattr("sys.stdin", _StringStdin("\n".join(fast + slow)))
        assert parser.main(["--code", "abc123"]) == 1
        assert "FAIL" in capsys.readouterr().err

    def test_main_reports_no_matching_lines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.stdin", _StringStdin("nothing relevant here"))
        assert parser.main(["--code", "abc123"]) == 2


class _StringStdin:
    """Minimal stdin stand-in: iterating yields lines, like a real file object."""

    def __init__(self, text: str) -> None:
        self._lines = text.splitlines()

    def __iter__(self):
        return iter(self._lines)
