# Azure trial integration verification

The authorized synthetic integration completed against the user's existing
Azure deployment. This checks the application path with a fictional document;
it does not establish prompt-injection resistance or produce benchmark rates.
No existing user-uploaded document or original benchmark fixture was submitted.

The first invocation stopped locally before any reservation or provider request
because the fresh ledger was uninitialized. Its empty workspace and log were
preserved. The initialization was fixed and covered by a regression test.
The subsequent run used the original four-call receipt and expiry, with no
provider retries or fallback.

Actual sanitized run summary:

```json
{
  "scope": "Synthetic Azure integration; not a benchmark effectiveness result",
  "passed": true,
  "provider_attempts": 4,
  "reserved_calls": 4,
  "modes": {
    "A": {
      "status": "answered",
      "expected_fact_and_source": true,
      "same_initial_evidence": true
    },
    "B": {
      "status": "answered",
      "expected_fact_and_source": true,
      "same_initial_evidence": true
    },
    "C": {
      "status": "answered",
      "expected_fact_and_source": true,
      "same_initial_evidence": true
    }
  },
  "authorized_total_ceiling": 1000,
  "manual_calls_allocated": 996,
  "expires_at_IST": "26 October 2026, 16:45 IST",
  "benchmark_enabled": false
}
```

All modes used identical initial evidence, the same deployment and output cap,
and omitted temperature. Each answer contained the expected fictional fact and
cited its expected document. These are automated integration assertions, not
human benchmark quality judgments. Complete responses, usage receipts and logs
remain private and are not committed.

The remaining allocation funds user-initiated benign Ask/compare requests only.
A/B reserve one call each; C reserves two. Reservations are cumulative, not
refunded. The original window is not extended. Expired/stopped historical
receipts remain intact. The 1000-request ceiling is user authorization, not an
independently verified Azure daily quota. Trial credits and spending protection
remain required; no resources or billing settings were changed.

Local regression command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false timeout --signal=INT --kill-after=10s 120s .venv/bin/python -m pytest backend/tests/llm/test_azure_openai.py backend/tests/llm/test_openrouter.py backend/tests/frontend/test_azure_submission.py backend/tests/rag/test_comparison.py -q
```

Actual output:

```text
36 passed, 16 subtests passed in 9.97s
```

The v3 benchmark remains disabled. Its metrics/graphs continue to show missing
observations as N/A; interactive integration results are not pooled into it.

Actual local UI verification (GET requests only; no additional model call):

```json
{
  "azure_live_ready": true,
  "manual_calls_available": 996,
  "remaining_reserved_units": 31872000,
  "expires_at": "2026-10-26T11:15:47.749409+00:00",
  "all_ABC_buttons_enabled": true,
  "verification_provider_calls": 0,
  "UI_HTTP_methods": [
    "GET"
  ]
}
```
