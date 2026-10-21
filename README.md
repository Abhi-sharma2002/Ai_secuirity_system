# AI Security Document Lab

A local fictional employee-document assistant with real parsing, CPU embeddings, persistent Chroma retrieval, SQLite document versions, FastAPI and a Streamlit UI. A/B/C share one Q&A service: ordinary grounding, instruction separation, and an LLM screener followed by separation.

Live Groq is disabled by default. The application never invents an answer when access is missing. Real local ingestion/retrieval can run without an API key. Live generation, live screening and final security measurements require operator-confirmed free/promotional allowance and model capabilities. No paid use is enabled automatically.

## Start on this workspace

The `.venv` here is configured and has passed `pip check`. It reuses existing libraries from the preserved lowercase project because disk space is limited. This shortcut is specific to this host. From `/home/sigmoid/Ai-Security-Poc`:

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal:

```bash
.venv/bin/streamlit run frontend/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501`; API documentation is at `http://127.0.0.1:8000/docs`. Upload a TXT/MD/PDF/DOCX, inspect readiness/warnings, and use search diagnostics or ask a question. Missing allowance produces an actionable `live_blocked` status. This is local single-user software without authentication; do not expose either port publicly.

## Reproducible setup on another Linux machine

Use Python 3.12 and adequate disk space. Create a virtual environment, install a CPU PyTorch wheel first, then the pinned application requirements:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip check
```

The exact fresh-machine procedure has not been executed on another host; see [verification](docs/VERIFICATION.md). Initial use may download the pinned Hugging Face embedding model. Imports and offline unit discovery do not download it. Retain the model cache to use `HF_HUB_OFFLINE=1` afterwards. No Groq key is required for this download or local search.

Backend configuration lives at **`/home/sigmoid/Ai-Security-Poc/.env`**, beside this README. It has been created locally with a privately supplied key and an empty `GROQ_MODEL`. On a fresh checkout, copy the root [.env.example](.env.example) to `.env` only if `.env` does not already exist. Enter your API key locally on the `GROQ_API_KEY=` line and your verified accessible model on `GROQ_MODEL=`. Do not paste either into the frontend or commit secret files.

The backend automatically loads this fixed file before configuration is read, including evaluator/maintenance commands and startup from `backend/`. Existing process environment variables (even empty ones) take precedence over `.env`. Relative data/index/allowance paths resolve from the repository root. No `--env-file` argument or shell export is needed. Restart backend processes after changes. The Streamlit frontend does not load this file; its optional `BACKEND_URL` is supplied separately through its process environment.

Keep `FREE_ONLY=true` and `LIVE_LLM_ENABLED=false`. The shared live gate validates booleans, requires nonempty credentials/model when explicitly enabled, and still requires the existing account-confirmed free/promotional allowance file with valid expiry, model constraints, capabilities and conservative budgets. A key does not establish free credit, and local flags/counters cannot guarantee zero provider charges. See [handover](docs/HANDOVER.md) before enabling any live use.

The root example lists the actual application path, embedding, chunk/retrieval, upload/evidence limits, log level and shared LLM request timeout settings. SQLite and saved experiments use `APP_DATA_DIRECTORY` (results are in its `experiments/` subdirectory); no separate results-path alias is needed. Parser deadline (20 seconds), batch/storage/page/expansion limits, output-token cap and zero Groq retries remain existing fixed code limits, not unused `.env` entries. External LangChain tracing and Chroma telemetry remain disabled by application code. Archived regression helpers under `backend/legacy_llm/` and their older offline scripts also read `LLM_PROVIDER`, `LLM_MODEL`, `LLM_CONNECT_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`, `LLM_BACKOFF_INITIAL_SECONDS`, `LLM_MAX_RETRY_DELAY_SECONDS`, `LLM_CREDENTIAL_ENV` and optional `LLM_PRICING_VERSION` / `LLM_INPUT_USD_PER_MILLION` / `LLM_OUTPUT_USD_PER_MILLION`; they are not alternate Groq configuration and are intentionally omitted from the application template. `RAG_COLLECTION` and `RUN_MODEL_TESTS` are opt-in diagnostics/test controls, not startup requirements.

From the backend directory, the equivalent startup is `../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`.

## Verification and experiments

From the repository root:

```bash
PYTHONPATH=backend ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=backend HF_HUB_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python backend/scripts/local_smoke.py
PYTHONPATH=backend .venv/bin/python backend/scripts/ui_smoke.py
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment validate
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment plan --split final
```

Stop the backend before benchmark preparation, execution or maintenance; the same one-process file lock protects these commands. Preparation performs actual local parsing/embedding/indexing only:

```bash
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment prepare
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment plan --split development --case-id development-01
```

No live execution happens without `--execute`, enabled live settings and a valid allowance. Full final runs require 30 cases × A/B/C = 90 attempts and at most 120 API calls per repetition with this no-retry design. Conservative reservation is 3,840,000 tokens per final repetition; this is an upper-bound safeguard, not a billed-token estimate. Use one development case first; do not buy credits automatically.

```bash
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment run --run-id dev-001 --case-id development-01 --execute
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment run --run-id final-paired-001 --split final --protocol paired --execute
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment run --run-id final-e2e-001 --split final --protocol end_to_end --execute
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment review --run-id dev-001 --judgments /absolute/path/reviews.json
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment report --run-id dev-001
```

Repeating the same run command resumes completed records; changed experiment settings are refused. Ambiguous interrupted attempts remain preserved, never silently retried. Human review is required for semantic attack/task grading; no keyword-based ASR is presented as truth. Saved reports/CSV/charts come only from actual run records. Synthetic inputs and test doubles are not empirical outcomes.

## Supported behavior and limits

- TXT/MD: bounded UTF-8, BOM removal/newline normalization, no executable rendering. PDF: page text, encrypted/corrupt rejection, no OCR. Empty/image-only PDF needs OCR; partial text requires explicit persistent acceptance. DOCX: ordered paragraphs/tables and headers/footers, bounded package expansion; embedded objects/revisions/macros are rejected where detected.
- UUIDs are independent of ordinary filenames, including Unicode. Same ready bytes deduplicate within playground; same name with different bytes is a new document unless explicitly replacing by ID/version. Failed replacement preserves active evidence. New retrieval excludes deleted/replaced versions.
- Parser subprocesses have parent-enforced deadlines and Linux resource bounds. These checks do not certify malware safety or complete extraction of every Office/PDF feature.
- Playground and frozen benchmark versions are separate. Gold facts/attack labels never enter runtime source metadata/prompts. Metadata hashes and citation IDs establish traceability, not truth or security.
- Source/model text is rendered as plain text. No autonomous tools, URL ingestion, arbitrary host paths, external tracing or hidden provider fallback.

See the [contract](docs/PROJECT_CONTRACT.md), [acceptance matrix](docs/ACCEPTANCE_MATRIX.md), [implementation status](docs/IMPLEMENTATION_STATUS.md), [report](docs/REPORT.md), and [demo](docs/DEMO.md). Older fake/provider-neutral LLM helpers now live outside the application in `backend/legacy_llm/` solely for regression compatibility. `backend/app/llm/` contains only `client.py` and `__init__.py`. Earlier lowercase-project modules/fixtures/tests remain for regression context; their old phase names and fake-client scripts are historical development tools, not the revision-2 application or evidence.

## Groq setup status

The active provider is Groq through `ChatGroq` in `backend/app/llm/client.py`. The installed integration is pinned to langchain-groq 1.1.3 and groq 0.37.1. Strict JSON-schema response format is explicitly bound on every generation and screening request; the assistant independently validates responses and source IDs. Trusted application system/developer rules share a system message; questions and document content remain user messages. A/B/C share temperature 1.0, output cap 700 and zero retries. No provider/model fallback is enabled.

The supplied Groq key is stored only in the ignored root `.env` with permissions 0600. Because it was shared in chat, revoke it and enter a replacement locally on `GROQ_API_KEY=`. Fill `GROQ_MODEL=` with an exact accessible model that supports strict structured output. It remains empty until verified. Older provider credentials and historical experiment records are preserved and are not consumed by the active client.

`FREE_ONLY=true` and `LIVE_LLM_ENABLED=false` remain enforced. No Groq API call has been made. Confirm Groq project free-plan eligibility and the selected model's RPM/TPM/daily limits before creating a private allowance file using `docs/FREE_ALLOWANCE.example.json`. It must identify `provider: "groq"`, the exact model, confirmed API capabilities, expiry and a bounded call/token budget. A previous Gemini approval cannot authorize Groq. Local flags and counters cannot guarantee zero provider charges.

Offline checks cover configuration precedence, disabled generation/screening/evaluation, call reservations, wrapped quota errors and the installed SDK request/response path with mocked transport and network forbidden. Live Groq generation and screening remain unverified. Earlier Gemini development evidence records one failed attempt; it is historical and does not establish Groq access or security results.

See [Groq structured outputs](https://console.groq.com/docs/structured-outputs) and [account rate limits](https://console.groq.com/docs/rate-limits). Restart the backend after changing `.env` using the commands above.
