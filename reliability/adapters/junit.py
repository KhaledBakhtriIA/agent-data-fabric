"""Adapter for JUnit XML result files.

JUnit XML is emitted by ``pytest --junitxml``, Selenium runners, and many CI
systems, which makes it the most broadly useful non-Playwright format. Parsing
uses the standard-library XML reader — no third-party dependency.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..storage.models import FAILED, PASSED, SKIPPED, Run, TestResult
from ..utils.text import truncate
from .base import Adapter


def _float(value: str | None) -> float:
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0


class JUnitAdapter(Adapter):
    name = "junit"

    def can_parse(self, path: Path, sample: str) -> bool:
        stripped = sample.lstrip()
        return stripped.startswith("<") and ("<testsuite" in sample or "<testsuites" in sample)

    def parse(self, path: Path) -> Run:
        root = ET.parse(path).getroot()
        # The root is either a <testsuites> wrapper or a single <testsuite>.
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

        results: list[TestResult] = []
        started_at: str | None = None
        total_time = 0.0
        for suite in suites:
            # Use the first suite's start time as the run's timestamp.
            started_at = started_at or suite.get("timestamp")
            for case in suite.findall("testcase"):
                results.append(self._case_to_result(case))
                total_time += _float(case.get("time"))

        return Run(
            framework=self.name,
            started_at=started_at,
            duration_ms=int(round(total_time * 1000)),
            tool_version=None,
            source_file=str(path),
            results=results,
        )

    def _case_to_result(self, case: ET.Element) -> TestResult:
        name = case.get("name", "")
        classname = case.get("classname", "")
        file = case.get("file")

        # JUnit expresses status through child elements. Precedence:
        # error/failure → failed, skipped → skipped, otherwise passed.
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")

        message: str | None = None
        if failure is not None or error is not None:
            status = FAILED
            node = failure if failure is not None else error
            if node is not None:
                message = truncate(node.get("message") or (node.text or "").strip())
        elif skipped is not None:
            status = SKIPPED
        else:
            status = PASSED

        display = f"{classname} › {name}" if classname else name
        return TestResult(
            # classname/file give the test a stable identity across runs.
            test_key=f"{file or classname}::{name}",
            name=display,
            status=status,
            duration_ms=int(round(_float(case.get("time")) * 1000)),
            retries=0,
            file=file or classname or None,
            message=message,
        )
