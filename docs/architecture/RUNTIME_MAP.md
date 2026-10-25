# Runtime map

## Folder responsibilities

| Folder | Responsibility |
|---|---|
| `backend/app/api/` | Active HTTP routes, request validation, response delivery |
| `backend/app/core/` | Root environment loading, configuration, logging |
| `backend/app/storage/` | SQLite registry, connection/transaction helpers, recovery |
| `backend/app/ingestion/` | Upload validation, extraction, chunking, document/version lifecycle |
| `backend/app/rag/` | CPU embeddings, Chroma indexing/retrieval, evidence assembly and orchestration |
| `backend/app/defenses/` | Active A/B prompts/messages, strict answer contracts, C screening and filtering |
| `backend/app/llm/` | Azure/OpenRouter transports, approval gate, reservations, diagnostics and settings |
| `backend/app/evaluation/` | Dataset/scoring versions, frozen execution, identities, reviews, metrics and presentation |
| `backend/app/models/` | Shared parsed-document/version and document identity contracts |
| `backend/app/legacy/` | Historical fixed-context defenses/E037, retired provider transport and upload API |
| `backend/legacy_llm/` | Existing historical client/model contracts required by legacy runners |
| `backend/tests/` | Tests grouped by responsibility, including explicit legacy checks |
| `backend/scripts/` | Operational/evaluation entry points; retired provider commands under `history/` |
| `frontend/` | Streamlit pages and UI-specific helpers |
| `backend/benchmark/` | Existing frozen dataset, approved annotations/rules and snapshot location |
| `backend/data/` | Existing configured document/runtime storage; never moved by this refactor |
| `docs/architecture/`, `docs/guides/` | Current implementation map and launch/command guide |
| `docs/history/` | Historical documentation/source snapshots; execution evidence stays at existing paths |

## Complete active flow

1. `run_app.py` starts `app.main:app` and `frontend/streamlit_app.py`.
2. `app.main` installs `api/runtime.py`; its lifespan owns the single backend lock
   and calls `storage/registry.py` initialization/recovery.
3. Document routes invoke `ingestion/lifecycle.py`. It validates uploads, parses
   supported formats via `ingestion/parsers.py`, creates chunks and asks
   `rag/indexer.py` to embed/store them. Only successfully activated versions
   become eligible for retrieval; failed replacement preserves the active version.
4. Search invokes `rag/retrieval.search`, using active lifecycle snapshots,
   `rag/retriever.DocumentRetriever`, the pinned `rag/embeddings.py` CPU model,
   provenance checks, deterministic sorting and the existing evidence limits.
5. Chat invokes `rag/assistant.respond`. It retrieves once or receives frozen
   initial evidence, checks interactive restrictions and reserves capacity.
6. A uses `defenses/baseline.messages`; B uses
   `defenses/instruction_separation.messages`. C first invokes
   `defenses/screening.apply`, then uses B's message builder with retained evidence.
7. `llm/client.call` rechecks approval, expiry, stop flags and request bound,
   combines application-controlled privileged rules into a system message and
   keeps evidence in user JSON. `llm/azure_openai.generate` performs one real
   selected provider attempt with zero retries; Azure uses strict wire JSON Schema,
   while the fixed OpenRouter free route uses trusted schema instructions and
   local strict response validation.
8. The assistant validates the answer contract and citation IDs against supplied
   evidence. It returns references and traces, or explicit errors without fallback.
9. `evaluation/experiment.py` freezes evidence/settings for paired runs, records
   actual outputs and operational failures, binds human reviews, and exports
   denominators/metrics through the existing presentation tools. Runtime prompts
   do not receive evaluator gold labels or scoring annotations.

## Actual A/B/C entry points

| Configuration | Active implementation | Behavior |
|---|---|---|
| A | `defenses/baseline.messages` | Existing GROUND policy plus serialized question/sources |
| B | `defenses/instruction_separation.messages` | Same inputs with existing privileged SEPARATION policy |
| C | `defenses/screening.apply` then B | Existing SCREEN policy, strict decision validation, original-record filtering, B answering |

`rag/assistant.py` retains imports of GROUND/SEPARATION/SCREEN and Answer/Screening
for existing callers. These refer to the moved implementations, not duplicate
classes or policies. `assistant.messages` is a small dispatch function.

C retains the exact distinction between `question_flagged` and
`flagged_source_ids`. Unknown source IDs cause a screening error even when the
question is flagged. No source-ID repair, new filtering heuristic, schema change,
unscreened fallback or automatic minimal-reasoning setting was introduced.

A/B reserve one call/32,000 local units; C reserves two/64,000 before screening.
Local reservations and provider-reported tokens remain separate. Citation-ID
validation is not semantic proof; genuine review is still required.

## Historical compatibility

Legacy classes now live in `app.legacy.defenses.*`; current legacy tests and CLI
imports use those paths. `legacy_llm` remains available for those callers.
Archived test snapshots under `backend/historical_tests/` are immutable original
sources, not runnable current-runtime compatibility claims. Use their matching
historical implementation for exact reproduction.

No runtime data, private setting, dataset, approval, review or saved experiment
was relocated. No dependency from core/storage to API/UI was introduced.
