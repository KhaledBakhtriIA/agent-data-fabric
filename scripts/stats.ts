import initSqlJs from 'sql.js';
import * as fs from 'fs';
import * as path from 'path';

const DB_PATH     = path.resolve(__dirname, '../evidence/qa-evidence.db');
const SCHEMA_PATH = path.resolve(__dirname, '../evidence/schema.sql');

async function main(): Promise<void> {
  if (!fs.existsSync(DB_PATH)) {
    console.error(`Error: evidence store not found at "${DB_PATH}"`);
    console.error('Run "npm run ingest" first to populate it.');
    process.exit(1);
  }

  const SQL = await initSqlJs({
    locateFile: (file: string) =>
      path.join(path.dirname(require.resolve('sql.js')), file),
  });

  const schema = fs.readFileSync(SCHEMA_PATH, 'utf-8');
  const db = new SQL.Database(fs.readFileSync(DB_PATH));
  db.exec(schema);

  try {
    // TODO (Phase 0 impl): query runs, test_results, pass/fail totals and print summary.
    console.log('[stats] stub — evidence store is open, queries not yet implemented');
  } finally {
    db.close();
  }
}

main().catch((err: Error) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
