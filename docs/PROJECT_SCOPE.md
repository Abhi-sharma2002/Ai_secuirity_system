# Standing local-first scope

Current selection, 26 October 2026: the user stopped OpenRouter and selected
their existing Azure gpt-5-mini deployment on their own Free Trial account.
The active OpenRouter key is blank; historical code, receipts and accounting
remain intact. Use trial credits only, preserve spending protection and create
no additional cloud resources. Live inference remains disabled until the local
Azure settings and a current bounded trial scope are complete. The user approved
omitting unsupported temperature identically for A/B/C; the shared YAML records
that compatibility amendment. Live benchmark execution remains disabled.
See [current setup](AZURE_TRIAL_SETUP.md) and the current amendment in AGENTS.md.

The temporary OpenRouter policy below is preserved as historical context.

On 25 October 2026, the user requested a temporary switch away from paid Azure
answering to `nvidia/nemotron-3-ultra-550b-a55b:free` through OpenRouter. For the
temporary runtime, the Azure implementation and its historical records remain
intact but are inactive when `LLM_BACKEND=openrouter`. OpenRouter is restricted in
code to the exact `:free` model alias and NVIDIA provider with provider fallbacks
disabled. A separate, one-hour local allowance is required (maximum 200 calls and
6400000 reserved units, only within explicit approval; see the 25 October
200-call amendment and linked benign recovery records). No live call is authorized by this code change. Free
pricing and account-level billing conditions are controlled by OpenRouter and can
change; verify the provider's current terms and dashboard before enabling calls.

The previous Azure-only authorization below is preserved as historical policy
context, except where the temporary OpenRouter amendment above explicitly differs.

Authorization basis: user's standing project instruction of 24 October 2026.
This supersedes historical paid-use exceptions for all future execution.

| Component | Permitted location |
|---|---|
| Answering and screening | Fixed OpenRouter Nemotron `:free` route temporarily; Azure retained but inactive |
| Embeddings | Existing local CPU model |
| Parsing, chunking, retrieval | Local application |
| Vector storage / registry | Local Chroma / SQLite |
| Evaluation, human reviews, metrics and charts | Local; no automatic LLM grading |
| Backend and Streamlit UI | Local |

Do not provision/enable Azure AI Search, cloud embeddings, storage accounts,
hosted apps, monitoring, agents, additional deployments or other paid features.
Do not change SKU/tier, deployment type, subscription plan, quota allocation or
spending protection. No Free Trial-to-pay-as-you-go upgrade. No out-of-pocket
consent exists under this scope. Report any required Azure change before acting;
this policy grants no permission to make it. Complete independent local work.

Provider requests require a current explicit bounded authorization. The
OpenRouter allowance caps usage locally but is not a provider billing guarantee.
Preserve limits, expiry, original stop flags and cumulative accounting. No background
calls, retries, fallback models or unnecessary model requests for health, grading,
planning or charts. Existing trial-account confirmations can be reused; local
code neither verifies remaining credits nor enforces provider billing protections.
No additional billing verification gate or duplicate account-confirmation flow
was introduced.

## Implementation

- Root `AGENTS.md` records the scope for all future repository work.
- `app.llm.client.approval` rejects `FREE_ONLY=false` and historical paid receipts
  before reservations/provider transport. Old receipt parsing/fingerprints remain
  supported for historical accounting; no historical consent is rewritten.
- `run_app.py` rejects `--paid-azure-test` and always supplies `FREE_ONLY=true`.
  Default launch remains live-disabled. `--live-answers` still needs its own valid
  allowance; it creates no capacity and makes no automatic request.
- `scripts.azure_live_integration.activate` refuses paid activation before writes.
- `scripts/run_authorized_development.py` is a non-executing retired paid-command
  stub; original source is preserved under `docs/history/trial_only_scope_20261024/`.
  Current trial-only staged/diagnostic mechanisms remain separately bounded.
- No cloud dependency, provisioning code, cloud embedding path, hosted service,
  resource management action, credential edit or account change was added.

## Verification

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.core.test_app_launcher backend.tests.llm.test_paid_azure_test backend.tests.llm.test_development_paid_scope backend.tests.llm.test_azure_openai.AzureTests.test_v1_payload_auth_roles_and_paired_settings backend.tests.llm.test_azure_openai.AzureTests.test_stop_survives_approval_edits -v
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.llm.test_paid_azure_test.PaidAzureTests.test_retired_paid_development_command_blocks_before_any_activation -v
```

First run: 14 passed in 0.995s. The one additional retired-command check passed;
see `docs/evidence/trial-only-scope-v1/retired-command-test.log` for timing.
Synthetic HTTP and temporary ledgers only. Covers paid refusal, no reservation
consumption, receipt round-trip stability, unchanged trial A/B/C wire behavior,
stop preservation, launcher defaults and paid activation/command rejection.
Original paid-era test sources are archived; active tests now assert revocation.

No provider calls, allowances, refunds, quota changes, Azure management actions
or service restarts occurred. Existing private settings/results/accounting were
not edited. New code changes source fingerprints; future live runs must bind the
current identity without modifying historical records. The earlier HTTP401 remains
an unresolved provider authentication event; this policy change does not fix it
or authorize another diagnostic request.
