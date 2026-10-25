# Local application and commands

Run from `/home/sigmoid/Ai-Security-Poc` using the existing `.venv`:

```bash
.venv/bin/python run_app.py --check
.venv/bin/python run_app.py
```

UI: http://127.0.0.1:8501. Backend: http://127.0.0.1:8000.
The default launcher disables live answering. It does not fabricate allowance,
refund reservations, clear stops, enable old approvals or make an automatic query.
For installation and pinned dependencies, follow [INSTALLATION.md](../INSTALLATION.md).
The only active environment template is root `.env.example`; root `.env` is private.

Use Documents to upload/replace/delete and Search to inspect actual provenance.
Use saved Results for presentation without provider calls. Ask is enabled only
when explicitly launched for live answering under a valid interactive approval.
Respect the existing trial-only/no-out-of-pocket restriction and Azure spending
protection. A local allowance is not proof or enforcement of Azure billing.

## Evaluation and reporting commands

Help/import checks do not generate model requests:

```bash
PYTHONPATH=backend .venv/bin/python -m app.evaluation.experiment --help
PYTHONPATH=backend .venv/bin/python backend/scripts/export_experiment.py --help
PYTHONPATH=backend .venv/bin/python backend/scripts/run_baseline.py --help
PYTHONPATH=backend .venv/bin/python backend/scripts/run_instruction_separation.py --help
```

The two fixed-context commands are legacy reproduction tools, not the website's
A/B/C entry point. The active evaluator is `app.evaluation.experiment`; the former
`run_evaluation.py` was a docstring-only placeholder and was removed.
Current authorized-operation scripts retain their existing `backend/scripts/`
paths. Historical provider commands moved to `backend/scripts/history/`; their
old frozen provider settings do not authorize current Azure use.

## Focused offline checks

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.organization.test_runtime_organization backend.tests.llm.test_azure_openai backend.tests.defenses.test_phase7_separation backend.tests.defenses.test_phase8_screening -v
```

For grouped discovery use `-m unittest discover -s backend/tests -t . -v` only
when a full suite is justified. Group directories have package markers; cross-test
fixtures use explicit imports. Historical snapshots are outside this discovery.
Do not mistake synthetic transport tests for real defense-effectiveness results.

## Troubleshooting and panel explanation

- Ask disabled: inspect readiness, active scope, expiry, remaining capacity and
  stop flags. Do not toggle flags or reuse stopped receipts to bypass them.
- Import failure: launch at the repository root; direct backend CLI commands need
  `PYTHONPATH=backend`. Tests now use responsibility-group module names.
- A second backend cannot start: the existing single-worker lock is intentional.
- Model unavailable offline: reuse the existing pinned cache; this refactor neither
  downloads a model nor substitutes synthetic embeddings for real retrieval.
- Screening error: inspect the saved validated trace. Complete JSON can still
  contain an invalid source ID; preserve the failure rather than repair silently.
- Resume refuses an old run: source paths/hashes changed. Preserve the old identity;
  prepare a new explicitly bound run instead of editing historical fingerprints.

Panel code tour: API → lifecycle → RAG retrieval → assistant → active defenses →
Azure gate/adapter → answer/citation validation → review/metrics/presentation.
See [runtime map](../architecture/RUNTIME_MAP.md) for the exact functions.
