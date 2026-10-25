# Bounded A-only authentication diagnostic · 22 October 2026

Run `phase6-auth-A-20261022-v1` is a separate diagnostic linked to the original failed `phase6-benign-20261021-v1`. Exactly one provider-boundary attempt ran through `assistant.respond` → the existing Groq client and allowance gate, for configuration A / development-02. Existing model `openai/gpt-oss-20b`, temperature 1.0, output cap 700, seed 5 metadata, 30-second timeout and zero retries/repairs/fallbacks were preserved. Seed remains experiment metadata as in the original runner; no new provider seed parameter was introduced. The existing RequestPacer was reused; its first call requires no intentional wait. B/C and the full smoke were not invoked.

Result: HTTP **401**, `AuthenticationError`, application category `authentication_or_permission`; application status `llm_error`. Client latency **888.108447 ms**; boundary latency **904.002759 ms**. No response/answer/cited references returned; provider usage and request ID are unavailable/null. The exact account/credential cause remains unresolved. Initial source evidence and provenance remain in diagnostics; there is no answer for semantic review. Full A/B/C integration remains incomplete.

Before execution the selected allowance had one failed record retaining 32000 units, leaving 3 calls / 96000 units. It had no applicable stop flag or quota failure. A historical stopped record belongs to another allowance and was preserved. Under backend.lock, only the expired approval's expiry was refreshed to one hour after the update, with the bounded authorization recorded separately. Identity, ceilings, capability/free claims and confirmation note were preserved. Local renewal does not establish fresh provider quota.

Exactly one NEW 32000-unit reservation was made (`4e154c12-ec65-4f8c-ace2-f6c768908038`) and retained after failure. The selected allowance now has 2 failed call records / 64000 units retained, leaving **2 calls / 64000 units**. Previous failed attempts and all stop flags/history remain. No refunds, reused reservations, resets or budget increases.

The original runner requires paired A/B/C, so a smoke-scoped wrapper was added in `backend/scripts/phase6_auth_attempt.py`. It reuses the completed offline findings and frozen readiness evidence, checks current application source/prompt/dataset identity, uses a new exclusive result directory and holds the backend lock. Two offline tests passed: actual assistant success/failure paths each enter the mocked boundary once, and attempted second reservation/boundary entries are blocked. Network was forbidden in those tests. No repeated credential/endpoint investigation was performed.

Final checks: effective live disabled, FREE_ONLY=true, root .env hash unchanged, backend lock released. Credential and authorization headers were never logged. No service restart or later phase was performed.

Artifacts:

- `docs/evidence/phase6-auth-A-authorization-v1.json`: bounded authorization, expiry update and before/after accounting.
- `docs/evidence/phase6-auth-A-bound-tests-v1.log`: offline bound verification.
- `backend/data/runtime/experiments/phase6-auth-A-20261022-v1/integration-diagnostics.json`: original-run link, initial source references, safe error/status, usage nulls, latency and reservation accounting.
- `backend/data/runtime/experiments/phase6-auth-A-20261022-v1/case-development-02-A-0.json`: actual application result.
