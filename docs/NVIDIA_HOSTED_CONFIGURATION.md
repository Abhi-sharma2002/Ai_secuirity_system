# NVIDIA hosted configuration · 22 October 2026

## User-initiated Ask enabled within remaining allowance · 22 October 2026

Actual backend now runs `run_app.py --live-answers`, UI http://127.0.0.1:8501. Local readiness/health only; **no automatic provider call**. FREE_ONLY=true. Remaining3 calls/96000 units; same NVIDIA identity/ceilings/history/stops. Existing approval unexpired, not renewed:22October2026 16:30:02.736257 IST. Unknown provider entitlement preserved. All call/allowance rows unchanged across restart. Default launcher/root .env remain live-disabled; explicit flag enables only backend.

Recorded HTTP500 finalized as failed without an allowance stop; no reset/stop bypass required. New manually submitted Ask requests are authorized, not an automatic retry/resume or proof of provider recovery. Current C reserves2 calls/64000 units up front and rechecks approval per call; A/B reserve1/32000. Expiry or insufficient capacity blocks provider requests. Two focused launcher tests passed; existing gate/C/expiry tests reused. Full A/B/C integration still incomplete. [Exact live status, expiry and recovery](ASK_LIVE_STATUS_20261022.md).


## NVIDIA paired smoke stopped: HTTP500 · 22 October 2026

Authorized one paired development-02 A/B/C repetition with <=4 attempts and128000 additional local units. Preserved NVIDIA identity/history, updated ceilings from cumulative1/32000 to5/160000, and set exactly one-hour local expiry (16:30:02 IST). Unknown provider entitlement and accepted eligibility evidence preserved; no fresh quota claim. Smoke reused baseline model/settings and frozen genuine retrieval; no prompt tuning/auth reinvestigation.

Actual run `nvidia-development-02-ABC-20261022-v1` stopped on first A generation: **HTTP500, NIMStatusError, provider_or_schema_error**. Exactly1 attempt; B/C unattempted; answer/usage/message/code/request-ID unavailable/null, error type redacted. Client14737.045702ms; boundary14754.541283ms; first-call pacing0.000000657s (no intentional wait). No retry/repair/rerun/fallback/probe. Original evidence preserved; C screening/retained evidence unobserved/null; no semantic support judgment possible.

A's new32000-unit reservation retained; NVIDIA cumulative2/64000, remaining **3 calls/96000 units**. All prior call/allowance rows and stop flags compared unchanged; Groq accounting untouched. Root .env unchanged. Services restarted live-disabled/free-only true. **A/B/C integration did not pass and remains incomplete**; no full benchmark or effectiveness claim. Three focused offline wrapper tests passed in0.046s, including fake-clock65s pacing and operational/schema stop behavior. compileall/diff checks passed. [Actual partial result and accounting](NVIDIA_ABC_SMOKE_RESULT_20261022.md).


## Single NVIDIA A baseline succeeded · 22 October 2026

Applied the expressly authorized unknown-entitlement-expiry amendment to PROJECT_CONTRACT and Approval validation. Recorded current-eligibility evidence/check time, activation and exactly one hour of local approval; unknown remains unknown, never unlimited or API-key expiry. Missing/unverified eligibility and invalid windows fail closed. Legacy approval serialization/fingerprint input unchanged. Focused offline command: 18 passed in0.952s; compileall/diff checks passed.

Exactly one NVIDIA A/development-02 request returned HTTP200 and answered “Development mentor check-ins occur every Friday.” Actual cited source contains the exact policy; agent inspection found support, without official human benchmark grades or effectiveness claims. Usage353 input/345 output/698 total; client latency3982.962357ms. No B/C/retry/repair/fallback/probe. One32000-unit reservation retained; NVIDIA capacity **0 calls/0 units**. Same NVIDIA identity/ceilings and all historical Groq usage/stops preserved. Root .env unchanged. Services restarted live-disabled, FREE_ONLY=true. Local approval expires22October2026 16:24:06 IST; provider entitlement expiry remains unknown. Full A/B/C evaluation incomplete. [Actual result and exact checks](NVIDIA_BASELINE_RESULT_20261022.md).


## NVIDIA baseline activation blocked before I/O · 22 October 2026

