-- Neutral evidence schema — framework-agnostic test-run history.
-- One local SQLite file accumulates runs from ANY adapter (Playwright, JUnit,
-- pytest, ...). Every statement uses IF NOT EXISTS so applying it is idempotent.

-- One row per ingested test-run execution, regardless of framework.
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT    PRIMARY KEY,        -- stable hash → re-ingesting is a no-op
    framework    TEXT    NOT NULL,           -- 'playwright' | 'junit' | 'pytest'
    started_at   TEXT,                       -- ISO 8601 timestamp the run began
    duration_ms  INTEGER NOT NULL DEFAULT 0,
    tool_version TEXT,                        -- e.g. Playwright version; nullable
    source_file  TEXT,                        -- path of the ingested result file
    total        INTEGER NOT NULL DEFAULT 0,
    passed       INTEGER NOT NULL DEFAULT 0,
    failed       INTEGER NOT NULL DEFAULT 0,
    flaky        INTEGER NOT NULL DEFAULT 0,
    skipped      INTEGER NOT NULL DEFAULT 0,
    ingested_at  TEXT    NOT NULL            -- when this row was written locally
);

-- One row per test per run. `test_key` is the stable identity that lets us
-- correlate the SAME test across many runs — the basis of all history analysis.
CREATE TABLE IF NOT EXISTS test_results (
    result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    test_key    TEXT    NOT NULL,            -- e.g. "file::describe › title [project]"
    name        TEXT    NOT NULL,            -- human-readable test title
    file        TEXT,                        -- source spec/file, nullable
    status      TEXT    NOT NULL,            -- 'passed'|'failed'|'skipped'|'flaky'
    duration_ms INTEGER NOT NULL DEFAULT 0,
    retries     INTEGER NOT NULL DEFAULT 0,
    message     TEXT                         -- truncated error message, nullable
);

-- History queries always filter/group by these two columns.
CREATE INDEX IF NOT EXISTS idx_results_test_key ON test_results(test_key);
CREATE INDEX IF NOT EXISTS idx_results_run_id   ON test_results(run_id);
