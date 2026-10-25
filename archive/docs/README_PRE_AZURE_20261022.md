# AI Security Document Lab

A local fictional employee-document assistant with real parsing, CPU embeddings, persistent Chroma retrieval, SQLite document versions, FastAPI and a Streamlit UI. A/B/C share one Q&A service: ordinary grounding, instruction separation, and an LLM screener followed by separation.

Live Groq is disabled by default. The application never invents an answer when access is missing. Real local ingestion/retrieval can run without an API key. Live generation, live screening and final security measurements require operator-confirmed free/promotional allowance and model capabilities. No paid use is enabled automatically.

## Current NVIDIA hosted setup

The subsequent authorized A/B/C smoke stopped on its first A request with NVIDIA HTTP500; B/C were not attempted. Three calls/96000 local units remain, but live mode is disabled and no rerun is authorized. See [paired smoke result](docs/NVIDIA_ABC_SMOKE_RESULT_20261022.md).

The authorized single NVIDIA A-only baseline succeeded (HTTP200), with a source-supported Friday answer. Its one-call allowance is now exhausted; live answering remains disabled. Provider entitlement expiry is recorded as unknown under the amended one-hour local-approval rule. See [actual baseline result](docs/NVIDIA_BASELINE_RESULT_20261022.md). Earlier missing-credential/allowance findings below are historical and superseded by this result.

The prepared NVIDIA adapter now selects `https://integrate.api.nvidia.com/v1` and `nvidia/nemotron-3.5-super-vl-120b-a12b` with Bearer authentication. The internal backend identifier remains `nvidia_nim`. Live calls remain disabled. The key-loading issue was fixed by moving the unchanged credential from .env.example into root .env; the restarted backend confirms credential presence. The NVIDIA allowance file is still absent; credential acceptance and account eligibility/quota remain unverified. See [hosted configuration and exact remaining prerequisites](docs/NVIDIA_HOSTED_CONFIGURATION.md) before any bounded test. The self-hosted section below is an alternative, not the selected endpoint.

## Self-hosted NVIDIA NIM setup (pending server details)

A self-hosted NIM server is separate from NVIDIA's hosted API service. Set these **locally in the root `.env`**, using your server's exact deployed model and API base:

```dotenv
LLM_BACKEND=nvidia_nim
NVIDIA_BASE_URL=
NVIDIA_MODEL=
NVIDIA_API_KEY=
NVIDIA_AUTH=bearer
NVIDIA_ALLOWANCE_FILE=.private/nvidia_allowance.json
NVIDIA_CA_FILE=
FREE_ONLY=true
LIVE_LLM_ENABLED=false
```

Supply an HTTP(S) base ending in `/v1`, without credentials or query strings. Use `NVIDIA_AUTH=none` only if your server does not require inference authentication; otherwise enter its Bearer key privately. A hosted NVIDIA key does not configure a self-hosted server. `NVIDIA_CA_FILE` optionally names a trusted custom CA; TLS verification is never disabled. Network proxy controls remain in effect.

