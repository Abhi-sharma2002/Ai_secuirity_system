# AI Security Document Lab

A local RAG assistant that compares **A: grounded baseline**, **B: instruction
separation**, and **C: screening plus output checks** against prompt injection.
FastAPI and Streamlit serve the app; parsing, CPU embeddings, retrieval, Chroma,
SQLite, evaluation and charts run locally. Current v3 live evaluation is deferred.

For a detailed explanation of ingestion, retrieval, A/B/C defenses, display
masking and evaluation limits, read the
[end-to-end defense guide](docs/END_TO_END_DEFENSE_GUIDE.md).

## Setup

Use Python with the pinned dependencies and preserve an existing private `.env`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
test -f .env || cp .env.example .env
```

Keep API keys out of source control. Model weights must already be cached for
offline indexing. On a new machine, download the pinned local embedding weights
once before using offline mode:

```bash
PYTHONPATH=backend .venv/bin/python -c "from app.rag.embeddings import get_embedding_model; get_embedding_model()"
```

This downloads CPU model weights; it makes no answering/screening request.
See [the project scope](AGENTS.md) and [Azure trial setup](docs/AZURE_TRIAL_SETUP.md).

## Run the app

```bash
.venv/bin/python run_app.py --check
.venv/bin/python run_app.py
```

Open **http://127.0.0.1:8501**. Upload a fictional TXT/MD, text PDF or DOCX, then
use **Ask / compare → Local-only** to search evidence. Live answering starts
disabled. Existing expired/stopped authorizations do not become valid on restart.
The selected runtime is the user's existing Azure gpt-5-mini trial deployment.
OpenRouter is stopped and its active environment key is blank. Enter Azure's
actual endpoint, key and deployment name locally; a key alone does not enable
calls or renew historical authorization.

The authorized Azure synthetic A/B/C check has now passed and the current local
services have bounded manual answering enabled. See the
[live verification record](docs/AZURE_TRIAL_VERIFICATION.md) for actual results,
remaining allocation and expiry-removal amendment. The default launcher command above remains
local-only; `--live-answers` requires a currently valid authorization.

Open **Metrics / evaluation** to inspect the v3 comparison, formulas, A/B/C
numerators and denominators, coverage, errors, human-review status and all six
charts. Case details and masked table/report downloads are available there.
This is a local read-only view; missing results show N/A and stale charts are
withheld. Historical runs remain separate under **Saved experiments**.
See the [metrics dashboard guide](docs/METRICS_DASHBOARD.md) for the inspection
workflow and verification details.

## Run the evaluation

```bash
.venv/bin/python backend/scripts/validate_v3.py
.venv/bin/python backend/scripts/run_eval.py --plan --limit 3
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python backend/scripts/run_eval.py --prepare-only
.venv/bin/python backend/scripts/make_report.py
.venv/bin/python backend/scripts/review_eval.py --prepare
.venv/bin/python backend/scripts/write_report.py
.venv/bin/python backend/scripts/write_report.py --check
```

These commands work locally without provider calls. The runner prepares an
isolated index; reporting represents missing observations as **N/A**. The
original benchmark is preserved; active v3 fixtures are in `backend/benchmark_v3/`.
The CSV core supports immediate saves and resume with frozen evidence. The live
`--limit 3`, `--all` and `--resume` execution commands currently refuse execution:
provider evaluation remains disabled by the explicit local-only scope. The
provider boundary must be deliberately revised under a later explicit benchmark
authorization; setting an environment variable alone does not authorize a run.
No delayed run or automatic authorization renewal is scheduled.

The user approved the Azure compatibility amendment: `eval_config.yaml` now
selects Azure `gpt-5-mini` and omits temperature (`null`) identically for A/B/C.
Local index preparation creates a fresh configuration identity and archives the
previous local generation. Historical results remain separate. Live benchmark
execution still requires explicit authorization and verified deployment limits.

After authorized real evaluation, follow [human review](docs/HUMAN_REVIEW.md) to
decide ambiguous responses and fill the seeded quality sample, then regenerate
the metrics and written report. A future live run must verify current limits
and fit its explicitly authorized request scope. Errors and provider filters
remain errors, never blocked attacks.

Offline checks:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_simple_*.py backend/tests/evaluation/test_run_eval.py -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/verify_v3_local.py --output /tmp/v3-local-check.json
```

The integration check starts isolated loopback services, uses the cached CPU
model and actual UI, and stops its own processes. Choose a new output filename
for each run. Synthetic unit fixtures stay in temporary directories.

## Results and report

<!-- v3-summary:start -->
| Configuration | Recorded | ASR | Benign success | Quality |
| --- | --- | --- | --- | --- |
| A | 0 | N/A | N/A | N/A |
| B | 0 | N/A | N/A | N/A |
| C | 0 | N/A | N/A | N/A |
<!-- v3-summary:end -->

The results table is generated by `backend/scripts/update_readme_results.py`
from `results/summary.csv`. N/A means unavailable, not a defense win.
See [the current report](docs/REPORT.md), [metric formulas](docs/METRICS_EXPLAINED.md),
[case table](results/test_cases.csv), [raw summary](results/summary.csv), and
[remaining deliverables](docs/COMPLETION_STATUS.md).

The requested live attack demonstration and video are pending real evaluation;
there is no recording link yet. [Demo procedure](docs/DEMO.md).
Historical source, documents and results remain readable under [archive/](archive/README.md).
