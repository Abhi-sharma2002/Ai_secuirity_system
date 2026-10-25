# Phase 8 screening · offline gate complete · 22 October 2026

Phase 8 was not already complete: the Phase 7 handoff still lacked current NVIDIA C-wire, decision-validation and retained-context evidence. Completed those gaps using synthetic responses and blocked sockets. Existing sufficient source/retrieval, dataset-label isolation, C-route and accounting evidence was reused. No image asset is required; the attached imagegen skill is outside this task's scope. No applicable ancestor/workspace AGENTS.md was found, including hidden workspace paths outside .git/.venv.

Current path: `app.rag.assistant.respond` → `app.llm.client` → `app.llm.nvidia_nim.generate`. No legacy `app/defenses` behavior was added. Inspected the requested contract/status/acceptance/verification records, Phase 7 handoff, current schemas/adapter and evaluator records. The recorded NVIDIA paired smoke stopped on A/HTTP500, so it contains no live C screen or answer and remains incomplete.

## Requirement-to-evidence map

| Requirement | Implementation / sufficient reused evidence | New focused check and conclusion |
|---|---|---|
| Privileged screener; untrusted question/document data | Fixed SCREEN constant becomes a privileged application message; client merges only trusted system/developer messages. NVI serializes them as system and question/sources as user. Phase 7 structural work and Phase 2 dataset-index label isolation reused. | Exact actual NVIDIA HTTP JSON screen message equals SCREEN, with exactly system/user roles. Quoted SYSTEM/developer JSON, delimiters, filenames and source text remain intact in user JSON. Evaluator sentinels supplied separately as operational test metadata never appear in any request payload. No source string can create a real privileged role. |
| Required fields/types/enums/IDs and invalid-output handling | Screening remains the existing strict three-field object: question_flagged bool, flagged_source_ids list[str], reason_codes existing literal enum. Extra fields forbidden; IDs must exist in the original context. | Actual strict JSON-schema envelope inspected; required-field set exact, additionalProperties=false. Missing fields, wrong scalar/list/boolean types, unknown enum/IDs, invented source records, malformed JSON, array/null roots and duplicate decisions all produce screening_error with no answering request. All four valid reason codes exercised across route fixtures. |
| Missing/duplicate decisions | Protocol is a sparse exclusion list, not one decision object per source. An omitted source ID means retain it; an empty flagged list is valid. Missing required response fields are invalid. | Added fail-closed duplicate JSON-field detection before client JSON normalization, plus uniqueness validation for flagged IDs/reason codes. No implicit benign default, coercion, majority vote, repair or deduplication of invalid model decisions. No new per-source completeness or reason/flag semantic-classifier rule was invented. |
| Separate original/retained evidence and traceability | candidate_evidence + snapshot/omitted_ids retain initial context; supplied_evidence is the actual generator context. Phase 5 provenance/source-boundary evidence reused. | Retention selects original objects, preserving order, IDs, document/version/hash/filename/page/section/partial flags and text. Output cannot supply replacement evidence: extra source objects fail schema validation. Generator citations to removed IDs are invalid_citations, never promoted to valid references. Original input is unchanged. On question block, supplied_evidence=[] means no generation input was supplied, not that every chunk was classified malicious. |
| Retention invokes B; all-clear and no-evidence routes | C generation calls messages('C'), which adds exactly the same GROUND+SEPARATION rules as B, with common Answer contract. | Retained-all final request equals B's final request. Partial exclusion sends only retained original chunks. Valid question block, all-source exclusion and empty initial context invoke only screening, then no generator. C still screens an empty initial context to assess the question; it reserves the existing full two-call unit. |
| Error/timeout/gate behavior and no unscreened fallback | C reserves two calls/64000 units before screening. Existing gate rechecks each call and retains unused/failed reservations. Historical current routing/gate checks reused. | Synthetic screening HTTP500/ReadTimeout yield screening_error, one failed screen and one retained unused reservation. Insufficient combined capacity blocks before I/O. Expiry between stages prevents answering. A generation failure after valid screening remains llm_error with the completed screen and retained-context trace. No error path invokes an unscreened answer or retry. |
| Fair settings, stage usage/latency and classification limits | Current model/settings/initial retrieval shared; reasoning_effort remains none; previous Phase 5 retrieval and Phase 7 parity evidence reused. Evaluator separates operational errors and completed-screen denominators. | Actual A/B/screen/C-answer wire requests retain the same model, temperature1, cap700, timeout30, nonstreaming and reasoning_effort=none; only intended prompts/schema/context differ. C traces have distinct screening/generation call IDs, stages, synthetic reported usage and per-call latency; total mode latency is separate. Blocks have a screening decision, invalid screens keep screening=null, and errors are not clean/benign screens. Synthetic classifications establish control flow only. |

## Demonstrated defects and narrow fixes

Initial regression: **2 test methods, 3 failures**. Actual current client/adapter accepted duplicate question_flagged JSON keys, letting the later false overwrite an earlier true before schema validation. Duplicate flagged-ID and reason-code entries were also accepted and reached generation. These are invalid/ambiguous decision outputs under this phase's requested duplicate-decision boundary; they must not silently become valid retained/benign routes.

Fixed only:

- `app/llm/client.py`: reject repeated object keys for screening-stage JSON before canonicalization can erase them. Preserve the existing operational error category, sanitized diagnostics and accounting.
- `app/rag/assistant.py`: reject duplicate flagged IDs and reason-code entries during Screening validation.

