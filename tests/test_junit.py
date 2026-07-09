"""Tests for the JUnit XML adapter, using the example fixture."""

from __future__ import annotations

from pathlib import Path

from reliability.adapters import detect_adapter
from reliability.adapters.junit import JUnitAdapter

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_detect_junit() -> None:
    adapter = detect_adapter(EXAMPLES / "junit.xml")
    assert adapter is not None
    assert adapter.name == "junit"


def test_junit_parse_counts() -> None:
    run = JUnitAdapter().parse(EXAMPLES / "junit.xml")
    assert run.framework == "junit"
    assert run.total == 3
    assert run.passed == 2
    assert run.failed == 1
    assert run.skipped == 0


def test_junit_captures_failure_message() -> None:
    run = JUnitAdapter().parse(EXAMPLES / "junit.xml")
    failed = next(r for r in run.results if r.status == "failed")
    assert "complete-header" in (failed.message or "")


def test_junit_test_key_is_stable() -> None:
    # The same test in two runs must produce the same key so history lines up.
    run_a = JUnitAdapter().parse(EXAMPLES / "junit.xml")
    run_b = JUnitAdapter().parse(EXAMPLES / "junit.xml")
    assert [r.test_key for r in run_a.results] == [r.test_key for r in run_b.results]
