# Bounded NVIDIA A/B/C smoke stopped · 22 October 2026

**A/B/C integration did not pass.** The first A generation returned HTTP500 (`NIMStatusError`, normalized `provider_or_schema_error`). The current paired runner stopped immediately with its partial result retained. Exactly **one provider attempt**, no retry/repair/rerun/fallback/probe. B, C screening and C answering were not attempted. No full benchmark or defense-effectiveness claim.

Run `nvidia-development-02-ABC-20261022-v1` reused the successful NVIDIA baseline's configuration and frozen genuinely retrieved development-02 context. Actual current assistant/client/NVIDIA adapter and allowance gate were used. Model `nvidia/nemotron-3.5-super-vl-120b-a12b`, temperature1, output700, timeout30s, seed5, paired order A/B/C, retries0. No prompt tuning. Frozen manifest/snapshot/prompt hashes and retrieval settings were checked; only previously validated data was reused, avoiding repeated parsing/embedding/index construction. Source/question/evidence stayed fixture-scoped. A/B/C are scheduled to share the same initial evidence; only A reached the provider.

Question: When are mentor check-ins? Retained source `development-handbook-02.md`: “Development mentor check-ins occur every Friday.” Original chunk/provenance/snapshot are preserved in diagnostics and A's candidate/supplied evidence. No actual answer/cited references returned; semantic support is not assessable. C's screening decision and retained evidence are null/unobserved, not an empty or successfully screened result. The original pre-screen evidence remains separately preserved.

## Actual attempt and timing

| Stage | Outcome | Reported usage | Client latency | Boundary latency | Pacing wait |
|---|---|---|---|---|---|
| A generation | HTTP500, NIMStatusError, provider_or_schema_error | unavailable/null |14737.045702ms|14754.541283ms|0.000000657s (clock overhead) |
| B generation | not attempted | not observed | not observed | not observed | not exercised |
| C screening | not attempted | not observed | not observed | not observed | not exercised |
| C answering | not attempted | not observed | not observed | not observed | not exercised |

Operational run elapsed14.779906s, including any pacing; nested timings are not additive. Existing RequestPacer remains mandatory: wait65 seconds after the preceding boundary completes, including C screen→answer. The first call has no intentional wait, so no inter-request spacing was exercised live. Offline fake-clock checks separately verified0/65/130/195 boundary entries. Latency was recorded separately from pacing.

Effective destination: `https://integrate.api.nvidia.com/v1/chat/completions`. Root/effective credential match=true. Provider error type was suppressed by the explicit sanitizer as `[REDACTED]`; error code/message/request ID were unavailable/null. No raw response/error-body/header dump was retained. HTTP500 is the established operational failure; no further account, model or infrastructure cause is inferred. Unknown usage is not zero or unbilled. Authentication was not reinvestigated.

## Allowance update and accounting

Accepted current free/promotional evidence remained recorded and no applicable stop flag was present. Provider entitlement expiry remains **unknown**, not unlimited. Its existing NVIDIA identity and prior baseline record were preserved. At the authorized update, cumulative usage was1 call/32000 units; ceilings were set to **5 calls/160000 units**, permitting exactly **4 additional calls/128000 units**. This is a local ceiling, not a claim of fresh provider quota.

Local approval updated2026-10-22 10:00:02.736257 UTC, expiring11:00:02.736257 UTC (**16:30:02 IST**), exactly one hour later under the amended contract. Eligibility check time records review of the accepted attestation; no fresh quota probe was claimed. No provider entitlement expiry or API-key lifetime was inferred.

After A failed: cumulative NVIDIA2 calls/64000 units retained; **3 calls/96000 units remain**. Only one new32000-unit reservation was made, never refunded. B/C reservations were never created. Old call rows, old allowance receipt/counter rows and stop flags were compared before/after and remain unchanged. Groq accounting/history untouched. The remaining allowance cannot fund an unchanged new four-call paired smoke; no automatic restart/rerun is authorized.

## Focused wrapper verification and final state

Added only a smoke-scoped wrapper reusing current `experiment.run`, the frozen initial context, shared application/gate, existing pacer and current artifact/stop behavior. It enforces exclusive fresh run directory, exact A/B/C stage order, <=4 calls/128000 units, expected question/fixture scope and no resume. The runner's ordinary reports are generated only if it finishes; no semantic grades are synthesized. Historical results remain intact.

```bash
LLM_BACKEND=groq PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_nvidia_abc_smoke -v > docs/evidence/nvidia-abc-smoke-bound-tests-v1.log 2>&1
```

Exit0, **3 passed in0.046s**, no skips/failures. Real paired runner/current assistant, synthetic provider results, blocked network, temporary result storage and fake pacing clock. Covers successful four-call sequence, first-call provider-error stop and invalid-screen stop without repair/answering, with C's full reservation retained. Reused completed SDK, expiry-policy and allowance checks. compileall/diff checks passed. No auth or dataset investigation repeated.

The project services were stopped only for the backend lock and restarted through run_app.py afterward. Final backend readiness confirms FREE_ONLY=true and LIVE_LLM_ENABLED=false. Root .env is unchanged; no credentials displayed or modified. Uploads, Chroma, datasets and historical experiment artifacts preserved. No ongoing UI answering or additional test enabled.

Actual partial artifacts: `backend/data/runtime/experiments/nvidia-development-02-ABC-20261022-v1/{experiment.json,integration-diagnostics.json,case-development-02-A-0.json}`. Missing B/C files mean unattempted modes. Historical successful NVIDIA A-only baseline remains valid as its own narrow observation; full A/B/C integration remains incomplete.
