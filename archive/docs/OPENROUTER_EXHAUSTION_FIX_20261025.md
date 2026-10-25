# OpenRouter exhausted interactive allowance: local correction

The existing five-call / 160000-local-unit allowance is exhausted. Saved ledger
inspection found two completed screening calls and three failed generation calls.
All three generation responses reported HTTP 200, finish_reason=length,
completion_tokens=700 and invalid JSON. No usable answer resulted. This is not
an authentication failure and does not establish provider credit exhaustion.

Corrections:
- Normalize new OpenRouter usage to input_tokens/output_tokens/total_tokens.
- Stop OpenRouter scopes after provider/JSON errors and application validation
  errors, using the existing stop mechanism. No historical flags were changed.
- Explain truncated invalid JSON in the UI; stop messages no longer presume quota.

Focused synthetic HTTP-transport verification:
`PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m unittest backend.tests.llm.test_openrouter -v`
Result: six tests passed, 0.517 seconds. The added truncation regression blocks
socket connections and verifies normalized usage, stopped readiness and UI text.
These tests do not verify live model output quality.

Restarted only the identified run_app.py project services. Local /health, /ready
and Streamlit /_stcore/health returned HTTP 200. Readiness confirms enabled=false,
remaining_calls=0, remaining_reserved_tokens=0, original expiry
2026-10-24T21:15:48+00:00. The original stop flag remains unchanged (false).
No provider request, allowance extension/refund, credential edit, dataset edit or
historical result rewrite was performed. The output cap remains 700.

A further live attempt requires a separately authorized bounded scope. Increasing
the answering output cap requires an explicit settings revision and is not a
proven cure: model adherence and endpoint availability remain unverified. Do not
retry automatically or bypass the exhausted receipt. Azure results stay separate.
