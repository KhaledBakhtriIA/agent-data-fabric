"""Tests for target-project detection and the end-to-end `run_once` flow."""

from __future__ import annotations

from pathlib import Path

from reliability import storage
from reliability.console import run_once
from reliability.runners import detect_runner


def test_detect_pytest_by_config(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    runner = detect_runner(tmp_path, tmp_path / ".reliability")
    assert runner is not None
    assert runner.name == "pytest"
    assert "--junitxml=" in " ".join(runner.command)


def test_detect_pytest_by_test_file(tmp_path: Path) -> None:
    (tmp_path / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    runner = detect_runner(tmp_path, tmp_path / ".reliability")
    assert runner is not None
    assert runner.name == "pytest"


def test_detect_playwright(tmp_path: Path) -> None:
    (tmp_path / "playwright.config.ts").write_text("export default {};\n", encoding="utf-8")
    runner = detect_runner(tmp_path, tmp_path / ".reliability")
    assert runner is not None
    assert runner.name == "playwright"
    assert "PLAYWRIGHT_JSON_OUTPUT_NAME" in runner.env


def test_detect_none_for_empty_dir(tmp_path: Path) -> None:
    assert detect_runner(tmp_path, tmp_path / ".reliability") is None


def test_run_once_against_a_pytest_target(tmp_path: Path) -> None:
    # A minimal pytest project standing in for "any project".
    (tmp_path / "test_smoke.py").write_text(
        "def test_math():\n    assert 2 + 2 == 4\n", encoding="utf-8"
    )

    code = run_once(tmp_path)
    assert code == 0

    db = tmp_path / ".reliability" / "history.db"
    assert db.exists()
    conn = storage.connect(db)
    try:
        assert storage.run_count(conn) == 1
    finally:
        conn.close()
