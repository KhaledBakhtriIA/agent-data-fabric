# Example result files

One representative result file per supported framework format:

| File | Framework | Adapter status |
|---|---|---|
| `playwright-results.json` | Playwright JSON reporter | **implemented** |
| `junit.xml` | JUnit XML (Selenium, CI runners) | stub (planned) |
| `pytest.json` | pytest-json-report | stub (planned) |

Try the implemented one:

```bash
python -m reliability ingest examples/playwright-results.json
python -m reliability report
```

The other two are format references — ingesting them reports a clear
"adapter not yet implemented" message until those adapters land.
