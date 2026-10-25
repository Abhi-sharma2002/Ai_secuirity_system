# AI Security Document Lab

A local document assistant for studying prompt injection with three configurations:
**A: grounded baseline**, **B: instruction separation**, and **C: screening followed
by instruction separation**. FastAPI serves the backend; Streamlit provides the UI.
The temporary active answering provider is OpenRouter's fixed Nemotron free route;
Azure transport and configuration remain available. Embeddings run locally on CPU.

## Standing project scope

[Current temporary provider policy](docs/PROJECT_SCOPE.md): answer/screen calls use
only the fixed OpenRouter Nemotron `:free` route, with Azure retained but inactive.
Embeddings, retrieval, storage, evaluation, charts and UI stay local. No paid model,
provider fallback or Azure resource/account change is part of this switch. Provider
calls require explicit bounded authorization;
`--paid-azure-test` is retired and rejected. See [AGENTS.md](AGENTS.md).

## Start the application

For a new local environment, install the application and test dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

Create `.env` from `.env.example` only if `.env` does not already exist. Keep
existing private settings. Activate the environment before running the tests:

```bash
source .venv/bin/activate
cd backend
python -m pytest tests -q
```

From the repository root, using the existing environment:

```bash
.venv/bin/python run_app.py --check
.venv/bin/python run_app.py
```

Open **http://127.0.0.1:8501**. This command starts both services with live
answering disabled. Document tools and genuine saved results remain available.
Ask requires a valid, separately scoped provider allowance with remaining capacity;
the launcher never grants capacity or clears stop flags. Do not reuse expired or
stopped evaluation receipts for interactive answering.

Use the single root [.env.example](.env.example) as the configuration reference.
Keep real credentials only in the private root `.env`. Existing settings, uploads,
SQLite, Chroma, frozen datasets, reviews and accounting are preserved.

See [OpenRouter temporary setup](docs/OPENROUTER.md) for the fixed free route,
private key setup, one-hour local allowance and provider limitations.

## Understand the implementation

- [Folder map and complete runtime flow](docs/architecture/RUNTIME_MAP.md)
- [Installation, commands and panel explanation](docs/guides/LOCAL_APPLICATION.md)
- [Refactor verification and exact path mapping](docs/architecture/REFACTOR_20261024.md)
- [Existing installation details](docs/INSTALLATION.md)
- [Technical report](docs/REPORT.md)
- [Reviewed partial benign results: six cases](docs/panel/partial-benign-six-cases-v1/INDEX.md)
- [Panel walkthrough](docs/PANEL_WALKTHROUGH.md)
- [Tests by responsibility](backend/tests/README.md)

Active defenses are under `backend/app/defenses/`; `rag/assistant.py` coordinates
them. Historical fixed-context defenses and the retired NVIDIA adapter are under
`backend/app/legacy/`. Historical provider commands are under
`backend/scripts/history/`. They are separate from the active website runtime.

## Evidence and current limits

Successful Azure baseline/integration evidence and 18 approved benign records
are retained. Attack effectiveness and final evaluation remain incomplete.
The latest separate development-08 screening probe returned complete JSON but
failed source-ID validation; see its [actual result](docs/DEVELOPMENT08_SCREENING_PROBE_RESULT_20261023.md).
Provider rejection and operational errors are not application-defense successes.
The final dataset is exposed, not an untouched holdout.

This organization refactor made no Azure requests, activated no allowance and
restarted no services. It changes implementation fingerprints; future evaluation
must bind the new identity, while historical run identities remain unchanged.
The pre-refactor README and source snapshot are retained under
`docs/history/refactor_20261024/`. Dated records describe their own execution time.
