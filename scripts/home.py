"""Minimal project dashboard — a one-glance status shown when you open the repo.

Prints the project banner, a snapshot of any local reliability history, and the
handful of commands you'll actually use. It only ever reads, so it's safe to run
anytime (and it's wired to run automatically on folder-open via .vscode/tasks.json).

    python scripts/home.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    # Make `reliability` importable when this file is run directly as a script.
    sys.path.insert(0, str(ROOT))

from reliability import __version__, storage  # noqa: E402
from reliability.analysis import analyse_reliability  # noqa: E402

BAR = "═" * 58


def _use_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _history_line(label: str, path: Path) -> str | None:
    """One status line for a history DB, or None if it doesn't exist yet."""
    if not path.exists():
        return None
    conn = storage.connect(path)
    try:
        runs = storage.run_count(conn)
        score = analyse_reliability(conn).suite_score
        return f"    {label:11} {runs:>3} run(s)  ·  suite reliability {score:.0f}%"
    finally:
        conn.close()


def main() -> int:
    _use_utf8()
    print(BAR)
    print("  QA Reliability Intelligence")
    print(f"  Local-first test-reliability history  ·  CLI  ·  v{__version__}")
    print(BAR)

    print()
    print("  History")
    lines = [
        _history_line("evidence", ROOT / "data" / "reliability.db"),
        _history_line("self-check", ROOT / "data" / "self-check.db"),
    ]
    shown = [line for line in lines if line is not None]
    if shown:
        for line in shown:
            print(line)
    else:
        print("    (none yet — ingest a report or run the self-check to begin)")

    print()
    print("  Commands")
    print("    python -m reliability ingest <file>    record a test run")
    print("    python -m reliability report           reliability · flakiness · trend")
    print("    python scripts/self_check.py           run & record this project's suite")
    print("    pytest                                 run the tests")
    print(BAR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
