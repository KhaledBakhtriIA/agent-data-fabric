"""Repeatable self-check — the tool measuring its own test suite's reliability.

Each run does three things, all through the tool's own CLI:

  1. run this project's test suite, emitting a JUnit XML report;
  2. ingest that report into local history (data/self-check.db);
  3. print the reliability report over all accumulated runs.

Because step 2 appends to a persistent database, running this repeatedly builds
a reliability trend for the tool's own suite over time. A failing or flaky run
is not an error here — it is exactly the signal worth recording.

Usage:
    python scripts/self_check.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "self-check.db"


def _run(cmd: list[str]) -> int:
    # Flush so this echo lands before the subprocess's own output, not after.
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "self-check.xml"

        # 1. Run our own suite. Don't abort on failures — record them instead.
        pytest_code = _run([py, "-m", "pytest", "-q", f"--junitxml={junit}"])
        if not junit.exists():
            print("error: pytest produced no JUnit report; aborting.", file=sys.stderr)
            return 1

        # 2. Record this run in the tool's own history (idempotent per run).
        _run([py, "-m", "reliability", "ingest", str(junit), "--db", str(DB)])

    # 3. Report over everything accumulated so far.
    _run([py, "-m", "reliability", "report", "--db", str(DB)])

    # Mirror pytest's status so callers/CI know whether the suite passed.
    return pytest_code


if __name__ == "__main__":
    raise SystemExit(main())
