# Coverage Summary

Generated from a local run on Python 3.11.15.

## Command

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
```

## Result

- Tests: 33 passed
- Total coverage: 67%
- HTML report: `htmlcov/index.html`
- XML report: `coverage.xml`

## Low Coverage Modules

| Module | Coverage | Notes |
|---|---:|---|
| `src/app.py` | 0% | Streamlit UI is not covered by unit tests. |
| `src/project_metrics.py` | 0% | CLI reporting helper; exercised manually during release checks. |
| `src/load_audit_report.py` | 36% | PDF parsing fallback paths are intentionally not fully covered by synthetic test data. |
| `src/agent.py` | 63% | Mock Agent paths are covered; optional LLM branches and several fallback paths are lightly covered. |

## Terminal Coverage Table

```text
Name                           Stmts   Miss  Cover
--------------------------------------------------
src/__init__.py                    0      0   100%
src/agent.py                     249     91    63%
src/app.py                       221    221     0%
src/case_matcher.py               60     12    80%
src/config.py                     14      0   100%
src/data_quality.py               79      4    95%
src/db.py                         60      9    85%
src/evidence_chain.py             88      6    93%
src/export_validated_data.py      75      3    96%
src/llm_client.py                 85     10    88%
src/load_audit_report.py          70     45    36%
src/project_metrics.py            48     48     0%
src/schema.py                     18      0   100%
src/seed_data.py                 153      4    97%
src/severity.py                   58      7    88%
src/validation.py                139     12    91%
--------------------------------------------------
TOTAL                           1417    472    67%
```
