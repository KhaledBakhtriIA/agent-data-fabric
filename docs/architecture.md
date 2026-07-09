# Architecture

The tool is a straight pipeline. Each stage has one job and knows nothing about
the stages around it except through the neutral model (`storage/models.py`).

There are **two ways to get data into the pipeline**:

- **`ingest`** — you already have a result file; normalise and store it.
- **`run`** — point at a target project; the tool executes *its* tests to
  produce the result file first, then ingests it.

```
  reliability run <project>                 reliability ingest <file>
        │                                          │
        │  runners.py detects the framework        │
        │  and runs the target's tests             │
        ▼                                          ▼
        result file  (Playwright JSON · JUnit XML · pytest-json)
                              │
                              ▼
  adapters/            can_parse() detects the format; parse() → neutral Run
        │              (playwright + junit implemented; pytest stubbed)
        ▼
  storage/             models.py = neutral dataclasses (Run, TestResult)
        │              database.py = local SQLite; stable run_id → idempotent
        ▼
  analysis/            statistics only, no AI:
        │                flakiness.py   — which tests flip between pass/fail
        │                trends.py      — is pass-rate improving or declining
        │                reliability.py — a 0–100 score per test and per suite
        ▼
  reports/             cli_report.py formats findings for the terminal
        │
        ▼
  cli.py / console.py  `reliability ingest | report | run`, or the bare
                       `reliability` interactive console
```

## The two front doors

- **`runners.detect_runner(project)`** inspects a directory and returns how to
  run its tests: **Playwright** (a `playwright.config.*` → `npx playwright test
  --reporter=json`) or **pytest** (config/markers/test files → `pytest
  --junitxml`). Anything else is driven with an explicit `--command` + `--result`.
- **`console.run_once(project)`** runs that command in the target, then feeds the
  produced file through the *same* adapter → store → analyse → report pipeline.
- **`console.interactive(project)`** wraps `run_once` and the report in a small
  menu that "pops up" (it's the bare `reliability` command, and the VS Code
  folder-open task launches it).

## Why this shape

- **Adapters isolate framework quirks.** Adding Selenium/JUnit or pytest support
  means writing one adapter; nothing downstream changes because everything speaks
  the neutral model. Playwright JSON and JUnit XML are implemented today.
- **Runners isolate "how do I run this project".** Detection lives in one place,
  so the tool can point at any project without the pipeline knowing or caring.
- **The store is the memory.** Single-run tools can't answer history questions
  ("has this test failed 8% of the time this month?"). Accumulated runs can.
- **Analysis is deterministic.** Flakiness, trend and reliability are arithmetic
  over stored rows — reproducible, explainable, and offline. No model in the core.
- **Reporting is separate from wiring.** `reports/` decides how findings look;
  `cli.py`/`console.py` decide which sections to show and what exit code to return.

## Data locations

- `data/reliability.db` — the tool's own default history (gitignored).
- `data/self-check.db` — history from `scripts/self_check.py` (gitignored).
- `data/imports/` — a convenient drop folder for result files to ingest.
- `<target>/.reliability/history.db` — per-project history created by `run`
  (gitignored; add `.reliability/` to the target project's `.gitignore`).
- `reliability/storage/schema.sql` — the versioned schema (two tables).
