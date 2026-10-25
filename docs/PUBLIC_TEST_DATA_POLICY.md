# Public test-data false refusal

The user's B response refused a published Australian BankCard sandbox value
because the application prompt prohibited all full payment-card numbers. Its
source citation displayed the same value. This was a false refusal, not an
injection-resistance finding. An `answered` response status means the model
returned a structurally valid response; it is not a human task-quality grade.
The reservation counter is local accounting, not actual token usage or a bill.

The public test-card facts were verified against PayPal's own
[Website Payments Pro Payflow Edition guide, test-card table](https://www.paypal.com/en_US/pdf/WPPPF_Guide.pdf).
[Current PayPal sandbox documentation](https://developer.paypal.com/credit-card-number-generator)
also distinguishes test transactions from live payment processing. The historical
published values are not instructions to use any live payment service.

The fix uses an application-owned exact allowlist. Only matching values already
present in supplied evidence enter the trusted prompt exception. The model is
instructed to identify them as test data and cite their source. A/B/C share this
rule. C's output check exempts only supported allowlisted values; unsupported
numbers remain subject to its card-pattern check. A document's filename, role
claims or assertion that a number is a test value do not create exceptions.

The answer/citation/audit preview hides unverified payment-card patterns while
preserving verified public fixtures. It makes a display copy and does not
rewrite saved evidence. Raw documents and historical audit records remain in
local storage; this remains a local PoC, not a secure-erasure system.

Prompt/output policy versions and prompt hashes changed. Existing responses,
fixtures, approvals, stop flags and consumed capacity remain unchanged. The
saved refusal is historical and is not silently regenerated. A new manual
question uses the corrected policy after the owned app service reload.

Offline command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/defenses/test_public_test_cards.py backend/tests/defenses/test_protected_output.py backend/tests/evaluation/test_simple_runner.py backend/tests/frontend/test_openrouter_submission.py -q > /tmp/ai-security-public-test-policy.txt 2>&1
```

Actual output:

```text
................................                                    [100%]
32 passed, 5 subtests passed in 5.85s
```

The response doubles are synthetic unit fixtures, not measured model behavior.
No model request was sent by this fix. The active manual allowance was neither
renewed nor expanded; the deferred portion remains inactive.

Final focused checks include the shared C screening exception and its
unchanged response to genuinely flagged instructions:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/defenses/test_public_test_cards.py backend/tests/defenses/test_protected_output.py backend/tests/evaluation/test_simple_runner.py backend/tests/frontend/test_openrouter_submission.py backend/tests/defenses/test_phase8_screening.py -q > /tmp/ai-security-public-test-policy-final.txt 2>&1
```

```text
............................................      [100%]
44 passed, 23 subtests passed in 11.68s
```

Actual local readiness after reloading only the owned app services:

```json
{
  "backend_http_status": 200,
  "frontend_http_status": 200,
  "live_enabled": true,
  "remaining_calls": 9,
  "expires_at": "2026-10-25T23:22:33.605033+00:00",
  "same_receipt_bytes": true,
  "inference_calls_sent_by_fix": 0
}
```

The current receipt bytes, remaining capacity and expiry were preserved.
No live inference was used to test the changed prompt. The corrected prompt
permits the supported public fixture; model behavior still requires the user’s
manual check. The earlier blanket-refusal response remains historical.

Full regression command from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-public-test-full-suite-final.txt 2>&1
```

Actual output, exit one:

```text
17 failed, 510 passed, 1 skipped, 1 warning, 531 subtests passed in 152.87s (0:02:32)
```

The failure identifiers exactly match the saved original baseline. The first
whole-suite attempt exposed a working-directory assumption in the new form
tests; resolving the script path from the test file fixed it before this rerun.
Original and frozen v3 benchmark files are unchanged. Generated report numbers
still match the same CSV summary; no model effectiveness results were invented.
