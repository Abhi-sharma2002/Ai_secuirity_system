**Where to see the project's evaluation information**

Open the local app and choose **Metrics / evaluation** in the sidebar. This
page reads the current v3 CSV records and human labels. Historical experiment
formats remain under **Saved experiments** and are not pooled into this model's
comparison. Ordinary interactive Ask answers do not automatically acquire
attack/task/quality grades: those need an evaluation case and scoring criteria.

The page includes:

- A/B/C values for every PDF metric, with numerators and denominators for rates.
- Counts of recorded, expected, missing, error and pending-review rows, human
  quality labels, and per-mode timing/review coverage.
- Formula definitions, whether higher/lower is better and interpretation notes.
- The shared public evaluation configuration and dataset size.
- All six PDF charts and their PNG downloads.
- Saved tables, human-review forms, the written report and metrics explainer as
  masked text downloads.
- Case/configuration filters for errors, pending review and eligible rows.
- Recorded questions, answers, citations, expected evidence, screening reasons,
  kept/removed IDs and optional original retrieval inspection.

**What each displayed metric means**

Eligible semantic-rate rows exclude operational errors and unresolved human
review. Each metric additionally uses its applicable population. Missing or
inapplicable values stay unavailable; a real observed zero rate is different.

| Display | Population and interpretation |
| --- | --- |
| Attack success — all | Successful attacks / eligible adversarial rows |
| Attack success — exposed | Successful exposed attacks / eligible exposed adversarial rows; exposure includes a direct question attack |
| Direct attack success | Successful direct attacks / eligible direct adversarial rows |
| Indirect attack success | Successful indirect attacks / eligible indirect adversarial rows |
| Benign task success | Passed benign tasks / eligible benign rows |
| C false positives — flag/block | Flagged/blocked benign C rows / eligible benign C rows |
| C false positives — answer removed | Benign C rows losing answer evidence / eligible benign C rows |
| C false positives — combined | Benign C rows with either kind / eligible benign C rows; overlaps count once |
| Citation accuracy | Applicable eligible rows citing an expected evidence document / applicable eligible rows |
| Mean latency | Mean recorded route timing, including timed errors |
| p95 latency | Nearest-rank percentile of recorded route timings |
| Human answer quality | Mean explicit quality_0_4 over the actual human sample, with its sample size |
| Human agreement | Sample rows where all applicable automated judgments were marked correct / checked rows |

The page explains the quality rubric. Factual citation support still needs
human reading: a citation ID/document match does not establish every claim's
semantic correctness. Shared benchmark retrieval is frozen outside the timed
per-mode route, so benchmark latency is not identical to a fresh interactive
request including retrieval. Local reservation units are not latency, measured
token consumption or a semantic grade.

**Evidence and review integrity**

`simple_dashboard.snapshot()` reuses the real record reader, human-label
validation and metric aggregator in `simple_reporting.py`. It does not maintain
another independent scoring formula or request a model judgment. Configuration
and available run identity are checked; incompatible/synthetic run metadata is
rejected. Missing records produce no invented rows.

Saved charts are withheld if their record hash or saved summary no longer
matches the current computed summary. The live table still computes from the
current valid records. Regenerate charts after changing records or human labels.
Artifact routes use fixed filenames and reject missing files and symlinks;
there is no arbitrary local-file download path.

C's evaluation output filters now retain the pre-filter answer and citation
IDs in `screen_reasons.output_candidate`. The pure scorer inspects both that
candidate and the final visible answer for required ambiguity review. A
marker-plus-warning or true-plus-false candidate is not automatically graded
as a failed attack just because an output filter withheld it. Such rows retain
`needs_review=true` and unresolved attack/task grades until a human decides.
Provider errors still take precedence and remain excluded from semantic rates.

Case inspection/downloads use masked copies. Original record/evidence bytes
remain local and unchanged; use them for exact synthetic-marker review. The
Ask workspace continues to show its answer and citation locations without
automatically appending this separate inspection data.

**Refreshing and reporting**

The **Refresh local metrics** button rereads files. It does not run evaluation,
write human labels, renew provider access or make an inference request.

The local commands remain:

```bash
.venv/bin/python backend/scripts/make_report.py
.venv/bin/python backend/scripts/review_eval.py --prepare
.venv/bin/python backend/scripts/write_report.py
.venv/bin/python backend/scripts/write_report.py --check
```

Apply human decisions only after a human fills the prepared decision form, as
explained in [HUMAN_REVIEW.md](HUMAN_REVIEW.md). Neither this dashboard nor these
reporting commands enables the currently prohibited provider benchmark.

The read-only backend endpoints are `/evaluation-v3`,
`/evaluation-v3/artifacts/{artifact}` and
`/evaluation-v3/evidence/{case_id}`. The frontend renders through FastAPI rather
than opening backend storage directly.

**Actual verification**

Related regression command from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s .venv/bin/python -m pytest backend/tests/evaluation/test_simple_*.py backend/tests/evaluation/test_run_eval.py backend/tests/evaluation/test_result_artifacts.py backend/tests/frontend -q -o faulthandler_timeout=40 > /tmp/ai-security-metrics-regression-final.txt 2>&1
```

Actual output:

```text
156 passed, 18 subtests passed in 30.31s
```

The first restricted-environment run stalled in the in-process HTTP test. It
was stopped and rerun with localhost socket access; provider execution stayed
disabled. Tests use temporary synthetic fixtures, not measured model outcomes.

A separate real reporting call generated all six PNGs from the current local
records into a fresh temporary directory. The existing `results/` file hashes
were preserved. Actual status was `no_records`: recorded `0`, expected/missing
`141`, human quality labels `0`, and no provider requests.

An actual Streamlit AppTest against the running localhost backend verified:

```json
{
  "metrics_visible": 13,
  "chart_files_loaded": [
    "asr.png", "asr_by_category.png", "benign_success.png",
    "false_positive.png", "latency.png", "tradeoff.png"
  ],
  "local_get_requests_only": true,
  "missing_observations_shown_as_na": true,
  "results_bytes_preserved": true,
  "provider_inference_requests": 0,
  "app_exceptions": 0
}
```

Both owned local services returned HTTP 200 after reloading. The allowance
receipt was unchanged and live execution remained disabled. There are still no
live v3 observations or actual human sample labels; this verification establishes
the calculation/display pipeline, not measured defense effectiveness.

Full regression command, from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 240s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-metrics-full-suite.txt 2>&1
```

Actual output, exit one:

```text
17 failed, 546 passed, 1 skipped, 1 warning, 531 subtests passed in 126.21s (0:02:06)
```

The failure identifiers match the original list in STEP_1_SETUP.md; there are
no new failure identifiers. The unrelated baseline failures were not reclassified
as passing. The existing `write_report.py --check` also returned `verified`,
with `comparison_and_human_sample_complete=false` and no provider requests,
confirming the current report/explainer still match the CSV summary.
