# Step 8: human-review tooling; human exercise pending

The local tools prepare the seeded spot check, record quality, validate human
labels and feed quality/agreement into metrics. They never supply human labels.
The user deferred live evaluation; without real answers there is nothing to
sample or judge. The real human spot-check requirement remains pending.

Executed commands from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_simple_review.py backend/tests/evaluation/test_simple_reporting.py -q > /tmp/ai-security-step8-unit.txt 2>&1
```

Actual output, exit zero:

```text
...............                                                          [100%]
15 passed in 5.50s
```

Synthetic test labels exist only in temporary test directories. They verify
sampling, explicit quality requirements, agreement arithmetic, stale-form
rejection, preserved original records and the refusal to auto-decide semantic
cases. Final regression also exercises the atomic reviewed-CSV replacement.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/review_eval.py --prepare > /tmp/ai-security-step8-review.txt 2>&1
```

After the existing dotenv warnings, actual structured output, exit zero:

```json
{
  "status": "no_records",
  "n_records": 0,
  "n_pending_review": 0,
  "n_sample_rows": 0,
  "n_human_checked": 0,
  "agreement": null,
  "seed": 42,
  "provider_requests_made": 0
}
```

`results/spot_check.csv` and `results/review_decisions.csv` contain headers only.
They are not a completed sample. Agreement and mean quality remain unavailable.
See [the actual reviewer workflow](HUMAN_REVIEW.md).

Full regression from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-step8-pytest.txt 2>&1
```

Exit one; actual summary:

```text
17 failed, 491 passed, 1 skipped, 1 warning, 531 subtests passed in 72.04s (0:01:12)
```

Failure identifiers exactly match the saved initial baseline.
