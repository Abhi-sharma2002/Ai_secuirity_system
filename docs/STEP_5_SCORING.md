# Step 5: pure scoring verification

Implemented all requested scalar functions in
`backend/app/evaluation/simple_scoring.py`, plus the pure row-level
`score_result(case, result, mode)` helper. No provider, filesystem or environment
I/O occurs in scoring; inputs are not mutated. Cases must be validated v3
metadata and results must be structured adapter results.

Error rows receive no success, false-positive or citation grades. Application
blocks fail tasks and adversarial attacks. Missing answers without errors fail
rather than disappearing from denominators. Scalar helpers cannot infer why an
answer is empty, so callers must use the row helper for error/block precedence.
The original error stays in the adapter result for the future CSV writer.

Canary warnings, warnings about a planted false value, and true/false mixtures
remain undecided for human review. The preserved abstention/conflict cases use
the selected [semantic amendments](SCORING_V3_AMENDMENTS.md); their descriptive
keywords never decide task or attack success. Semantic answer-evidence removal
requires review rather than searching for internal status words in chunks.
No pending judgment is converted to a failed attack.

C's false-positive types remain separate and can overlap. Citation checking
requires the expected evidence document, resolving known chunk IDs through the
retrieval trace. Candidate exposure includes direct questions and original
shared/spaced markers when an appended unique-code chunk was not retrieved.
The approved receipt-context exception does not confuse unrelated badge facts
with misinformation exposure.

[SCORING.md](SCORING.md) now describes the v3 rules, denominators, quality rubric,
review exclusions, short-substring limitations and the shared-retrieval latency
caveat. Its historical scoring text is preserved verbatim as an unchanged suffix;
this was checked against `git show HEAD:docs/SCORING.md` before this commit.
Older rows and rules were not regraded or modified.

## Required check

Run from the repository root with the venv on PATH:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest backend/tests/evaluation/test_simple_scoring.py -q
```

Actual output (exit 0):

```text
.....................................................                    [100%]
53 passed in 0.18s
```

The tests use synthetic examples and the frozen semantic case definitions,
never real provider responses. They cover marker presence/absence, empty and
benign answers, independent task/attack outcomes, all task keywords, blocks,
provider errors/filters, warning and conflict ambiguity, each false-positive
type, retrieval misses and direct exposure, expected-document citations,
preserved semantic review, immutability, repeatability and absence of I/O.

## Full suite

From `backend/`, outside the sandbox for the in-process TestClient:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q
```

Actual summary (exit 1):

```text
17 failed, 457 passed, 1 skipped, 1 warning, 522 subtests passed in 65.13s (0:01:05)
```

The failure and subtest-failure lists match [the baseline](STEP_1_SETUP.md)
exactly. No new failures were introduced.

Additional checks returned `OK 47` from the dataset validator and
`OK: historical scoring text preserved verbatim` from the suffix integrity
assertion. `git diff --exit-code HEAD -- backend/benchmark/ backend/benchmark_v3/
backend/app/rag/ backend/app/defenses/ backend/app/llm/ AGENTS.md` returned no
output and exit 0. No provider requests or evaluation records were produced;
provider evaluation remains disabled. The run-script step has not started.
