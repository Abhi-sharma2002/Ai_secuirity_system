# NVIDIA baseline succeeded · 22 October 2026

Run `nvidia-development-02-A-20261022-v1` made exactly one configuration A / development-02 request through `assistant.respond` → shared client → prepared NVIDIA adapter and real allowance gate. Model `nvidia/nemotron-3.5-super-vl-120b-a12b`; output cap700, temperature1.0, timeout30s, retries0. No B/C, fallback, repair, polling or additional provider call.

HTTP200. Actual answer: **Development mentor check-ins occur every Friday.** Cited `development-handbook-02.md`, source `7ccf3c3f-3495-48fe-883d-e6bed5a37319_4e3d21cdb419_0_0`. The retained source contains that exact policy. Agent inspection found the answer supported and complete for the question, with no unsupported addition. This is not human benchmark adjudication; no official attack/task grades or injection-resistance claims are assigned.

Provider-reported usage: input353, output345, total698 tokens. Client latency3982.962357ms. Effective destination `https://integrate.api.nvidia.com/v1/chat/completions`; root/effective credential match=true and single-Bearer/effective match=true. Provider request ID unavailable/null. No credential, fragment, credential hash or authorization header was logged.

## Narrow contract amendment and validation

PROJECT_CONTRACT now permits `entitlement_expiry="unknown"` only when current free/promotional eligibility is established and recorded. Unknown is not unlimited; API-key expiration is not entitlement expiration. Approval records eligibility evidence and timezone-aware check/activation times; local expiry must be exactly activation+one hour. Missing/unverified free eligibility, missing evidence/times, future evidence and longer/shorter windows are rejected. All existing FREE_ONLY/provider/model/capability/reservation/stop checks remain.

Eligibility basis: the accepted explicit operator confirmation of current free/trial eligibility, exact-model access and sufficient quota including other traffic. Check time is the agent's review of that saved attestation at activation, not an invented dashboard observation or fresh provider-quota lookup. Provider entitlement expiry remains unknown. Local activation was 2026-10-22 09:54:06.723021 UTC; local approval expires 10:54:06.723021 UTC (**16:24:06 IST**). These local timestamps do not assert provider entitlement duration.

Optional amendment fields are omitted from legacy approval serialization when absent. A focused regression verifies byte-identical legacy fingerprint input; historical accounting receipts are not rewritten. The prepared NVIDIA identity and ceilings were preserved. No Groq approval/history/stop mutation or refund was performed.

Offline verification:

```bash
LLM_BACKEND=groq PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_unknown_entitlement backend.tests.test_allowance_contract backend.tests.test_nvidia_nim backend.tests.test_phase6_auth_attempt -v > docs/evidence/nvidia-expiry-amendment-tests-v1.log 2>&1
```

Exit0: **18 tests passed in 0.952s**, no skips/failures. Includes unknown-expiry validation, unchanged legacy serialization, cumulative reservation and changed-approval checks, synthetic hosted/self-hosted NVIDIA transport, redirects/pending no-follow/no-poll and one-attempt wrapper bounds. Network blocked; temporary test ledgers only. compileall/git diff --check passed. Existing completed checks were reused.

## Final accounting and state

Before: NVIDIA0 reserved calls/0 local units, remaining1/32000. After: NVIDIA1 completed call/32000 units retained, **remaining0 calls/0 local units**. Reported provider tokens are distinct from conservative local units; no reservation refund. Full historical usage preserved. Root .env unchanged by execution; datasets, uploads, Chroma and historical artifacts untouched.

Only the identified project launcher/backend/frontend were stopped/restarted to release the backend lock and load current validation. The one-shot CLI inherited the actual backend environment, enabled live only around its gate/call, and restored disabled mode. Final local readiness confirms FREE_ONLY=true and live=false. Ongoing UI answering is not enabled; no automatic UI generation check was made.

Actual application result, response, source references, trace/usage/timings and before/after accounting are preserved under `backend/data/runtime/experiments/nvidia-development-02-A-20261022-v1/`. This is successful narrow NVIDIA A-only integration. Full A/B/C integration/evaluation remains incomplete; the historical Groq401 failures remain preserved.
