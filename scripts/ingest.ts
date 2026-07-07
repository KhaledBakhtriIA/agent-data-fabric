import initSqlJs from 'sql.js';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

const DB_PATH        = path.resolve(__dirname, '../evidence/qa-evidence.db');
const SCHEMA_PATH    = path.resolve(__dirname, '../evidence/schema.sql');
const DEFAULT_REPORT = path.resolve(__dirname, '../test-results/report.json');

async function openDb() {
  const SQL = await initSqlJs({
    // sql.js ships a WASM file alongside its JS entry; tell it where to find it.
    locateFile: (file: string) =>
      path.join(path.dirname(require.resolve('sql.js')), file),
  });
  const schema = fs.readFileSync(SCHEMA_PATH, 'utf-8');
  // Load existing DB from disk, or create a fresh in-memory one.
  const db = fs.existsSync(DB_PATH)
    ? new SQL.Database(fs.readFileSync(DB_PATH))
    : new SQL.Database();
  // exec() handles multi-statement SQL; IF NOT EXISTS makes each run idempotent.
  db.exec(schema);
  return db;
}

// sql.js keeps the database in memory; flush it to disk after every write.
type Db = Awaited<ReturnType<typeof openDb>>;
function saveDb(db: Db): void {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  fs.writeFileSync(DB_PATH, db.export());
}

// Derive a stable run_id so that re-ingesting the same report never creates
// duplicate rows. "Idempotent" means many runs produce the same result as one.
function deriveRunId(report: Record<string, unknown>): string {
  const stats  = report['stats']  as Record<string, unknown> | undefined;
  const config = report['config'] as Record<string, unknown> | undefined;
  const seed   = `${stats?.['startTime'] ?? ''}|${config?.['version'] ?? ''}`;
  return crypto.createHash('sha1').update(seed).digest('hex').slice(0, 16);
}

async function main(): Promise<void> {
  const reportPath = process.argv[2] ?? DEFAULT_REPORT;

  if (!fs.existsSync(reportPath)) {
    console.error(`Error: report file not found at "${reportPath}"`);
    console.error('Run "npx playwright test" first to generate a report.');
    process.exit(1);
  }

  const report: Record<string, unknown> = JSON.parse(
    fs.readFileSync(reportPath, 'utf-8'),
  );

  const db = await openDb();

  try {
    const runId = deriveRunId(report);
    // TODO (Phase 0 impl): insert into runs, test_results, and attempts tables.
    console.log(`[ingest] stub — run_id=${runId}, report parsed OK, no rows written yet`);
    saveDb(db);
  } finally {
    db.close();
  }
}

main().catch((err: Error) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
