# Authorized contract-v2 screening verification — 24 October 2026

Exactly one provider attempt executed through the existing gate and separate
linked receipt `azure-development08-screening-contract-v2-probe-v1`.

Outcome: **HTTP 401 / authentication_or_permission**. No screening content,
finish reason, reported usage or reasoning breakdown returned. Source-ID/schema
validation was not possible. This is not a screening decision or defense success.
Boundary latency: 1287.243 ms.
Safe provider request ID: `eed805e3-d422-449f-8b5e-1fa416e3b320`.
The allowlisted explanation indicates access denied; the sanitized error code
was redacted. It does not establish whether the key was rotated, the key/resource
pair mismatched, or the Azure resource/account state changed. No extra probe,
retry, key replacement or provider-setting change was made.

Current user authorization: one screening-only attempt / 32,000 additional local
reservation units, trial-credit-only, no out-of-pocket consent. Existing accepted
trial/spending-protection confirmations reused; no independently verified balance
claim. Activation: 2026-10-24T13:37:48.131300+00:00. Expiry: 2026-10-24T14:37:48.131300+00:00.
Consumed: 1 attempt / 32,000 units. Remaining: 0 / 0. Receipt stopped.

The runner's new explicit `--contract-v2` selection uses a new receipt/identity,
checks the corrected prompt/schema binding, and links both original development-08
failure and the prior invalid-ID diagnostic without clearing their stops. The
gate accepts only this exact dedicated bounded identity/context and prompt/schema.
Frozen question, ordered evidence, strict schema, minimal reasoning and cap700
were preserved; temperature/seed absent, zero retries, no answering call.
Actual identity SHA256: `98c3c6ae3dcc2cab6068e17ffabad318c1640a7aaa7b4726ab28f62a3a51fae0`.

The effective key, endpoint and deployment matched root `.env` privately before
activation. Azure nevertheless returned 401. Exact rejection boundary:
`backend/app/llm/azure_openai.py` non-200 status check; classified by
`backend/app/llm/client.py` 401/403 branch as authentication_or_permission.
No secret values, headers or raw provider dumps are recorded here.

All prior allowance/call rows, private receipts, parent stop and original
experiment artifacts verified unchanged. The identified project services were
paused only to release the exclusive backend lock and restored live-disabled.
No offline tests, general audit, development batch or final execution occurred.

Raw screening result/traces, sanitized diagnostics, binding and preservation
checks: `backend/data/runtime/diagnostics/azure-development08-screening-contract-v2-probe-v1/`.
This diagnostic is outside scored evaluation; original records remain ungraded
where previously ungraded.

Remaining blocker: resolve Azure authentication/resource authorization privately.
A new explicit bounded execution authorization is required before another attempt;
this one-shot receipt must not be renewed or reused.
