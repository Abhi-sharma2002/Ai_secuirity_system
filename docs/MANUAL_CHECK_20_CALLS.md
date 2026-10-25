# Manual interactive activation — 26 October 2026

## Later user restriction: ten calls for twenty minutes

This supersedes the active cap/deadline in the original activation record
below. The running backend confirmed the reduced cap without a restart.
The other ten calls stay inactive until the user asks; no automatic
activation or expiry renewal is scheduled. Actual restriction output:

```json
{
  "active_call_cap": 10,
  "remaining_calls": 10,
  "previously_consumed_calls_preserved": 0,
  "deferred_calls_inactive": 10,
  "restricted_at_utc": "2026-10-25T23:02:33.605033+00:00",
  "expires_at_utc": "2026-10-25T23:22:33.605033+00:00",
  "expires_at_ist": "2026-10-26T04:52:33.605033+05:30",
  "window_seconds": 1200,
  "same_allowance_identity": true,
  "prior_receipt_preserved": true,
  "old_stop_flags_preserved": true,
  "inference_requests_sent": 0,
  "automatic_deferred_activation": false
}
```

## Original activation record (historical)

The user requested enabling twenty provider calls for manual checking. No
background inference or benchmark run was requested or performed. The key
authenticated through a read-only account metadata request. The fixed route
was checked against [the current model listing](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free)
and [provider limits](https://openrouter.ai/docs/api_reference/limits).

Actual activation/readiness evidence:

```json
{
  "enabled": true,
  "manual_provider_call_cap": 20,
  "remaining_calls": 20,
  "mode_available": {
    "A": true,
    "B": true,
    "C": true
  },
  "activated_at_utc": "2026-10-25T22:59:48.248634+00:00",
  "expires_at_utc": "2026-10-25T23:59:48.248634+00:00",
  "expires_at_ist": "2026-10-26T05:29:48.248634+05:30",
  "provider": "openrouter",
  "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
  "nvidia_only_routing": true,
  "api_key_authentication_http_status": 200,
  "preflight_daily_free_remaining": 50,
  "background_inference_requests_sent": 0,
  "historical_receipts_unchanged": true,
  "historical_call_records_preserved": 86,
  "historical_allowance_records_unchanged": true,
  "benchmark_execution_enabled": false,
  "app_url": "http://127.0.0.1:8501"
}
```

The caps count provider calls, not successful answers. A/B use one call each;
C reserves two, and Compare reserves four. Local-only search consumes none.
The app requires its existing per-request external-processing checkbox.
Its existing stop-on-error, no-retry and expiry behavior is unchanged.
No provider request is made by the launcher or health/readiness checks.

Offline validation command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/llm/test_openrouter.py backend/tests/evaluation/test_openrouter_scope_boundary.py -q > /tmp/ai-security-manual20-offline.txt 2>&1
```

Actual output:

```text
............                                                             [100%]
12 passed in 3.03s
```

Private receipt, live flag and service logs remain ignored by Git. Existing
credentials and all unrelated environment fields were preserved. This is a
dated activation record; the private receipt and cumulative ledger govern
current remaining capacity and expiry. It grants no future automatic renewal.
