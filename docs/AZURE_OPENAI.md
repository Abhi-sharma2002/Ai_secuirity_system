> Current standing scope: [PROJECT_SCOPE.md](PROJECT_SCOPE.md). Trial credits only; historical paid-use examples below do not authorize new paid execution. No new Azure resources or account changes.

# Azure OpenAI integration (retained option)

This page describes the retained Azure option. The temporary active selection is
the separate OpenRouter Nemotron free route documented in [OPENROUTER.md](OPENROUTER.md).
Select `LLM_BACKEND=azure_openai` deliberately to use this configuration. Azure
uses its own `.private/azure_allowance.json`; no old provider budget funds Azure.

## Configuration

Edit only the repository-root `.env`, preserving existing private values:

```dotenv
LLM_BACKEND=azure_openai
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_ALLOWANCE_FILE=.private/azure_allowance.json
FREE_ONLY=true
LIVE_LLM_ENABLED=false
LLM_REQUEST_TIMEOUT_SECONDS=30
```

Use the actual Azure resource root or `/openai/v1` base and the actual deployment
name. Only HTTPS Azure endpoints are accepted. The runtime posts to
`/openai/v1/chat/completions`, with the deployment in `model` and the key in the
`api-key` header. No dated `api-version`, legacy deployment URL or alternate API
is silently substituted. HTTP redirects/retries and provider fallback are disabled.
TLS verification remains enabled. No tools, streaming or stored-response request
is enabled. System/developer application rules share a trusted system message;
questions, document text and metadata remain user-message JSON.

All A/B/C answering calls omit temperature (configuration `azure-gpt5mini-v2-temperature-not-sent`), `max_completion_tokens=700`, the
configured 30-second timeout and strict JSON schema. The actual deployed
model/version must support these settings and schemas. Reasoning deployments
that do not support those fixed settings cannot be made compatible by silently
dropping the limits or changing models. A/B reserve 32000 local units; C reserves
64000 up front. Missing response usage remains unknown; reservations are retained.

Microsoft references:
- [Azure v1 REST, authentication and completion parameters](https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/chat?preserve-view=true&view=rest-microsoft-foundry-v1)
- [Structured outputs and supported Azure model versions](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)

## Operator account evidence and activation

No Azure key, deployment, account eligibility or quota was present on 22 October
2026. The user deferred credentials until tomorrow morning and explicitly
prohibited calls, activation and live enablement in this implementation turn.
The prepared code does not establish live Azure compatibility or success.

When resuming the already authorized live task, record the actual Azure account
facts in a private draft based on `AZURE_ALLOWANCE.example.json`. Do not change
the old provider files. Populate the real deployment, normalized endpoint ending
`/openai/v1`, deployed model/version, capability confirmations, current
free/promotional eligibility evidence and its timezone-aware check time, plus
entitlement expiry. Use `"unknown"` only if Azure shows none; a key expiry is not
an entitlement expiry. Confirm enough actual account quota for five attempts,
including other traffic, and record that in eligibility evidence. Local approval
does not establish Azure credit or authorize unapproved paid use.

The draft stays inactive (`activated_at=null`) until the authorized baseline
command activates exactly one hour. The activation preserves its stable Azure
allowance ID and ceilings and refuses existing stops, prior activation, missing
evidence or capacity other than five remaining calls / 160000 units. Known
entitlement expiry must cover that local hour. No approval was activated now.

## Bounded live procedure (deferred; not run)

Stop only the identified project launcher/services first. The integration CLI
refuses an occupied backend lock. Keep the root live flag false. Use the cached
embedding model offline and existing frozen snapshot; no reindex/download is
part of this test.

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m scripts.azure_live_integration --activate-baseline
```

Inspect the actual baseline response and cited source text under
`backend/data/runtime/experiments/azure-development-02-A-v1/`. Only a successful,
source-supported answer permits the paired continuation:

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m scripts.azure_live_integration --paired --source-review-note 'Actual answer/source support finding recorded here'
```

This uses the same actual retrieved initial evidence, deployment, timeout,
limits and answering settings, seed5 A/B/C order, 65 seconds between call
boundaries, and no retries. A baseline failure prevents paired execution.
Every case reserves before I/O. C decisions and original/retained evidence are
saved through the existing assistant/evaluator, along with per-stage timing,
reported usage, errors and unknowns. Existing run directories cannot be retried
or overwritten. Identity drift and changed approval block the continuation.
Operational errors stop immediately and preserve partial artifacts. Do not run
another probe, switch model or increase/renew budgets automatically.

The scripts never write live-enabled settings. After a successful integration,
start `run_app.py --live-answers` only within the same unexpired remaining
capacity; a fully consumed five-call sequence leaves no Ask capacity. Following
an operational failure, start the ordinary live-disabled launcher until the
failure is reviewed and new execution is authorized. Health requests do not call
the model. The UI disables modes without one (A/B) or two (C) funded calls.

This is integration evidence only. It does not establish defense effectiveness.

## Explicit paid bounded integration exception

The user now accepts Azure charges for the existing5-attempt/160000-unit test.
The approval records `paid_azure_test_authorized=true`, the user's authorization
basis and `confirmed_free_promotional=false`; actual quota and promotional
coverage remain unknown. The paid receipt must be Azure-only, no greater than
those ceilings, and expire exactly one hour after activation. Missing new fields
remain excluded from serialization, preserving old approval fingerprints.
Launch an already activated valid receipt with:
`.venv/bin/python run_app.py --live-answers --paid-azure-test`.
This command grants no capacity and makes no automatic request. Without the paid
switch FREE_ONLY stays true; without the bounded paid receipt the paid switch
cannot authorize a provider request. Expiry, capacity and prior stop flags are
checked at reservation and before transport. Errors stop this paid allowance;
no refunds/retries/renewal or larger evaluation is authorized.

## Separate development authorization

The current user additionally authorizes the documented twelve-case DEVELOPMENT
schedule:36 A/B/C records, maximum48 attempts/1536000 new local units, two hours
from activation. See [scoped policy](../archive/docs/AZURE_DEVELOPMENT_POLICY_20261023.md).
Its separate receipt/run ID preserves exhausted integration history. This scope
is evaluator-only and rejects ordinary Ask, final cases, duplicate case/mode
reservations and mismatched execution identity. It does not expand or renew the
old5-call integration grant. All semantic grades remain pending human review.
