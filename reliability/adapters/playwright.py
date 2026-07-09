"""Adapter for the Playwright JSON reporter (``report.json``).

Playwright's report nests ``suites`` arbitrarily deep; each spec carries one
``tests`` entry per project (browser), and each of those carries one ``results``
entry per attempt (original + retries). We flatten all of that into neutral
:class:`TestResult` rows.

Playwright JSON is external, untyped data, so every field is pulled through the
small typed coercion helpers below (``_dict``/``_list``/``_str``/``_num``). That
keeps the parser defensive against malformed reports — and fully typed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ..storage.models import FAILED, FLAKY, PASSED, SKIPPED, Run, TestResult
from ..utils.text import truncate
from .base import Adapter

# Playwright's per-test status vocabulary → our neutral vocabulary.
_STATUS_MAP: dict[str, str] = {
    "expected": PASSED,
    "unexpected": FAILED,
    "flaky": FLAKY,
    "skipped": SKIPPED,
}


def _dict(value: Any) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return cast("list[Any]", value) if isinstance(value, list) else []


def _str(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _num(value: Any) -> float:
    # JSON numbers arrive as int or float; treat anything else as zero.
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


class PlaywrightAdapter(Adapter):
    name = "playwright"

    def can_parse(self, path: Path, sample: str) -> bool:
        # The Playwright JSON report is an object with both "config" and
        # "suites" keys — a combination no other supported format has.
        stripped = sample.lstrip()
        return stripped.startswith("{") and '"suites"' in sample and '"config"' in sample

    def parse(self, path: Path) -> Run:
        report = _dict(json.loads(path.read_text(encoding="utf-8")))
        config = _dict(report.get("config"))
        stats = _dict(report.get("stats"))

        results: list[TestResult] = []
        for raw_suite in _list(report.get("suites")):
            # Top-level suites are files; their title is the filename, not a
            # describe block, so it must not become part of a test's identity.
            self._walk_suite(_dict(raw_suite), ancestors=[], file=None, out=results, is_root=True)

        return Run(
            framework=self.name,
            started_at=_str(stats.get("startTime")) or None,
            duration_ms=int(round(_num(stats.get("duration")))),
            tool_version=_str(config.get("version")) or None,
            source_file=str(path),
            results=results,
        )

    def _walk_suite(
        self,
        suite: dict[str, Any],
        ancestors: list[str],
        file: str | None,
        out: list[TestResult],
        is_root: bool = False,
    ) -> None:
        # Files are attached at the top suite level and inherited by children.
        file = _str(suite.get("file")) or file
        title = _str(suite.get("title"))

        # Only nested suites are describe blocks. The root suite is the file
        # itself (its title is the filename) and never part of a test's identity.
        describe = list(ancestors)
        if title and not is_root and title != file:
            describe.append(title)

        for raw_spec in _list(suite.get("specs")):
            self._emit_spec(_dict(raw_spec), describe, file, out)

        for raw_child in _list(suite.get("suites")):
            self._walk_suite(_dict(raw_child), describe, file, out)

    def _emit_spec(
        self,
        spec: dict[str, Any],
        describe: list[str],
        file: str | None,
        out: list[TestResult],
    ) -> None:
        spec_file = _str(spec.get("file")) or file
        spec_title = _str(spec.get("title"))
        name_path = " › ".join([*describe, spec_title]) if describe else spec_title

        # One "test" per project (browser). Keep them distinct in the history.
        for raw_test in _list(spec.get("tests")):
            test = _dict(raw_test)
            project = _str(test.get("projectName")) or _str(test.get("projectId"))

            # Normalise to our vocabulary; pass through anything unmapped.
            raw_status = _str(test.get("status")) or "unknown"
            status = _STATUS_MAP.get(raw_status, raw_status)

            attempts = [_dict(a) for a in _list(test.get("results"))]
            duration_ms = int(round(sum(_num(a.get("duration")) for a in attempts)))
            retries = max(len(attempts) - 1, 0)

            # Prefer the error message from the final attempt.
            message: str | None = None
            for attempt in reversed(attempts):
                err_message = _str(_dict(attempt.get("error")).get("message"))
                if err_message:
                    message = truncate(err_message)
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
