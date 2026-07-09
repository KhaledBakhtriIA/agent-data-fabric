"""Adapter for JUnit XML result files (Selenium, many CI runners).

Stubbed for a later phase. Detection is wired up so the CLI can give a precise
"not yet implemented" message instead of a confusing generic parse error.
"""

from __future__ import annotations

from pathlib import Path

from ..storage.models import Run
from .base import Adapter


class JUnitAdapter(Adapter):
    name = "junit"

    def can_parse(self, path: Path, sample: str) -> bool:
        stripped = sample.lstrip()
        return stripped.startswith("<") and ("<testsuite" in sample or "<testsuites" in sample)

    def parse(self, path: Path) -> Run:  # pragma: no cover - stub
        raise NotImplementedError(
            "The JUnit XML adapter is planned but not implemented yet. "
            "Only Playwright JSON is supported in this phase."
        )
