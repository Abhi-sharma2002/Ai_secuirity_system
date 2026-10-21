# Phase 4: shared LLM client and usage accounting

## Inspected state and scope

The project has strict fixture loading, LangChain ingestion/retrieval, separate
user uploads, validated evaluation cases, and the working Phase 3 fixed-context
evidence builder. At inspection, `rag/llm_client.py`, the A/B/C defenses, the runner,
and grading modules were placeholders. No LLM provider/model/credential variables
were present in the environment, and `backend/.env` did not exist. Embedding model
settings are not approval to use a generative LLM provider. Secret values were
not printed or copied.

Consequently this phase implements a provider-neutral Python interface and an
offline fake adapter. No provider SDK, LangChain chat-model integration, live
transport, paid call, tool execution, defense, scoring, endpoint, or deployment
was added. Phase 3 evidence bytes, source manifests, and fixture references are
unchanged.

## Components

| File | Responsibility |
| --- | --- |
| `app/llm/models.py` | Frozen validated messages, request/configuration, and model/API capabilities |
| `app/llm/client.py` | Adapter protocol, factory, environment credential loading, retries, errors, latency, safe operational logs |
| `app/llm/fake.py` | Scripted responses and errors with no SDK/network use; labels usage as fake |
| `app/llm/usage.py` | Token records, versioned Decimal pricing, attempt/request records, JSON export, thread-safe in-memory tracker |
| `app/rag/llm_client.py` | Compatibility imports for future RAG callers |
| `scripts/demo_llm.py` | Explicitly offline demonstration, including a retry with unknown usage |
| `tests/test_llm_client.py` | Unit tests including a socket-connection guard and Phase 3 compatibility |

## Configuration and approved adapters

The existing project uses explicit shell environment variables, not automatic
`.env` loading. `LLMConfig.from_env()` follows that convention and validates
settings without exposing rejected values. See `backend/.env.example` for names.
Defaults are `fake` / `fake-model`, 5-second connection timeout, 30-second request
timeout, 2 retries after the first attempt, 0.5-second initial backoff, and a
30-second maximum retry delay. Retry count must be 0–10. Timeouts/delays must be
finite positive numbers. Connection timeout cannot exceed request timeout.

`create_client()` reads configuration and optional pricing. Selecting a live
provider without credentials fails clearly. Even with credentials it refuses to
construct a live client because no approved adapter is installed. There is no
silent fallback from a live provider to fake output.

After company approval, an adapter can be explicitly injected. It must declare
its provider, whether credentials are needed, and capabilities for the specific
configured model/API. It must implement `generate(request, model=..., credential=...,
connect_timeout_s=..., request_timeout_s=...)` and return a normalized
`ProviderResponse`. Credentials are read from the variable named by
`LLM_CREDENTIAL_ENV`, held only in memory, never hardcoded, and never included in
records/logs. The default secret variable name is `LLM_API_KEY`.

A future transport adapter must enforce connection/request timeouts at the SDK or
HTTP layer, disable its own retries to avoid multiplying attempts, translate
provider errors, parse numeric/date Retry-After or reset guidance to seconds,
and disable tools and raw body/header logging. This synchronous orchestration
layer passes both timeouts but cannot forcibly interrupt a noncompliant adapter.
The configured request timeout applies per attempt, not across the entire retry
sequence; end-to-end latency includes every attempt and backoff. Provider context
limits and model-specific parameters must be reviewed with the approved API.

## Requests and role separation

`LLMRequest` contains an immutable tuple of `Message` objects, optional temperature,
output-token limit, test/configuration IDs, and an optional evidence fingerprint.
A request does not select or execute a defense. IDs are tracking metadata only.

System, developer, user, and assistant roles are supported by the interface.
Capabilities explicitly declare supported roles, temperature bounds, and whether
an explicit output-token limit is supported (and its maximum). Unsupported roles
or parameters fail before calling the adapter; developer messages are never
silently merged into system/user messages. Unspecified generation settings remain
unspecified so an adapter can use its documented model defaults.

Evidence can be sent unchanged as a separate `Message('user', text, untrusted=True)`.
The marker prevents accidentally constructing an untrusted system/developer
message; it is application metadata, not a provider-enforced trust boundary or a
prompt-injection defense. No screening, sanitization, truncation, command execution,
function calling, tool schema, or automatic promotion of model output is provided.

Compatibility example, from `backend`:

```python
from app.evaluation.test_case_loader import load_test_cases
from app.evaluation.evidence_builder import load_verified_sources, build_evidence
from app.llm.client import create_client
from app.llm.models import LLMConfig, LLMRequest, Message

case = load_test_cases()[0]
package = build_evidence(case, load_verified_sources())
client = create_client(LLMConfig())  # Explicit fake configuration, no live calls.
result = client.complete(LLMRequest(
    messages=(
        Message('user', package.question),
        Message('user', package.evidence_text, untrusted=True),
    ),
    test_id=package.test_id,
    evidence_fingerprint=package.fingerprint,
))
metadata = result.record.to_dict()
```

This is only an interface example, not configuration A/B/C. Later phases must
version their actual prompt serialization separately from Phase 3 evidence and
choose their defense behavior explicitly.

