"""Neutral data model shared by every adapter and analyser.
Adapters translate framework-specific result files into these dataclasses;
the store persists them; the analysers read them back. Keeping one neutral
shape here is what makes the tool framework-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The only status values the rest of the system understands. Adapters are
# responsible for mapping their framework's vocabulary onto these.
PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"
FLAKY = "flaky"  # passed only after a retry within a single run
VALID_STATUSES = frozenset({PASSED, FAILED, SKIPPED, FLAKY})


@dataclass
class TestResult:
    """One test's outcome within one run."""

    test_key: str          # stable identity across runs (see schema.sql)
    name: str              # human-readable title
    status: str            # one of VALID_STATUSES
    duration_ms: int = 0
    retries: int = 0
    file: str | None = None
    message: str | None = None


@dataclass
class Run:
    """One test-run execution, normalised from a single result file."""

    framework: str
    started_at: str | None
    duration_ms: int
    tool_version: str | None
    source_file: str | None
    results: list[TestResult] = field(default_factory=list[TestResult])

    # Counts are derived from `results` so an adapter never has to keep them in
    # sync by hand — the neutral model is the single source of truth.
    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == FAILED)

    @property
    def flaky(self) -> int:
        return sum(1 for r in self.results if r.status == FLAKY)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == SKIPPED)
