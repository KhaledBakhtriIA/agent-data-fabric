# CLAUDE.md — QA Reliability Intelligence, Phase 0 (Evidence Foundation)

> Direction change (2026-07-09): this project was refactored from a
> TypeScript/Playwright-specific "platform" into a **local-first,
> framework-agnostic reliability tool written in Python**, to match the vision
> in `README.md`. Earlier revisions of this file mandated TypeScript,
> `better-sqlite3`, and an LLM analysis phase — those no longer apply. The
> README is the source of truth for *what* the tool is; this file governs *how*
> to work in the repo.

## What this project is

A **local-first** command-line tool that tracks test-suite reliability **across
many runs over time** — surfacing flakiness patterns and reliability trends that
single-run tools can't see. Test data never leaves the machine.

**Operating principle (never violated):**
Observe → Analyse → Recommend → Human decides.
The tool surfaces evidence and patterns; a human makes every decision. It never
modifies tests, never generates or heals tests, never deploys, never acts
autonomously.

## What makes it different (and what it deliberately is NOT)

- **Local-first / private.** Runs on your machine. No cloud upload, no telemetry.
- **Framework-agnostic.** Reads standard result files through small **adapters**
  into one **neutral schema**, so one reliability view can span Playwright,
  Selenium/JUnit, and pytest — not just one framework.
- **Deterministic first.** Flakiness and trend analysis are **statistics over
  stored history — rules and math, not a language model.** The core needs no AI.

It does **not** generate tests, does **not** auto-heal or modify tests, and
**deliberately does not compete** on single-run locator linting or flaky
detection (Playwright's native tooling already covers those). Its reason to
exist is the cross-run, local-first, multi-framework reliability view.

## What Phase 0 is — and is not

Phase 0 builds the **evidence foundation**: normalise result files into a local
store and accumulate run history. Collection only — analysis is thin on purpose.

**In scope:**
1. Adapters that parse framework result files into the neutral model
   (`reliability/adapters/`). Playwright JSON is implemented; JUnit XML and
   pytest-json are stubbed with clear "not yet implemented" messages.
2. The **evidence store**: local SQLite (`data/reliability.db`) accumulating
   run history. Schema is versioned at `reliability/storage/schema.sql`.
3. `reliability ingest <result-file>` — normalise one file into the store
   (idempotent).
4. `reliability report` — deterministic flakiness + reliability-trend output.

**Explicitly OUT of scope (do not build, do not suggest building):**
- Any LLM / Anthropic API call in the core. (An optional explanation layer may
  come *much* later; it is not part of Phase 0 and must never be required.)
- Test generation, auto-healing, or any modification of test files.
- A locator/selector linter (deliberately not competing there).
- Any cloud upload, telemetry, or network call from the tool.
- Any UI beyond terminal output.

If a task drifts toward these, stop and say so instead of building it.

## Success criteria (definition of done)

- [ ] `reliability ingest` stores any Playwright JSON report without errors.
- [ ] Re-running ingest on the same file does NOT duplicate a run (idempotent).
- [ ] `reliability report` prints per-test flakiness and a reliability trend.
- [ ] Adding a new framework means adding one adapter and nothing else.
- [ ] The tool's own tests (`tests/`) pass via `pytest`.
- [ ] README documents the workflow: run tests → ingest → report.

## Tech stack and constraints

- **Language:** Python (>= 3.9). The tool is external and framework-neutral, so
  it isn't tied to any test framework's language.
- **Storage:** SQLite via the standard-library `sqlite3` module. No server, no
  ORM, no third-party database driver.
- **Core dependencies:** none beyond the standard library. `pytest` is a dev-only
  dependency for the tool's tests. Justify any new package before adding it.
- **No network calls** from the tool. It reads local files and writes a local DB.

## Project structure

Pure Python. There is no Node/Playwright suite in this repo any more — result
files are supplied as static examples/fixtures instead.

```
project-root/
├── reliability/                # the tool (Python package)
│   ├── __init__.py  __main__.py
│   ├── cli.py                  # `reliability ingest` / `reliability report`
│   ├── adapters/               # per-framework parsers → neutral model
│   │   ├── base.py             # Adapter ABC + registry contract
│   │   ├── playwright.py       # Playwright JSON (implemented)
│   │   ├── junit.py            # JUnit XML (stub)
│   │   └── pytest.py           # pytest-json (stub)
│   ├── analysis/               # deterministic statistics (NO AI)
│   │   ├── flakiness.py        # per-test instability over history
│   │   ├── trends.py           # reliability trend over time
│   │   └── reliability.py      # 0–100 reliability score per test / suite
│   ├── storage/                # neutral model + local SQLite store
│   │   ├── models.py           # dataclasses (Run, TestResult)
│   │   ├── database.py         # SQLite open/insert/idempotency (stdlib sqlite3)
│   │   └── schema.sql          # neutral evidence schema (versioned in git)
│   ├── reports/
│   │   └── cli_report.py       # terminal report formatting
│   └── utils/                  # small shared helpers (e.g. text.truncate)
├── data/
│   ├── reliability.db          # local run history (gitignored)
│   └── imports/                # drop-folder for result files to ingest
├── examples/                   # one result file per format (pw json, junit, pytest)
├── tests/                      # pytest tests for the tool (+ fixtures/)
├── docs/                       # architecture notes
├── pyproject.toml              # packaging + `reliability` entry point
├── LICENSE
└── README.md                   # product vision + workflow (source of truth)
```

## Neutral evidence schema (guidance)

Two tables, framework-neutral (see `reliability/storage/schema.sql`):

- **runs** — one row per ingested run: `run_id` (stable hash → idempotent),
  `framework`, `started_at`, `duration_ms`, `tool_version`, `source_file`,
  `total/passed/failed/flaky/skipped`, `ingested_at`.
- **test_results** — one row per test per run: `run_id` (FK), `test_key` (stable
  identity across runs), `name`, `file`, `status`, `duration_ms`, `retries`,
  `message` (truncated).

Rules:
- `test_key` is what correlates the same test across runs — keep it stable.
- Truncate error messages (~500 chars). Never store credentials or secrets that
  a test may have echoed into output.
- Idempotency comes from a stable `run_id` derived from run-identifying fields.

## Coding conventions

- Small pure functions; dataclasses for the model. Prefer explicit types.
- Every capability is reachable from the CLI (`reliability <verb>`).
- Handle "file missing" / "unrecognised format" with a clear message, not a stack
  trace.
- Comments explain *why*, not *what*.
- The developer is a junior QA engineer learning this stack: when introducing a
  new concept (adapter, idempotency, neutral schema), add a 1–2 sentence
  explanation the first time it appears.

## How Claude should work in this repo

- Before writing code, restate which Phase 0 item the task belongs to. If it
  belongs to none (or drifts into out-of-scope AI / test-modification), flag it.
- Propose changes as diffs or new files; never rewrite the sample test files
  wholesale.
- When something is ambiguous, pick a reasonable default, state the assumption in
  one line, and continue.
- Keep the core deterministic and offline. If you ever think you need an LLM to
  make Phase 0 work, you've misunderstood the design — stop and ask.

## What comes after (context only — do not build yet)

- **Phase 1:** more adapters (JUnit XML, pytest-json) and richer deterministic
  analysis (per-test reliability scores, regression alerts across runs).
- **Phase 2:** correlation across findings; optional trace/artefact summarisation.
- **Optional, much later:** a *non-required* natural-language explanation layer
  over the deterministic findings. The core must always work without it.

Every phase keeps the same rule: the tool recommends; the human decides.
