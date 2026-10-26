**Current Azure trial setup**

The user selected their already deployed Azure gpt-5-mini on their own Free
Trial account and requested that OpenRouter stop. The active root environment
now selects Azure and leaves the active OpenRouter key blank. After explicit
bounded authorization and a successful synthetic A/B/C check, live interactive
use is enabled. See [the recorded verification](AZURE_TRIAL_VERIFICATION.md). Historical private settings, receipts, stop flags and
cumulative accounting are preserved. No account/key was revoked remotely and
no cloud resource, deployment, plan, quota or spending protection was changed.

Initial setup template: enter values only in the local root `.env`, never in
chat or a commit. Do not overwrite the current private receipt path or enabled
settings with this disabled template after activation:

```dotenv
LLM_BACKEND=azure_openai
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_ALLOWANCE_FILE=.private/azure_current_trial.json
OPENROUTER_API_KEY=
FREE_ONLY=true
LIVE_LLM_ENABLED=false
```

Use the actual resource HTTPS endpoint and actual deployment name from Azure.
The deployment name can differ from the model's catalog name. Accepted resource
roots are normalized to `/openai/v1`; the existing transport uses Chat
Completions, an `api-key` header, `max_completion_tokens`, strict JSON Schema,
no automatic retries and no provider fallback.

Microsoft's [reasoning-model documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
documents the parameter differences for this model family and using the
deployment name in the request. The existing Azure runtime omits temperature.
The PDF instead specifies temperature zero. The user explicitly approved the
compatibility amendment: the shared evaluation YAML selects Azure gpt-5-mini
and records temperature as null, omitted identically for A/B/C. Local preparation
creates a new index identity and archives the previous generation. Historical
results remain intact; this configuration change does not execute a benchmark.

Microsoft's [structured-output documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)
describes the JSON Schema response format. Existing local tests verify the
transport shape with synthetic responses. They do not establish compatibility,
remaining credits or response quality for the user's actual deployment.

Azure trial use consumes trial credit; it is not an unlimited free-model
request allowance. Preserve the trial's spending protection and verify the
remaining entitlement without upgrading the account. See Microsoft's
[free-account charging explanation](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/avoid-charges-free-account).
The user confirmed saved credentials, active trial credits and spending protection.
The current request-bounded scope follows the user's explicit authorization;
the user subsequently removed its local time expiry.
old expired/stopped receipts cannot authorize this new account.

The Ask interface now labels the selected provider as Azure OpenAI. The same
backend selection is used for A/B/C; there is no UI OpenRouter selection while
Azure is active. Explicit compare confirmation is also forwarded through the
API into every mode's request context. Local-only search and metrics remain
available without a provider call. After local credentials are saved, restart
the owned services so they load the updated environment.

Local dependency check:

```bash
.venv/bin/python run_app.py --check
```

The saved endpoint/key/deployment are checked locally without printing their
values. The user subsequently authorized a current bounded scope and the synthetic
live check completed. See the verification record for actual results and the later expiry-removal amendment.
This does not produce defense effectiveness metrics.


Local verification completed for this change:

```text
102 passed, 26 subtests passed in 35.24s
16 failed, 552 passed, 1 skipped, 1 warning, 531 subtests passed in 150.78s (0:02:30)
```

The complete-suite failures all match the recorded Step 1 baseline; no new
failure identifiers were introduced. One baseline Azure readiness assertion
was corrected to match the intentional withholding of capacity while disabled.
The API/UI verifier passed actual upload, CPU embeddings, search, source-label
presentation, every workspace, disabled A/B/C, request idempotency, invalid
replacement preservation and logical deletion. It recorded zero provider calls
and zero outbound events; benchmark/results/private state remained unchanged.
These are integration checks, not a claim of measured attack resistance.

Commands used from the repository root (full-suite invocation runs in backend):

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s .venv/bin/python -m pytest backend/tests/evaluation/test_run_eval.py backend/tests/evaluation/test_simple_runner.py backend/tests/llm/test_azure_openai.py backend/tests/core backend/tests/rag/test_comparison.py backend/tests/frontend backend/tests/api/test_runtime_v2.py::RoutingV2Tests -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=False LIVE_LLM_ENABLED=false timeout --signal=INT --kill-after=10s 240s .venv/bin/python backend/scripts/verify_v3_local.py --output /tmp/ai-security-azure-end-to-end-local-final.json
```

The verifier requires a new output filename on repeat execution to preserve
prior evidence. The complete suite command, run from `backend/`, was:

```bash
PATH="$PWD/../.venv/bin:$PATH" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false FREE_ONLY=true ANONYMIZED_TELEMETRY=False MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 240s python -m pytest tests -q -o faulthandler_timeout=45
```

The prepared live smoke test can be inspected without importing the app or
making a provider request:

```bash
.venv/bin/python backend/scripts/azure_trial_smoke.py --plan
```

It uses only its displayed fictional policy and question in a new private
workspace. It plans A generation, B generation, C screening and C generation;
no original benchmark or user-uploaded document is sent. It checks the actual
answer for the expected fact and citation and checks identical initial evidence.
It stops on the first error, never retries and never writes security metrics.
Running requires a separately authorized current four-call trial receipt and
explicitly enabled live settings. The completed receipt is consumed; do not
rerun or renew it. The script cannot create or renew authorization.

The later [token-efficiency fix](TOKEN_EFFICIENCY_FIX.md) adds shared minimal
reasoning effort to the YAML without raising the completion cap. Historical
verification outputs below remain facts about their original settings.
