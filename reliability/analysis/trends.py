"""Reliability-trend analyser — is the suite getting better or worse over time?

Pure arithmetic over stored runs: compute each run's pass rate in chronological
order, then compare the recent half against the earlier half. No AI, no model.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import List

from ..storage.models import PASSED


@dataclass
class RunPoint:
    run_id: str
    started_at: str
    total: int
    passed: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


@dataclass
class TrendReport:
    points: List[RunPoint] = field(default_factory=list)
    earlier_avg: float = 0.0
    recent_avg: float = 0.0

    @property
    def runs(self) -> int:
        return len(self.points)

    @property
    def delta(self) -> float:
        """Change in average pass rate, recent minus earlier (−1.0 … +1.0)."""
        return self.recent_avg - self.earlier_avg

    @property
    def direction(self) -> str:
        # A 2-point band around zero avoids calling normal noise a "trend".
        if self.delta > 0.02:
            return "improving"
        if self.delta < -0.02:
            return "declining"
        return "stable"


def analyse_trend(conn: sqlite3.Connection) -> TrendReport:
    """Build a chronological reliability trend from stored runs.

    ``passed`` here counts cleanly-passing tests only; a run's flaky/failed
    tests both count against its pass rate, which is what a human cares about.
    """
    rows = conn.execute(
        f"""
        SELECT
            r.run_id,
            r.started_at,
            COUNT(tr.result_id) AS total,
            SUM(CASE WHEN tr.status = '{PASSED}' THEN 1 ELSE 0 END) AS passed
        FROM runs r
        LEFT JOIN test_results tr ON tr.run_id = r.run_id
        GROUP BY r.run_id
        -- NULL started_at sorts last so undated runs don't distort recency.
        ORDER BY r.started_at IS NULL, r.started_at ASC
        """
    ).fetchall()

    points = [
        RunPoint(
            run_id=r["run_id"],
            started_at=r["started_at"] or "",
            total=r["total"] or 0,
            passed=r["passed"] or 0,
        )
        for r in rows
    ]

    report = TrendReport(points=points)
    if len(points) >= 2:
        mid = len(points) // 2
        earlier, recent = points[:mid], points[mid:]
        report.earlier_avg = sum(p.pass_rate for p in earlier) / len(earlier)
        report.recent_avg = sum(p.pass_rate for p in recent) / len(recent)
    return report
