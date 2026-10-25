# Replaced-key single attempt · 22 October 2026

Run `groq-restore-development-02-A-20261022-v2` used exactly one A/development-02 generation through the current assistant/client/allowance gate. The user reported replacing the root .env key. Only the project launcher/backend/frontend were restarted. The restarted backend reported source `repository-root .env: GROQ_API_KEY`, effective/root match true, and live disabled. The diagnostic reused that backend's inherited environment and enabled live only inside its bounded call. The key was never displayed or changed by the agent.

Result: HTTP **401**, SDK `AuthenticationError`, provider type `invalid_request_error`, code `invalid_api_key`, sanitized message **Invalid API Key**. Request ID: `req_01m5hdvxa3emfbqj5mnt984pgy`. Start: 2026-10-22 09:07:54.704547 UTC; finish: 09:07:55.838640 UTC. Client latency 1096.367556 ms. No answer or references returned; provider usage unavailable/null. Semantic evidence support cannot be assessed.

Actual runtime diagnostics: destination `https://api.groq.com/openai/v1/chat/completions`; credential source root .env; credential_matches_root_env=true; single_bearer_matches_effective_credential=true. These establish what was sent for this attempt, not why Groq considers it invalid. No additional investigation or provider request followed. An account-side cause beyond the explicit invalid-key rejection is not established.

Model `openai/gpt-oss-20b`, temperature 1.0, output cap 700, timeout 30 seconds, zero retries/repairs/fallbacks and existing pacing were preserved. No applicable stop flag prevented execution, and no stop flag was cleared. Approval was still unexpired, so **no expiry update occurred**; expiry remains 2026-10-22 10:01:52.879199 UTC (15:31:52 IST).

Before: 3 calls / 96000 local units retained, 1 call / 32000 units remaining. After the single new failed reservation: 4 calls / 128000 units retained, **0 calls / 0 units remaining**. No refund, ceiling change, identity reset or history deletion. Both original Phase 6 artifacts and the previous restoration attempt remain unchanged. Root .env remained unchanged during this execution.

Final backend readiness and frontend health checks passed with live disabled and root/effective match true. Ongoing UI answering was not enabled. No automatic UI generation check occurred. Phase 6 and full A/B/C evaluation remain incomplete.

Actual application result and sanitized diagnostics: `backend/data/runtime/experiments/groq-restore-development-02-A-20261022-v2/`. No runtime code changes or repeated offline tests were needed; the previously verified exclusive runner and one-attempt bounds were reused under a fresh run ID. The next action is account-side verification of the active key with Groq support, using the sanitized request ID/timestamp/error above; never send the key. No further provider request can run within the exhausted existing allowance.
