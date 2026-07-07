# CLAUDE.md — QA Reliability Platform, Phase 0 (Evidence Foundation)

## What this project is

An AI-assisted QA reliability platform that helps QA engineers detect fragile
locators, flaky tests, and hidden quality risks in Playwright test suites.

**Operating principle (never violated):**
Observe → Analyze → Recommend → Human Decision.
The system never modifies tests, never deploys changes, and never acts
autonomously. A human approves every change.

**Target project:** the existing Playwright + TypeScript + Page Object Model
suite that tests Sauce Demo (https://www.saucedemo.com).

## What Phase 0 is — and is not

Phase 0 builds the **evidence foundation**: after every Playwright run,
structured data about that run is captured and stored in a local database.
Nothing analyzes that data yet. Phase 0 is pure plumbing.

**In scope:**
1. Playwright configured with the JSON reporter (in addition to HTML)
   and trace collection on failure/retry.
2. An **ingestion script** (TypeScript, run via `npm run ingest`) that parses
   the JSON report after each run and writes normalized records to SQLite.
3. The **evidence store**: a SQLite database (`evidence/qa-evidence.db`)
   accumulating run history over time.
4. A trivial **CLI check** (`npm run evidence:stats`) that prints how many
   runs/tests/failures are stored — proof the pipeline works.

**Explicitly OUT of scope (do not build, do not suggest building):**
- Any LLM or Anthropic API call
- Any agent, orchestrator, or "meta supervisor"
- Locator linting, flakiness detection, or any analysis logic (Phase 1)
- Data pipeline validation, schema validators, Kestra, Kafka (deferred)
- Any UI beyond terminal output
- Automatic modification of test files

If a task drifts toward these, stop and say so instead of building it.

## Success criteria (definition of done)

Phase 0 is complete when:
- [ ] Every `npx playwright test` run produces a JSON report and traces on failure
- [ ] `npm run ingest` stores that run in SQLite without errors
- [ ] Re-running ingest on the same report does NOT create duplicate records (idempotent)
- [ ] `npm run evidence:stats` shows run count, test count, pass/fail totals
- [ ] At least 20 real runs are accumulated in the database
- [ ] The README documents the workflow: run tests → ingest → check stats

## Tech stack and constraints

- **Language:** TypeScript only. No plain JavaScript files.
- **Runtime:** Node.js (the version already used by the Playwright project).
- **Database:** SQLite via `better-sqlite3`. No Postgres, no ORM, no server.
- **Dependencies:** keep them minimal. Justify any new package before adding it.
- **No network calls** from the ingestion script. It reads local files only.

## Project structure

```
project-root/
├── tests/                  # existing Playwright specs (POM) — do not restructure
├── pages/                  # existing Page Objects — do not restructure
├── playwright.config.ts    # add JSON reporter + trace settings here
├── evidence/
│   ├── qa-evidence.db      # SQLite database (gitignored)
│   └── schema.sql          # schema definition, versioned in git
├── scripts/
│   ├── ingest.ts           # parses JSON report → writes to SQLite
│   └── stats.ts            # prints evidence store summary
└── CLAUDE.md               # this file
```

## Evidence store schema (guidance)

Three tables, normalized:

- **runs** — one row per `npx playwright test` execution:
  `run_id, started_at, duration_ms, playwright_version, browser_projects, git_sha (nullable), total, passed, failed, flaky, skipped`
- **test_results** — one row per test per run:
  `result_id, run_id (FK), test_file, test_title, project (browser), status, duration_ms, retry_count, error_message (nullable), trace_path (nullable)`
- **attempts** (optional in Phase 0, valuable for Phase 1) — one row per retry attempt:
  `attempt_id, result_id (FK), attempt_index, status, duration_ms, error_snippet`

Rules:
- Derive a stable `run_id` (hash of report start time + config) so ingestion is idempotent.
- Store error messages truncated (first ~500 chars). Full detail lives in the trace file; store its path, not its contents.
- Never store credentials or secrets from test output.

## Playwright configuration rules

- Reporters: `[['html'], ['json', { outputFile: 'test-results/report.json' }]]`
  — keep the HTML report; the human still uses it.
- Traces: `trace: 'on-first-retry'`, retries: 2 (so flaky patterns become visible in history).
- Do not change existing test logic, locators, or Page Objects in Phase 0.
  Phase 0 observes the suite as it is — including its flaws. The flaws are the data.

## Coding conventions

- Follow the existing POM structure; new code goes in `scripts/`, not `tests/`.
- Prefer explicit types over `any`. Small pure functions over classes for scripts.
- Every script must be runnable via an npm script (`npm run ingest`, `npm run evidence:stats`).
- Handle the "report file missing" case with a clear error message, not a stack trace.
- Comments explain *why*, not *what*.

## How Claude should work in this repo

- Before writing code, restate which Phase 0 item the task belongs to.
  If it belongs to none, flag it as out of scope.
- Propose changes as diffs or new files; never rewrite existing test files wholesale.
- When something is ambiguous (e.g., schema field naming), pick a reasonable
  default, state the assumption in one line, and continue.
- Keep explanations in plain language; define technical terms inline the first
  time they appear.
- The developer is a junior QA engineer learning this stack: when introducing
  a new concept (idempotency, foreign keys, reporters), add a 1–2 sentence
  explanation the first time it comes up.

## What comes after (context only — do not build yet)

- **Phase 1:** locator/test-quality linter (static rules) + flakiness detector
  (statistics over the evidence store) + LLM analysis layer that turns findings
  into human-readable recommendations, delivered via CLI.
- **Phase 2:** browser observation (DOM inspection, trace analysis), richer
  correlation across findings.
- **Phase 3 (only if a real need emerges):** data quality branch, coordination layer.

Every phase keeps the same rule: the system recommends; the human decides.
