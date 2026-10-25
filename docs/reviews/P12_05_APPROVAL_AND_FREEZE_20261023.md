# P12-05 applied; remaining Phase12 freeze review

Reviewer: repository user via conversation (no personal name supplied).
Date: 23 October 2026, Asia/Calcutta. No exact approval time asserted.

Authorization basis, quoted from the current user message:

> I approve P12-05 using the exact E037 rubric presented.
>
> Apply it as a separate versioned legacy rubric. Preserve the original
> rubric, grades, fixtures and historical results. Do not regrade old runs
> or include incompatible legacy results in current aggregates.
>
> Bind applicable future runs to the new rubric version.
> Record this message as the approval basis.

## Applied version and boundary

**legacy-e037-task-v2** is stored at
`backend/benchmark/revisions/legacy-e037-task-v2/rubric.json`.
The task definition is exactly the previously presented blockquote, with its
Markdown line wrapping joined into a paragraph. The version also retains the
original task definition, unchanged citation criterion and attack-success N/A.
Human grading is required; no classifier or model judge was added.

`E037.original.json` preserves the complete original case. `proposal.before.md`
preserves the complete previously pending proposal and illustrative examples.
`SCORING.before.md` preserves the preceding active scoring document. Original
source fixtures, original test-case file, prior versioned rules and grades,
historical runs and results remain unchanged. Earlier records saying P12-05 was
pending retain their historical scope; this approval supersedes that status.

The shared legacy fixed-context runner binds future E037 executions before
generation, verifies the complete original-case fingerprint, and saves the rubric
snapshot, version, hash and source-case fingerprint in new execution metadata
(schema2). Baseline and instruction-separation use that shared runner. Other
legacy cases keep schema1 and their original criteria. The rubric is evaluator
metadata only and is not inserted into prompts. No stored execution is upgraded,
regraded, resumed or rewritten. Legacy runs use fresh exclusive UUID directories.

Keep legacy-e037-task-v2 results separate from old E037 grades and from the
current fictional-v2.1 experiment aggregates. Compare only records with compatible
dataset/rubric hash, model/settings, configuration and protocol. The current
benchmark has no E037 case, and the current aggregate loader does not consume
legacy metadata.json files. No aggregate or report was regenerated here.

## Verification

The completed19 inventory/hash checks, saved coverage, genuine retrieval/exposure,
prior semantic-version checks and metric arithmetic evidence were reused.

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -B -m unittest backend.tests.test_legacy_e037_rubric backend.tests.test_baseline_runner -v > docs/evidence/p12-05-focused-v1.log 2>&1
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -B -m unittest backend.tests.test_instruction_separation.InstructionSeparationTests.test_execution_reuses_client_and_schema_with_a backend.tests.test_instruction_separation.InstructionSeparationTests.test_model_failure_has_no_fabricated_answer_and_preserves_metadata -v > docs/evidence/p12-05-shared-runner-v1.log 2>&1
```

First command:20 tests passed in0.232s. Second command:2 shared-runner tests
passed in0.039s. All generated responses are explicit offline
fixtures, with a network sentinel and disposable output. No real human grades
were assigned. AST/diff and preservation results are saved separately in
`evidence/p12-05-preservation-v1.json`. No full regression, ingestion, embedding,
retrieval or benchmark execution was repeated.

## Remaining freeze criteria

| Criterion | Current evidence/status | Remaining work |
|---|---|---|
| Semantic decisions P12-01 through06 | All approved and applied:phase12-approved-v1 plus legacy-e037-task-v2 | None of these six decisions remains pending |
| Immutable data identity/category inventory | Reused19 checks; original42 fixtures/manifest/annotations retained; hash preservation checked | No new source or category issue demonstrated |
| Scoring and exposure rules | Versioned rubric/sidecars, separate task/attack grades, human review, full-span denominator unchanged; previous focused arithmetic checks reused | No unapproved semantic change remains in these proposals |
| Dataset role | Approved exposed controlled comparison; six shared template groups and sparse categories disclosed | Never describe it as untouched holdout; an unseen set would require a separate revision |
| Actual provider/model/version and compatibility freeze | Azure-only adapter/offline checks exist; private presence-only check still finds the key/endpoint/deployment absent; no accepted actual Azure model/version/capability facts | Supply actual deployment/model/version and fixed-setting/schema capability facts, then bind them to the execution manifest |
| Controlled evaluation plan and execution identity | Both paired/end-to-end protocols implemented; settings defaults documented; seed5/one development case approved only for bounded integration; no completed controlled-evaluation freeze record | Finalize scope, selected protocol(s), repetitions, seed/order and review assignment; capture approved data/rules/source/index/model/settings hashes in a new freeze/run identity |
| Account readiness (execution prerequisite) | No Azure approval file or accepted funding/quota facts; local budget is not Azure credit | Current eligibility/quota/expiry facts are needed before separately permitted live execution; no allowance is activated now |
| Real-response review and live A/B/C | Pending; no new actual responses exist | Perform authorized integration, then separately scoped evaluation and human adjudication; do not infer success from offline fixtures |

**Conclusion:** all documented P12 semantic decisions are resolved, but the complete
dataset/scoring-and-experiment freeze criteria are not all met. Dataset/scoring
preparation is not marked fully complete and Phase12 remains **Partial**.
Real-response human review and live A/B/C evaluation are explicitly pending.
This task made no provider calls, allowance changes or live activation; root live
mode remains disabled. Credentials/account approval are not requested again here.
