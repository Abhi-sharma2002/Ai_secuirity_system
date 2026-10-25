## Current genuine development review queue

`backend/data/runtime/experiments/azure-development-12cases-v1/` contains19
response-bound review packets and19 blank review entries:18 completed benign
records and1 operational HTTP400 failure. Review actual sources/tasks/quality
for completed responses; keep semantic grades null on the error.17 scheduled
records were not executed. Do not treat them or the provider rejection as
defense successes. Preserve approved criteria and record bindings; no grade has
been invented or imported. The run is stopped and cannot be retried/resumed.
See [operational summary](AZURE_DEVELOPMENT_EXECUTION_20261023.md).

# Result export and human review

Actual Azure development-02 baseline and paired A/B/C records now exist under
`backend/data/runtime/experiments/azure-development-02-A-v1/` and
`azure-development-02-ABC-v1/`. Their human judgments remain blank; use the paired
run's `review-packets.json` and `review-template.json` for genuine human review.
Do not pool the baseline and paired populations. Presentation fixtures remain exclusively under
`docs/demo-fixtures/presentation-v2/`,outside application experiment storage.
Their charts/reports are marked **SYNTHETIC VERIFICATION ONLY**. A fixture's
boolean grade is arithmetic test data,not a real human or model finding.

## Read-only export of an actual saved run

Choose an existing source experiment directory and a **new output directory
outside that source**. This command never initializes registry storage or calls
a provider;it rejects overwrite/nested-output attempts:

```bash
PYTHONPATH=backend MPLCONFIGDIR=/tmp/results-mpl .venv/bin/python -B -m scripts.export_experiment --source /absolute/path/to/saved-run --output /absolute/path/to/new-export
```

It preserves source files,including old summaries/reports. Do not export
different provider/model/protocol/rubric populations into one merged result.

| Files | Purpose |
|---|---|
| summary.json | Frozen source specification,all-scheduled/common-paired populations,errors,unknowns,exposure,usage and metrics |
| records.json / records.csv | Raw rows and flat case outcomes with separate reported tokens,reservations and missing-usage counters |
| metrics.csv / metrics-detail.csv | Existing compact and full flattened metric exports |
| comparison.json / comparison.csv | A/B/C comparison including ASR/task/false positives/quality/latency,denominators and review/error counts |
| asr.png / exposed_asr.png | Reviewed attack outcomes with N/A for zero denominator |
| benign_task_success.png | Task preservation |
| benign_false_flags.png / benign_false_blocks.png | C-only completed-route screening rates;A/B N/A |
| quality.png / latency.png | Human quality and observed route time;failed routes with numeric time remain in latency population |
| review-packets.json | Actual response/evidence/criteria and bound coordinates |
| review-template.json | Blank judgments;requires actual reviewer and notes,never automatic approval |
| PRESENTATION.md / REPORT.md | Origin label,limitations and coverage explanation |

Empty/unreviewed/error-only runs preserve N/A rather than inventing zero rates.
Partial reports expose missing records and review coverage. Numbers shown in
fixtures do not fill the empirical section of the technical report.

## Review procedure

1. Select only a new actual experiment under its frozen identity. Read its
   source specification and record_binding;check model/settings/protocol first.
2. Use each packet to inspect original question,initial candidate evidence,
   C decision/retained evidence,actual answer and cited source support. A valid
   source ID alone is insufficient. Match precise payload spans;distinguish
   retrieval misses,full-span exposure and supplementary terminal/cue exposure.
3. Copy review-template.json to a private review file. Enter actual reviewer,
   human-v1 rubric,reasoned notes,quality0–4 and independent task/attack
   true/false/null. Benign attack grade stays null. Errors stay ungraded. Apply
   approved phase12 semantics;E037's legacy rubric is outside this dataset.
4. Record exposed/answering_exposed only after inspection. For cross_chunk rows,
   fill candidate/supplied component booleans or null. A question block has no
   answering presentation. Component labels do not change exposed-ASR arithmetic.
5. With the identified backend stopped to release its one-worker lock,import
   only into that new run through the existing evaluator review command:

```bash
PYTHONPATH=backend .venv/bin/python -B -m app.evaluation.experiment review --run-id ACTUAL_NEW_RUN_ID --judgments /absolute/path/to/human-review.json
```

ACTUAL_NEW_RUN_ID is chosen from that real run,not a new identity assigned here.
No live flags are needed. The importer rejects stale bindings,invalid grades,
duplicates and missing reviewer/notes before writing the batch. Identical imports
are no-ops;changed judgments preserve review history. Per-record writes are
atomic;the file batch is not a multi-file database transaction under crashes.
Never use this to regrade historical runs silently.

6. Re-export into a new directory. Report errors,unknowns,exposure and exact
   denominators beside rates;compare common-evaluable pairs and all-scheduled
   completion. Do not infer defense success from operational failures or low
   coverage. Keep development/final and paired/end-to-end separate.

## Reproduce presentation verification only

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/demo-mpl .venv/bin/python -B -m scripts.prepare_offline_demo --output /tmp/new-synthetic-presentation
```

The destination must not exist or be under runtime storage. This imports the
existing test_phase9_evaluation.row fixtures,not a provider. Three states:empty,
partial/unreviewed,and labeled arithmetic. Do not copy them into genuine runs.
