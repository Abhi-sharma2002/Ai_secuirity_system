## Current authorized staged execution and interactive handover

[Actual current state,17phases and seven deliverables](docs/STAGED_EXECUTION_HANDOVER_20261023.md).
Remaining development stopped at08 C:HTTP200 length/empty content, cap700;
1actual call,2slots/64000units reserved,0new completed records. No retry/settings
change. Conditional final NOT activated. Original18benign human approvals and
all earlier stops/accounting preserved. Separate interactiveAsk enabled with
5slots/160000units at handover until2026-10-23T13:28:53.645160+00:00; user requests
may consume this capacity. See the app for actual remaining budget/expiry.

## Current independent continuation preparation

[Actual state and verification](docs/CONTINUATION_PREPARATION_STATUS_20261023.md) · [one staged execution proposal](docs/CONSOLIDATED_EXECUTION_APPROVAL_20261023.md).
Provider-blocked diagnostics remain separate from application outcomes.
No further calls/activation; Ask remains disabled without valid interactive
capacity. Reviewed benign records preserved; attack/final completion not claimed.

## Panel presentation and reviewed results

[Technical report](docs/REPORT.md) · [Partial benign evaluation: six cases](docs/panel/partial-benign-six-cases-v1/INDEX.md) · [Exact panel steps](docs/PANEL_WALKTHROUGH.md).
18 actual human-approved benign records; ASR is not evaluable. One HTTP400
failure and17 unexecuted configurations remain disclosed. Launch locally with
`.venv/bin/python run_app.py` if not already running. Saved results need no
provider calls; answering remains disabled under the stopped allowance.

## Current website implementation and handover

See [current17-phase status, seven deliverables and verified website](docs/END_TO_END_HANDOVER_20261023.md).
Actual saved-result downloads/charts and operational explanations implemented;
no provider calls or accounting changes. Local website verified, Ask disabled
by stopped development authorization. Representative attack evaluation and
human review remain incomplete. Earlier dated statuses below are historical.

## Current DEVELOPMENT execution · 23 October 2026

[Actual stopped development run](docs/AZURE_DEVELOPMENT_EXECUTION_20261023.md):18/36 records operationally
completed,1 HTTP400 failure on development-07 A,17 records not executed.
25 provider attempts;19854 known reported tokens plus1 unknown-usage call.
Used800000 local units;23 calls/736000 units unspent but STOPPED and unusable.
Expiry2026-10-23T10:42:45.285799+00:00 unchanged. Live answering/Ask disabled,
local services healthy. No retries, repairs, final generation or refunds.
Human review0/19; no validated ASR/task-success/quality result. Development
evaluation is Partial, final evaluation Not started, human review Pending.
New scoped policy and actual identity bound before generation;19 post-run
evidence checks passed. Historical receipts/calls/reservations preserved.
Earlier dated states below remain history.

## Current paired Azure integration · 23 October 2026

[Actual paired A/B/C result](docs/AZURE_PAIRED_INTEGRATION_RESULT_20261023.md): development-02 completed with4 real
HTTP200 attempts, source-supported Friday answers in A/B/C, valid clear C
screening and identical original/retained evidence. No operational defect or
retry. Original integration allowance exhausted:0 calls/0 units; unchanged expiry
2026-10-23T08:37:14.088375+00:00. App healthy and **live-disabled**; Ask disabled.
Roadmap Phase11 and checklist Phase9 local workflow/live integration are complete
for this benign integration case; representative attack evaluation and human
review remain pending. No defense-effectiveness claim is made.

See [separate development approval package](docs/DEVELOPMENT_EVALUATION_APPROVAL_20261023.md).
12 cases/36 mode records need at most48 attempts/1536000 units under a new,
separately scoped approval/policy. Actual model/code/evidence identities bound in
preparation only; no benchmark executed or execution freeze invented. Seven
calculation checks and16 saved-evidence checks passed. Earlier dated states below
are retained as history and superseded for these integration facts.

## Current Azure baseline and paid test status · 23 October 2026

[Actual baseline result and accounting](docs/AZURE_PAID_BASELINE_RESULT_20261023.md): ONE real Azure A request
succeeded with source-supported Friday answer. User approved paid use for the
existing bounded test; free eligibility and actual Azure quota remain unknown.
Ask enabled at verification with4 calls/128000 local units remaining until
2026-10-23T08:37:14.088375+00:00, subject to consumption, stop flags and expiry.
No automatic paired A/B/C run or benchmark occurred. Phase9 remains Partial;
real human review/evaluation/results remain pending. Earlier blocker/status
entries below are historical observations, superseded for this baseline only.

# AI Security Document Lab

Local fictional employee-document Q&A with bounded TXT/MD/PDF/DOCX parsing,
CPU embeddings, persistent Chroma, SQLite document versions, FastAPI and Streamlit.

