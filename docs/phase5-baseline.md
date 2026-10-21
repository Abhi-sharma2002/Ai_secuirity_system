# Phase 5: Configuration A baseline with fixed-context evidence

This implements the supplied Phase 5 baseline brief using the working Phase 3
fixed-context evidence and Phase 4 shared LLM client. It adds one-case execution,
response/usage capture, citation candidates, safe recording, and a CLI around the
existing versioned baseline prompt. B/C, grading, and the experiment runner remain
separate work. No provider approval is inferred from this phase.

## Implemented path

```
validated case + pinned sources
    -> Phase 3 EvidencePackage
    -> BaselineDefense.prepare()
    -> versioned LangChain prompt -> shared LLMRequest
    -> Phase 4 client and injected adapter
    -> raw answer + usage + prompt/evidence provenance
```

`app/defenses/base.py` defines frozen preparation/result records and content-free
metadata exports. It also defines a safe execution-error type and a deterministic
application-message fingerprint function. `app/defenses/baseline.py` implements
`BaselineDefense.prepare()` and `.run()`. `scripts/demo_baseline.py` is explicitly
offline; it cannot select a live provider from environment configuration.

## Baseline prompt contract

The prompt version is `baseline-fixed-context-v1`. LangChain's
`ChatPromptTemplate.format_messages()` creates exactly two messages:

1. A fixed generic system message asks for an answer grounded in supplied sources,
   citations to document IDs, and an insufficient-information response when needed.
2. A user message contains `Question:\n{question}\n\nSources:\n{evidence}`.

There are no injection-specific warnings, developer messages, screening,
rewriting, added role-isolation defenses, truncation, or source dropping. Generic
QA role framing remains part of this baseline and must be reported in comparisons.
The user message is locally marked untrusted because it contains source text;
that flag does not enforce any provider-side trust boundary or prevent injection.
Question and source variables are inserted once, never interpreted recursively as
another prompt template. Fake role markers, braces, Unicode, CRLF, encoded text,
and malicious textual instructions remain unchanged.

This phase deliberately uses the dataset's `fixed_context` mode, not Chroma
retrieval. Changing the evidence selection would confound the controlled
comparison. It is not a new upload-to-answer UI or a complete live RAG application.
The existing upload, ingestion, and retrieval paths are unchanged.

## Reproducibility and evidence delivery

Preparation requires an `EvidencePackage` with supported schema/mode. It rechecks
the Phase 3 canonical fingerprint, source inventory, framing counts, source
checksums, and character/byte boundaries. It does not reopen source files; call
Phase 3 `build_evidence()` when a fresh verification of the current files is
required. A digest detects drift, not replacement by a party able to forge both
content and its expected digest. Callers must build packages from trusted,
validated cases and pinned manifests.

Every prepared prompt retains:

- Original evidence fingerprint and test/configuration IDs.
- Prompt version and `model_input_fingerprint`.
- Ordered document IDs.
- Message index and exact half-open character/UTF-8 byte offsets for each source
  inside the actual application user message.
- The immutable request with actual role-separated prompt text, held in memory
  and excluded from representations and safe metadata exports.

`model_input_fingerprint` is SHA-256 of canonical JSON containing the prompt
version, configuration ID, role/content/untrusted fields, and generation settings.
It identifies the application message payload, not a provider's unknown wire
serialization or internal prompt. Provider/model are retained in the shared usage
record. Source-delivery offsets confirm supplied evidence bytes; they do not
prove model attention, successful attack exposure, answer correctness, or security.

Neither attack labels, expected answers, supporting quotes, nor scoring policies
are read from the evaluation case by this prompt adapter. The adapter accepts
only the evidence package. Existing source text can itself contain malicious or
misleading claims; none is automatically treated as safe or removed.

## Execution and errors

