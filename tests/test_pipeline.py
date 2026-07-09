"""End-to-end tests for the reliability tool, using the fixture reports.

Deterministic and framework-runner-free: parse fixture reports → store →
analyse, and assert the numbers. This is the tool testing itself.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from reliability import storage
from reliability.adapters import detect_adapter
from reliability.adapters.playwright import PlaywrightAdapter
from reliability.analysis import analyse_flakiness, analyse_reliability, analyse_trend

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_FILES = sorted(FIXTURES.glob("run-*.json"))

FLAKY_TEST_KEY = "tests/inventory.spec.ts::Inventory › can add two items to cart::chromium"


def _ingest_all(db_path: Path) -> sqlite3.Connection:
    conn = storage.connect(db_path)
    for f in FIXTURE_FILES:
        run = PlaywrightAdapter().parse(f)
        run_id = storage.derive_run_id(run)
        if not storage.run_exists(conn, run_id):
            storage.insert_run(conn, run, run_id)
    return conn


def test_fixtures_present() -> None:
    assert len(FIXTURE_FILES) == 4


def test_detect_playwright() -> None:
    adapter = detect_adapter(FIXTURE_FILES[0])
    assert adapter is not None
    assert adapter.name == "playwright"


def test_parse_produces_four_results() -> None:
    run = PlaywrightAdapter().parse(FIXTURE_FILES[0])
    assert run.framework == "playwright"
    assert run.tool_version == "1.45.0"
    assert run.total == 4
    assert run.passed == 4


def test_ingest_counts(tmp_path: Path) -> None:
    conn = _ingest_all(tmp_path / "ev.db")
    assert storage.run_count(conn) == 4
    conn.close()


def test_ingest_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "ev.db"
    conn = _ingest_all(db)
    assert storage.run_count(conn) == 4
    # Re-ingest everything: count must not grow.
    for f in FIXTURE_FILES:
        run = PlaywrightAdapter().parse(f)
        rid = storage.derive_run_id(run)
        if not storage.run_exists(conn, rid):
            storage.insert_run(conn, run, rid)
    assert storage.run_count(conn) == 4
    conn.close()


def test_flakiness_surfaces_unstable_test(tmp_path: Path) -> None:
    conn = _ingest_all(tmp_path / "ev.db")
    unstable = analyse_flakiness(conn, min_runs=2)
    keys = {t.test_key for t in unstable}
    assert FLAKY_TEST_KEY in keys

    flaky = next(t for t in unstable if t.test_key == FLAKY_TEST_KEY)
    # Across the 4 runs: pass, fail, flaky, pass
    assert flaky.runs == 4
    assert flaky.passed == 2
    assert flaky.failed == 1
    assert flaky.flaky == 1
    assert flaky.flaky_rate == pytest.approx(0.5)
    conn.close()


def test_flakiness_ignores_always_passing_tests(tmp_path: Path) -> None:
    conn = _ingest_all(tmp_path / "ev.db")
    unstable = analyse_flakiness(conn, min_runs=2)
    names = {t.name for t in unstable}
    # "standard user can log in" passes in every run → not flaky.
    assert not any("standard user can log in" in n for n in names)
    conn.close()


def test_trend_is_improving(tmp_path: Path) -> None:
    conn = _ingest_all(tmp_path / "ev.db")
    trend = analyse_trend(conn)
    assert trend.runs == 4
    # earlier avg (100%, 50%) = 75%  →  recent avg (75%, 100%) = 87.5%
    assert trend.recent_avg > trend.earlier_avg
    assert trend.direction == "improving"
    conn.close()


def test_reliability_scores(tmp_path: Path) -> None:
    conn = _ingest_all(tmp_path / "ev.db")
    report = analyse_reliability(conn, min_runs=1)
    # 13 clean passes out of 16 considered results across the 4 runs.
    assert report.suite_score == pytest.approx(13 / 16 * 100)
    flaky = next(t for t in report.tests if t.test_key == FLAKY_TEST_KEY)
    assert flaky.score == pytest.approx(50.0)
    # Least-reliable-first ordering.
    assert report.tests[0].score <= report.tests[-1].score
    conn.close()


def test_flaky_run_captures_failure_message() -> None:
    # Even when a test ends up flaky (passes on retry), we keep the failure
    # reason from the failed attempt.
    run = PlaywrightAdapter().parse(FIXTURES / "run-2026-07-03.json")
    flaky = next(r for r in run.results if r.status == "flaky")
    assert flaky.retries == 1
    assert "TimeoutError" in (flaky.message or "")