User authorized at most one A/development-02 request conditional on existing FREE_ONLY contract permitting the recorded evidence. PROJECT_CONTRACT.md:17 explicitly requires actual free/promotional eligibility **and expiry** recorded before a provider request. Current eligibility/model/quota confirmations are accepted; entitlement expiry is explicitly unknown. A one-hour local approval cannot establish actual entitlement expiry. Therefore activation is blocked under the unchanged written contract. No approval/expiry change, reservation, provider attempt, service change or Groq-accounting mutation occurred. NVIDIA capacity remains 1 call/32000 local units; live disabled. No resolved question repeated or provider/key expiry inferred. Evidence: docs/evidence/nvidia-baseline-activation-blocked-v1.json.


## NVIDIA allowance draft prepared · 22 October 2026

Credential was not found in .env.example's available Git history (including reflog-referenced revisions) or staged version. No Git-exposure-based replacement requirement was established. Configured private NVIDIA allowance file did not exist; created a mode0600 draft with a new stable NVIDIA-only identity, max_calls=1 and max_reserved_tokens=32000. Published API capability flags are documented; actual account eligibility/access/quota remain pending. confirmed_free_promotional=false and deliberately inactive expiry prevent authorization. No ledger/history/stop edits or provider calls. Awaiting only operator account confirmation and entitlement validity before finalizing approval; live remains disabled.


## NVIDIA credential loading fixed · 22 October 2026

Demonstrated cause: NVIDIA_API_KEY was nonblank in root .env.example but blank in the application's sole loaded file, /home/sigmoid/Ai-Security-Poc/.env. One definition in each file, no dotenv syntax errors or BOM; no inherited NVIDIA key override. Moved the exact same credential into root .env and cleared the example value without displaying it; other private settings preserved. Restarted only project services. Actual backend readiness now confirms credential_present=true, source_is_root_env=true and credential_matches_root_env=true; FREE_ONLY=true and live=false. No provider calls, allowance edits or runtime-code changes. Existing ledger/private allowances/frozen data/historical experiments passed unchanged-file verification. Account eligibility/quota, NVIDIA approval and separate bounded execution authorization remain pending. Evidence: docs/evidence/nvidia-credential-loading-fix-v1.json.