`BaselineDefense.run(package, client)` prepares a request and calls the same
Phase 4 `LLMClient.complete()`. Retries, timeout configuration, capability checks,
usage accounting, costs and log safety remain in the shared client. Optional
`temperature` and `max_output_tokens` are passed explicitly; by default both are
unspecified. Keep them equal across future configurations when comparing results.

The result contains the raw returned text under `result.completion.text`, the
prepared request under `result.prepared`, and metadata under
`result.safe_metadata()`. No command execution, tool invocation, answer grading,
citation validation, or security classification occurs. A model call failure
raises `DefenseExecutionError`, retaining both preparation metadata and the failed
request's usage record. Preflight capability validation still raises the shared
`RequestValidationError` without making an adapter call or inventing usage.

No live adapter is installed. Future live execution requires an explicitly
injected, approved adapter; its transport must enforce the Phase 4 timeouts and
preserve messages. The included demonstration always injects the fake adapter.

## Try it

From the repository root:

```bash
cd backend
.venv/bin/python -m scripts.demo_baseline
```

The demo builds the first real evidence package, sends the resulting baseline
request to a fake adapter, and prints metadata only. Its answer is scripted,
token usage and costs are unknown, and its latency is local fake-client timing.
Success proves the wiring completed, not real model quality or defense efficacy.

Python usage:

```python
from app.defenses.baseline import BaselineDefense
from app.evaluation.evidence_builder import build_evidence, load_verified_sources
from app.evaluation.test_case_loader import load_test_cases
from app.llm.client import LLMClient, ProviderResponse
from app.llm.fake import FakeAdapter
from app.llm.models import LLMConfig

case = load_test_cases()[0]
package = build_evidence(case, load_verified_sources())
client = LLMClient(LLMConfig(), FakeAdapter([ProviderResponse('Scripted output')]))
result = BaselineDefense().run(package, client)
metadata = result.safe_metadata()  # excludes original prompt/evidence and answer text
```

## Verification and remaining phases

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_baseline.py' -v
.venv/bin/python -m scripts.verify_evidence
.venv/bin/python -m unittest discover -s tests -v
```

Focused tests cover all 45 cases' exact evidence delivery, source order, Unicode,
CRLF, prompt-like markers, variable braces, deterministic fingerprints, generation
settings, annotation exclusion, invalid evidence, immutability, shared usage,
capability failures, failed-call provenance, safe logs, inert model output, and
an offline demo guarded against live-provider environment settings. Unit tests
block socket connections.

Next implement B and C under separately versioned behavior, then the evaluation
runner and human-reviewed scoring. Select and approve a live provider adapter
before collecting real model outcomes. No security effectiveness, answer/citation
accuracy, billed cost, or attack-success result can be inferred from fake output.

Executed results: 14 baseline tests passed; the full suite discovered 106 tests
with 105 passed and 1 optional real-model test skipped. All 45 Phase 3 evidence
packages still verified with repeated deterministic fingerprints. The offline
baseline demo completed successfully. No live model call was made.


## One-case runner and complete execution schema

`app/defenses/baseline_runner.py` adds `BaselineRunner(client, sources).run(case)`.
Pass a case returned by `load_test_cases()`; the runner does not replace the full
dataset validator. It builds fixed-context evidence with the existing builder, or
accepts `evidence=package` and verifies that test ID, question, ordered document
IDs, mode, and any supplied supporting source hash match the selected case. The
baseline's existing fingerprint/content/boundary validation still runs. Supplying
an existing package supports using exactly the same package across future A/B/C.

The frozen execution object holds:

- Metadata: execution/test/configuration IDs, simulation mode, provider/model,
  evidence and model-input fingerprints, prompt version, source-delivery offsets,
  generation settings, execution status/error, latency, attempt count, usage/cost.
- Separate untrusted content: original question, raw answer (or null on failure),
  and citation candidates with their exact answer offsets.
- Full shared LLM usage record, preserving individual failed/retried attempts and
  unknown billed/total usage. Summary token/cost fields refer to the successful
  response; complete-attempt accounting stays in the nested `llm` record.

Provider failures yield a failed execution with no fabricated answer. Preflight
input/capability failures raise before executing and do not manufacture usage.
A `D001`-style answer mention is only a citation candidate. Membership in supplied
evidence is reported, but `validation_status` remains `not_validated` even for a
supplied ID. This does not establish citation support or correctness. Other
citation formats are not parsed. There is no task/attack-success field or scorer.

Fake provider names, fake adapter instances/subclasses, and explicitly fake
reported usage mark a run `simulated`. No scoring pipeline is implemented;
future real-result aggregation must exclude simulated executions explicitly.

## Requested smoke CLI and safe result recording

From the repository root, the requested command now exists:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m scripts.run_baseline --test-id E001
```

