# Step 7: local metrics and charts

`make_report.py` now reads the v3 records and computes the requested metrics,
with a numerator and denominator for every rate. Errors and pending human
reviews are excluded from rates and counted separately. Type-one and type-two
false positives and their union are C-only. Missing denominators remain N/A.
Latency includes recorded error durations and excludes shared initial retrieval;
quality uses only explicit, record-bound human spot-check labels.

No live records currently exist. The generated summary and charts describe
that absence; they are not evidence of defense effectiveness. The user explicitly
deferred live checks and authorized continuing independent local implementation.

Exact checks from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_simple_reporting.py -q > /tmp/ai-security-step7-unit.txt 2>&1
```

```text
........                                                                 [100%]
8 passed in 6.08s
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/make_report.py > /tmp/ai-security-step7-report.txt 2>&1
```

Structured output (exit zero):

```json
{
  "status": "no_records",
  "n_records": 0,
  "n_expected": 141,
  "n_errors": 0,
  "n_needs_review": 0,
  "n_human_quality": 0,
  "provider_requests_made": 0,
  "records_sha256": null,
  "note": "Unavailable rates are empty CSV cells and N/A in charts; no winner inferred."
}
```

The command also emitted the pre-existing dotenv parse warnings and a
Matplotlib cache-directory warning; Matplotlib used a temporary local cache.
All chart files were opened and visually inspected: configuration labels,
titles, rate axes and unavailable annotations are legible. Latency has seconds
on its axis. The false-positive plot identifies the inapplicability to A/B.
The trade-off plot has no invented observation dots.

The live-data portion of the PDF check remains pending with Step 6.

Full regression command from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-step7-pytest-recheck.txt 2>&1
```

Exit one; actual output:

```text
17 failed, 484 passed, 1 skipped, 1 warning, 531 subtests passed in 82.92s (0:01:22)
```

The failure identifiers exactly match the initial baseline. The first full-suite
invocation was terminated before completion (exit 143); the bounded diagnostic
rerun completed. No new regression failure was found.
