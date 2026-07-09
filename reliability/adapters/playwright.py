"""Adapter for the Playwright JSON reporter (``report.json``).

Playwright's report nests ``suites`` arbitrarily deep; each spec carries one
``tests`` entry per project (browser), and each of those carries one ``results``
entry per attempt (original + retries). We flatten all of that into neutral
:class:`TestResult` rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..storage.models import FAILED, FLAKY, PASSED, SKIPPED, Run, TestResult
from .base import Adapter, truncate

# Playwright's per-test status vocabulary → our neutral vocabulary.
_STATUS_MAP = {
    "expected": PASSED,
    "unexpected": FAILED,
    "flaky": FLAKY,
    "skipped": SKIPPED,
}


class PlaywrightAdapter(Adapter):
    name = "playwright"

    def can_parse(self, path: Path, sample: str) -> bool:
        # The Playwright JSON report is an object with both "config" and
        # "suites" keys — a combination no other supported format has.
        stripped = sample.lstrip()
        return stripped.startswith("{") and '"suites"' in sample and '"config"' in sample

    def parse(self, path: Path) -> Run:
        report: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        config = report.get("config", {}) or {}
        stats = report.get("stats", {}) or {}

        results: List[TestResult] = []
        for suite in report.get("suites", []) or []:
            # Top-level suites are files; their title is the filename, not a
            # describe block, so it must not become part of a test's identity.
            self._walk_suite(suite, ancestors=[], file=None, out=results, is_root=True)

        return Run(
            framework=self.name,
            started_at=stats.get("startTime"),
            duration_ms=int(round(stats.get("duration", 0) or 0)),
            tool_version=config.get("version"),
            source_file=str(path),
            results=results,
        )

    def _walk_suite(
        self,
        suite: Dict[str, Any],
        ancestors: List[str],
        file: str | None,
        out: List[TestResult],
        is_root: bool = False,
    ) -> None:
        # Files are attached at the top suite level and inherited by children.
        file = suite.get("file") or file
        title = suite.get("title")

        # Only nested suites are describe blocks. The root suite is the file
        # itself (its title is the filename) and never part of a test's identity.
        describe = list(ancestors)
        if title and not is_root and title != file:
            describe.append(title)

        for spec in suite.get("specs", []) or []:
            self._emit_spec(spec, describe, file, out)

        for child in suite.get("suites", []) or []:
            self._walk_suite(child, describe, file, out)

    def _emit_spec(
        self,
        spec: Dict[str, Any],
        describe: List[str],
        file: str | None,
        out: List[TestResult],
    ) -> None:
        spec_file = spec.get("file") or file
        spec_title = spec.get("title", "")
        name_path = " › ".join([*describe, spec_title]) if describe else spec_title

        # One "test" per project (browser). Keep them distinct in the history.
        for test in spec.get("tests", []) or []:
            project = test.get("projectName") or test.get("projectId") or ""
            status = _STATUS_MAP.get(test.get("status", ""), test.get("status", "unknown"))

            attempts = test.get("results", []) or []
            duration_ms = int(round(sum(a.get("duration", 0) or 0 for a in attempts)))
            retries = max(len(attempts) - 1, 0)

            # Prefer the error message from the final attempt.
            message = None
            for attempt in reversed(attempts):
                err = attempt.get("error") or {}
                if err.get("message"):
                    message = truncate(err["message"])
                    break

            display = f"{name_path} [{project}]" if project else name_path
            test_key = f"{spec_file}::{name_path}::{project}"

            out.append(
                TestResult(
                    test_key=test_key,
                    name=display,
                    status=status,
                    duration_ms=duration_ms,
                    retries=retries,
                    file=spec_file,
                    message=message,
                )
            )