Current selection: `LLM_BACKEND=nvidia_nim` (the prepared adapter's identifier, used for both hosted and self-hosted NVIDIA APIs), `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`, `NVIDIA_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b`, `NVIDIA_AUTH=bearer`. Root nonsecret settings were set to the requested values; NVIDIA_API_KEY was never displayed, copied from elsewhere or overwritten. FREE_ONLY=true and LIVE_LLM_ENABLED=false.

The actual project launcher/backend/frontend were restarted, preserving inherited environment precedence. A local `/ready` check inside the running backend confirmed provider/base/model/auth matches, 30-second timeout, free-only true, live false. Credential presence **false**; source `repository-root .env: NVIDIA_API_KEY`; effective/root equality true because both are blank. Equality is not credential presence or validity. Root .env has one NVIDIA_API_KEY definition, parsed as blank. Save a nonempty key locally on that existing line (not .env.example), then restart the project services. No key material or credential hashes were recorded.

## Offline hosted checks

Reused the prepared adapter and the prior 30-test offline evidence. Added only hosted-specific checks: final A-mode wire payload to the exact HTTPS host/path and exact model; a single dummy Bearer header, no cookie/query; unchanged strict Answer schema, temperature1/max_tokens700/nonstreaming/timeout30; hosted HTTP/no-auth configuration rejection; HTTP202 stops without polling or another request. Redirects/retries/fallback remain disabled. The shared adapter now treats only HTTP200 as a completed response. TLS verification and organizational proxy behavior remain enabled.

```bash
LLM_BACKEND=groq PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_nvidia_nim.NIMTests.test_hosted_baseline_wire_success backend.tests.test_nvidia_nim.NIMTests.test_hosted_pending_stops_without_polling backend.tests.test_nvidia_nim.NIMTests.test_hosted_requires_https_bearer -v > docs/evidence/nvidia-hosted-offline-v1.log 2>&1
```

Exit0: **3 passed in 0.274s**, no failures/skips. All provider transport is synthetic with sockets blocked, dummy credentials and temporary ledgers. The process-only Groq selection isolates legacy defaults; hosted test settings explicitly select NVIDIA. compileall and git diff --check passed. Runtime safe booleans are saved in `docs/evidence/nvidia-hosted-runtime-v1.json`.

Published model API reference: https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer . It documents the endpoint/model, Bearer authentication, Chat Completions, json_schema response_format, temperature1 and max_tokens700 within accepted ranges. It does not establish this account's entitlement, key validity, remaining quota, latency or compatibility of the exact application schema in a real invocation. No hosted API call/model listing/quota/auth probe was sent.

## Exact outstanding prerequisites for one bounded A/development-02 test

1. **Credential:** a nonempty NVIDIA_API_KEY in root .env loaded by the running backend. Do not paste the key in chat or a template. Offline presence/equality cannot prove provider acceptance.
2. **Account facts, personally confirmed:** the key belongs to the intended NVIDIA hosted account/project and is enabled for this exact model; actual free/promotional/trial entitlement and its expiry/restrictions for this request; remaining request/token credits or quotas, rate limits and competing traffic sufficient for the exact payload plus up to700 generated tokens. A published free endpoint, a key or a local budget is not proof of account eligibility/headroom. Do not enable billing or assume paid capacity.
3. **API capabilities:** confirm access to Chat Completions with this model and strict JSON-schema output for the actual Answer contract, temperature1, nonstreaming output cap700 and existing 30-second timeout. Published support and synthetic checks are available; exact live acceptance and semantics remain unverified. Default model reasoning behavior has not been changed or tested live; output/time caps are bounds, not a guarantee of a complete answer.
4. **Separate truthful NVIDIA approval:** configured `NVIDIA_ALLOWANCE_FILE=.private/nvidia_allowance.json` currently does not exist. Do not reuse the exhausted Groq approval or alter its history. The existing Approval schema needs the following operator-confirmed values:

| Field | Required for the proposed new NVIDIA-only allowance |
|---|---|
| provider | `nvidia_nim` (adapter identifier, even for hosted API) |
| allowance_id | A stable distinct NVIDIA allowance identity; preserve any existing NVIDIA usage tied to that ID |
| approved_model | `nvidia/nemotron-3.5-super-vl-120b-a12b` |
| confirmed_free_promotional | true only after actual account eligibility is confirmed |
| expires_at | Explicit unexpired timezone-aware UTC timestamp within the entitlement period |
| max_calls | 1 for a new unused bounded allowance; existing consumption under an established ID must be counted |
| max_reserved_tokens | 32000 for that new unused allowance; conservative local units, not measured/billed tokens |
| chat_completions_supported | true only after capability/access confirmation |
| structured_outputs_supported | true only after strict JSON-schema capability/access confirmation |
| max_output_tokens_supported | true only after cap700 compatibility confirmation |
| confirmation_note | At least10 characters, recording actual operator confirmation time/basis and one-request scope; never credentials |

No approval/identity/budget or free-access claims were created by this configuration task. The current client still checks expiry/provider/model/capabilities and cumulative accounting before reservation and request. Any applicable stop flag blocks the proposed run; do not clear it.

5. **Separate execution authorization:** after the above prerequisites are met, explicitly authorize one A/development-02 attempt, one32000-unit reservation, existing model/settings, zero retries/repairs/probes/fallback, process-only live enablement and a fresh exclusive run ID. No test is authorized here. Do not invoke the old Groq-specific one-shot scripts for NVIDIA; a reviewed NVIDIA-scoped bound must retain the existing gate and evidence. Stop after the attempt, retain its reservation on failure and return live-disabled; no ongoing UI calls.

## Preservation and readiness verdict

A before/after inventory check found no changes to the ledger, existing private allowances, frozen benchmark/revision files or stored experiment artifacts. Groq usage remains retained/exhausted. No uploads/index/dataset maintenance occurred. Private .env/allowance paths remain Git-ignored. No new reservations, allowance edits or expiry updates. Current configuration is installed and observed in the running backend, but **not ready for a live test** because the credential is blank, NVIDIA approval is absent and account facts/execution authorization are pending. Phase6/full A/B/C evaluation remain incomplete.
