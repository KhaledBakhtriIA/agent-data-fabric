# Architecture

The tool is a straight pipeline. Each stage has one job and knows nothing about
the stages around it except through the neutral model.

```
result file (any framework)
      │
      ▼
  adapters/            can_parse() detects the format; parse() → neutral Run
      │                (playwright implemented; junit, pytest stubbed)
      ▼
  storage/             models.py = neutral dataclasses (Run, TestResult)
      │                database.py = local SQLite; stable run_id → idempotent
      ▼
  analysis/            statistics only, no AI:
      │                  flakiness.py   — which tests flip between pass/fail
      │                  trends.py      — is pass-rate improving or declining
      │                  reliability.py — a 0–100 score per test and per suite
      ▼
  reports/             cli_report.py formats findings for the terminal
      │
      ▼
  cli.py               `reliability ingest` / `reliability report`
```

## Why this shape

- **Adapters isolate framework quirks.** Adding Selenium/JUnit or pytest support
  means writing one adapter; nothing downstream changes because everything speaks
  the neutral model.
- **The store is the memory.** Single-run tools can't answer history questions
  ("has this test failed 8% of the time this month?"). Accumulated runs can.
- **Analysis is deterministic.** Flakiness, trend and reliability are arithmetic
  over stored rows — reproducible, explainable, and offline. No model in the core.
- **Reporting is separate from wiring.** `reports/` decides how findings look;
  `cli.py` only decides which sections to show and what exit code to return.

## Data locations

- `data/reliability.db` — the accumulated history (gitignored).
- `data/imports/` — a convenient drop folder for result files to ingest.
- `reliability/storage/schema.sql` — the versioned schema (two tables).
