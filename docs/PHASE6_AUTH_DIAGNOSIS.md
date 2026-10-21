# Phase 6 HTTP 401: offline diagnosis · 21 October 2026

No configuration-loading or endpoint defect was demonstrated. The saved live attempt confirms HTTP 401, SDK AuthenticationError and application category authentication_or_permission. It does not establish the exact account/credential cause. No live request, retry, restart or runtime fix was made during this investigation.

## Configuration trace and safe credential findings

`app/__init__.py` calls `core.environment.load_environment()` before importing application settings. It loads the fixed repository-root .env with override=False and interpolate=False. Inherited process values, including empty ones, win. `LiveSettings.from_env()` reads GROQ_API_KEY and strips outer whitespace; its credential field is excluded from repr. The dynamic gate/client reads LiveSettings again and passes its api_key explicitly into ChatGroq. OPENAI_API_KEY and historical provider variables are not the active credential source.

Current inspected credential source: **repository-root .env GROQ_API_KEY**. Safe boolean findings:

| Check | Result |
|---|---|
| Inherited GROQ_API_KEY present | false |
| Root GROQ_API_KEY missing | false |
| Effective credential missing/empty/blank after strip | false / false / false |
| Effective credential differs from parsed root value | false |
| Outer whitespace / any whitespace / control characters | false / false / false |
| Placeholder pattern detected | false |

These are syntax/source checks, not credential-validity checks. The original .env hash still matches the authorized-update audit; current client source hash and SDK package versions match saved execution identity. A historical complete child environment or credential fingerprint was not captured; current source inspection alone cannot reconstruct it. No key, prefix/suffix, authorization value or .env contents were printed or copied into this report.

## Actual installed SDK endpoint

The application explicitly sets base_url=https://api.groq.com. Installed groq 0.37.1 also defaults to that host; its completion resource appends **/openai/v1/chat/completions**. Resulting URL is **https://api.groq.com/openai/v1/chat/completions**. Do not append /openai/v1 to the configured base merely because the application supplies a host-only URL: this installed SDK already supplies the resource prefix.

The application passes both api_key and base_url explicitly. Offline actual-SDK transport tests prove that conflicting GROQ_API_KEY/GROQ_API_BASE/GROQ_BASE_URL test environment values do not replace those explicit application arguments. Dummy credentials only were used in assembled requests; assertions report booleans rather than header values. Synthetic HTTP 200 and 401 responses were returned in memory; sockets were blocked. This confirms current request assembly, not a newly observed live URL or key acceptance.

## Saved failure and exception handling

The single saved A generation attempt has HTTP401/AuthenticationError, attempts=1, usage=null, provider_request_id=null and no answer. The application's exception traversal extracts status from wrapped causes and maps 401/403 to authentication_or_permission, records safe metadata, marks the ledger record failed and raises ModelFailure. The evaluator then stops; B/C remain unattempted. Raw SDK error text is not retained because it can expose secrets. No evidence here establishes billing, quota exhaustion, model rejection or an endpoint typo as the cause.

Possible unresolved causes include provider rejection of the configured replacement credential or account/project access restrictions. Clean local syntax and the user's rotation confirmation do not prove provider acceptance. No additional provider diagnostic was attempted to distinguish these possibilities.

## Verification and preservation

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_groq_endpoint -v > docs/evidence/phase6-auth-offline-tests.log 2>&1
.venv/bin/python -m compileall -q backend/tests/test_groq_endpoint.py
```

Both exit0; **2 tests passed in 1.578s**. Tests use actual installed ChatGroq/Groq serialization, temporary SQLite and explicit dummy approval/configuration doubles. HTTP transport is in-memory, network forbidden. Synthetic401 verifies one attempt, correct classification, failed ledger state and retained32000 reservation in disposable storage. No production approval/ledger mutation. Additional read-only checks exit0: effective live disabled/free-only true; root .env and approval fingerprints unchanged; one existing failed production ledger record retains32000 units. No runtime defect/fix. Added only this diagnosis, safe JSON evidence, focused tests/log.

## Remaining prerequisite for another run

User-side verification/remediation of the configured replacement Groq credential and its intended account/project access is required; do not paste credentials here. Provider acceptance cannot be established offline. A further live verification requires **separate explicit authorization and a new reviewed run ID/plan**: the existing single-use run is exhausted by its stopped execution and must not be resumed. A full unchanged A/B/C smoke additionally needs an unexpired truthful allowance with at least4 remaining calls/128000 local units; current retained accounting leaves3/96000, so it cannot fund that plan. No refund, expiry extension, allowance identity/history change or automatic future run is authorized by this diagnosis. Live remains disabled.
