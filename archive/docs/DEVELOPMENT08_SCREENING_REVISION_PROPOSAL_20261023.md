# Development-08 C: inactive screening revision proposal

Status: **PROPOSED / NOT ACTIVATED / NOT LIVE VERIFIED**, 2026-10-23.
Candidate version: `azure-gpt5mini-v3-screening-minimal-cap700-proposed`.
Active configuration remains `azure-gpt5mini-v2-temperature-not-sent`.

## Evidence and diagnosis

Saved run: `backend/data/runtime/experiments/azure-development-08-12-stage-v1/`.
`case-development-08-C-0.json` records one screening attempt: HTTP 200,
`finish_reason=length`, input 651 / completion 700 / total 1351 tokens,
empty string content, `response_validation_error=empty_content`, route
`screening_error`. No valid screening decision or answering call occurred.
The route reserved two calls / 64,000 local units; the unused answering
reservation is not refunded. No semantic judgment is justified.

The saved call contains no `completion_tokens_details`, `reasoning_tokens`,
or response metadata carrying a reasoning count. Inspection of
`app/llm/azure_openai.py` confirms normalization retains only the three
aggregate usage counts and returns empty response metadata. The original
provider reasoning-token breakdown cannot be recovered from these artifacts.
This is a confirmed length termination, not a confirmed provider filter event.
Reasoning consuming the completion allowance is a plausible explanation,
not proof that all 700 tokens were reasoning tokens. We cannot establish how
many tokens were reasoning, formatting, or other non-visible generation.

