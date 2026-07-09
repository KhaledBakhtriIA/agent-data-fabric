"""Storage layer: neutral data model + local SQLite evidence store."""

from .database import (
    DEFAULT_DB_PATH,
    connect,
    derive_run_id,
    insert_run,
    run_count,
    run_exists,
)
from .models import (
    FAILED,
    FLAKY,
    PASSED,
    SKIPPED,
    VALID_STATUSES,
    Run,
    TestResult,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "connect",
    "derive_run_id",
    "insert_run",
    "run_count",
    "run_exists",
    "Run",
    "TestResult",
    "PASSED",
    "FAILED",
    "SKIPPED",
    "FLAKY",
    "VALID_STATUSES",
]
