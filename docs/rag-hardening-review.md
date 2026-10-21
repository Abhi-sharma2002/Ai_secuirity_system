# RAG hardening review

The existing architecture is appropriate for this PoC: a strict text loader feeds a character chunker, a cached CPU embedding model, a persistent Chroma index, and a provider-independent retriever. The API, LLM, defenses and evaluation modules are currently placeholders. They were not expanded in this change.

## Actual findings and fixes

No critical vulnerability was established. These issues were found by inspecting the implementation:

| Priority | Affected files | Original behavior and impact | Implemented fix |
|---|---|---|---|
| High | ingestion/indexer.py | Version included IDs and text hashes only; metadata/model changes reused the same collection and every run upserted all records | Canonical version includes model commit, dimension, schema, normalization, metric, chunk configuration and evidence metadata; never deletes collections |
| High | ingestion/indexer.py, rag/retriever.py | Partial collections could be queried; final verification checked only IDs | Building/verified lifecycle, full text/metadata/vector checks, resumable missing-record insertion, explicit compatible collection selection |
| High | rag/embeddings.py | Model outputs accepted without validation | Count, dimension, finite values and unit norm checked; model errors retain their cause; immutable model revision |
| Medium | ingestion/loader.py | Unsupported files silently skipped; Unicode digits accepted in IDs; opening a FIFO could block | Explicit logged filename ignore list, ASCII IDs, unsupported-entry errors and nonblocking open followed by regular-file validation |
| Medium | ingestion/chunker.py | Missing input validation, duplicate document IDs could produce duplicate chunk IDs | Validate documents/checksums, integer chunk settings, preserve configuration in metadata |
| Medium | rag/retriever.py | Wrong types accepted; missing metadata crashed indirectly; zip silently truncated mismatched results | Strict question/top-k/allowlist validation; aligned result arrays; evidence offsets/hashes and distance validation; deterministic ordering |
| Medium | core/*, scripts/*, tests/*, requirements.txt | Configuration placeholders; broken loader import; fixed document-count assumptions; empty test and dependency files | Central validated settings, operational logging, script repairs, temporary-database regression tests and pins for existing runtime libraries |

## File-by-file changes

- `backend/app/core/config.py`: central environment settings with backend-relative default paths, immutable model revision, validated numeric limits and log level. Settings are read once at import; restart after changing environment variables.
- `backend/app/core/logging.py`: standard operational logging configuration, used by ingestion.
- `backend/app/ingestion/loader.py`: preserves strict decoding, raw hashes, limits, deterministic order and duplicate detection. Adds explicit entry policy, ASCII IDs and nonblocking file opens. `.gitkeep` is the default explicitly ignored entry. Set `IGNORED_DOCUMENT_ENTRIES=` to reject it too.
- `backend/app/ingestion/chunker.py`: validates document records/checksums and duplicate IDs; records actual chunk size/overlap; logs count. Keeps original text, offsets, hashes and ID format.
- `backend/app/rag/embeddings.py`: lazy cached CPU initialization, initialization lock, configurable batches and pinned revision, validated normalized vectors and timing logs.
- `backend/app/ingestion/indexer.py`: configuration-sensitive versions, building/verified state, record integrity checks and resumption without re-embedding existing valid records. Unexpected or corrupt records cause an error, not replacement. Chroma's implicit embedding function is disabled.
- `backend/app/rag/retriever.py`: requires a compatible verified index, validates search inputs and results, preserves evidence hashes, logs duration/count. Existing positional result fields remain compatible; hash fields are additive.
- `backend/scripts/ingest_documents.py`: central settings/logging; no fixed corpus size.
- `backend/scripts/test_loader.py`: repairs nonexistent module import.
- `backend/scripts/test_chunker.py`: corpus-size-independent assertions.
- `backend/scripts/test_retrieval.py`: explicit `RAG_COLLECTION` selection instead of the hardcoded legacy index.
- `backend/tests/test_hardening.py`: 13 regression tests with parameterized cases, mocked embeddings and real temporary Chroma storage.
- `backend/tests/test_live_rag.py`: opt-in complete dataset ingestion/retrieval with the real CPU model, temporary storage and an assertion that repeated ingestion does not re-embed.
- `backend/.env.example`: documents settings. No automatic dotenv loading.
- `backend/requirements.txt`: pins existing ChromaDB 1.5.9 and Sentence Transformers 6.1.0. No new libraries; tests use standard-library unittest.

## Validation and commands

From the repository root:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -v
RUN_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p test_live_rag.py -v
```

The real-model test requires the pinned model commit in the local Hugging Face cache when offline flags are set. Remove offline flags to allow a first download in an environment with network access.

From `backend`:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.test_loader
PYTHONPATH=. .venv/bin/python -m scripts.test_chunker
# Creates/reuses a NEW configuration-versioned collection; preserves legacy indexes.
PYTHONPATH=. .venv/bin/python -m scripts.ingest_documents
# Substitute the collection printed above.
RAG_COLLECTION=enterprise_documents_<new-version> PYTHONPATH=. .venv/bin/python -m scripts.test_retrieval
```

Verified results: 13 regression tests passed; default discovery skips the opt-in real-model test. Loader and chunker smoke tests passed against the actual 30 documents and 180 chunks. A complete real CPU model round trip in temporary storage passed, including repeated ingestion and three authorized D001 results. No tests wrote to the existing persistent database. Initial development failures (Chroma metadata update restrictions, a test update that invoked implicit embeddings, and the corpus's `.gitkeep`) were corrected and rerun.

The legacy production-directory ingestion/retrieval commands above were deliberately not executed. Collection `enterprise_documents_76ff2817415d16df` remains untouched. It lacks the new provenance/state contract and the hardened retriever rejects it; build a new collection and explicitly select it. The old collection is not silently upgraded or overwritten.

## Limits and next work

- Authentication and authorization are absent. A trusted application must derive the document allowlist; accepting caller-supplied IDs at an HTTP endpoint would bypass that boundary.
- Run one ingestion writer at a time. There is no cross-process writer coordination, transaction covering the whole build, or automatic recovery of corrupt records. Valid interrupted builds resume; corrupt indexes fail closed for operator investigation.
- Filesystem and database directories must be controlled by the application/operator. Final-component symlinks are rejected on Linux; this is not a sandbox against an adversary changing ancestor directories or directly modifying the database.
- Integrity verification reads the entire small PoC index into memory. It is not tuned for millions of records. New dataset versions embed the new version's chunks; cross-version vector reuse is not implemented.
- Pinned direct dependencies do not constitute a complete transitive dependency lock. Changing models requires setting the model name, immutable revision and expected dimension together.
- MiniLM token limits can truncate long embedding input even though evidence text is preserved in full. Assess this during relevance/attack-exposure evaluation before changing the requested character chunking policy.
- The real retrieval check establishes successful authorized retrieval, not ranking quality: the allowlist contains D001 only. Build evaluation metrics and corpus-wide relevance assertions next using the existing test cases.
- No prompt-injection screening, text cleanup, LLM invocation or full evaluation runner was added. All configurations A/B/C receive the same original evidence. This is a hardened PoC pipeline, not a claim of production readiness.

## Technical-review explanation

“We retained the original five-stage pipeline. Inputs are validated without rewriting evidence. Each index version identifies its data, chunking and embedding configuration. A build remains unavailable until all stored evidence and vectors verify; interrupted builds resume missing work. Retrieval uses a trusted document allowlist, returns original evidence and hashes, and remains independent of both the LLM provider and injection-defense variants.”
