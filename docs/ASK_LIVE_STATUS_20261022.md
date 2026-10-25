# Local Ask enabled · 22 October 2026

User explicitly authorized ongoing user-initiated Ask submissions within the **existing** NVIDIA allowance only, with no additional budget and no automatic provider test. Actual backend started with `run_app.py --live-answers`; interface: http://127.0.0.1:8501 . Local `/ready` confirms live=true, provider=nvidia_nim, free_only=true, credential present/root-source/root-match=true. Frontend health passed. No query/answer endpoint or provider endpoint was invoked to verify readiness.

Remaining capacity at enablement: **3 provider-call reservations / 96000 local units**. Existing totals remain5 calls/160000 units, with2 calls/64000 units retained. Same identity, private approval, all call history and stop flags. Local approval remains **2026-10-22 11:00:02.736257 UTC = 16:30:02.736257 IST**. It was unexpired, so no expiry/activation/evidence field changed. Provider entitlement expiry remains unknown, not unlimited, and accepted eligibility evidence remains recorded. Root .env stays live-disabled by default; only the explicitly selected actual backend process is live.

## Recorded HTTP500 recovery

The previous smoke finalized its first A call as failed and stopped. HTTP500 did not set an allowance quota stop. Read-only checks found no applicable stop flag or ambiguous outstanding request requiring recovery. This user authorization permits fresh manually submitted Ask requests; it does not resume the interrupted smoke, retry that request automatically, erase its reservation or claim the provider recovered. No ledger reset or stop clearing was required/performed. The provider's HTTP500 may recur and has not been tested again. Quota/rate stops must never be bypassed.

## Gate and launcher behavior

The added launcher option `--live-answers` enables only the backend child, leaves FREE_ONLY=true and frontend live flag=false, and sends no automatic query. Default `.venv/bin/python run_app.py` still starts live-disabled. Explicit launch:

```bash
.venv/bin/python run_app.py --live-answers
```

Existing `assistant.respond` reserves1 call/32000 units for A or B, and2 calls/64000 units atomically for C before screening. If C cannot fund both calls, no screening request is sent. Both C calls pass `live.call`'s expiry/approval/reservation checks; no unscreened fallback. Expired/insufficient allowance blocks provider use. Failed or unused reservations remain retained. Existing NVIDIA model, temperature1, output700, timeout30s, zero retries/redirects/polling/fallback remain unchanged. No prompts, retrieval, uploads, indexes, defenses or experiments were modified.

Two focused launcher environment tests passed (exit0,0.000s), verifying disabled default, explicit backend-only enablement, immutable parent environment and preserved provider settings/FREE_ONLY. Log: docs/evidence/ask-live-launcher-tests-v1.log. Reused completed allowance, C route, expiry and SDK checks. compileall/git diff --check passed. Read-only before/after comparison confirms all calls and allowance rows unchanged across service restart/health verification. No provider calls, new reservations, model probes or benchmark runs.

Necessary restart: the supervisor manages backend/frontend together and exits its sibling when a child stops; only that identified project service pair was restarted. No unrelated service was touched. Authorization and safe readiness records: docs/evidence/ask-live-authorization-v1.json and ask-live-readiness-v1.json.

Ask is enabled locally; no local blocker currently prevents a permitted submission. Provider availability is unverified after the500, and remaining budget/expiry can block subsequent submissions. A/B/C integration remains incomplete; no defense-effectiveness or benchmark claim.
