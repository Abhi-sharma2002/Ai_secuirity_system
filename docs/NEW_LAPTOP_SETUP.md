# Run on another laptop (Ubuntu/Linux)

Use Python 3.12. Complete dependency installation before the presentation; the
first installation and embedding-model download need internet and can take time.

```bash
git clone https://github.com/Abhi-sharma2002/Ai_secuirity_system.git
cd Ai_secuirity_system
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements.txt
test -f .env || cp .env.example .env
.venv/bin/python run_app.py --check
.venv/bin/python run_app.py
```

Open http://127.0.0.1:8501. Keep that terminal running. Ctrl+C stops the app.
If ports 8000 or 8501 are occupied, stop the previous app in its own terminal
before starting another copy.

## What works from the repository

Metrics / evaluation reads the saved benchmark results, source fixtures and human
reviews. The report, graphs and eight-slide presentation are included. Opening
saved metrics does not require an Azure key or new model calls.

Presentation: `docs/presentation/AI_Security_Document_Lab_Abhishek_Sharma.pptx`.
PDF preview: `docs/presentation/AI_Security_Document_Lab_preview.pdf`.

## Search your documents locally

Before the demo, download the pinned CPU embedding model once:

```bash
PYTHONPATH=backend .venv/bin/python -c "from app.rag.embeddings import get_embedding_model; get_embedding_model()"
```

Then upload the required files in Documents and use Search evidence or the
local-only question workflow. Uploads, Chroma indexes and SQLite runtime databases
are local to each laptop and are intentionally not in Git. Re-upload the needed
documents on the new laptop. Do not rebuild or rerun the frozen benchmark merely
to display its saved results.

## Live answers are a separate setup

Cloning does not copy `.env`, `.private/`, credentials or the consumed-call ledger.
Live answering remains disabled by default. Use the existing Azure trial only;
enter credentials privately and preserve the existing allowance identity,
consumption and stop flags when migrating its private state. Do not create a new
allowance or reset accounting. Stop the old laptop's backend before using any
migrated live allowance; independent copies must not consume the same allowance.
Only after that private migration is verified, start with:

```bash
.venv/bin/python run_app.py --live-answers
```

For a saved-results presentation, use the default launcher; no private migration
or provider calls are needed. This setup was checked against the current local
project; a clean dependency installation on the destination laptop still needs
to be completed and checked there.
