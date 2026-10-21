# Phase 2: evaluation dataset validation

Implemented only dataset preparation and integrity verification. The existing RAG modules, source documents, manifest, JSON and CSV were not modified. No dependencies were added.

## Files

- `backend/app/evaluation/test_case_loader.py`: `load_test_cases()` returns original dictionaries after validating the complete dataset. It checks required fields/types, unique ASCII test IDs, document references, family/evidence-mode/label values and conditional fixture/scoring requirements. It verifies manifest hashes for every referenced source, supporting hashes when nonempty, supporting quotes within their named sections, and the exact full attack section and indicator against its source. Source documents are read once per load. Errors include a safe test ID or record position and a reason, without printing evidence.
- `backend/scripts/validate_test_cases.py`: CLI with success counts by family, evidence mode and label, fixture/benign totals and source-integrity status. Validation failure prints a concise reason to stderr and exits with status 1; it never labels a partially checked dataset verified.
- `backend/tests/test_evaluation_loader.py`: 19 tests using synthetic files in temporary directories. Includes malformed/duplicate-key JSON, invalid UTF-8, missing fields/files, invalid types/enums/IDs, source/hash/quote failures, attack-fixture mismatches, benign quotations and mixed evidence, metadata/Unicode preservation, traversal, file and ancestor-directory symlinks, and CLI output/exit codes.

## Schema decisions

The actual 45-case inventory is:

| Field | Value | Count |
|---|---|---:|
| Family | legitimate_quality | 18 |
| Family | benign_quotation | 4 |
| Family | attack | 23 |
| Evidence mode | fixed_context | 45 |
| Expected screening label | benign | 22 |
| Expected screening label | suspicious | 23 |
| Fixture | present | 23 |
| Fixture | null | 22 |

These counts describe the supplied records, not successful integrity validation of all 45.

All 23 schema fields remain available unchanged. `notes` may be empty; an empty supporting hash is preserved without inventing a value, while manifest hashes remain mandatory. Source IDs need not be sequential. Future ground-truth/scoring outcomes are not inferred. Additional record fields are retained.

Non-attack cases require a null fixture and the dataset's benign/not_applicable labels. Attack cases require the dataset's suspicious label, fixture object, and applicable attack/exposure definitions. These are schema consistency checks, not content screening. In particular, E037 and E038 are legitimate-quality cases containing poisoned evidence; they remain labeled benign. Manifest `is_attack_fixture` is not used to classify a case: the manifest also applies that flag to educational quotation documents.

Only `fixed_context` is currently supported because that is the only evidence mode in this dataset. Future normal-RAG cases require an explicit schema extension and must not silently reinterpret fixed-context cases. `document_ids` describes experimental evidence, not trusted authorization. The CSV is an export; JSON is the authoritative loader input. CSV/JSON parity is not validated.

## Actual integrity problem found

The validation command currently exits 1:

```text
FAIL: E032: manifest hash mismatch for D032
```

D032 begins with the unexpected prefix `python -m scripts.test_document_loader` immediately before its original document header.

- Manifest SHA-256: `8a4aa063e3f8d8a3ebdecc5007ffd43838a8caf76211227f3f88237ae0f6fe9a`
- Actual SHA-256: `d95c77e384613f9d7b8dcb16a8c65a74fbe3b015d6495cfb10d01b5cbee3bd65`

A diagnostic hash calculation excluding precisely that prefix matches the manifest. No bytes were removed or rewritten. Individually checking every case against the unchanged sources found 42 passing and three failing source integrity: E032, E042 and E045, all referencing D032. They are not silently skipped by `load_test_cases()`; it fails the whole dataset at the first error.

The next dataset-maintenance step is to review and restore D032 from a trusted original, then rerun validation. Updating hashes merely to accept an unexplained change would conceal evidence drift.

## Commands and executed results

Run from the project root:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m scripts.validate_test_cases
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -v
RUN_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p test_live_rag.py -v
```

- Validation CLI: FAILED because of the real D032 source drift above. No claim that all 45 cases are verified.
- New loader tests: 19 passed.
- Default complete suite: 32 passed, 1 optional real-model test skipped (33 discovered).
- Real CPU-model integration: 1 passed separately in temporary storage; ingestion, idempotent reuse and authorized retrieval still work.

The validator uses Linux `dir_fd`, `O_NOFOLLOW` and pinned directory descriptors to reject traversal and symlinks in every component without a check/open race. JSON/manifest files are limited to 8 MiB; documents use the existing configured size limit. Source bytes are decoded strictly as UTF-8 without newline or Unicode normalization. Section container newlines are excluded for comparison; the actual fixture string is never rewritten. The filesystem and manifest remain operator-controlled inputs; hashes detect drift but are not digital signatures.

There are no LLM calls, generated outcomes, defenses, screening, endpoints, dashboards or cloud changes. Once the source issue is resolved and validation passes, the later evaluation runner can consume the same records for A/B/C, preserve actual model-input evidence, and assess exposure and human-reviewed outcomes separately.
