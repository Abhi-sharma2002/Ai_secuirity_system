# Interactive comparison review bridge — 25 October 2026

Local implementation and isolated verification complete. No provider calls,
configuration changes, service restarts or genuine review imports were performed.
OpenRouter Nemotron routing, prompts and generation/screening settings are unchanged.

## What changed

- `app.rag.comparison` captures public execution/scoring/defense provenance and
  a content binding when saving a comparison. Answers and evidence remain intact.
- `app.evaluation.comparison_review` reads the authoritative SQLite request in
  read-only mode, checks its binding and optional downloaded export, and creates
  a separate unreviewed interactive run. Initial/retained evidence, citations,
  screening, errors, usage, latency and reservations are copied without regrading.
  Atomic imports and deterministic run IDs reject duplicate imports in the same
  output root. Missing provenance, mismatched initial evidence and altered records
  fail explicitly. Partial executions retain missing-mode coverage.
- `app.evaluation.compatibility` checks provider, model, endpoint, routing,
  generation/screening settings, timeout, defense/prompt versions, execution
  identity, scoring rules, rubric and specification before aggregation. Intended
  A/B/C stage and defense differences are represented explicitly in one profile.
  Review bindings cover that identity and the original response/evidence.
- Reporting labels interactive runs as non-benchmark data and shows provider/model.
  Unreviewed semantic judgments stay null; errors cannot become semantic successes.
  Missing ASR stays unavailable. Explicit legacy single-run reporting preserves
  historical arithmetic without asserting compatibility with current runs.

## Offline operator workflow

For a newly saved comparison, create a separate criteria JSON file. Supply actual
human-written criteria, not inferred model judgments. Its exact fields are:

```json
{
  "question": "The exact saved question",
  "expected_answer": "The source-supported legitimate answer expected by the reviewer",
  "review_notes": "Source references and the intended task rubric",
  "criteria_author": "Actual criteria author",
  "adversarial": false
}
```

Criteria are explicitly retrospective. This bridge supports the existing benign
interactive comparison scope, not an attack benchmark reclassification.

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/import_comparison.py --request-id SAVED_REQUEST_ID --criteria /path/to/criteria.json
```

Optional `--exported-comparison /path/to/download.json` verifies the UI download
against SQLite. Optional `--database` and `--output-root` select isolated storage.
Defaults use the application's registry and experiments directory. Import creates
review packets/template, CSV/JSON exports and charts, all initially unreviewed.
Inspect packets, copy the template to a separate judgments file, and fill only
explicit human decisions with reviewer identity and notes. Then:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/review_saved_comparison.py --source /path/to/imported-run --judgments /path/to/judgments.json
PYTHONPATH=backend .venv/bin/python backend/scripts/export_experiment.py --source /path/to/imported-run --output /path/to/new-export
```

Historical Azure/NVIDIA NIM records require an explicit separate export:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/export_experiment.py --source /path/to/historical-run --output /path/to/new-legacy-export --legacy-single-run
```

Legacy exports are labeled incomplete-identity single-run reports. Missing fields
do not imply compatibility; cross-run pooling and known provider/model/settings
mixtures are rejected. Do not combine those outputs with OpenRouter comparisons.

## Verification

Synthetic fixtures used temporary SQLite and experiment storage; network transport
was blocked. The focused regression command was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/bridge-mpl .venv/bin/python -m unittest backend.tests.evaluation.test_comparison_review_bridge backend.tests.evaluation.test_presentation_exports backend.tests.evaluation.test_phase9_evaluation backend.tests.evaluation.test_phase12_semantics backend.tests.evaluation.test_dataset_scoring backend.tests.rag.test_comparison -q
```

Result: **54 tests passed in 25.775s**. After adding the CLI round-trip check and
provider/model presentation labels, reran only the affected bridge and presentation
modules: **17 tests passed in 28.086s**. These overlap the earlier suite; they are
not 71 distinct tests.

Coverage: matched A/B/C; SQLite save/download/import; unreviewed and synthetic human
review; metrics and seven charts; partial/errors/screening blocks; empty execution;
tampered source/export/import/review; duplicate import; provider/model/settings/
identity mismatch; legacy exports; both bridge CLI commands. Synthetic reviews
are test fixtures only and were never inserted into genuine storage.

Read-only compatibility validation passed for all six existing historical experiment
folders. No historical report was regenerated. Preservation check: **677 protected
files unchanged; zero new protected files**, covering private settings, datasets,
accounting, historical reviews/results and active provider/prompt configuration.

## Limits and remaining work

Older interactive comparisons without captured provenance/binding cannot be
imported; current metadata is not substituted retrospectively. New provenance is
captured when the updated comparison code is loaded during a normal future service
restart; no services were restarted in this task. No new live execution is required
or authorized by these commands. Human review of actual comparisons remains manual.
Content hashes detect inconsistent edits, not a malicious rewrite of every trusted
local artifact and binding. This work establishes a local workflow, not defense
effectiveness or a completed controlled benchmark.
