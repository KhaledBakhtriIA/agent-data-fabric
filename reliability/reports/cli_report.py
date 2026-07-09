"""Terminal report rendering.

Kept separate from cli.py so the presentation (how findings are printed) is
independent of the command wiring (argument parsing, exit codes). All analysis
is deterministic; this module only formats it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..analysis import analyse_flakiness, analyse_reliability, analyse_trend

_BAR = "═" * 55
_RULE = "-" * 51


def _render_reliability(conn: sqlite3.Connection) -> None:
    # A reliability score is just a pass rate — meaningful from a single run, so
    # it is NOT gated by the flakiness --min-runs threshold.
    report = analyse_reliability(conn, min_runs=1)
    print("  Reliability score")
    print(f"  {_RULE}")
    if not report.tests:
        print("  No tests stored yet.")
        return
    print(f"  Suite reliability: {report.suite_score:.0f}%")
    # Show the five least reliable tests — the ones worth a human's attention.
    worst = [t for t in report.tests if t.score < 100.0][:5]
    if not worst:
        print("  ✓ Every stored test passes cleanly every time.")
        return
    for t in worst:
        print(f"    {t.score:5.0f}%  {t.name}  ({t.passed}/{t.considered} clean of {t.runs})")


def _render_flakiness(conn: sqlite3.Connection, min_runs: int) -> None:
    unstable = analyse_flakiness(conn, min_runs=min_runs)
    print(f"  Flakiness  (tests seen in ≥ {min_runs} runs)")
    print(f"  {_RULE}")
    if not unstable:
        print("  ✓ No flaky tests detected in the stored history.")
        return
    for t in unstable:
        band = "HIGH" if t.flaky_rate >= 0.5 else "MED " if t.flaky_rate >= 0.2 else "LOW "
        print(f"  [{band}] {t.name}")
        print(
            f"         {t.runs} runs — "
            f"pass:{t.passed} fail:{t.failed} flaky:{t.flaky} skip:{t.skipped}"
            f"   flaky-rate {t.flaky_rate * 100:.0f}%"
        )


def _render_trend(conn: sqlite3.Connection) -> None:
    trend = analyse_trend(conn)
    print("  Reliability trend")
    print(f"  {_RULE}")
    if trend.runs < 2:
        print(f"  Need ≥ 2 runs for a trend — {trend.runs} stored so far.")
        return
    arrow = {"improving": "▲", "declining": "▼", "stable": "▬"}[trend.direction]
    print(
        f"  {arrow} {trend.direction.upper()}   "
        f"earlier {trend.earlier_avg * 100:.0f}%  →  recent {trend.recent_avg * 100:.0f}%"
        f"   ({trend.delta * 100:+.0f} pts over {trend.runs} runs)"
    )
    spark = "  ".join(f"{p.pass_rate * 100:.0f}%" for p in trend.points)
    print(f"  per run (old→new): {spark}")


def render_report(
    conn: sqlite3.Connection,
    db_path: Path,
    total_runs: int,
    *,
    show_reliability: bool,
    show_flakiness: bool,
    show_trend: bool,
    min_runs: int,
) -> None:
    """Print the full report. Section flags let the CLI show a subset."""
    print()
    print(_BAR)
    print("  QA Reliability Intelligence — Report")
    print(f"  {total_runs} run(s) in local history  ({db_path})")
    print(_BAR)
    if show_reliability:
        print()
        _render_reliability(conn)
    if show_flakiness:
        print()
        _render_flakiness(conn, min_runs)
    if show_trend:
        print()
        _render_trend(conn)
    print()
    print(_BAR)
    print("  Evidence only — you read it, you decide. Nothing was changed.")
    print(_BAR)
    print()
