# Example result files

One representative result file per supported framework format:

| File | Framework | Adapter status |
|---|---|---|
| `playwright-results.json` | Playwright JSON reporter | **implemented** |
| `junit.xml` | JUnit XML (pytest, Selenium, CI runners) | **implemented** |
| `pytest.json` | pytest-json-report | stub (planned) |

Try the implemented ones:

```bash
python -m reliability ingest examples/playwright-results.json
python -m reliability ingest examples/junit.xml
python -m reliability report
```

`pytest.json` is a format reference — ingesting it reports a clear
"adapter not yet implemented" message until that adapter lands.
