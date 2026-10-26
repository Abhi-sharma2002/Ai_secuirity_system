# Azure trial integration verification

Current amendment: the user removed the local time expiry. The dated window
in the original verification below is historical; current status is recorded
in the expiry-removal section at the end.

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

## User-requested removal of local time expiry

The current Azure interactive receipt now records `expires_at: null` and the
UI displays **No time expiry**. This is the user's explicit amendment to the
current authorization; its original identity and activation time remain intact.
The earlier finite-expiry receipt and parent authorization were backed up
privately. No historical stopped/expired scope was reactivated, no reservations
were refunded and no additional capacity was allocated. The original combined
request ceiling still includes the completed synthetic smoke calls.

Actual amendment verification:

```json
{
  "time_expiry": null,
  "remaining_calls": 996,
  "consumed_reservations": 0,
  "call_ceiling_unchanged": true,
  "identity_unchanged": true,
  "capacity_and_stop_flags_unchanged": true,
  "new_provider_calls": 0
}
```

Actual running API/UI check, restricted to local GET requests:

```json
{
  "live_enabled": true,
  "expires_at": null,
  "remaining_calls": 996,
  "UI_displays_no_time_expiry": true,
  "new_provider_calls": 0,
  "UI_HTTP_methods": [
    "GET"
  ]
}
```

Regression output:

```text
40 passed, 16 subtests passed in 11.79s
24 passed, 41 subtests passed in 3.79s
```

Tests cover continuing beyond the original deadline, unchanged cumulative
usage, exhausted capacity, preserved stop flags and expired known trial
entitlement. OpenRouter, staged evaluations and paid historical authorizations
still require their original finite-expiry rules. No-expiry interactive access
does not authorize benchmark execution, paid use or additional resources.