From `backend`, use:

```bash
.venv/bin/python -m scripts.run_baseline --test-id E001
.venv/bin/python -m scripts.run_baseline --test-id E032 --temperature 0 --max-output-tokens 256
```

The default always injects a fake adapter, irrespective of live-provider
environment settings. Output clearly says SIMULATED and displays only operational
summary fields and the saved path. The scripted response is not derived from the
expected answer or scoring labels. Fake usage/cost remains unknown unless counts
and pricing were explicitly scripted elsewhere.

The default result root is `results/baseline` in the project; override it with
`--output-dir /trusted/operator/chosen/path`. Each save creates a new UUID directory
with mode 0700 and two exclusively created files with mode 0600:

- `metadata.json`: operational metadata, generation settings, prompt/evidence
  provenance, shared usage, and the explicit simulation flag; no raw answer,
  question, prompts, source text, or citation claims.
- `untrusted_content.json`: the original question, raw model answer, and unvalidated
  citation candidates. These strings are inert JSON data, never configuration,
  commands, paths, or executable templates. Escape them if displaying in a UI.

Document IDs, question text, citations, and model answers never select filenames
or directories. Repeated saves cannot overwrite existing runs. Results are
ignored by `results/.gitignore`. Ordinary write failures remove the partial run
directory; process termination or storage outages can leave orphans. The output
root and its ancestors are trusted operator input, not attacker-controlled paths.
A direct symlink output root is rejected. This is local private storage, not
multi-user authorization, encryption, retention management, or a transactional
experiment database.

The CLI records successful and failed attempted executions. Exit codes are 0 for
success, 1 for an attempted model failure or recording error, and 2 for setup,
selection or preflight errors. A result is announced only after both files close
successfully. Provider failures never acquire a fallback synthetic answer.

`--allow-live` is an explicit opt-in, but currently fails closed: no approved live
adapter is installed. It requires a non-fake model/provider configuration, secure
credentials, and a reviewed adapter in the shared factory before real execution
can work. It never silently falls back to fake. No real calls were made to verify
this flag. The CLI does not add a provider SDK or choose an approved service.

## Fair comparison and Configuration B

Future B/C must keep the same validated case, pinned fixed-context package,
provider/model, explicit generation settings, usage/latency implementation, and
execution schema. The baseline's full evidence must not be reduced to improve
another configuration's apparent effectiveness. Configuration B will introduce
explicit source/instruction separation with its own prompt version and input
fingerprint; it should preserve the original source bytes and record precisely
what was delivered. Its exact template and mechanism are not implemented here.
No attack detection, filtering, LLM judge, scoring, endpoint or deployment was
added by this brief.

Verification against the supplied brief: all 45 cases validated (23 attack,
18 legitimate-quality, 4 benign-quotation; all fixed_context), all 45 evidence
packages verified, and the full suite discovered 121 tests with 120 passed and
1 optional real-model test skipped. The 29 focused baseline/prompt/runner/CLI
tests passed. The exact `scripts.run_baseline --test-id E001` command completed in
simulated mode, recorded separate metadata/content files, and the resulting
0700 directory/0600 file permissions were checked. Compilation checks passed.
No live API call, paid execution, screening, or scoring was performed.
