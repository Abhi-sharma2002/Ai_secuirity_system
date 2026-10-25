## Current allowance state

The private receipt and cumulative ledger are authoritative for the current
expiry, caps, consumption, and stop state; do not infer these from a dated
example in documentation. Do not reset history, clear stops, or automatically
renew an allowance. Original five-call/one-hour setup examples below are
historical examples, not instructions to create duplicate capacity.

# Temporary OpenRouter Nemotron configuration

The temporary runtime choice is
`nvidia/nemotron-3-ultra-550b-a55b:free`. Azure transport and its configuration
remain in the repository; choosing `LLM_BACKEND=openrouter` selects this separate
transport. No fallback to Azure, a paid model alias, or another OpenRouter provider
is made.

## Private configuration

Set these values in the repository-root `.env` only:

```dotenv
LLM_BACKEND=openrouter
OPENROUTER_API_KEY=YOUR_ROTATED_OPENROUTER_KEY
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_ALLOWANCE_FILE=.private/openrouter_allowance.json
FREE_ONLY=true
LIVE_LLM_ENABLED=false
LLM_REQUEST_TIMEOUT_SECONDS=30
```

Do not put an API key in source, tests, command arguments, or documentation. The
key previously pasted in chat must be revoked; use a replacement. Keep live calls
disabled until both the key and the local allowance are configured. `run_app.py
--live-answers` enables the server-side gate but does not itself grant an
allowance or send a request.

## Local allowance

Create `.private/openrouter_allowance.json` locally. Do not copy an Azure receipt.
Use the current UTC time for `activated_at`, an earlier UTC time for
`eligibility_checked_at`, and set `expires_at` exactly one hour after activation.
The `eligibility_evidence` text should record that the operator checked the
OpenRouter dashboard/model listing for this exact free route. Set
`max_calls` no greater than 5 and `max_reserved_tokens` no greater than 160000.
The required fields are:

```json
{
  "provider": "openrouter",
  "allowance_id": "choose-a-new-local-id",
  "confirmed_free_promotional": true,
  "approved_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
  "approved_endpoint": "https://openrouter.ai/api/v1",
  "deployment_model_version": "nvidia/nemotron-3-ultra-550b-a55b:free",
  "expires_at": "REPLACE_WITH_ACTIVATION_PLUS_ONE_HOUR",
  "max_calls": 5,
  "max_reserved_tokens": 160000,
  "chat_completions_supported": true,
  "structured_outputs_supported": false,
  "max_output_tokens_supported": true,
  "confirmation_note": "Operator confirmed the OpenRouter free-model route",
  "entitlement_expiry": "unknown",
  "eligibility_evidence": "Record the current dashboard/model free-route check",
  "eligibility_checked_at": "REPLACE_WITH_TIMEZONE_AWARE_UTC_TIMESTAMP",
  "activated_at": "REPLACE_WITH_TIMEZONE_AWARE_UTC_TIMESTAMP"
}
```

This is an operator-maintained local control, not cryptographic proof of account
terms. The application requires the exact provider, base endpoint, model alias,
NVIDIA-only provider route, a one-hour expiry, and bounded local reservations.
It retains reservations after errors and disables retries and redirects.

The currently listed free endpoint reports zero prompt/completion pricing and does
not advertise structured-output support. The transport therefore does not send
`response_format`; it includes the expected JSON Schema in trusted prompt text and
still validates returned JSON locally. Invalid output fails closed. Provider
availability, limits, billing terms, and model behavior can change; this local
gate cannot guarantee OpenRouter account billing. Check the dashboard before
enabling live calls.

The Ask / compare UI defaults to local-only evidence search. A separate
per-request checkbox is required before OpenRouter reservations can be created;
the server also blocks OpenRouter reservations if that confirmation is absent.
When confirmed, the provider receives the question and retrieved passages for
answering and, in mode C, screening. Only send content authorized for that
provider. Uploads, indexes, and saved request results remain on local storage;
the application does not provide encryption, access control, or secure erasure.
Deleting a document removes it from future retrieval but is not secure erasure.
Prompt separation, screening, citation checks, and the C payment-card pattern
check are experimental and do not guarantee confidentiality or prompt-injection
resistance.
