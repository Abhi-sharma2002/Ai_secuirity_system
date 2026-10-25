# Paid Azure development evaluation — stopped partial execution

**Actual outcome: stopped_no_retry. Human semantic review pending.**
Run:`azure-development-12cases-v1`. User authorized twelve development cases,
paired A/B/C once,36 records, maximum48 attempts/1536000 additional local units,
exactly two hours from activation. No final set, retries, repairs, reruns or
extra API probes were performed. No defense-effectiveness claim is justified.

## Completion coverage and error

| Mode | Scheduled | Recorded | Operationally completed | Errors | Not executed | Actual provider attempts |
|---|---:|---:|---:|---:|---:|---:|
|A|12|7|6|1|5|7|
|B|12|6|6|0|6|6|
|C|12|6|6|0|6|12|
|Total|36|19|18|1|17|25|

Development-01 through06 each produced A/B/C answered records. The first
adversarial case, development-07 A, returned HTTP400 and status llm_error,
coarse category `invalid_request_or_unsupported_parameters`. Execution stopped
immediately; development-07 C/B and all development-08–12 were not executed.
There were24 HTTP200 calls and1 HTTP400. No adversarial configuration completed.

The failed call's provider code is redacted and the saved message is heavily
redacted. These diagnostics do **not** establish a specific unsupported setting,
content-filter decision, model resistance or screening success. Key/root equality
was true for the failed call. Parameters were unchanged from the successful
integration and prior development calls. No diagnostic request or parameter
change was used to investigate; no repair or retry followed the error.

## Actual usage, timing and reservations

| Mode | Known reported input | Known reported output | Calls with unknown usage |
|---|---:|---:|---:|
|A|2410|2237|1|
|B|2878|3084|0|
|C|5558|3687|0|
|Total|10846|9008|1|

**19854 known reported tokens**, with one failed-call usage unknown. This is not
a complete billed-token total or a monetary charge estimate. Local reservation
usage is independently **800000 units/25 call records**, without refunds.
Route timing, per-stage provider timing, original/retained evidence, citations,
answers, screening decisions and settings are saved for each recorded response.
Mean observed route times:A6.078s (includes the failed route), B6.130s, C9.413s.
This population has serial zero-added-delay pacing, distinct from integration's
65second pacing. Activation-to-finish elapsed6m59.087s includes local setup/
validation/model/retrieval/report overhead, not just provider time.

## Approval and final state

Separate stable allowance ID:`azure-development-12cases-20261023-v1`.
Activation:2026-10-23T08:42:45.285799+00:00.
Expiry:2026-10-23T10:42:45.285799+00:00
(**23 October2026,16:12:45.285799 IST**), exactly two hours.
Receipt:`.private/azure_development_allowance_v1.json` (no key stored there).
Remaining **23 calls/736000 units**, but **stopped=true**: unusable, not permission
to resume. No expiry extension, duplicate grant, refund or old accounting reset.
Original integration receipt and every prior allowance/call row were verified
unchanged. Actual Azure quota remains unknown and paid coverage is not promotional.

App restarted with default live-disabled launch, using the development receipt
only for process-local capacity display. Root.env was not edited. Health-only
verification: backend/frontend healthy, configured_live_enabled=false, Ask=false,
all modes unavailable, development allowance stopped with the above remaining
capacity. URL:http://127.0.0.1:8501. No model request followed the failure.

## Bound identity, code and verification

[Scoped policy](AZURE_DEVELOPMENT_POLICY_20261023.md) adds a DevelopmentScope
receipt binding and exact schedule/identity validation to the existing evaluator
and provider gate. Only client.py/experiment.py changed from the prepared runtime
identity; dependency/retrieval, model, prompts, schemas, dataset/index, annotations,
approved semantic rules and scoring hash were verified unchanged. The actual
rebound identity and approval window were saved **before generation** in
`activation-and-binding.json`; the evaluator saved its complete specification
and frozen per-case initial retrieval. A/B/C share each original initial hit set;
retained chunks remain original objects/provenance. Temperature/provider seed
not sent, cap700, timeout30, strict schemas, zero retries/fallbacks retained.

Execution command:
```
PYTHONPATH=backend .venv/bin/python -B -m scripts.run_authorized_development
```
The command is **single-use**: do not run it again. It rejects existing receipt/run
artifacts and cumulative history. No final-set generation occurred.

Focused offline tests before activation:29 test executions PASS(4.715s), with
fixture-class discovery repeats; final3 scoped tests PASS(0.193s), including
wrong-run/final/seed/identity rejection before generation and duplicate reservation
blocking. Four changed/new Python AST checks and diff check passed. No full audit,
ingestion verification or full regression repeated.

Read-only post-run check:
```
PYTHONPATH=backend LIVE_LLM_ENABLED=false .venv/bin/python -B docs/evidence/check_development_execution_v1.py
```
**19/19 checks passed**; saved output in `docs/evidence/development-execution-checks-v1.json`.
Checks cover schedule/identity/window, development-only scope, exact coverage,
HTTP statuses, known/unknown usage, unchanged settings, frozen initial/original
retained evidence, untouched null judgments, complete review-template coverage,
N/A semantic metrics, consumed/stopped capacity, historical preservation, seven
charts/exports, exposed-final disclosure and live-disabled exit.
No post-error code repair or rerun occurred.

## Review exports and next step

Actual run directory:
`backend/data/runtime/experiments/azure-development-12cases-v1/`.
Important files: `operational-summary.json`, `activation-and-binding.json`,
`experiment.json`,19 case JSONs,7 frozen retrieval JSONs, `review-packets.json`,
`review-template.json`, `records.csv/json`, `comparison.csv/json`, `summary.json`,
`REPORT.md`, seven metric charts and sanitized evaluator/export console logs.
The exports are marked as saved records with incomplete human review, not synthetic
fixtures or validated security findings. No original fixtures or past results
were overwritten or regraded.

All19 human review entries remain blank; all per-mode ASR/task-success
eligible human-reviewed denominators are0 and quality graded counts0. Rates
remain N/A, not0% success. Eighteen completed responses can be reviewed for task,
source support and quality. The HTTP400 record must retain null semantic grades
and an operational-error explanation; it is not an attack resistance observation.
Missing17 records stay missing, not failed or successful defenses.

Next: the user reviews the19-entry `review-template.json` beside actual
`review-packets.json`, preserving record bindings and approved human-v1/P12 rules.
Import only genuine reviewed judgments with reviewer identity and notes via the
existing review workflow. Do not populate grades automatically. Any investigation
requiring a provider request, repair or new execution requires new scope; this
stopped run must not be resumed, repaired, deleted or silently replaced.
Final data remains **exposed**, not an untouched holdout. Final evaluation,
reviewed security comparisons, conclusions and final demo remain pending.
