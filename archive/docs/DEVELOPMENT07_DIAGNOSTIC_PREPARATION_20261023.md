## Current instruction: reuse existing bounded mechanism

The proposed new trial billing gate and duplicate approval steps below are
superseded. See [final consolidated preparation](DIAGNOSTIC_TRIAL_WORKFLOW_20261023.md).
No new billing gate is built. Independent preparation is complete; only available
account evidence cannot yet establish trial-only execution. The diagnostic stays
inactive. Local code does not verify credits or enforce Azure billing.

# One diagnostic attempt prepared — NOT AUTHORIZED / NOT ACTIVE

Scope: development-07 A only, at most1 provider attempt/32000 NEW local units.
No execution, activation, stop recovery or allowance selection occurred.
Private inactive receipt: `.private/azure_development07_diagnostic_receipt.DRAFT.json`.
It is deliberately a draft envelope, not an executable Approval receipt. The live
gate still selects its existing configuration and cannot consume this draft.
Paid authorization, recovery acknowledgement, activated_at and expires_at are
unset; a proposed one-hour window is a future decision, not an active expiry.

## Demonstrated diagnostic gap and smallest fix

Previous diagnostics retained safe top-level code/type and a512character bounded
sanitized message, but never inspected `param` or `innererror`. This prevented
capture of a provider-supplied recognized parameter or nested policy category.
Only `backend/app/llm/diagnostics.py` production code was changed:

- Recognized unsupported_parameter/unsupported_value/invalid_parameter codes.
- Fixed parameter-name allowlist (temperature,seed,max_completion_tokens,
  max_tokens,response_format,messages,model,top_p,reasoning_effort,stream).
- Fixed recognized inner error codes; no nested object dump.
- Fixed content-filter category allowlist, retaining only categories explicitly
  marked `filtered is True`. Strings/numbers masquerading as booleans are ignored.
- Constant `diagnostic_detail_policy` explicitly states that unknown metadata is
  omitted and sanitized explanations may be insufficient.

Existing HTTP status/provider request-ID capture is unchanged. No headers or raw
request/response bodies are persisted. Parsed error bodies can exist transiently
in the exception while extracting allowed fields. Unknown code/type/parameter
strings are redacted, unknown categories omitted, messages remain sanitized and
bounded512characters. Category metadata missing is null, not evidence of no filter.
This is intentionally incomplete information, not a promise to preserve every
provider explanation. No cause is inferred from status or message fragments.

The original development-07 code/message was already redacted; no new code can
recover it. The retained historical provider request ID remains
f04f2d2a-f9b5-4e9c-9e9c-9e80295db608. Historical failure and reviewed results remain
unchanged. Known content-filter code support added in prior work was reused.

## Frozen input and identity

The draft links the original failed call and stopped development allowance,
original case response binding, frozen retrieval path/hash and question hash.
No request dump is created; the future attempt reconstructs A's existing messages
from that exact saved question and ordered original evidence. No attack text,
prompt, schema, model, generation parameter or provider safety control changed.
Model/version remain gpt-5-mini-1 / gpt-5-mini2025-08-07. Temperature/provider seed
not sent, cap700, timeout30, zero retries/fallbacks. One diagnostic means no
additional model probe or follow-up even if the response succeeds.

The prepared full source/dependency/retrieval identity and hash are in the private
draft. Diagnostics source changed, so full execution identity necessarily differs
from the historical development run. The API presentation source also changed
in earlier work. This is a linked diagnostic population, not a resumed controlled
run, not replacement for original07A, and not a security result to pool silently.
Revalidate exact current model/schema/prompt/evidence/source hashes immediately
before any later authorized activation. If a scoped execution gate is added,
rebind the source identity after focused verification.

## Required recovery before any execution

1. Obtain explicit new authorization accepting paid Azure use for one diagnostic
   request/32000 NEW units and a chosen activation window (proposed1hour).
2. Obtain explicit acknowledgement that the prior HTTP400 stop remains unresolved
   and permission for this narrowly linked recovery attempt. The draft records
   neither acknowledgement nor authorization on the user's behalf.
3. Add/verify the single-case/mode diagnostic policy before making the draft an
   executable receipt. Current DevelopmentScope permits the twelve-case run,
   not a one-case diagnostic. A generic receipt or new unlinked grant must not
   bypass the old stop. Narrow recovery must reference and acknowledge that
   exact parent event, reject unrelated stops, and preserve its immutable flag.
4. Activate the separate stable diagnostic identity once, using exclusive-create
   checks and cumulative ledger history; bind expiry from actual activation.
   Never replenish/refund/extend the original development allowance. Its unspent
   23calls/736000units remain stopped and unavailable for this attempt.
5. Issue exactly one A request from frozen input. Persist only allowed diagnostics
   and ordinary validated result/evidence records; no credentials, headers or raw
   dumps. Stop after the one result/error, no retry, and finish live-disabled.

These steps are prerequisites, not actions performed by this task. No final,
remaining-development, screening or judge request is part of this preparation.

## Focused offline verification

```
PYTHONPATH=backend LIVE_LLM_ENABLED=false .venv/bin/python -B -m unittest backend.tests.test_diagnostic_preparation backend.tests.test_saved_400_diagnosis backend.tests.test_provider_diagnostics -q
```
12 tests PASS(0.820s). Three new socket-blocked adapter tests prove one synthetic
transport invocation each and capture of status/request ID, recognized code/type/
parameter, known inner code/category, bounded credential-sanitized explanation,
and explicit uncertainty for unknown/nonexistent details. Prior status/ID/non-JSON
and safe-diagnostics checks reused. No provider/ledger activity in tests.

Preparation checks saved in `docs/evidence/development07-diagnostic-preparation-v1.json`:
inactive draft, no activation/expiry, no allocated capacity; existing receipt
bytes unchanged, historical run artifacts unchanged, accounting unchanged,
original stop preserved, live disabled. Files saved mode0600 for the private draft.
No production service restart or live enabling. `git diff --check` passed.

## Superseding trial-only consolidation

See [consolidated workflow](DIAGNOSTIC_TRIAL_WORKFLOW_20261023.md). The user has
conditionally authorized the prepared diagnostic against valid trial credits
only, explicitly excluding out-of-pocket use. Repeating a paid-use or generic
execution approval question is obsolete. Known subscription/deployment/input
facts are reused. Unknown remaining credit availability and spending-limit state
remain unknown. The inactive draft requires a verified narrow trial-only gate;
original stop/history remain intact. Earlier paid-use checklist items above are
historical and superseded for this diagnostic, not permission to spend.
