# Azure deployment compatibility check · 23 October 2026

No provider request,credential edit,allowance activation or experiment-setting
change was performed. No new execution identity is bound.

## Operator-confirmed portal facts

Deployment gpt-5-mini-1; underlying model gpt-5-mini,version2025-08-07;
GlobalStandard;provisioning Succeeded;configured limits100000TPM/100RPM.
These are accepted user confirmations,not a portal inspection by the agent.
Configured limits do not establish available quota,current credits or eligibility.
Do not ask the user to reconfirm the model/version already supplied.

## Private configuration check

Read-only dotenv parsing,with no interpolation and no secret output,found the
Azure key and endpoint blank and deployment not matching the confirmed name
(the saved deployment field is blank). Root backend is Azure-only,live=false,
FREE_ONLY=true,timeout30. No Azure allowance file exists. Neither secret material,
key fragments,headers nor raw .env contents were displayed or saved here.
The operator must populate the three settings privately;no credential replacement
requirement is inferred without evidence that a real Azure credential was exposed.

## Documentation-backed compatibility

Sources checked23October2026:

- [Microsoft structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)
- [Microsoft reasoning models](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
- [Microsoft Azure v1 API](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)
- [Azure model catalog](https://ai.azure.com/catalog/models/gpt-5-mini)

| Existing requirement | Finding |
|---|---|
| Azure v1 Chat Completions and deployment name | Supported documented approach;retain /openai/v1/chat/completions with actual deployment in model,no invented dated api-version |
| Strict Answer/Screening JSON schemas | Model supports structured outputs. Current schemas are required-field objects with additionalProperties=false and primitive/array fields;local shape check passed for both. Application-only validators remain local. Documentation support is not a live deployment acceptance result. |
| Explicit temperature1 | **Compatibility blocker:**Microsoft lists temperature as unsupported for this reasoning-model family. Existing adapter sends it explicitly. Do not equate an internal/default sampling value with documented permission to send this field. |
| max_completion_tokens700 | Correct documented Chat Completions parameter,within published model output ceiling. Reasoning and visible output share the completion budget;700 does not guarantee usable final JSON. Do not increase the cap or alter reasoning settings automatically. |
| Privileged instructions | System/developer messages supported;existing merged trusted system message/user JSON approach remains structurally appropriate |
| Timeout30/retries0 | Local settings unchanged. Documentation does not guarantee response completion within this limit. |

Before live execution,the explicit-temperature incompatibility needs an authorized
settings revision and versioned identity update. Omitting temperature,changing
reasoning effort,changing API/model or raising output cap was not performed.
Existing offline wire tests assert current settings and cannot establish that
Azure accepts unsupported fields. No diagnostic provider request was used.

## Remaining gates

1. Privately populate actual key,resource endpoint and confirmed deployment.
2. Resolve/document the explicit-temperature setting before a live attempt.
3. Obtain current Azure free/promotional funding eligibility,sufficient actual
   remaining quota for the bounded test and entitlement expiry (or recorded
   unknown). No such account confirmation is available in this conversation.
4. Reuse existing bounded authorization only after these gates;at most5 attempts,
   160000 additional units,one hour,no retries/fallbacks;baseline then source
   review then paired continuation only on success. No full evaluation authorized.

The bounded approval was not activated and its hour has not started. Preserve
historical provider usage and stop flags;neither exhausted NVIDIA accounting nor
configured Azure rate limits substitute for Azure account approval.

## Superseding loading/configuration verification

The latest user authorized omission of temperature. Root values are now saved,
the operation-route normalization issue is fixed, and running root matches are
verified. See [settings-v2 record](AZURE_LOADING_AND_SETTINGS_V2_20261023.md).
Earlier blank-field and temperature-blocker observations above are historical.
Funding/quota confirmation remains pending; no provider request was made.
