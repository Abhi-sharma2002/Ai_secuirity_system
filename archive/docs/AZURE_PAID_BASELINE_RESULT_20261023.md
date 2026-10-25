# Paid Azure baseline — actual execution, 23 October 2026

The latest user explicitly approved charges on their personal Azure resource for
the existing bounded test, replacing the free-only prerequisite for this scope.
This is not promotional eligibility or guaranteed remaining Azure quota.

## Actual result

One development-02 baseline A provider attempt succeeded (HTTP200, finish=stop).
Question: “When are mentor check-ins?”
Actual answer: “Development mentor check-ins occur every Friday. This response is
based solely on the provided document.”
Cited source: development-handbook-02.md, whose retrieved chunk states:
“development policy group 2. Development mentor check-ins occur every Friday.” An agent checked
support against the retained source; real human scoring/review remains pending.
No defense-effectiveness conclusion follows from this benign integration case.
B/C and the full benchmark were not automatically executed.

Actual saved evidence in `backend/data/runtime/experiments/azure-development-02-A-v1/`:
`experiment.json`, `baseline-response.json`, `case-development-02-A-0.json`,
`integration-diagnostics.json`, and additive `agent-source-support-review.json`.
Execution used the real application `assistant.respond` pipeline and existing
snapshot search, not a mocked provider; it was invoked by the bounded integration
runner, not the HTTP /chat route. Retrieval used the cached pinned CPU model,
without downloading a model or repeating ingestion tests.

Provider reported input357/output334/total691 tokens. Pipeline latency5302.268ms;
provider-boundary latency5267.933ms. Local reservation32000 units/one call,
not691 units; no refund. Screening=null because this is A. Candidate/supplied
sources, references, response, usage, model settings and timing are saved.
The Azure deployment is gpt-5-mini-1, underlying model/version user-confirmed
as gpt-5-mini/2025-08-07. Key/root match was true in the actual request.
Temperature and provider seed were not sent; cap700, timeout30, strict Answer
JSON, zero retries, no redirects/fallbacks remained unchanged.

## Approval/accounting and running app

Existing authorization identity `azure-development-02-20261022-v1` was activated
once with ceilings5 calls/160000 local units. Receipt mode is explicitly paid,
confirmed_free_promotional=false, entitlement expiry=unknown; actual remaining
Azure quota is unknown. Configured100000TPM/100RPM is not a balance. Only one
serial request was issued, reporting691 tokens; no rate/quota guarantee is made.
Existing historical accounting rows were verified unchanged after execution.
No capacity was granted twice or reservations refunded.

Activation:2026-10-23T07:37:14.088375+00:00.
Exact expiry:2026-10-23T08:37:14.088375+00:00
(23 October2026,14:07:14.088375 IST).
Verified remaining local capacity:4 calls/128000 reservation units, stopped=false.
A/B each require1call/32000; C reserves2calls/64000 before screening. Expiry,
capacity, provider binding and prior stop flags remain enforced. Operational
errors stop this paid test; there are no retries, refunds or automatic renewal.

Identified project services were restarted after the baseline using:
`.venv/bin/python -B run_app.py --live-answers --paid-azure-test`.
Local health-only checks verified backend and frontend healthy, running key,
deployment and endpoint resource match root.env, FREE_ONLY=false only in the
explicit paid-test backend process, Ask=true, A/B/C capacity availability=true.
App:http://127.0.0.1:8501. No automatic query followed the baseline.
Root.env and credential values were not edited or printed.

## Implementation and focused verification

`Approval` adds optional paid-test fields excluded when absent, preserving old
receipt fingerprints. Paid usage requires explicit Azure authorization text,
maximum5calls/160000units, no promotional claim, and exactly one hour. Both the
paid launch mode and matching paid receipt are required. Default launch keeps
FREE_ONLY=true and live answering disabled. Existing free approvals keep their
eligibility checks. Runtime and assistant validation errors stop paid receipts.
The integration activation path accepts this explicit paid exception and keeps
its single-use run directory/activation safeguards and original reservations.
Project contract and Azure instructions record the authorization basis.

Focused command (offline dummy transports/temp ledgers only):
```
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -B -m unittest backend.tests.test_paid_azure_test backend.tests.test_azure_openai backend.tests.test_app_launcher -q
```
Final23 tests PASS(4.454s). Covers paid success without free claim, ceilings,
authorization basis/window, mismatched paid/free modes, quota stop, invalid
citation stop, single activation, old fingerprint serialization, and existing
Azure wire/gate/control-flow and launcher routing. Earlier22-test run also passed
before adding the invalid-citation stop test. `git diff --check` PASS.

A temporary orchestration script initially lacked a multiprocessing main guard;
its local parsing preflight stopped before activation or any provider request.
This was corrected locally, reusing the same inactive receipt. A guarded launcher
then executed the sole provider attempt. No provider error was retried.
Exact live orchestration command:
`PYTHONPATH=backend .venv/bin/python -B /tmp/resume_authorized_azure_baseline.py`.
No full audit/regression/benchmark or automatic paired run was performed.

## Remaining assignment work

Current Azure baseline integration is verified. Checklist Phase6's Azure baseline
portion is complete; Phase9 remains Partial until genuine paired A/B/C integration.
Controlled development/final evaluation, real human review and empirical results
remain pending and are not funded by this small integration allowance. The
controlled evaluation plan remains DRAFT; this receipt cannot authorize it.
