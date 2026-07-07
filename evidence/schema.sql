-- Evidence store schema — Phase 0.
-- Each statement uses IF NOT EXISTS so this file is safe to re-run (idempotent).

CREATE TABLE IF NOT EXISTS runs (
    run_id             TEXT    PRIMARY KEY,
    started_at         TEXT    NOT NULL,
    duration_ms        INTEGER NOT NULL,
    playwright_version TEXT,
    browser_projects   TEXT,            -- JSON array, e.g. ["chromium","firefox"]
    git_sha            TEXT,            -- nullable; populated when running inside CI
    total              INTEGER NOT NULL DEFAULT 0,
    passed             INTEGER NOT NULL DEFAULT 0,
    failed             INTEGER NOT NULL DEFAULT 0,
    flaky              INTEGER NOT NULL DEFAULT 0,
    skipped            INTEGER NOT NULL DEFAULT 0
);

-- One row per test per run.
-- A "foreign key" (run_id) links each result back to the run that produced it.
CREATE TABLE IF NOT EXISTS test_results (
    result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT    NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    test_file     TEXT    NOT NULL,
    test_title    TEXT    NOT NULL,
    project       TEXT    NOT NULL,     -- browser project name, e.g. "chromium"
    status        TEXT    NOT NULL,     -- "passed" | "failed" | "flaky" | "skipped"
    duration_ms   INTEGER NOT NULL,
    retry_count   INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,                 -- first 500 chars of error, if any
    trace_path    TEXT                  -- relative path to .zip trace file, if any
);

-- One row per retry attempt within a test result (optional in Phase 0, valuable in Phase 1).
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id     INTEGER NOT NULL REFERENCES test_results(result_id) ON DELETE CASCADE,
    attempt_index INTEGER NOT NULL,
    status        TEXT    NOT NULL,
    duration_ms   INTEGER NOT NULL,
    error_snippet TEXT                  -- first 200 chars of error for this attempt
);