Microsoft's [reasoning documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
describes `max_completion_tokens` for Chat Completions as covering reasoning,
visible output and formatting. Its model-dependent effort table supports
`minimal` on the original GPT-5 models. The [gpt-5-mini catalog](https://ai.azure.com/catalog/models/gpt-5-mini?publisher=openai)
identifies version 2025-08-07, minimal reasoning, Chat Completions support and
a 128k output limit. These are documented capabilities, not proof of a
successful request against this deployment. `none` is not substituted.

## Exact proposed settings

| Setting | Old | Proposed |
|---|---|---|
| Deployment / model / version | gpt-5-mini-1 / gpt-5-mini / 2025-08-07 | Identical |
| API | Azure OpenAI v1 Chat Completions | Identical |
| Screening `reasoning_effort` | Not sent; provider default unspecified locally | `minimal` |
| A/B/C answering `reasoning_effort` | Not sent | Not sent |
| `max_completion_tokens`, screening and answering | 700 | 700 |
| Temperature / provider seed | Not sent / not sent | Not sent / not sent |
| Schema | Strict Screening schema with existing local validation | Identical |
| HTTP timeout / retries / stream | 30 seconds / 0 / false | Identical |
| Prompts, evidence, attacks, provider filters | Frozen existing inputs | Identical |
| Pacing | Existing evaluator/provider-gate pacing | Identical; no extra requests |

This is a one-wire-parameter proposal scoped to screening. Lower documented
reasoning effort may leave capacity for JSON without raising the existing cap.
It does not guarantee completion, valid JSON, accurate screening, or resistance.
No arbitrary cap increase is bundled in. If the single probe fails, preserve
it and stop; a different cap or effort requires another version and approval.

`backend/scripts/prepare_screening_revision.py` provides only a pure candidate
payload transformation. It has no transport, CLI execution, gate bypass or
runtime caller. Production does not import it; the current adapter still omits
reasoning effort. Activation would require an explicit stage-specific adapter
change, matched call-record settings and identity binding. Merely setting the
existing config field would be insufficient: the current adapter does not send it.

## Identity and comparability

The screening treatment changes, so a new configuration and execution identity
are required. Bind the proposed stage-specific settings, exact saved retrieval,
case/prompt/schema/scoring hashes, actual model/version, adapter/source hashes,
timeouts and schedule before any approved generation. Do not invent or freeze
that execution identity now. Bind the screening-only parameter explicitly;
the global configuration field must not accidentally change A/B/C answering.

A/B answering settings remain identical; C answering retains B's implementation
and settings but receives evidence selected by the revised screening treatment.
New C results cannot be pooled silently with v2 C results. Preserve all stopped
runs and original reviews. A separately labeled new development-08–12 cohort
can compare A/B/C with identical initial evidence and answering settings within
that cohort; old benign results remain a distinct v2 cohort. Probe output is
operational evidence only, not a scored repetition or replacement for failed C.
Incomplete triples remain incomplete; errors are excluded from semantic success
numerators and disclosed with their own coverage denominators.

## Exactly one proposed probe

- Case development-08; frozen query and ordered chunks from the saved retrieval.
- Only C screening, strict existing schema; no answer generation, retrieval
  refresh, diagnostics request, repair, retry or other provider call.
- Maximum **1 provider attempt / 32,000 new local reservation units**.
- Proposed one-hour approval from future activation; trial credits only,
  spending protection unchanged, no subscription or billing changes.
- Use a separate linked receipt and new identity. Preserve the original run's
  stop flag and all 64,000 reservations. Do not consume stopped leftovers.
- Success requires nonempty complete schema-valid JSON, valid source IDs and
  consistent reason metadata. A screening decision is not a security finding.
- Capture aggregate reported usage, termination reason, timing, safe request ID
  and optional numeric `completion_tokens_details.reasoning_tokens` if supplied.
  That optional numeric telemetry needs a small adapter/record patch before the
  probe; it must remain null when absent. Store no reasoning text or raw dumps.
  Existing historical records must not be backfilled with inferred counts.
- Stop after the attempt regardless of outcome; no automatic evaluation follows.

## Updated workload capacity (not activated)

The actual reservation implementation charges A/B one slot / 32,000 units and
C two slots / 64,000 units before screening. `client.call` checks a conservative
bound of message UTF-8 bytes + schema bytes + 1,800 against each reservation.
These local units are not Azure token usage or credit balances. The 700 cap is
unchanged, so no reservation formula or capacity increase is proposed.

| Workload | Configuration records | Maximum attempts | New reservation units | Proposed window |
|---|---:|---:|---:|---|
| Screening-only probe | 0 scored | 1 | 32,000 | 1 hour |
| Development-08–12, ABC once | 15 | 20 | 640,000 | 2 hours |
| Final planned exposed subset, ABC once | 84 | 112 | 3,584,000 | 2 hours |
| Probe + both evaluation stages | 99 scored | 133 | 4,256,000 | Separate windows |

Development IDs: development-08,09,10,11,12. Preserve original seed-5 mode
orders: CBA, BAC, BAC, BCA, ACB. Development-08 C would be a separately approved
new-version execution, not an overwrite or automatic retry. Reviewed 01–06 are
not rerun. Development-07 A is not retried; B/C using its prohibited payload
remain withheld and disclosed, not silently treated as completed.

Final IDs: final-01–15, final-17–27, final-29–30. Final-16/28 remain withheld
because of the prohibited shared payload. The final set is **exposed**, not an
untouched holdout. The 28-case subset is not a complete 30-case benchmark.
Final execution remains conditional on development review and readiness.

Each five-case development stage has at most 14,000 completion tokens; final
at most 78,400; probe at most 700, all including reasoning. Input usage and
charges are not those reservation numbers and cannot be guaranteed from this
failed screen. No new monetary estimate or credit-balance claim is asserted.

The stopped development stage retains 18 unspent slots / 576,000 units after
its two-slot reservation, but these are unavailable while stopped and do not
fund the proposed new revision. Existing interactive authorization remains
separate and unmodified; do not borrow or refresh it. This proposal neither
grants capacity nor extends any approval. New-version/probe authorization and
linked recovery are required before calls. Never clear the original stop flag.

## Offline verification

Exact command (repository root):

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_screening_revision_proposal -v
```

Exit 0: **3 tests passed in 0.143 seconds**. The current adapter constructs the
v2 request using genuine saved development-08 inputs, a synthetic credential,
a synthetic HTTP response and blocked network connections. The pure proposal
adds exactly `reasoning_effort=minimal`; schema, evidence, model and all other
payload fields remain equal. Tests reject answering/changed-cap/temperature/
seed/previous-effort inputs, confirm timeout 30, inspect the historical failure
and verify active v2 identity remains unchanged. These tests establish request
construction only, not provider acceptance or valid live screening output.

No provider calls, activation, stop-flag clearing, service restart, historical
result edits or accounting changes occurred during this preparation.
