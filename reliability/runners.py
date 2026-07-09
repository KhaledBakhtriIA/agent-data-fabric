"""Detect how to run a *target* project's tests and where the results land.

This is what lets the tool point at any project: given a directory, work out
which test framework it uses and the command that produces a result file we can
ingest. Supported out of the box: Playwright (JSON) and pytest (JUnit XML).
Anything else can be driven with an explicit command.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Runner:
    name: str  # framework name (for display)
    command: list[str]  # argv to execute in the target directory
    produces: Path  # absolute path to the result file the command will write
    env: dict[str, str] = field(default_factory=dict[str, str])


def _contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def _has_playwright(project: Path) -> bool:
    return any(
        (project / f"playwright.config.{ext}").exists()
        for ext in ("ts", "js", "mjs", "cjs")
    )


def _looks_like_pytest(project: Path) -> bool:
    if (project / "pytest.ini").exists() or (project / "conftest.py").exists():
        return True
    if _contains(project / "pyproject.toml", "[tool.pytest"):
        return True
    if _contains(project / "setup.cfg", "[tool:pytest]"):
        return True
    # Fall back to "are there any test files that pytest would collect?"
    for pattern in ("test_*.py", "*_test.py", "tests/test_*.py", "tests/**/test_*.py"):
        if next(project.glob(pattern), None) is not None:
            return True
    return False


def detect_runner(project: Path, result_dir: Path) -> Runner | None:
    """Return how to run ``project``'s tests, or None if we can't tell."""
    if _has_playwright(project):
        out = (result_dir / "playwright.json").resolve()
        npx = shutil.which("npx") or "npx"
        return Runner(
            name="playwright",
            command=[npx, "playwright", "test", "--reporter=json"],
            produces=out,
            # The JSON reporter writes to the file named by this env var.
            env={"PLAYWRIGHT_JSON_OUTPUT_NAME": str(out)},
        )
    if _looks_like_pytest(project):
        out = (result_dir / "pytest-junit.xml").resolve()
        return Runner(
            name="pytest",
            command=[sys.executable, "-m", "pytest", "-q", f"--junitxml={out}"],
            produces=out,
        )
    return None
