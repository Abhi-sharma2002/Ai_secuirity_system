# Installation and local operation

Verified target:Linux,Python3.12,single local user,one backend worker. Launch from
the repository root with **one command**:

```bash
.venv/bin/python run_app.py
```

UI:http://127.0.0.1:8501 · API:http://127.0.0.1:8000/docs.
Default launch forces backend live=false and FREE_ONLY=true;frontend never owns
the credential. Ctrl+C stops only launcher-owned children. No services were
restarted for this handoff. Existing data remains in place.

## Existing verified host

```bash
.venv/bin/python run_app.py --check
.venv/bin/python -m pip check
```

Both passed23October2026. Earlier verification matched23 direct pins. Active
requirements now have21 matching pins;the two unused Groq SDK pins are retained
separately in backend/historical_tests/requirements.txt for optional historical replay.
The host venv includes system-site packages and a .pth reference to an older
environment. This is **not a portable self-contained installation**. Preserve
that environment;do not recreate it over an existing checkout's .venv.

## Fresh checkout procedure (not executed with downloads)

In a new copy without a venv,using a compatible Linux Python3.12 installation:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip check
.venv/bin/python run_app.py --check
```

These are operator installation instructions,not commands run during this task.
The exact CPU wheel's availability/platform compatibility has not been verified
against a remote index. Stop if resolution fails;do not silently switch to GPU
packages or different versions. requirements.txt pins observed direct versions,
not a complete transitive wheel lock. Historical Groq pins are optional in backend/historical_tests/requirements.txt;
the runtime can select Azure or the fixed OpenRouter free Nemotron route and does
not require either retired SDK. See [OpenRouter temporary setup](OPENROUTER.md).

Copy `.env.example` to `.env` **only if .env does not exist**;never overwrite an
existing private file. Keep live=false and FREE_ONLY=true. Provider fields may
remain blank for local upload/search;do not publish the private file. Backend settings
resolve relative paths from repository root and process environment wins over
root.env. Frontend calls the backend over loopback.

Local retrieval requires the existing cached CPU model/revision documented in
DATASET.md and the draft plan. No model download was performed here. A fresh
machine needs separately provisioned approved model files;keep offline flags
HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 when downloads are not allowed.
Do not substitute synthetic embeddings for the main workflow.

An isolated fresh venv/no-index dry resolution was attempted offline and failed
at chromadb==1.5.9 because no wheels were supplied. This is an explicit remaining
reproducibility limit,not evidence that the pinned package is unavailable online.
See evidence/assignment-installation-v1.json and clean-offline-resolution log.

## Troubleshooting

| Symptom | Action |
|---|---|
| Missing module | Use repository .venv,inspect --check and pinned metadata;do not install from another project's environment blindly. |
| Port8000/8501 busy or backend lock occupied | Identify the owner;use its existing UI or stop only an authorized project launcher. Never kill unrelated services. |
| Embedding cache unavailable | Keep offline mode;report missing pinned cache. Do not download or change model/revision automatically. |
| Snapshot/configuration mismatch | Preserve source/index/history;use an explicit new dataset/index revision. Never overwrite a frozen benchmark to force resume. |
| Upload rejected/needs_ocr/needs_review | Inspect per-version status;no OCR is implemented. Accept partial text only explicitly,with its citation limits. |
| Failed replacement | Prior usable version remains active;inspect the failed attempt rather than deleting history. |
| Ask disabled | Expected today. Root live=false;account approval/capacity gates remain. A/B require1 funded slot,C requires2. Health is not an Azure probe. |
| Timeout/schema/citation/screening/provider error | Preserve outcome and reservations;stop,no automatic retry/fallback. Usage may be unknown. |
| Empty charts or N/A | Inspect scheduled/recorded/error/review counts. Missing judgments are not zero ASR. |
| Stale review binding | Reopen actual evidence/criteria and export a new packet;do not copy an unrelated binding. |

Maintenance is explicit and potentially destructive;HANDOVER.md describes it.
Cleanup/rebuild is not an installation step. No historical usage refund/reset or
approval edit is needed for offline work.

## Current separately funded interactive launch

If the existing app is running, open http://127.0.0.1:8501; do not start a second
worker. To launch an already active, unexpired interactive receipt:

```bash
AZURE_OPENAI_ALLOWANCE_FILE=.private/azure-interactive-benign-stage-v1-allowance.json .venv/bin/python run_app.py --live-answers
```

This allocates no capacity and makes no automatic request. Trial-only uses
FREE_ONLY=true; do not use the paid-test switch. Receipt expiry/budget/stops remain
authoritative. Upload a playground document before asking a source question.
Default no-flag launch stays live-disabled. Expired receipts are not renewed.


Organization update (24 October 2026): see [current runtime map](architecture/RUNTIME_MAP.md) and [refactor verification](architecture/REFACTOR_20261024.md). Source paths/identities changed; prompts, schemas, saved results and accounting were preserved. No new live or security evaluation result is implied.
