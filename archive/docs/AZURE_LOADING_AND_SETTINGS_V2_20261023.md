# Azure loading and approved settings revision — 23 October 2026

Authorization: latest user message confirms root credentials are saved, approves
omission of unsupported temperature across A/B/C and necessary project restarts,
and limits automatic execution to ONE baseline, without automatic paired A/B/C.
FREE_ONLY account facts remain mandatory. No provider requests were made.

## Private diagnosis

Exact file: `/home/sigmoid/Ai-Security-Poc/.env`. Presence true for key,
endpoint and deployment; duplicate definitions false for each. Before importing
`app`, inherited Azure variable presence was false for each. `app.__init__` loads
root dotenv; process overrides take precedence and interpolation is disabled.
An initial diagnostic inspected inheritance after app import, so its inherited
true results were dotenv-loaded values, not external overrides; the corrected
pre-import check established this distinction.

Both example files exist and contain no nonempty Azure credentials;
`backend/.env` does not exist. No credential, private setting or dotenv file was
edited. The saved endpoint is the recognized Azure v1 Responses route. The
chosen API is Chat Completions; the validator now normalizes either exact v1
operation route to the same HTTPS Azure resource's `/openai/v1` base. It still
rejects query strings, userinfo, arbitrary paths and non-Azure hosts.

The sandbox initially could not see host project processes or use sockets.
A socket-restricted startup failed and stopped its children. An external local
health check found the existing backend had credentials_present=false and
root matches false. Identified project launcher20316/backend20318/frontend20319
were restarted using `.venv/bin/python -B run_app.py` without live enablement.
No unrelated service was restarted. Final host health checks: backend ready=true,
frontend healthy=true; running key present=true, key/root equality=true,
endpoint resource/root equality=true, deployment/root equality=true,
FREE_ONLY=true and Ask enabled=false. Root endpoint normalization is intentional;
raw operation URL and normalized base are different strings.

## Versioned settings

New `azure-gpt5mini-v2-temperature-not-sent` lives in
`backend/app/llm/experiment_settings.py`. Runtime call records, future experiment
specifications and integration baseline specifications share this revision.
Temperature is **not sent**, not1; provider seed is **not sent**. Cap700,
strict schemas, timeout30, stream=false and zero retries/fallbacks are unchanged.
Reasoning effort/top_p/tools remain unset. Local schedule seed5 remains local.
No provider seed support is asserted for this deployment; no seed is requested.
The revised DRAFT plan points to `evidence/controlled-plan-v2.json`; v1 schedule,
original results, fixtures and prior execution specifications remain unchanged.
A changed configuration causes existing specification comparisons to reject
incompatible resume; no actual execution identity or freeze was invented.

Microsoft documents gpt-5-mini/2025-08-07 support for Chat Completions, strict
outputs and max_completion_tokens, and lists temperature as unsupported:
https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning
https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs
Reproducible-output documentation does not establish this deployment's seed
support; local schedule randomness is independent of provider determinism:
https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reproducible-output
Cap700 includes reasoning tokens and may yield no complete JSON; this risk was
not resolved by silently increasing the cap or changing reasoning effort.

## Focused verification

Commands used the existing `.venv`, PYTHONPATH=backend, HF_HUB_OFFLINE=1,
TRANSFORMERS_OFFLINE=1 and LIVE_LLM_ENABLED=false:

```
.venv/bin/python -B -m unittest backend.tests.test_azure_openai backend.tests.test_environment -q
.venv/bin/python -B -m unittest backend.tests.test_azure_openai.AzureTests.test_v1_payload_auth_roles_and_paired_settings backend.tests.test_phase9_evaluation.EvaluationTests.test_execution_and_stopped_resume_no_repeat -q
git diff --check
```

First run:22 tests, one obsolete expectation rejected an operation URL now
intentionally normalized. Updated that expectation and retained arbitrary-path
rejection. Final22 tests PASS(3.914s). Two focused follow-ups PASS(0.424s), including
A/B/C wire omission and metadata, and specification-bound stopped resume. Diff
check PASS. Synthetic transports and temporary ledgers only; not live evidence.
No ingestion/full audit/full regression/benchmark/model download was repeated.

## Accounting and remaining gate

Read-only existing allowance rows (calls/units/stopped):1/32000/true,
1/32000/false,1/32000/false,2/64000/false,1/32000/false,4/128000/false.
These are historical reservations, not fresh Azure funding. No Azure allowance
file exists; no identity/capacity was added, renewed or refunded. Existing history
and stop flags remain. Authorized ceiling remains5 attempts/160000 local units;
currently activated Azure capacity is0 calls/0 units, with no approval expiry.
No baseline was attempted and no automatic paired run is authorized by the latest
message. Ask remains disabled. App URL:http://127.0.0.1:8501.

Only unresolved account inputs: current free/promotional eligibility, actual
remaining quota sufficient for the bounded authorization, and entitlement expiry
(or explicitly unknown). Configured100000TPM/100RPM does not establish them.
After those facts arrive, use existing activation/accounting checks once,
activate for one hour, issue ONE source-grounded development baseline through
the actual application, preserve response/evidence/usage/timing/reservations,
and stop on operational error. If successful, leave Ask available only within
remaining valid capacity, without another automatic model request.
