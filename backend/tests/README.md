# Active test scope

Run from the repository root with `PYTHONPATH=backend` and the existing `.venv`.
Generic tests must not select a real provider from private `.env` settings, require
a retired provider SDK, read a real approval or write production registry state.
`offline_settings.py` supplies public dummy settings for generic evaluator,
exposure, planning and readiness fixtures. Environment tests explicitly supply
dummy settings to subprocesses at each tested working directory. Adapter boundary
tests use either a labeled adapter double or in-memory HTTP with sockets blocked.

- `test_runtime_v2.LiveClientContractTests`: shared message/usage/error/reservation
  behavior using an explicit adapter double, independent of any SDK implementation.
- `test_provider_endpoint`, `test_provider_diagnostics`, `test_answer_content`:
  current Azure boundary, redaction and content validation with synthetic HTTP.
- `test_azure_openai`: Azure-only wire/gate/baseline/paired contract. Synthetic
  response fixtures establish control flow, never classification/effectiveness.
- Generic evaluator/metric/review fixtures remain synthetic and disposable.
  Real-response human review remains pending.
- Historical helper tests (`test_phase6_preparation`, `test_phase6_auth_attempt`,
  `test_nvidia_abc_smoke`)
  exercise explicitly doubled historical utilities. They are not current Azure
  readiness evidence and their helpers must not be used to authorize live Azure.

Exact pre-9A sources for retired Groq/NIM runtime assertions are preserved under
`backend/historical_tests/pre_9a_20261023/`, with SHA-256 inventory. That snapshot
includes six complete original modules, including the old mixed runtime module.
It is outside active test discovery and may require the historical implementation;
it is not a passing current test suite and is not silently skipped as success.

Coverage migration:

| Old assertion | Current evidence |
|---|---|
| Groq request assembly/auth/redirect/401/retained reservation | `test_provider_endpoint`, `test_azure_openai` |
| SDK role placement, usage and wrapped quota stop | `LiveClientContractTests`, Azure Phase7 wire tests |
| Missing Groq SDK | Retired requirement; current dependency check is in `run_app.py --check` |
| NIM hosted/self-hosted auth and endpoint acceptance | Retired feature; Azure tests reject old routing and cross-provider approvals |
| NIM screen/answer routing and retained evidence | Current Azure Phase8 screening and Azure A/B/C wire tests |
| Missing final text, finish reason, usage, safe UI error | `test_answer_content` |
| Provider-specific reasoning default | Azure ignores retired reasoning setting; fixed request settings tested |

For Phase10 use the real cached embedding model, disposable documents, separate
temporary SQLite/raw/Chroma storage and disabled live calls. Unit embedding doubles
do not substitute for that current-version local workflow verification.

Current runtime completion checks are in `test_runtime_completion`:blank-answer
rejection,Azure-only read-only preflight,old-receipt stop preservation,retired
credential/destination rejection and no assigned preflight identity.
`smoke_preflight.local_status` tests now use explicit Azure approval fixtures.
Optional retired SDK pins are in `backend/historical_tests/requirements.txt`,
not active backend requirements. Historical test snapshots are not rewritten.

## Organization revision: 24 October 2026

Tests are now grouped under `api/`, `core/`, `defenses/`, `evaluation/`,
`ingestion/`, `legacy/`, `llm/`, `rag/`, `storage/` and `organization/`.
The filenames mentioned above retain their basenames within these groups.
`offline_settings.py` remains the shared public fixture at the tests root.

Examples:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.llm.test_azure_openai -v
PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.defenses.test_phase8_screening -v
PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.evaluation.test_phase9_evaluation -v
```

Grouped discovery, when warranted: `-m unittest discover -s backend/tests -t . -v`.
Exact historical test commands in frozen records retain their old paths; the
organization mapping supplies current equivalents. The legacy E037 rubric stays
versioned and its tests are at `evaluation/test_legacy_e037_rubric.py`.

Two older defense-wire fixtures now supply an isolated approval file needed by
the existing interactive-scope check. Their assertions use the already-approved
omitted temperature/seed settings. No production policy was changed for testing.
The environment test checks disabled-live precedence instead of the superseded
blanket FREE_ONLY rejection. Attack-case review remains pending; the six benign
cases already have actual human approvals preserved in the existing records.
