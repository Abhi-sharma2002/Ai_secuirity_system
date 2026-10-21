# Phase 3: fixed-context evidence

A validated case and pinned source manifest produce an immutable evidence package. The builder has no defense selection, retrieval, screening, scoring, prompts or LLM integration. No dependencies were added. Documents, evaluation records and manifest are unchanged.

## Files and functions

- `backend/app/evaluation/evidence_builder.py`: `load_verified_sources()` checks the manifest and original source bytes, then pins expected hashes and source provenance in read-only mappings. `build_evidence()` reads and verifies referenced documents again and builds a frozen `EvidencePackage`. Frozen document records and tuples keep the package immutable for reuse across A/B/C.
- `backend/app/evaluation/test_case_loader.py`: extracted `read_verified_document()` from the existing validation loop. Both the dataset validator and evidence builder now use the same bounded UTF-8 reader, symlink protection and manifest-hash check. Existing validation behavior and exceptions remain unchanged.
- `backend/app/core/config.py` and `backend/.env.example`: added `EVIDENCE_MAX_CHARACTERS` (100,000) and `EVIDENCE_MAX_BYTES` (400,000). Both require positive integer environment values. Per-call limits are also supported and reject booleans/non-integers.
- `backend/scripts/verify_evidence.py`: loads the validated dataset, builds every package twice, compares complete package equality (including fingerprints), reports each result and size statistics, and shows safe sample metadata. It exits nonzero on setup/build/consistency failures and prints no questions or source text.
- `backend/tests/test_evidence_builder.py`: 19 temporary-fixture tests cover success, ordering, repeated fingerprints, payload/newline/Unicode preservation, source changes/deletion, expected-hash pinning, invalid inputs, exact size thresholds, counts/offsets, source provenance, fairness, immutable outputs and CLI behavior.

## Usage

From the repository root:

```python
from app.evaluation.test_case_loader import load_test_cases
from app.evaluation.evidence_builder import load_verified_sources, build_evidence

cases = load_test_cases()
sources = load_verified_sources()  # Pin once for the experiment.
package = build_evidence(cases[0], sources)

# Question stays separate; evidence_text contains only framed source material.
question = package.question
evidence = package.evidence_text
```

`load_test_cases()` remains responsible for the full scoring/fixture schema and supporting quotes. The builder accepts that validated case, checks its own input boundary, and rechecks any provided supporting hash against the pinned sources. It does not infer ground truth or interpret fixture instructions. Test-case IDs are evidence-selection inputs, not an authorization grant.

## Integrity and reproducibility

Manifest expectations are pinned once and cannot be accidentally updated through the returned mapping. Every build reads the files again using the existing Linux directory-descriptor reader, rejects symlinks/traversal, and compares original UTF-8 bytes to the pinned SHA-256. A deleted or altered file fails even if it previously verified. Changing the manifest on disk does not update an existing experiment's expected hashes. The builder uses all referenced documents in their declared order, without dropping sections or truncating text.

The manifest is the trusted expectation source; SHA-256 detects content drift, not malicious replacement of both the manifest and data before experiment initialization. Titles and provenance are pinned from the manifest rather than independently authenticated against document header fields. Only title, document ID, source filename, hash, domain, classification, owner, version and effective date enter the package. Attack annotations, expected screening labels, fixture scoring and human-review fields stay in the original case for later evaluation; they do not enter model evidence.

Strict UTF-8 decode followed by UTF-8 encode preserves the original bytes, including CRLF, trailing whitespace, invisible Unicode, embedded JSON/XML, multilingual text and encoded payloads. No normalization or sanitization is applied.

Sources are framed with stable ordinal/ID/hash BEGIN and END markers. `SourceBoundary` stores half-open character and UTF-8 byte offsets pointing to the exact original content inside the framed text. These offsets are authoritative even if a document contains text resembling a marker. Markers are formatting, not a prompt-injection defense or trust boundary.

The fingerprint is SHA-256 of UTF-8 canonical JSON (`ensure_ascii=False`, sorted object keys, compact separators) containing the entire package except the fingerprint field itself. It covers schema version, test ID, original question, evidence mode, ordered source content and provenance, rendered framing, counts and boundaries. Source paths are data-relative; host paths, timestamps, size-limit settings and defense configuration are excluded. Changing the question or declared order changes the fingerprint. Increase `schema_version` if the evidence format changes in future.

## Size accounting

`character_count` and `byte_count` measure the complete framed evidence. `source_character_count` and `source_byte_count` measure only original source contents. Each document also has its own counts. The separate question and a provider's future prompt serialization are outside these evidence limits. Python characters are Unicode code points, not grapheme clusters or tokens. No token usage is claimed.

Both size limits are checked incrementally before returning a package. Exactly-at-limit evidence is allowed; exceeding either limit raises `EvidenceBuildError`. The result is never shortened or summarized. The existing maximum single-document read size also remains enforced.

## Verification

Run from the project root:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m scripts.verify_evidence
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -v
```

Executed results:

- Existing dataset validator: all 45 cases passed, with 23 attack, 18 legitimate-quality and 4 benign-quotation cases.
- Evidence verification: 45 successful, 0 failed; all repeated complete packages and fingerprints identical.
- Default test suite: 51 passed, 1 optional real-model integration test skipped (52 discovered). The real-model test was not needed or executed for Phase 3; embedding/indexing/retrieval modules were not changed.
- Evidence size: 4,654–14,441 characters; 4,654–14,441 UTF-8 bytes. Mean framed size: 6,145.60 characters and 6,146.00 bytes.
- E032: order `D032,D031`, 9,419 characters, 9,421 UTF-8 bytes, fingerprint `0a6c8575aaa7da02f3bfea36658b9d2ac1f3566bd86235a0583f3585eca9efbb`.

The previous D032 hash problem was already resolved in the current workspace before this phase; the input dataset passed validation at inspection. Phase 3 did not repair or rewrite the dataset.

## Limits and next phase

This is a local CPU PoC component using Linux filesystem safety primitives. Call `load_verified_sources()` once and reuse it; recreating it explicitly begins a new source snapshot. Metadata expectations are pinned for that snapshot, so metadata edits on disk take effect only when loading a new snapshot. Each document is verified from the bytes read; this is not a filesystem-wide atomic snapshot or a digital signature.

The builder intentionally rereads source files for every build, trading small local I/O for detecting drift. The package is held in memory. Its title/provenance metadata is separate from the framed evidence text, so a later prompt adapter must define and version any additional serialization. Provider context limits must be checked later using the complete actual prompt. Case validation and source loading must use the same manifest and document directory when custom paths are supplied.

Next, implement the evaluation harness and provider adapter with explicit A/B/C prompt/defense behavior. Record the initial package fingerprint separately from any later screened/serialized model input, and retain actual input evidence for attack-exposure measurement. Those behaviors are outside Phase 3 and have not been added.