The active provider is **Azure OpenAI only**, using v1 Chat Completions, the actual
Azure deployment name, strict JSON schemas and a separate Azure allowance.
Historical Groq/NVIDIA records and accounting are preserved; there is no active
routing or fallback to either provider.

Azure credentials and account confirmation are pending. **Live remains disabled;
no Azure allowance has been activated and no Azure provider request has been sent.**
The user deferred credentials to tomorrow morning. The already authorized scope
is one baseline followed, if source-supported and successful, by one paired
A/B/C development-02 test, <=5 attempts /160000 additional local units and a
one-hour local approval. No paid use is inferred from this authorization.

## Run locally without provider calls

```bash
.venv/bin/python run_app.py --check
.venv/bin/python run_app.py
```

UI: http://127.0.0.1:8501 · API: http://127.0.0.1:8000/docs

Root `.env` is the only automatically loaded backend configuration. Set
`LLM_BACKEND=azure_openai`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`,
`AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_ALLOWANCE_FILE=.private/azure_allowance.json`.
Keep `FREE_ONLY=true`, `LIVE_LLM_ENABLED=false` and timeout30s until live resumption.
Keys stay private; the frontend never loads the root `.env`.

[Azure configuration, account evidence and bounded live procedure](docs/AZURE_OPENAI.md)
explains the exact missing configuration, inactive approval draft and deferred
baseline/paired commands. Never reset old usage or substitute the exhausted
NVIDIA allowance. `--live-answers` remains an explicit launcher option after
valid Azure activation; health checks send no provider queries.

## A/B/C behavior

- A: ordinary grounded answering.
- B: privileged instruction separation; question/document JSON remains untrusted.
- C: strict-schema screening then B on retained original chunks. Invalid decisions,
  unknown source IDs, duplicate decisions and operational errors fail closed.

All answering modes use the same deployment, temperature1, completion cap700,
30-second timeout, zero retries and citation validation. A/B reserve32000 local
units; C reserves64000 up front. The UI disables unfunded/expired modes. Local
reservation units are not provider billing or actual remaining Azure quota.

## Local data and limits

Uploads support UTF-8 TXT/MD, text PDF and bounded non-macro DOCX. Image-only PDFs
need OCR; partial extraction requires explicit acceptance. Versions, replacement,
deduplication and deletion preserve source provenance. Local search needs the
pinned CPU embedding cache but no LLM key. Benchmark labels/objectives never enter
runtime prompts. No autonomous tools, URL ingestion or public/multi-user hosting.

[Contract](docs/PROJECT_CONTRACT.md), [verification](docs/VERIFICATION.md),
[scoring](docs/SCORING.md), [exposure audit](docs/SEMANTICS_EXPOSURE_AUDIT.md).
Historical setup and provider chronology are retained in
[the pre-Azure README](docs/README_PRE_AZURE_20261022.md) and existing reports;
they do not describe current Azure runtime status.

## Completion roadmap and tests

[Current phase status and exact gaps](docs/ROADMAP_STATUS.md) distinguishes offline
verification, historical local integration and pending Azure live results.
Generic tests use dummy public configuration and adapter doubles; current Azure
wire tests use in-memory transport with sockets blocked. Preserved retired-provider
test sources are under `backend/historical_tests/pre_9a_20261023/`; they are not
active-runtime assertions. See [test scope](backend/tests/README.md).

## Assignment handoff

- [Installation and troubleshooting](docs/INSTALLATION.md):one-command launch,
  verified host checks and explicitly unverified fresh-machine setup.
- [Assignment traceability](docs/ASSIGNMENT_TRACEABILITY.md):53 existing named
  requirements and seven deliverables;original PDF verification pending.
- [Results and review guide](docs/RESULTS_GUIDE.md):CSV/JSON exports,seven metric
  charts,source-preserving offline export and bound human-review template.
- [Technical report](docs/REPORT.md) and [planned demonstration](docs/DEMO.md).
- [Current 17-phase assessment](docs/ASSIGNMENT_HANDOFF_20261023.md).

Real Azure responses,human outcome review and empirical conclusions remain pending.
Synthetic presentation fixtures are outside genuine runs and visibly labeled;
they do not measure defense effectiveness. Controlled evaluation remains DRAFT.

## Where the defenses actually run

[Active runtime implementation](docs/ACTIVE_RUNTIME_IMPLEMENTATION.md) traces
UI → API → retrieval → `app.rag.assistant.respond/messages` → gated Azure v1.
That module implements A,B and C. The legacy `app/defenses/screening.py` placeholder
is not the production path. Azure transport,separation,screening/error routes
and nonblank-answer validation are offline verified;real model behavior remains
pending. Active dependencies exclude the unused Groq SDKs;historical pins and
all accounting/evidence are preserved separately.
