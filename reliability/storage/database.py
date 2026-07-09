"""Local SQLite evidence store — the run-history memory.

Uses the Python standard-library ``sqlite3`` module (no third-party driver, no
server, nothing to install). The database is a single local file; test data
never leaves the machine.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Run

# Schema lives beside this module and is versioned in git.
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Default location for the accumulated history. Kept local and gitignored.
DEFAULT_DB_PATH = Path("data") / "reliability.db"


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the evidence DB and ensure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enforce the ON DELETE CASCADE relationship between runs and test_results.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def derive_run_id(run: Run) -> str:
    """Stable id so re-ingesting the same result file never duplicates a run.

    "Idempotent" means running ingest on the same file ten times leaves the
    store in the same state as running it once. We hash values that identify
    the run itself (not the moment we happened to ingest it).
    """
    seed = "|".join(
        [
            run.framework,
            run.started_at or "",
            run.tool_version or "",
            str(run.total),
        ]
    )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def run_exists(conn: sqlite3.Connection, run_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row is not None


def insert_run(conn: sqlite3.Connection, run: Run, run_id: str | None = None) -> str:
    """Persist a run and all its test results in a single transaction.

    Returns the run_id. Callers should check :func:`run_exists` first if they
    want idempotent behaviour with a friendly message.
    """
    run_id = run_id or derive_run_id(run)
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with conn:  # transaction: commit on success, roll back on error
        conn.execute(
            """
            INSERT INTO runs
                (run_id, framework, started_at, duration_ms, tool_version,
                 source_file, total, passed, failed, flaky, skipped, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run.framework,
                run.started_at,
                run.duration_ms,
                run.tool_version,
                run.source_file,
                run.total,
                run.passed,
                run.failed,
                run.flaky,
                run.skipped,
                ingested_at,
            ),
        )
        conn.executemany(
            """
            INSERT INTO test_results
                (run_id, test_key, name, file, status, duration_ms, retries, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    r.test_key,
                    r.name,
                    r.file,
                    r.status,
                    r.duration_ms,
                    r.retries,
                    r.message,
                )
                for r in run.results
            ],
        )
    return run_id


def run_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
