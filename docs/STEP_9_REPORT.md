# Step 9: reproducible written report; measured conclusion pending

The historical report was preserved with `git mv docs/REPORT.md
archive/docs_before_v3/REPORT.md`. Its bytes and historical observations are
unchanged. The new report has the requested heading order and full case table,
links all requested plots, describes each defense and usability cost, and has
the limitations table. It explicitly states that a measured recommendation and
successful-attack quotations are unavailable until real records exist.

`write_report.py` recomputes the metrics from records and human labels, verifies
every summary value, and generates the report and metrics explainer. The check
mode detects any divergence. Formula examples use only matching eligible rows;
without such rows they remain explicitly pending. No model calls are made.

Executed commands from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_simple_documents.py -q > /tmp/ai-security-step9-unit.txt 2>&1
```

Actual output:

```text
......                                                                   [100%]
6 passed in 2.58s
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/write_report.py > /tmp/ai-security-step9-write.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/write_report.py --check > /tmp/ai-security-step9-check.txt 2>&1
```

Both exited zero. After the existing dotenv warnings, actual check output:

```json
{
  "status": "verified",
  "documents": [
    "REPORT.md",
    "METRICS_EXPLAINED.md"
  ],
  "comparison_and_human_sample_complete": false,
  "provider_requests_made": 0,
  "summary_sha256": "c101c9db0e97600d1a3fcefe54230b9d1cf849dee908e06df78c6b8120e3cc8c"
}
```

The measurement-dependent report requirements remain pending, rather than being
filled from synthetic fixtures or pooled with historical Azure data.

Full regression from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-step9-pytest.txt 2>&1
```

Exit one; actual summary:

```text
17 failed, 497 passed, 1 skipped, 1 warning, 531 subtests passed in 78.97s (0:01:18)
```

Failure identifiers exactly match the initial baseline.
