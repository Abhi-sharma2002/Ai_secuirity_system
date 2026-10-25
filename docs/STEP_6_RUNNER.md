# Step 6: local runner implementation; live checks pending

The user selected **“Implement and test locally only; keep provider calls
disabled”** at the request-limit preflight. This checkpoint implements and tests
the local runner mechanics. It does not complete the PDF's live evaluation
check. No attack effectiveness or model quality measurements were generated.

## Preflight and scope

The read-only script counts the frozen manifest: the full comparison has
141 case/mode rows and needs up to 188 requests. The separate new-case A checks
add 5 requests, for 193 total without retries. The initial comparison subset
needs up to 12 requests; those rows can be retained with resume.

[OpenRouter pricing](https://openrouter.ai/pricing) publishes a default limit of
50 free requests per day and 20 per minute; already-qualified accounts can have
1,000 per day. [The limits documentation](https://openrouter.ai/docs/api_reference/limits)
describes the daily reset and account limits. These were checked during the
preflight; the account's remaining allowance is unverified. No authenticated
quota probe was sent. No live call is authorized by these published limits.

The fixed route remains `nvidia/nemotron-3-ultra-550b-a55b:free` in the single
configuration. The provider boundary in `simple_runner.py` remains disabled,
and the CLI refuses execution before writing evaluation artifacts. There is no
new allowance, budget, approval, provider fallback or retry system. The PDF's
HTTP 429 retry instruction is superseded by the standing no-automatic-retries
scope. Errors must remain errors if execution is authorized separately later.

## Implemented mechanics

`backend/scripts/run_eval.py` validates the original/v3 fixture integrity and
loads the shared configuration. Its locally tested CSV core:

- Writes the exact ordered columns requested by the PDF, flushing and syncing
  each row immediately. Structured traces use JSON cells; unresolved scores
  use empty cells, preserving human review requirements.
- Keeps errors separate from defense blocks, including provider filters,
  timeouts, rate-limit errors and empty unexpected responses. Errors are never
  scored as successfully blocked attacks.
- Saves each case's retrieved evidence once and restores it for every mode,
  including a partially completed case on resume. Snapshots contain fixture
  content and provenance, without evaluator labels in the model context.
- Skips recorded rows, including error and review rows. It refuses changed
  dataset/configuration/index/implementation identities, malformed or duplicate
  rows, modified retrieval snapshots, and overwriting existing artifacts.
- Journals row starts and completion. If interrupted after starting a row but
  before saving it, resume records an error rather than replaying an uncertain
  provider call. This is crash recovery; it grants no provider capacity.
- Spaces individual screening/generation calls by at least one second after
  completion and 3.1 seconds between starts. The default provider boundary
  remains disabled. No retries or fallbacks are implemented.

The index preparer uses the existing bounded document parsers, configured
chunking, pinned CPU embedding model and Chroma. Downloads are disabled before
CLI library imports; preparation also checks that offline mode is active. It
verifies stored chunk contents and metadata before activating the index.
Each index has a separate generation directory under `.cache/evaluation_v3/`.
Rebuilding preserves the previous identity and generation under ignored
`archive/local_evaluation_stores/`. These ignored, untracked local databases
are moved with filesystem rename; tracked files are not deleted. The PDF's
instruction to delete the old evaluation store is superseded by the user's
preservation rule.

Retrieval is prepared before the individual `ask` calls, so their `latency_s`
measures the adapter/defense/model work and excludes that shared retrieval.
No real latency comparison is available from these tests.

## Executed checks

From the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=False LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/run_eval.py --plan --limit 3 > /tmp/ai-security-step6-plan.txt 2>&1
```

Exit 0. Structured output:

```json
{
  "n_cases": 47,
  "selected_cases": 3,
  "selected_records": 9,
  "selected_calls_upper_bound": 12,
  "full_records": 141,
  "full_calls_upper_bound": 188,
  "new_case_A_smoke_ids": [
    "v3-direct-01",
    "v3-direct-02",
    "v3-misinfo-01",
    "v3-misinfo-02",
    "v3-misinfo-03"
  ],
  "full_plus_smokes_calls_upper_bound": 193,
  "small_check_included_by_resume": true,
  "automatic_retries": 0,
  "published_default_daily_requests": 50,
  "published_requests_per_minute": 20,
  "account_remaining_requests": "unverified",
  "live_execution_enabled": false,
  "provider_requests_made": 0,
  "limits_reference": "https://openrouter.ai/pricing",
  "new_case_A_smokes": "pending; required before full live evaluation"
}
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=False LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/run_eval.py --prepare-only > /tmp/ai-security-step6-index.txt 2>&1
```

Exit 0. Progress and structured output:

```text
Parsed 10/45 fixture documents locally.
Parsed 20/45 fixture documents locally.
Parsed 30/45 fixture documents locally.
Parsed 40/45 fixture documents locally.
Parsed 45/45 fixture documents locally.
{
  "manifest_sha256": "be7cd6778453852d1e4539c69d558bcf82d993418f06f7c3a0e858f3599e306c",
  "config_sha256": "a266f485e1a0903b242ef651b6e986a2ae4b4b58b05c3f98d4e20e740fa58ef6",
  "embedding_sha256": "355e70c295612f1e3a005754831ebc6c4502eb923bed0f3f7887b7a55a5fbdbd",
  "generation": "342f9efdf2194bda95bdaeb222884e0b",
  "n_documents": 45,
  "n_chunks": 67,
  "provider_requests_made": 0
}
```

These two logs also contain the existing python-dotenv parse warnings for
private configuration lines and, for preparation, the cached model's weight
loading progress. Private configuration contents were not printed or changed.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=False LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_run_eval.py backend/tests/evaluation/test_simple_index.py backend/tests/evaluation/test_simple_runner.py backend/tests/evaluation/test_simple_scoring.py -q > /tmp/ai-security-step6-targeted.txt 2>&1
```

Exit 0. Complete output:

```text
.......................................................... [ 63%]
.................................                                        [100%]
91 passed, 14 subtests passed in 9.92s
```

All response doubles and their CSVs are confined to disposable test directories;
they are not evaluation observations. Tests exercise the subset and full row
counts, flush-before-next-call, resume, interruption handling, evidence reuse,
error exclusion, redaction, pacing, provenance and preservation on rebuild.

```bash
.venv/bin/python backend/scripts/validate_v3.py
```

Exit 0:

```text
OK 47
```

The actual live-check invocation was also attempted as a refusal check:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=False LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/run_eval.py --limit 3 > /tmp/ai-security-step6-live-refusal.txt 2>&1
```

Exit 1. After the existing dotenv warnings:

```text
Provider evaluation remains disabled by project scope. Use --plan or --prepare-only; no result rows were written.
```

This is the expected scope refusal, not a passed live benchmark check.
`results/records.csv` was not created. The new-case A smokes, real comparison
subset and full comparison remain pending; later metrics/report steps cannot
claim results from this local checkpoint.

## Full regression check

From `backend/` (outside the sandbox because its in-process TestClient checks
stall inside the sandbox):

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q > /tmp/ai-security-step6-pytest-final.txt 2>&1
```

Exit 1. Actual summary:

```text
17 failed, 476 passed, 1 skipped, 1 warning, 531 subtests passed in 74.90s (0:01:14)
```

Comparing the final failure identifiers with [the saved initial baseline](STEP_1_SETUP.md):

```text
{'baseline_failure_entries': 17, 'current_failure_entries': 17, 'new_failures': [], 'resolved_failures': []}
```

The focused Step 6 checks pass; the pre-existing repository failures remain.
The original benchmark, frozen v3 fixtures, interactive assistant, provider
transports and defenses have no changes in this checkpoint.
