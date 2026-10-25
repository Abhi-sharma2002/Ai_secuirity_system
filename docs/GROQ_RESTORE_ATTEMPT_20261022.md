# Groq answering restoration attempt · 22 October 2026

The one authorized provider attempt failed. Groq explicitly returned HTTP 401, `invalid_request_error`, code `invalid_api_key`, sanitized message **Invalid API Key**. This establishes provider rejection of the credential submitted on this attempt. It does not determine why that credential is invalid (for example revoked, copied incorrectly or from a different provider/account). No answer was returned, and usage remains unavailable rather than zero. No retry, fallback, repair or extra provider probe occurred. Ask cannot currently generate real answers; live remains disabled.

Provider request ID: `req_01m5hdgvmaesnb977xzs8qjd94`.

Run: `groq-restore-development-02-A-20261022-v1`, linked to both earlier failed Phase 6 attempts. Application start 2026-10-22 09:01:52.895787 UTC; transport entry 09:01:53.521031 UTC; completion 09:01:53.671176 UTC. Client latency 769.321643 ms. Actual effective destination captured in the request hook: `https://api.groq.com/openai/v1/chat/completions`.

## Running-process findings

Identified launcher PID 31730 with backend 31733 and frontend 31734, all in this workspace. The actual process startup environments contained no GROQ_API_KEY, no endpoint-override variables and no HTTP(S)/ALL/NO_PROXY variables (including lowercase names). No proxy values were printed or organizational controls disabled. Root .env has no duplicate GROQ_API_KEY/GROQ_MODEL definitions. The launcher forces LIVE_LLM_ENABLED=false/FREE_ONLY=true and otherwise preserves inherited environment precedence. That explains disabled UI generation; it does not explain Groq's authentication rejection.

Restarted only the identified project services using the original launcher's environment. The new backend's own `/ready` response reported source `repository-root .env: GROQ_API_KEY` and `credential_matches_root_env=true`. This was an observation inside the running application, not a separate shell's inference. The diagnostic child reused the actual backend's startup environment, enabled live only around its bounded call, and independently captured the same source/match boolean. The final transport hook reported `single_bearer_matches_effective_credential=true`. Together these equality observations establish root credential → effective settings → supplied client/wire credential equality for this new attempt. No historical provenance claim is added to the previous attempts.

No custom authentication headers or alternate auth parameter are passed by the active client. Actual installed SDK tests with conflicting dummy environment overrides confirmed exactly one Bearer header with the explicit dummy key, no cookie/alternate auth/query, correct host/path and identical existing model/settings. No custom proxy transport is configured; the client uses Groq's DefaultHttpxClient with metadata hooks, retains its environment-proxy support and existing timeout. No localhost shell test was represented as a historical network request.

## Focused changes and offline verification

- `/ready` now returns only credential-source name and root-match boolean, permitting safe actual-process inspection.
- The live request hook records only a boolean confirming one Bearer header matches the effective credential.
- Groq's default transport follows redirects. Explicitly disabled redirect following so a redirected response cannot cause another request. A synthetic 307 test confirms one request and no forwarded authorization. This was a bounded-request safeguard, not the cause of the observed 401.
- Added a separate exclusive-use diagnostic runner `backend/scripts/groq_restore_attempt.py`, reusing the existing single-attempt wrapper and frozen development-02 context. Existing model `openai/gpt-oss-20b`, temperature 1.0, output cap 700, timeout 30s, seed-5 experiment metadata, RequestPacer and zero retries/repairs remain.

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_groq_endpoint backend.tests.test_provider_diagnostics -v > docs/evidence/groq-restore-offline-v1.log 2>&1
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_phase6_auth_attempt -v > docs/evidence/groq-restore-bound-v1.log 2>&1
```

Final outcomes: 9 passed in 1.802s and 2 passed in 0.008s respectively, both exit 0. All provider transport is synthetic and sockets blocked; temporary ledgers only. compileall and git diff --check passed. The earlier 8-test run before adding redirect coverage also passed; it overlaps and is not an additional distinct count.

## Accounting and final service state

Before: 2 failed calls / 64000 retained local units; 2 calls / 64000 units remaining. No applicable selected-allowance stop flag. The unrelated historical stopped allowance was untouched. Approval was expired; only its expiry was renewed under the backend lock, preserving identity, ceilings, claims and history. Renewal is not provider quota confirmation.

One NEW reservation was consumed and retained: now 3 failed calls / 96000 units retained, **1 call / 32000 units remaining**. Approval expires **2026-10-22 10:01:52.879199 UTC (15:31:52 IST)**. No refunds, reset or ceiling increase. Root .env unchanged; both earlier result folders preserved. New diagnostics and actual application result are under `backend/data/runtime/experiments/groq-restore-development-02-A-20261022-v1/`.

Services restarted through run_app.py with the same inherited environment and live disabled. Final local readiness and frontend health checks passed; credential root-match remained true. Those local checks made no provider call. Root .env and private allowance remain Git-ignored. Uploads, Chroma, frozen datasets and existing uncommitted work were preserved; only the authorized allowance expiry and new usage records changed private runtime state. Full A/B/C evaluation and Phase 6 integration remain incomplete.

## Required local action

Create or copy an active API key for the intended Groq account/project in Groq Console. In `/home/sigmoid/Ai-Security-Poc/.env`, replace only the value of the existing `GROQ_API_KEY=` line. Keep GROQ_MODEL unchanged and keep LIVE_LLM_ENABLED=false. Do not put the key in .env.example, chat, source code or the frontend. Restart the project services after saving so the running process loads it. Do not increase the allowance or erase usage. Any further verification requires a new explicit authorization and unexpired approval; no second request was made here. If a key confirmed active in Groq Console is still rejected, give Groq support the request ID, UTC timestamp, model, endpoint and sanitized error above, without the key.