No prompt string, enum set, schema field/layout, NVIDIA adapter/reasoning setting, output cap, timeout, retrieval setting or dataset changed. Provider strict schema and local decision validation remain distinct: a provider may emit a JSON-schema-valid array containing duplicates, which local validation now rejects without another request. Screen failures remain ungraded operational errors. No accuracy/semantic classifier was implemented.

## Exact offline execution

```bash
LLM_BACKEND=groq LIVE_LLM_ENABLED=false PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_phase8_screening.ScreeningTests.test_duplicate_json_decisions_fail_closed backend.tests.test_phase8_screening.ScreeningTests.test_duplicate_decision_list_entries_fail_closed -v > docs/evidence/phase8-duplicate-regression-before.log 2>&1
# Before fixes: exit1; 2 methods, 3 failures (subtests); expected regression evidence.

LLM_BACKEND=groq LIVE_LLM_ENABLED=false PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -m unittest backend.tests.test_phase8_screening -v > docs/evidence/phase8-screening-offline-tests-v1.log 2>&1
# Final: exit0; 11 passed in3.217s; no skips/failures.

.venv/bin/python -m compileall -q backend/app/rag/assistant.py backend/app/llm/client.py backend/tests/test_phase8_screening.py
git diff --check
```

Compileall/diff checks exit0. An intermediate10-test pass (3.055s) preceded adding the screened-out citation case; runs overlap and are not added as distinct tests. New cases use the real shared client, real NVIDIA HTTP serialization, in-memory HTTP responses and disposable SQLite with synthetic approval/config doubles. Actual LIVE_LLM_ENABLED remains false in every test process; production approval/gate state is never activated. Both socket.connect and create_connection are blocked. No model download or live provider traffic.

Reused, not rerun: current RoutingV2Tests and `DatasetTests.test_runtime_index_and_prompts_exclude_gold` recorded in the 50-pass semantics audit; Phase 5 four-pass source/context tests and genuine retrieval audit; Phase 7 six-pass structural tests; previous NVIDIA adapter/content/accounting tests. They cover independent preserved boundaries and are not counted as new Phase 8 executions. No legacy defense result substitutes for current screening evidence.

## Preservation and deployment boundary

Before/after verification: **68 inventoried frozen-data/historical-result/ledger/NVIDIA-adapter files unchanged**, plus unchanged size/mtime/mode metadata for root .env and both private allowance files. No production calls/reservations, expiry edits, history reset, stored-file maintenance, service restart or live enablement occurred. NVIDIA adapter and reasoning configuration were left intact. Existing uploads/Chroma were neither ingested, queried nor maintained. Private credential values were not inspected or displayed for this audit.

The fix is verified in source/offline only. Already running services were deliberately not restarted, per instruction; no claim is made that they have loaded the new validation code. A later authorized service restart is required before live verification. Existing live configuration was not changed or re-enabled by this task.

## Remaining live verification

An authorized, funded run must still observe actual NVIDIA Screening schema acceptance/decisions and C generation on retained context. Review benign quotations/instructions, mixed legitimate/malicious content, direct/indirect attacks and combined-chunk exposure against source spans. Assess semantic answer support/task completion separately from schema/ID validity and attack outcome. Measure real false flags/blocks, task loss and overhead with explicit unknown/error denominators. Synthetic outputs do not establish screening accuracy, injection resistance, benign-quotation recognition, supported answers or defense effectiveness. The earlier failed A/B/C integration remains failed/incomplete; Phase 8 offline completion does not pass that live gate.

## Specific Phase 9 gaps — identified, not started

| Area already present | Remaining Phase 9 audit/work |
|---|---|
| Workload planner, paired/end-to-end loops, seed/order, exclusive result placeholders and frozen spec | Verify current NVIDIA end-to-end vs paired reporting, complete cross-mode/common-evaluable record selection, and controlled partial/interrupted/resume behavior using disposable artifacts. Reuse the existing resume/ambiguity tests first; no benchmark started here. |
| Provider/model/base/auth/reasoning identity and prompt/dataset/annotation/scoring hashes | Request timeout is not currently frozen in the main experiment settings; new screening validation behavior lacks an explicit spec policy/version or exact dirty-source hash. Audit/fix exact execution identity so changed timeouts/validation/adapter behavior cannot silently resume an old experiment. No evaluator fix made in Phase 8. |
| Known-count metrics, false-flag/block/error/null denominators and human review importer already tested | Verify current NVIDIA partial/missing-usage/per-stage latency records through saved summary/CSV/report and review-history round trips, including completed-screen→generation-error cases per SCORING.md. Reuse sufficient arithmetic tests; do not grade synthetic results as empirical outcomes. |
| Original/supplied evidence and manual exposure annotations | Resolve disclosed development-12/cross-chunk semantics and historical E037/E038 classification-unit reviews without altering frozen records silently. Review actual pre/post-screen exposure spans and keep retrieval misses distinct from resistance. |
| Exposed final split and recorded template overlap limits | Define a reviewable evaluation plan and human adjudication with these limitations; no untouched-holdout claim or defense recommendation. Actual authorized provider runs, successful full A/B/C integration and semantic review remain pending. |

Phase 9 implementation, tests, full benchmark and model-effectiveness claims were not started.