The adapter sends a single nonstreaming Chat Completions request with strict JSON schema, temperature 1.0, max output 700, timeout 30 seconds and no retries, redirects or provider fallback. Exact schema/model support must be verified for your deployment using its documented contract; the adapter does not silently downgrade output constraints. See [NVIDIA NIM API reference](https://docs.nvidia.com/nim/large-language-models/latest/reference/api-reference.html).

A separately confirmed NVIDIA allowance is required before live use. Existing exhausted Groq approvals cannot authorize NVIDIA, and no new approval or capacity has been fabricated. Current setup is offline-prepared: enter the server URL/model and confirm auth requirements before restarting the project services. The running services have not been switched as part of this preparation. `.env.example` contains placeholders only; never put a real key in it. Use the launcher below after completing configuration; it continues to force live calls off.

## Current Ask status

**Current blocker: allowance exhausted (0 calls/0 units).** The backend remains live-configured, while the updated UI correctly disables unfunded submissions and shows remaining capacity. The last user request timed out; usage is unknown and its reservation is retained. Additional bounded capacity requires explicit authorization. No automatic test call was made. [Current readiness repair](docs/ASK_BUDGET_READINESS_FIX_20261022.md). Earlier capacity figures below are historical.

The latest saved Ask failures returned no usable final text after using700 output tokens. The configured Nemotron model now explicitly uses `reasoning_effort=none`; the cap remains700 and no retry is added. One call/32000 local units remain after the two user submissions. Refresh shows the saved failure until you explicitly submit again; no automatic retry occurs. [Response-content repair](docs/NVIDIA_ANSWER_CONTENT_FIX_20261022.md).

Ask is enabled at **http://127.0.0.1:8501** using the configured NVIDIA hosted model. At enablement3 calls/96000 local units remained; approval expires22October2026 at16:30:02.736257 IST. No automatic provider test was made. Each submission remains gated; C requires2 calls up front. The earlier HTTP500 may recur; A/B/C integration is incomplete. [Exact status and recovery](docs/ASK_LIVE_STATUS_20261022.md).

## Run the app only

From this folder:

```bash
.venv/bin/python run_app.py
```

Open **http://127.0.0.1:8501**. This starts the backend and the full interface together: Documents, Ask / compare, and Saved experiments. Under Ask / compare, choose defense A (baseline), B (instruction separation), or C (screening + separation). B is selected by default. Ctrl+C stops both child services. Existing experiment tools and history remain available separately; they are not needed to run the app.

The launcher keeps live answering disabled by default. Explicitly run `.venv/bin/python run_app.py --live-answers` to enable the backend only within its existing valid allowance; this sends no test query. Document uploads, indexing and local search remain available; generated answers are blocked until provider access is resolved. This is a local, single-user app setup; it does not add public hosting or user authentication.

Optional local dependency check: `.venv/bin/python run_app.py --check`.

## Quick setup in this workspace

You only need the root `.env` for backend configuration. `.env.example` is a template, not the file the application reads. If `.env` already exists, keep it; do not overwrite your saved key with the template.

The key and model must be on separate lines:

```dotenv
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=openai/gpt-oss-20b
FREE_ONLY=true
LIVE_LLM_ENABLED=false
FREE_ALLOWANCE_FILE=.private/free_allowance.json
```

The startup commands below run document upload and local search without Groq calls. Live answers also require this lab's existing allowance gate. Experiment scripts, benchmark preparation and verification commands are not startup steps.

Current saved Groq status: two requests returned HTTP 401; live answering remains blocked. The extra lab checks did not generate those provider responses. Correcting this example or removing old scripts does not establish that Groq accepts the configured credential. Keep live mode disabled until a separate live attempt is authorized. Historical evidence is retained under `docs/` and the runtime experiment directory.

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

Backend configuration lives at **`/home/sigmoid/Ai-Security-Poc/.env`**, beside this README. It already exists locally; preserve its configured values. On a fresh checkout, copy the root [.env.example](.env.example) to `.env` only if `.env` does not already exist. Enter your API key locally on the `GROQ_API_KEY=` line and your verified accessible model on `GROQ_MODEL=`. Do not paste either into the frontend or commit secret files.

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

See the [contract](docs/PROJECT_CONTRACT.md), [acceptance matrix](docs/ACCEPTANCE_MATRIX.md), [implementation status](docs/IMPLEMENTATION_STATUS.md), [report](docs/REPORT.md), and [demo](docs/DEMO.md). Older fake/provider-neutral LLM helpers now live outside the application in `backend/legacy_llm/` solely for regression compatibility. `backend/app/llm/` contains the active client and its diagnostic helper. Earlier lowercase-project modules/fixtures/tests remain for regression context; their old phase names and fake-client scripts are historical development tools, not the revision-2 application or evidence.

## Groq setup status

The active provider is Groq through `ChatGroq` in `backend/app/llm/client.py`. The installed integration is pinned to langchain-groq 1.1.3 and groq 0.37.1. Strict JSON-schema response format is explicitly bound on every generation and screening request; the assistant independently validates responses and source IDs. Trusted application system/developer rules share a system message; questions and document content remain user messages. A/B/C share temperature 1.0, output cap 700 and zero retries. No provider/model fallback is enabled.

Keep the Groq key only in the ignored root `.env`; never paste it into chat or the frontend. The configured model is `openai/gpt-oss-20b`. Existing credentials, private allowance and historical results are preserved.

`FREE_ONLY=true` and `LIVE_LLM_ENABLED=false` remain the defaults. Both recorded Phase 6 Groq attempts returned HTTP 401; provider access remains unresolved and Phase 6 is incomplete. The private allowance is a local budget/approval record, not provider authentication or proof of fresh quota. Do not recreate it to bypass retained usage or stop flags. See [the saved attempt report](docs/PHASE6_AUTH_ATTEMPT_20261022.md).

Offline checks cover configuration precedence, disabled generation/screening/evaluation, call reservations, wrapped quota errors and the installed SDK request/response path with mocked transport and network forbidden. Live Groq generation and screening remain unverified. Earlier Gemini development evidence records one failed attempt; it is historical and does not establish Groq access or security results.

See [Groq structured outputs](https://console.groq.com/docs/structured-outputs) and [account rate limits](https://console.groq.com/docs/rate-limits). Restart the backend after changing `.env` using the commands above.
