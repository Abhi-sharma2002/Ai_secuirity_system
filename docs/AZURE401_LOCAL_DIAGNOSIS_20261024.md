# Latest Azure 401: private local diagnosis — 24 October 2026

Scope: saved evidence and read-only local configuration inspection only. No
provider request, Azure resource/subscription change, allowance activation,
service restart, accounting edit or credential edit.

## Confirmed

The contract-v2 screening attempt returned HTTP401 and was classified
`authentication_or_permission`. The saved sanitized request ID is
`eed805e3-d422-449f-8b5e-1fa416e3b320`. No screening response arrived; neither
screening accuracy nor source-ID compliance was evaluated.

Private checks emitted only presence/source/equality booleans:

- Canonical file is `/home/sigmoid/Ai-Security-Poc/.env`, loaded using
  `app/core/environment.py`'s fixed root path. No `backend/.env` exists.
- Key, endpoint and deployment are present, each with exactly one definition.
  No inherited overrides, unresolved variable interpolation or embedded whitespace
  were found in these fields. Values were never printed or copied to this report.
- Effective values equal the saved root values; endpoint normalization is valid.
- Root `.env` bytes are unchanged from the snapshot made after the earlier
  successful screening probe. Endpoint identity and deployment equal those bound
  to that successful probe and to the later 401 request.
- The actual 401 trace records that its effective key matched root `.env` and its
  single transport API key matched that effective credential. Authentication mode
  is API-key. The adapter uses the existing Azure v1 Chat Completions route with
  redirects disabled and zero retries.

This rules out the checked duplicate-definition, inherited-override, wrong-local-
file, absent-value and unintended-key-loading explanations. It does not establish
that Azure currently accepts the saved credential, or independently verify Azure
account/resource state. The sanitized provider code was redacted. The access-denied
message cannot distinguish a no-longer-current key, mismatched resource/key pairing,
or a resource-side authentication/access change. No content-policy diagnosis follows
from this 401. The earlier root settings also succeeding does not prove present
credential validity.

## Fix and exact private action

**No demonstrated local code/configuration defect; no fix was applied.**
Keep `screening-question-source-contract-v2`, cap700, schema, filters and original
stop flags unchanged. Do not switch APIs/models or use a different Azure resource.

Single next action: in the Azure portal, open the **existing resource's Keys and
Endpoint** page and privately reconcile root `.env` with one CURRENT key and the
resource endpoint from that SAME resource. If different, replace only
`AZURE_OPENAI_API_KEY` and/or `AZURE_OPENAI_ENDPOINT` privately in that root file;
keep the existing deployment. Do not paste credentials into chat, regenerate keys,
provision resources, change tiers, upgrade the subscription or remove spending
protection. If both already match, report that match; there is no justified local
credential replacement, and resource-side authentication status remains unresolved.

This is a private inspection/correction of existing configuration, not permission
for an Azure management change. No repeated trial-account confirmation is needed.
After that prerequisite is resolved, any live validation needs a NEW explicit
bounded trial-only authorization; the consumed 1-call/32,000-unit receipt remains
stopped and must never be reused or renewed. No verification request is authorized
or attempted by this diagnosis.

Checks: `docs/evidence/azure401-local-diagnosis-v1/checks.json`. Original results,
private settings, datasets, accounting and prior approvals were not modified.
No repeated tests or general audit were required for a read-only diagnosis.
