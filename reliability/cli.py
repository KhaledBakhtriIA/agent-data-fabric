"""Command-line interface: ``reliability ingest`` and ``reliability report``.

Two verbs, matching the README:
  ingest  — normalise one result file into the local history store
  report  — print deterministic reliability + flakiness + trend analysis

This module is thin on purpose: parsing/persistence live in adapters/storage,
statistics in analysis, and formatting in reports. Here we only wire them up.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import storage
from .adapters import detect_adapter, get_adapter
from .reports import render_report


# --------------------------------------------------------------------------- #
# ingest
# --------------------------------------------------------------------------- #
def cmd_ingest(args: argparse.Namespace) -> int:
    result_file = Path(args.result_file)
    if not result_file.exists():
        print(f"Error: result file not found at '{result_file}'", file=sys.stderr)
        print("Run your tests first to produce a result file.", file=sys.stderr)
        return 1

    # Pick the adapter: explicit --framework, or sniff the file.
    if args.framework == "auto":
        adapter = detect_adapter(result_file)
        if adapter is None:
            print(
                f"Error: could not recognise the format of '{result_file}'.",
                file=sys.stderr,
            )
            print(
                "Pass --framework playwright|junit|pytest to force an adapter.",
                file=sys.stderr,
            )
            return 1
    else:
        adapter = get_adapter(args.framework)

    try:
        run = adapter.parse(result_file)
    except NotImplementedError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    conn = storage.connect(Path(args.db))
    try:
        run_id = storage.derive_run_id(run)
        if storage.run_exists(conn, run_id):
            # Idempotency: re-ingesting the same run changes nothing.
            print(f"[ingest] run {run_id} already stored — skipping (idempotent)")
            return 0

        storage.insert_run(conn, run, run_id)
        print(f"[ingest] stored run {run_id} ({adapter.name})")
        print(f"         source : {run.source_file}")
        print(
            f"         results: {run.total}  "
            f"passed:{run.passed} failed:{run.failed} "
            f"flaky:{run.flaky} skipped:{run.skipped}"
        )
        print(f"         history: {storage.run_count(conn)} run(s) now stored")
        return 0
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def cmd_report(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: no evidence store at '{db_path}'.", file=sys.stderr)
        print("Run 'reliability ingest <result-file>' first.", file=sys.stderr)
        return 1

    # If the user names no section, show all three; otherwise show only those named.
    any_flag = args.reliability or args.flakiness or args.trend
    show_reliability = args.reliability or not any_flag
    show_flakiness = args.flakiness or not any_flag
    show_trend = args.trend or not any_flag

    conn = storage.connect(db_path)
    try:
        render_report(
            conn,
            db_path,
            storage.run_count(conn),
            show_reliability=show_reliability,
            show_flakiness=show_flakiness,
            show_trend=show_trend,
            min_runs=args.min_runs,
        )
        return 0
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reliability",
        description="Local-first, framework-agnostic test-reliability history.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="normalise a result file into local history")
    p_ingest.add_argument("result_file", help="path to a test result file (e.g. report.json)")
    p_ingest.add_argument(
        "--framework",
        default="auto",
        choices=["auto", "playwright", "junit", "pytest"],
        help="force an adapter instead of auto-detecting (default: auto)",
    )
    p_ingest.add_argument(
        "--db", default=str(storage.DEFAULT_DB_PATH), help="evidence DB path"
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_report = sub.add_parser("report", help="print reliability, flakiness and trend")
    p_report.add_argument("--db", default=str(storage.DEFAULT_DB_PATH), help="evidence DB path")
    p_report.add_argument(
        "--reliability", action="store_true", help="show only the reliability-score section"
    )
    p_report.add_argument(
        "--flakiness", action="store_true", help="show only the flakiness section"
    )
    p_report.add_argument(
        "--trend", action="store_true", help="show only the reliability-trend section"
    )
    p_report.add_argument(
        "--min-runs",
        type=int,
        default=2,
        help="minimum runs before a test is judged flaky (default: 2)",
    )
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
