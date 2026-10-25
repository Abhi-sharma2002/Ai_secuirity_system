# Dataset v3

Only `manifest.json` and its referenced `documents/` are active evaluation data.
`manifest.sha256` freezes the manifest; fixture hashes bind the documents.
`source_provenance.json` inventories the untouched source benchmark.

Copied v2 manifest, frozen hash and annotations were moved with `git mv` to
`archive/benchmark_v3_source/` at the repository root. Copied `revisions/` remain
historical records and must not be ingested or treated as v3 annotations. The
historical v2 evaluator schema is not the v3 loader.

Human-review exceptions are specified in
`docs/SCORING_V3_AMENDMENTS.md`. Gold labels, keywords, canaries, supporting
quotes and source provenance are evaluation metadata: do not include them in
model prompts or retrieval text. Only fixture document contents and the unchanged
case query enter the assistant.

Use `python backend/scripts/validate_v3.py` from the repository root. Use
`--summary` for computed coverage and pending-check status. The build script
defaults to a label preview; `--write` regenerates only the v3 copy and demo table
from the untouched source and archived metadata.
