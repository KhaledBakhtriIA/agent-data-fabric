"""Interactive console and one-shot `run` for testing any target project.

`run_once` points the tool at a project: it runs that project's tests, ingests
the results into the project's own local history (``<project>/.reliability/``),
and prints the reliability report. `interactive` wraps that in a small menu that
"pops up" when you open the project.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

from . import storage
from .adapters import detect_adapter
from .analysis import analyse_reliability
from .reports import render_report
from .runners import detect_runner

BAR = "═" * 60


def use_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _work_dir(project: Path) -> Path:
    return project / ".reliability"


def _project_db(project: Path) -> Path:
    return _work_dir(project) / "history.db"


def run_once(project: Path, command: str | None = None, result: str | None = None) -> int:
    """Run the target's tests once, record the run, and report. Returns an exit code."""
    project = project.resolve()
    if not project.is_dir():
        print(f"error: not a directory: {project}", file=sys.stderr)
        return 1

    work = _work_dir(project)
    work.mkdir(parents=True, exist_ok=True)

    # Decide what to run and which result file to read afterwards.
    if command:
        if not result:
            print("error: --command also needs --result <file the command writes>", file=sys.stderr)
            return 1
        produces = Path(result)
        if not produces.is_absolute():
            produces = (project / produces).resolve()
        print(f"Running: {command}")
        proc = subprocess.run(command, cwd=str(project), shell=True)
    else:
        runner = detect_runner(project, work)
        if runner is None:
            print(f"Could not detect a test framework in {project}.")
            print("Supported: Playwright (playwright.config.*) and pytest.")
            print('Otherwise:  reliability run <path> --command "<cmd>" --result <file>')
            return 1
        produces = runner.produces
        print(f"Detected {runner.name}. Running: {' '.join(runner.command)}")
        proc = subprocess.run(
            runner.command, cwd=str(project), env={**os.environ, **runner.env}
        )

    if not produces.exists():
        print(f"error: the test command produced no result file at {produces}", file=sys.stderr)
        return proc.returncode or 1

    adapter = detect_adapter(produces)
    if adapter is None:
        print(f"error: could not recognise the result format at {produces}", file=sys.stderr)
        return 1

    run = adapter.parse(produces)
    db = _project_db(project)
    conn = storage.connect(db)
    try:
        run_id = storage.derive_run_id(run)
        if storage.run_exists(conn, run_id):
            print(f"[record] run {run_id} already recorded (idempotent)")
        else:
            storage.insert_run(conn, run, run_id)
            print(
                f"[record] run {run_id} — {run.total} test(s); "
                f"history now {storage.run_count(conn)} run(s)"
            )
        render_report(
            conn,
            db,
            storage.run_count(conn),
            show_reliability=True,
            show_flakiness=True,
            show_trend=True,
            min_runs=2,
        )
    finally:
        conn.close()
    return proc.returncode


def _snapshot(project: Path) -> None:
    db = _project_db(project)
    runner = detect_runner(project, _work_dir(project))
    detected = runner.name if runner is not None else "unknown (use a custom command)"
    print(BAR)
    print("  QA Reliability Intelligence — console")
    print(BAR)
    print(f"  Target : {project}")
    print(f"  Tests  : {detected}")
    if db.exists():
        conn = storage.connect(db)
        try:
            score = analyse_reliability(conn).suite_score
            print(f"  History: {storage.run_count(conn)} run(s) · reliability {score:.0f}%")
        finally:
            conn.close()
    else:
        print("  History: none yet")
    print()


def _view_report(project: Path) -> None:
    db = _project_db(project)
    if not db.exists():
        print("  No history yet — choose [r] to run the tests first.")
        return
    conn = storage.connect(db)
    try:
        render_report(
            conn, db, storage.run_count(conn),
            show_reliability=True, show_flakiness=True, show_trend=True, min_runs=2,
        )
    finally:
        conn.close()


def interactive(project: Path) -> int:
    """A tiny menu loop. Exits cleanly on EOF (e.g. piped/non-interactive stdin)."""
    use_utf8()
    project = project.resolve()
    while True:
        _snapshot(project)
        print("  [r] run tests & analyse   [v] view report   [t] change target   [q] quit")
        try:
            choice = input("  > ").strip().lower()
        except EOFError:
            return 0

        if choice in ("q", "quit", "exit"):
            return 0
        elif choice in ("r", "run"):
            run_once(project)
        elif choice in ("v", "view", "report"):
            _view_report(project)
        elif choice in ("t", "target", "cd"):
            try:
                new = input("  new target path> ").strip()
            except EOFError:
                return 0
            if new:
                candidate = Path(new).expanduser().resolve()
                if candidate.is_dir():
                    project = candidate
                else:
                    print(f"  not a directory: {candidate}")
        elif choice:
            print(f"  unknown option: {choice!r}")
        print()
