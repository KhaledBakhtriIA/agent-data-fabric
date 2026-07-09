"""Flakiness analyser — pure statistics over stored run history. No AI.

The signal a single run can't give you: a test that sometimes passes and
sometimes fails *for the same code* is flaky. A test that always fails is
broken, not flaky. We separate the two by looking across every stored run.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..storage.models import FAILED, FLAKY, PASSED, SKIPPED


@dataclass
class FlakyTest:
    test_key: str
    name: str
    runs: int
    passed: int
    failed: int
    flaky: int
    skipped: int

    @property
    def bad(self) -> int:
        """Runs where the test did not cleanly pass (failed or flaky-passed)."""
        return self.failed + self.flaky

    @property
    def flip_flaky(self) -> bool:
        """True when outcomes are inconsistent — the classic flaky fingerprint.

        Either the framework reported an in-run flaky pass, or across history
        the test has both passed and failed. A test that only ever fails is
        excluded here (it's broken, and reported as such).
        """
        return self.flaky > 0 or (self.passed > 0 and self.failed > 0)

    @property
    def flaky_rate(self) -> float:
        """Share of runs that didn't cleanly pass, 0.0–1.0."""
        return self.bad / self.runs if self.runs else 0.0


def analyse_flakiness(conn: sqlite3.Connection, min_runs: int = 2) -> list[FlakyTest]:
    """Return unstable tests, most-unstable first.

    ``min_runs`` guards against calling a test flaky on a single data point —
    you need history for the word to mean anything.
    """
    rows = conn.execute(
        f"""
        SELECT
            test_key,
            -- most recent human-readable name for this test_key
            (SELECT name FROM test_results t2
              WHERE t2.test_key = t1.test_key
              ORDER BY t2.result_id DESC LIMIT 1) AS name,
            COUNT(*)                                                   AS runs,
            SUM(CASE WHEN status = '{PASSED}'  THEN 1 ELSE 0 END)      AS passed,
            SUM(CASE WHEN status = '{FAILED}'  THEN 1 ELSE 0 END)      AS failed,
            SUM(CASE WHEN status = '{FLAKY}'   THEN 1 ELSE 0 END)      AS flaky,
            SUM(CASE WHEN status = '{SKIPPED}' THEN 1 ELSE 0 END)      AS skipped
        FROM test_results t1
        GROUP BY test_key
        HAVING runs >= ?
        """,
        (min_runs,),
    ).fetchall()

    tests = [
        FlakyTest(
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

    # Only surface tests that are actually unstable (flip between outcomes).
    unstable = [t for t in tests if t.flip_flaky]
    unstable.sort(key=lambda t: (t.flaky_rate, t.runs), reverse=True)
    return unstable