## Retries and structured failures

Adapters report `ProviderError` categories: timeout, rate_limit, transient,
authentication, permission, invalid_request, or invalid_response. Only timeout,
rate_limit, and transient are retried. Built-in `TimeoutError` and `ConnectionError`
are normalized as provider failures. Other exceptions are non-retryable
`application_error` failures, so programming errors are not mistaken for outages.

The number of attempts is at most `1 + max_retries`. Delay grows exponentially
from the configured initial delay, capped by the local maximum. Provider guidance
is a minimum delay; if it exceeds the local wait cap, the request fails rather
than retrying earlier than instructed. There is no jitter in this initial
single-process PoC policy. Unknown raw HTTP status codes are not guessed here;
classification belongs to the reviewed provider adapter.

Invalid configuration raises `ConfigurationError`. Invalid inputs/unsupported
capabilities raise `RequestValidationError` before any attempt, so they produce
no usage record. A terminal attempted-call failure raises `LLMRequestError` with
its content-free `record`; that record is also available in the tracker.

## Tokens, cost, and latency

Each `AttemptRecord` contains its number, latency, success, error category/origin,
optional reported usage, optional explicitly billed usage, estimated cost, and
planned retry delay. Each `RequestRecord` includes provider/model, test/configuration
IDs, optional evidence fingerprint, UUID request ID, final status/error, all
attempts, the exact pricing snapshot, and total latency.

Counts are adapter-reported nonnegative integers. Fake counts are labeled `fake`.
No tokenizer estimate is substituted. Input/output/total can individually be
unknown; total is derived from reported input+output when both are known. An
inconsistent supplied total fails validation. No prompt contents enter records.

The successful response's usage is separate from observed usage across attempts.
`known_reported_usage` sums only observed attempts. `total_reported_usage` remains
unknown if any attempt has no usage. `total_billed_usage` requires explicitly
reported billed usage for every attempt; normal response usage is not silently
assumed to be a billing receipt. Missing usage is never treated as zero.

Pricing is opt-in: configure version, input USD per million, and output USD per
million together. It is tied to provider/model and saved with every request.
No verified current vendor prices are hardcoded. Decimal arithmetic computes:

```
(input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
```

`successful_response_estimated_cost_usd` covers the final successful response.
`known_attempts_estimated_cost_usd` covers only attempts with enough usage data.
`total_estimated_cost_usd` requires an estimate for every attempt.
`total_billed_estimated_cost_usd` applies the same rate card to fully reported
billed usage. Missing pricing or input/output counts yields unknown, not $0.
These are estimates, not provider invoices; this two-rate model does not implement
cached-token discounts, reasoning/image/audio token categories, tiered charges,
taxes, or provider-specific billing rules. Explicit zero rates yield zero.

`time.perf_counter()` measures each adapter attempt and the complete request in
milliseconds. Request latency includes sleep/backoff; per-attempt latency excludes
it. Tests inject a virtual clock and sleeper to check exact durations without
waiting. The tracker retains immutable records in memory with a lock. Callers can
export `record.to_dict()` as JSON (Decimal values become strings). Persistence,
retention limits, and experiment aggregation belong to later orchestration.

## Safe logs and demonstration

Operational logs contain only generated request UUID, attempt number, normalized
status/category, and latency. They deliberately exclude arbitrary exception
strings, SDK responses, prompts, generated text, endpoints, and credentials.
Redaction uses this allowlist/exclusion boundary rather than trying to redact
unknown secret patterns from untrusted exception text. Message/response/result
representations hide text. The fake adapter retains requests in memory for unit
test assertions; do not use it as a production request recorder. A future live
adapter is responsible for preventing its SDK/transport from emitting raw logs.

```bash
cd backend
.venv/bin/python -m scripts.demo_llm
.venv/bin/python -m unittest discover -s tests -p 'test_llm_client.py' -v
.venv/bin/python -m scripts.verify_evidence
.venv/bin/python -m unittest discover -s tests -v
```

The demo fixes the provider to fake regardless of live-provider environment
variables. Its token counts and versioned rates are artificial; the initial
rate-limited attempt has unknown usage, so complete usage/cost remain unknown.
No real response or live-provider timeout behavior is claimed.

## Remaining work

Confirm an approved provider, API interface, model, credential source, supported
roles/parameters, context limits, timeout semantics, retry guidance, and verified
pricing before adding a real adapter. Test that adapter's transport, SDK retry
settings, response normalization, usage mapping, billing semantics and log safety.
Then implement the next explicitly selected phase: A/B/C prompt/defense behavior
and experiment orchestration using the same shared client. None of those defense,
scoring, judge, dashboard, API or infrastructure behaviors are part of Phase 4.

## Executed verification

- Full suite: 92 discovered, 91 passed, 1 optional real-model test skipped.
- Phase 4: 23 tests passed, including the explicit offline demo with live-provider
  environment variables and a guard against socket connections.
- Phase 3: all 45 evidence packages verified successfully with deterministic
  repeated fingerprints; the source manifest and evaluation data were unchanged.
- The offline demonstration ran successfully and compilation checks passed.
- No provider SDK was added and no live/paid LLM API calls were made.
