# QA Reliability Intelligence

> A **local-first** tool that tracks test-suite reliability **across many runs over time** —
> surfacing flakiness patterns and reliability trends that single-run tools can't see.

<p>
  <a href="https://github.com/KhaledBakhtriIA/agent-data-fabric/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/KhaledBakhtriIA/agent-data-fabric/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/KhaledBakhtriIA/agent-data-fabric/actions/workflows/self-check.yml"><img alt="Self-check" src="https://github.com/KhaledBakhtriIA/agent-data-fabric/actions/workflows/self-check.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="Dependencies" src="https://img.shields.io/badge/core%20deps-0-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Privacy" src="https://img.shields.io/badge/local--first-no%20telemetry-blueviolet">
</p>

Your test data never leaves your machine. No cloud upload, no telemetry, no AI in the core —
just reproducible statistics over your own run history.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What makes it different](#what-makes-it-different)
- [Quick start](#quick-start)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [The evidence model](#the-evidence-model)
- [Roadmap](#roadmap)
- [Design principles](#design-principles)
- [Development](#development)
- [License](#license)

---

## Why this exists

Modern test tooling is good at the *present moment*. Playwright's agents can generate tests
and heal a broken locator *right now*; linters flag a fragile selector *in the file*;
commercial dashboards show today's pass/fail.

What they mostly don't do — or only do in the cloud, per-framework, behind a subscription —
is answer the **history** questions:

- Which tests have quietly failed 5–10% of the time for the last month?
- Is this test *flaky*, or did the app genuinely break?
- Has a selector been "healed" four times in three weeks — meaning the real problem is the
  app, not the test?
- Is our suite getting *more* reliable over time, or less?

Those questions need **run history**. A single run can't answer them — you have to remember
every run and compare. That memory is what this tool provides.

## What makes it different

- **🔒 Local-first / private.** Runs on your machine. No cloud upload, no telemetry, ever.
  Built for teams whose test data (URLs, DOM, payloads) *cannot* leave their environment —
  finance, health, regulated, or just privacy-conscious.
- **🔌 Framework-agnostic.** Reads standard result formats through small adapters, so one
  reliability view can span Playwright, Selenium/JUnit and pytest — not just one.
- **📊 Deterministic first.** Flakiness, trend and reliability analysis are statistics over
  stored history — rules and math, not a language model. The core needs no AI and makes no
  network calls.

**What it does _not_ do:** it does not generate tests, does not auto-heal or modify your
tests, and deliberately does not compete on single-run locator linting (Playwright's native
tooling already covers that). Its reason to exist is the cross-run, local-first,
multi-framework reliability view those tools don't provide.

## Quick start

**Requirements:** Python 3.9+ (standard library only — nothing to `pip install` to run the core).

```bash
# 1. Get the code
git clone https://github.com/KhaledBakhtriIA/agent-data-fabric.git
cd agent-data-fabric

# 2. (optional) install the `reliability` command
pip install -e .

# 3. Ingest a result file and read the report
python -m reliability ingest examples/playwright-results.json
python -m reliability report
```

> Without `pip install -e .`, use `python -m reliability <command>` everywhere the docs show
> `reliability <command>` — they are equivalent.

## Usage

Main verbs: **ingest** (remember a run), **report** (analyse the history), and **run**
(test a target project end to end). Running `reliability` with no arguments opens an
interactive console.

### Ingest a run

```bash
reliability ingest path/to/report.json          # auto-detects the format
reliability ingest report.json --framework playwright
reliability ingest report.json --db data/reliability.db
```

Ingestion is **idempotent** — re-ingesting the same file never creates a duplicate run.

### Read the report

```bash
reliability report                 # reliability score + flakiness + trend
reliability report --flakiness     # one section only
reliability report --trend
reliability report --min-runs 5    # only judge flakiness on tests with ≥ 5 runs
```

Example output:

```
  QA Reliability Intelligence — Report
  4 run(s) in local history  (data/reliability.db)

  Reliability score
  Suite reliability: 81%
       50%  Inventory › can add two items to cart [chromium]  (2/4 clean of 4)
       75%  complete purchase flow [chromium]  (3/4 clean of 4)

  Flakiness  (tests seen in ≥ 2 runs)
  [HIGH] Inventory › can add two items to cart [chromium]
         4 runs — pass:2 fail:1 flaky:1 skip:0   flaky-rate 50%

  Reliability trend
  ▲ IMPROVING   earlier 75%  →  recent 88%   (+12 pts over 4 runs)
  per run (old→new): 100%  50%  75%  100%
```

### Test any project

Point the tool at a project and it runs *that project's* tests, records the run, and
reports — no result file needed. It auto-detects **Playwright** (`playwright.config.*`)
and **pytest**; anything else can be driven with an explicit command.

```bash
cd path/to/your/project
reliability run                 # detect the framework, run its tests, record + report
# ...or target it by path, or drive a custom command:
reliability run path/to/project
reliability run . --command "npm test" --result results/junit.xml
```

Each project keeps its own history in its own `.reliability/` folder, so reliability
accumulates per project. (Add `.reliability/` to that project's `.gitignore`.) The bare
`reliability` command works from any directory once you `pip install -e .`; otherwise use
`python -m reliability` from this repo.

### Interactive console

`reliability` with no arguments opens a small menu that shows the target, its detected
framework and history, and lets you run tests, view the report, or switch target:

```
  QA Reliability Intelligence — console
  Target : /path/to/your/project
  Tests  : pytest
  History: 3 run(s) · reliability 100%

  [r] run tests & analyse   [v] view report   [t] change target   [q] quit
```

**Open it without VS Code** — double-click **`console.bat`** (Windows) or run
**`./console.sh`** (macOS/Linux) and the console pops up in its own terminal window.
It also opens automatically when you open the folder in VS Code — see
[Project dashboard](#development).

## How it works

Two ways in — **`run`** a target project (the tool executes its tests to produce a
result file) or **`ingest`** a result file you already have — both feed one pipeline
where each stage only speaks the neutral model to its neighbours.

```
  reliability run <project>              reliability ingest <file>
        │  (runs the target's tests)              │
        ▼                                          ▼
        result file  (Playwright JSON · JUnit XML · …)
                          ▼
   Adapter  ── normalises into one neutral schema
                          ▼
 Evidence store (local SQLite)  ── accumulates run history over time
                          ▼
 Analysers (statistics, no AI)  ── reliability score · flakiness · trend
                          ▼
   CLI report / console  ── you read it, you decide
```

See [`docs/architecture.md`](docs/architecture.md) for the detailed breakdown.

## Project structure

```
.
├── reliability/            # the tool (Python package, stdlib only)
│   ├── cli.py              # ingest · report · run · (bare = interactive console)
│   ├── console.py          # run_once(target) + the interactive menu
│   ├── runners.py          # detect a target project's framework & test command
│   ├── adapters/           # per-framework result parsers → neutral model
│   │   ├── playwright.py   #   Playwright JSON  — implemented
│   │   ├── junit.py        #   JUnit XML        — implemented
│   │   └── pytest.py       #   pytest-json      — stub (planned)
│   ├── analysis/           # deterministic statistics (no AI)
│   │   ├── flakiness.py    #   which tests flip between pass/fail
│   │   ├── trends.py       #   is the suite improving or declining
│   │   └── reliability.py  #   a 0–100 score per test and per suite
│   ├── storage/            # neutral model + local SQLite store
│   │   ├── models.py · database.py · schema.sql
│   ├── reports/            # terminal report formatting (cli_report.py)
│   └── utils/              # small shared helpers (text.truncate)
├── scripts/                # self_check.py (dogfood) · home.py (quick dashboard)
├── data/                   # local history (reliability.db) + imports/ drop-folder
├── examples/               # one result file per format (playwright, junit, pytest)
├── tests/                  # pytest suite + fixtures
├── docs/                   # architecture notes
└── .github/workflows/      # CI (lint · types · tests) + scheduled self-check
```

Each *target* project you `run` also gets its own `.reliability/history.db` (gitignored).

## The evidence model

Two framework-neutral tables (see [`reliability/storage/schema.sql`](reliability/storage/schema.sql)):

| Table | Purpose | Key columns |
|---|---|---|
| `runs` | one row per ingested run | `run_id` (stable hash → idempotent), `framework`, `started_at`, `passed/failed/flaky/skipped` |
| `test_results` | one row per test per run | `test_key` (stable identity across runs), `status`, `duration_ms`, `retries`, `message` |

`test_key` is what correlates the *same* test across many runs — the basis of every history
metric. `run_id` is derived from run-identifying fields, so ingesting the same report twice
produces one row, not two.

## Roadmap

| Capability | Status |
|---|---|
| Playwright JSON adapter | ✅ Implemented |
| JUnit XML adapter (pytest, Selenium, CI runners) | ✅ Implemented |
| Evidence store + idempotent ingest | ✅ Implemented |
| Reliability score · flakiness · trend | ✅ Implemented |
| Run any project (auto-detect Playwright/pytest) + interactive console | ✅ Implemented |
| CI + daily scheduled self-check | ✅ Implemented |
| pytest-json adapter | 🔜 Planned |
| Per-test regression alerts across runs | 🔭 Later |
| Optional natural-language explanation layer (never required) | 🔭 Later |

## Used in production

**[⚡ The Volt System](https://github.com/KhaledBakhtriIA/the_volt)** — an autonomous,
agent-based quantitative trading platform (companion project) — runs this tool over its
190-test suite on **every CI run**: pytest emits JUnit XML, the run is ingested into a
history DB cached across CI runs, and the flakiness/trend report prints in the pipeline.
Locally it's one command from the Volt repo: `make reliability`.

```yaml
# .github/workflows/ci.yml (the_volt) — the integration in full
- run: pytest tests -q --junitxml=test-results/junit.xml
- uses: actions/cache@v4
  with: { path: .reliability, key: reliability-${{ github.run_id }}, restore-keys: reliability- }
- run: |
    pip install git+https://github.com/KhaledBakhtriIA/agent-data-fabric.git
    reliability ingest test-results/junit.xml --db .reliability/history.db
    reliability report --db .reliability/history.db
```

## Design principles

**Operating principle (never violated):** Observe → Analyse → Recommend → **Human decides.**
The tool surfaces evidence and patterns; a human makes every decision. It never modifies
tests, never deploys, and never acts autonomously.

- Deterministic and offline by default — no model, no network in the core.
- Adding a framework means adding **one adapter** and nothing else.
- Errors are reported as clear messages, never stack traces.

## Development

```bash
pip install -e ".[dev]"   # installs pytest, ruff and pyright
pytest                    # runs the tool's own tests (browser-free, deterministic)
ruff check .              # lint
pyright                   # strict type check
```

The test suite parses the fixtures in `tests/fixtures/`, stores them, and asserts the
analysers' numbers — the tool testing itself end to end.

### Project dashboard

Opening the folder in VS Code **pops up the interactive console** automatically
(`.vscode/tasks.json`, `runOn: folderOpen`, running `python -m reliability`). The first
time, VS Code asks to _"Allow Automatic Tasks"_ — allow it (Terminal menu → Allow
Automatic Tasks in Folder).

For a quick, read-only glance at your local histories without the menu:

```bash
python scripts/home.py
```

### Self-check (dogfooding)

The tool can measure the reliability of *its own* test suite. This runs the suite,
records the run in local history, and reports the trend across every run so far:

```bash
python scripts/self_check.py
```

Run it repeatedly to accumulate history (stored in `data/self-check.db`). Example:

```
  Reliability score
  Suite reliability: 100%
  ✓ Every stored test passes cleanly every time.

  Reliability trend
  ▬ STABLE   earlier 100%  →  recent 100%   (per run: 100% 100% 100%)
```

The same self-check also runs **daily in CI** (`.github/workflows/self-check.yml`)
to track the suite's reliability over real calendar time — a flakiness canary.
That history is carried between the ephemeral runners with an Actions cache, and
each run's reliability report is published to its
[job summary](https://github.com/KhaledBakhtriIA/agent-data-fabric/actions/workflows/self-check.yml).
You can also trigger it on demand from the Actions tab ("Run workflow"). It keeps
its own history, separate from your local `data/self-check.db`.

## License

[MIT](LICENSE) © 2026 Khaled Bakhtri

---

*Honest note: locator-quality and single-run flaky detection are already well covered by
Playwright's native tooling and existing linters. This project deliberately does not compete
there. Its only reason to exist is the cross-run, local-first, multi-framework reliability
view that those tools don't provide.*
