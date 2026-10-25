# Step 4: shared assistant adapter

`app.evaluation.simple_runner.ask(mode, question, doc_ids)` wraps the existing
`rag.assistant.respond()` and reuses its A/B prompts, C screening/filtering,
answer schema, citation-ID validation and payment-card output check. It passes
the question unchanged. All named return fields in the PDF are present; the
contract has ten fields.

A private, explicitly supplied evaluation call hook requires `EVAL_MODE=1` and
provided retrieval. Only this path skips interactive input checks, reservations
and stop updates. The API does not supply this hook. Setting `EVAL_MODE=1` alone
does not bypass interactive protections. Existing Azure/OpenRouter transports,
private settings, receipts, flags, histories and original benchmark are unchanged.

The hook's default model boundary raises a controlled error because the standing
scope prohibits provider evaluation. It has no HTTP implementation, retries,
fallback, allowance, receipt or capacity system. Local tests replace only that
boundary with clearly synthetic responses. This is an implemented and locally
tested adapter, not a completed live evaluation or evidence of effectiveness.
The optional judge remains disabled.

## Shared retrieval

Evaluation uses only `.cache/evaluation_v3/chroma`, collection `benchmark_v3`.
It never falls back to interactive storage and does not prepare an index itself.
The later run-script step must ingest the v3 documents there first.

`identity.json` in the evaluation-store root must contain `manifest_sha256`,
`config_sha256` and a nonempty `generation`. The configuration hash uses
`sha256(json.dumps(config, sort_keys=True).encode())`. The collection metadata
must contain the same identity. Rebuilding an index must use a new generation.
Each chunk needs `document_id`, `source`, `fixture_sha256`, `chunk_sha256`,
`chunk_size` and `chunk_overlap`; optional page/section metadata is retained.
The fixture hash is the manifest's raw-file hash, distinct from parsed-text hashes.

Retrieval embeds the unchanged query locally, filters the supplied fixture IDs,
uses `top_k` from `eval_config.yaml`, validates chunks and orders them by distance
then ID. The last comparison's chunks are copied for each different mode;
repeating a mode or changing the question/documents begins another retrieval.
Changed settings or index identity during a comparison cause an error.
No global provider functions or production storage settings are monkeypatched.
Latency is actual wall-clock time inside each ask, including the work that call
performs; the first mode's shared retrieval work is not repeated for other modes.
This cache effect must be disclosed when comparing latency.

## C trace and output checks

The evaluation screening schema extends the unchanged interactive schema with a
question reason and a reason map whose keys must exactly match flagged source
IDs. Unknown source IDs or missing reasons are errors, not blocks. The existing
screener consumes the validated base decision and the adapter saves the reasons.

C's kept/removed IDs partition the original candidates even if the question is
blocked. These are source-screen classifications, not a claim that generation
received evidence after a question block. On a screening failure there is no
validated removal decision: IDs remain in the not-removed list, `error` is
nonempty, and no rate may treat this as a defense success. On a generation
failure, validated screening metadata is retained.

C additionally withholds answers containing any v3 canary or the original
fictional protected marker. This is an output defense, not automatic attack
adoption grading. Only the final visible answer is returned; candidate output
and call traces are not dumped. A/B keep their existing output behavior.
Exceptions return an empty answer and an error; arbitrary exception prose is
redacted and schema errors omit raw model inputs. Provider/operational errors
never set `blocked` merely because execution could not complete.

## Required check

Run from `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" EVAL_MODE=1 python -c "from app.evaluation.simple_runner import ask; print(ask('A','How many days of leave?',[]))"
```

Actual combined stdout/stderr (exit 0):

```text
python-dotenv could not parse statement starting at line 56
python-dotenv could not parse statement starting at line 57
python-dotenv could not parse statement starting at line 58
python-dotenv could not parse statement starting at line 59
python-dotenv could not parse statement starting at line 60
python-dotenv could not parse statement starting at line 61
python-dotenv could not parse statement starting at line 67
python-dotenv could not parse statement starting at line 68
{'answer': '', 'sources': [], 'retrieved_chunks': [], 'kept_chunk_ids': [], 'removed_chunk_ids': [], 'screen_reasons': {}, 'question_flagged': False, 'blocked': False, 'latency_s': 0.0017146800237242132, 'error': 'No evaluation documents were selected; no request sent.'}
```

The dotenv parsing warnings were already present in the baseline. No private
file contents are included, and `.env` was not edited. An empty document
selection intentionally returns a no-request error with the full contract;
this check does not establish live answering.

## Adapter and retrieval tests

```bash
.venv/bin/python -m pytest backend/tests/evaluation/test_simple_runner.py -q
```

Actual output (exit 0):

```text
...................                                                 [100%]
19 passed, 5 subtests passed in 2.27s
```

Tests cover the C partition for successful filtering, question blocking, all
sources removed, screening errors and generation errors. They verify retrieval
runs once for A/B/C, identical questions/settings, source filtering through a real
local Chroma query with synthetic embeddings, no interactive gate access from
the adapter, unchanged interactive guards, output checks, invalid citations,
error redaction and refusal of paid model configuration. All model responses in
these tests are synthetic; they are not evaluation records.

## Full suite

From `backend/`, outside the sandbox for the in-process TestClient:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q
```

Actual summary (exit 1):

```text
17 failed, 404 passed, 1 skipped, 1 warning, 522 subtests passed in 64.77s (0:01:04)
```

Failure and subtest-failure lists match [the original baseline](STEP_1_SETUP.md)
exactly. Dataset validation also returned `OK 47`; the app check returned
`Local app dependencies and .env present. No services or provider requests started.`
No original benchmark, standing scope, provider transport or provider setting
changed. New-case A smoke calls remain pending before the full evaluation.
