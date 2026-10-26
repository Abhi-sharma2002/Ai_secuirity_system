# Azure token-efficiency fix

A saved user request exhausted the configured completion cap and returned empty
content with finish_reason length. The prior record did not preserve the
reasoning-token breakdown, so it cannot establish how that request divided its
completion allowance between reasoning and visible output.

The user requested fixing excessive token use. The Azure compatibility amendment
adds reasoning_effort: minimal to the shared eval_config.yaml, beyond its
original eight keys. Temperature remains omitted, and the original completion
cap remains unchanged. Both the transport and call metadata read these values
from the shared file for A/B/C. Screening uses the same minimal effort.
The new configuration identity separates these observations from earlier runs.

Microsoft documents that the completion cap covers reasoning and visible output,
and that original GPT-5 reasoning models support minimal effort:
[Azure reasoning models](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning).
Minimal effort reduces reasoning allocation; it does not guarantee that every
possible answer can fit the completion cap. Any incomplete/error response remains
an operational error, never a successful prompt-injection defense.

Actual synthetic verification, using supplied fixed fictional passages and no
user documents or failed user question:

```json
{
  "scope": "Synthetic model/defense integration with fixed supplied evidence; no retrieval or benchmark effectiveness measurement",
  "passed": true,
  "settings": {
    "configuration_version": "azure-gpt5mini-v4-shared-minimal-reasoning",
    "temperature": "not sent",
    "provider_seed": "not sent",
    "max_output_tokens": 700,
    "reasoning_effort": "minimal",
    "max_retries": 0
  },
  "modes": {
    "A": {
      "status": "answered",
      "expected_fact_and_citation": true
    },
    "B": {
      "status": "answered",
      "expected_fact_and_citation": true
    },
    "C": {
      "status": "answered",
      "expected_fact_and_citation": true
    }
  },
  "receipt_identity_preserved": true,
  "provider_attempts": 4,
  "call_usage": [
    {
      "mode": "A",
      "stage": "generation",
      "outcome": "returned",
      "usage": {
        "input_tokens": 827,
        "output_tokens": 70,
        "total_tokens": 897
      },
      "reasoning_tokens": 0,
      "finish_reason": "stop"
    },
    {
      "mode": "B",
      "stage": "generation",
      "outcome": "returned",
      "usage": {
        "input_tokens": 969,
        "output_tokens": 68,
        "total_tokens": 1037
      },
      "reasoning_tokens": 0,
      "finish_reason": "stop"
    },
    {
      "mode": "C",
      "stage": "screening",
      "outcome": "returned",
      "usage": {
        "input_tokens": 908,
        "output_tokens": 32,
        "total_tokens": 940
      },
      "reasoning_tokens": 0,
      "finish_reason": "stop"
    },
    {
      "mode": "C",
      "stage": "generation",
      "outcome": "returned",
      "usage": {
        "input_tokens": 969,
        "output_tokens": 68,
        "total_tokens": 1037
      },
      "reasoning_tokens": 0,
      "finish_reason": "stop"
    }
  ],
  "remaining_calls": 991
}
```

This is a model/defense integration check. It does not measure retrieval quality,
attack resistance or comparable before/after performance on the failed question.
The existing request receipt, consumed capacity and no-expiry setting were
preserved. No retry, fallback, new allowance or full benchmark was executed.
Raw synthetic responses and full receipts remain private.

Actual restarted-service check (local GET requests only):

```json
{
  "azure_enabled": true,
  "time_expiry": null,
  "remaining_calls": 991,
  "shared_reasoning_effort": "minimal",
  "shared_max_tokens": 700,
  "ui_health": 200,
  "extra_provider_calls": 0
}
```

The isolated evaluation index was prepared locally for the new configuration;
the prior local generation was archived. Saved benchmark records and historical
provider receipts were preserved. Benchmark metrics remain based only on real
benchmark records and human labels, not these interactive diagnostic checks.

The broad offline regression run reported:

```text
17 failed, 557 passed, 1 skipped, 1 warning, 531 subtests passed in 149.92s (0:02:29)
```

Its newly failing historical screening-wire test assumed that the current
transport still omitted reasoning effort. Its fixture was updated to reconstruct
the historical omitted-parameter payload explicitly and verify that the new
transport matches the minimal-effort candidate. Historical saved records were
not edited. The other failures match recorded baseline failure identifiers.

Final focused regression output after updating that historical fixture:

```text
107 passed, 36 subtests passed in 38.10s
```
