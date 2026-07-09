"""Adapter for the ``pytest-json-report`` format (pytest suites).

Stubbed for a later phase. Detection is wired up so the CLI can report a clear
"not yet implemented" message rather than mis-parsing the file.
"""

from __future__ import annotations

from pathlib import Path

from ..storage.models import Run
from .base import Adapter


class PytestJsonAdapter(Adapter):
    name = "pytest"

    def can_parse(self, path: Path, sample: str) -> bool:
        # pytest-json-report emits an object with "tests" and "summary" keys and,
        # unlike Playwright, no "suites"/"config".
        return (
            sample.lstrip().startswith("{")
            and '"summary"' in sample
            and '"tests"' in sample
            and '"suites"' not in sample
        )

    def parse(self, path: Path) -> Run:  # pragma: no cover - stub
        raise NotImplementedError(
            "The pytest-json adapter is planned but not implemented yet. "
            "Only Playwright JSON is supported in this phase."
        )
