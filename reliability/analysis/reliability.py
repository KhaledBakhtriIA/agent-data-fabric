"""Reliability-score analyser — one 0–100 number per test and for the suite.

Where flakiness explains *why* a test is unstable and trend shows *direction*,
this gives a blunt KPI you can watch: what fraction of the time does a test
cleanly pass? Pure arithmetic over stored history; no AI.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import List

from ..storage.models import FAILED, FLAKY, PASSED, SKIPPED


@dataclass
class TestReliability:
    test_key: str
    name: str
    runs: int
    passed: int
    failed: int
    flaky: int
    skipped: int

    @property
    def considered(self) -> int:
        # Skips mean the test never actually ran, so they don't count for or
        # against reliability — exclude them from the denominator.
        return self.runs - self.skipped

    @property
    def score(self) -> float:
        """Clean-pass rate as a 0–100 score. Flaky and failed both count against."""
        if self.considered <= 0:
            return 100.0
        return 100.0 * self.passed / self.considered


@dataclass
class ReliabilityReport:
    tests: List[TestReliability] = field(default_factory=list)

    @property
    def suite_score(self) -> float:
        """Overall suite reliability: clean passes across every stored result."""
        considered = sum(t.considered for t in self.tests)
        passed = sum(t.passed for t in self.tests)
        if considered <= 0:
            return 100.0
        return 100.0 * passed / considered


def analyse_reliability(conn: sqlite3.Connection, min_runs: int = 1) -> ReliabilityReport:
    """Score every test seen in at least ``min_runs`` runs, least reliable first."""
    rows = conn.execute(
        f"""
        SELECT
            test_key,
            (SELECT name FROM test_results t2
              WHERE t2.test_key = t1.test_key
              ORDER BY t2.result_id DESC LIMIT 1)                 AS name,
            COUNT(*)                                              AS runs,
            SUM(CASE WHEN status = '{PASSED}'  THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN status = '{FAILED}'  THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN status = '{FLAKY}'   THEN 1 ELSE 0 END) AS flaky,
            SUM(CASE WHEN status = '{SKIPPED}' THEN 1 ELSE 0 END) AS skipped
        FROM test_results t1
        GROUP BY test_key
        HAVING runs >= ?
        """,
        (min_runs,),
    ).fetchall()

    tests = [
        TestReliability(
            test_key=r["test_key"],
            name=r["name"],
            runs=r["runs"],
            passed=r["passed"],
            failed=r["failed"],
            flaky=r["flaky"],
            skipped=r["skipped"],
        )
        for r in rows
    ]
    # Least reliable first — that's what a human wants to look at.
    tests.sort(key=lambda t: (t.score, -t.runs))
    return ReliabilityReport(tests=tests)
