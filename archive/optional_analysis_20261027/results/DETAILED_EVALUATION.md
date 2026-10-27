# Detailed evaluation evidence

Computed locally from saved observations. No provider calls or invented human reviews. Results are partial until coverage and review are complete.

## Rates and 95% Wilson intervals

| Mode | Metric | Successes / graded | Rate | 95% interval |
| --- | --- | --- | --- | --- |
| A | asr_all | 0 / 4 | 0.0% | 0.0% – 49.0% |
| A | asr_retrieved_only | 0 / 4 | 0.0% | 0.0% – 49.0% |
| A | asr_direct | 0 / 1 | 0.0% | 0.0% – 79.3% |
| A | asr_indirect | 0 / 3 | 0.0% | 0.0% – 56.1% |
| A | benign_task_success | 6 / 6 | 100.0% | 61.0% – 100.0% |
| A | false_positive_rate | 0 / 0 | N/A | N/A – N/A |
| A | answer_chunk_removed_rate | 0 / 0 | N/A | N/A – N/A |
| A | false_positive_total | 0 / 0 | N/A | N/A – N/A |
| A | citation_accuracy | 10 / 10 | 100.0% | 72.2% – 100.0% |
| B | asr_all | 0 / 4 | 0.0% | 0.0% – 49.0% |
| B | asr_retrieved_only | 0 / 4 | 0.0% | 0.0% – 49.0% |
| B | asr_direct | 0 / 1 | 0.0% | 0.0% – 79.3% |
| B | asr_indirect | 0 / 3 | 0.0% | 0.0% – 56.1% |
| B | benign_task_success | 6 / 6 | 100.0% | 61.0% – 100.0% |
| B | false_positive_rate | 0 / 0 | N/A | N/A – N/A |
| B | answer_chunk_removed_rate | 0 / 0 | N/A | N/A – N/A |
| B | false_positive_total | 0 / 0 | N/A | N/A – N/A |
| B | citation_accuracy | 10 / 10 | 100.0% | 72.2% – 100.0% |
| C | asr_all | 0 / 3 | 0.0% | 0.0% – 56.1% |
| C | asr_retrieved_only | 0 / 3 | 0.0% | 0.0% – 56.1% |
| C | asr_direct | 0 / 1 | 0.0% | 0.0% – 79.3% |
| C | asr_indirect | 0 / 2 | 0.0% | 0.0% – 65.8% |
| C | benign_task_success | 6 / 6 | 100.0% | 61.0% – 100.0% |
| C | false_positive_rate | 0 / 6 | 0.0% | 0.0% – 39.0% |
| C | answer_chunk_removed_rate | 0 / 6 | 0.0% | 0.0% – 39.0% |
| C | false_positive_total | 0 / 6 | 0.0% | 0.0% – 39.0% |
| C | citation_accuracy | 6 / 9 | 66.7% | 35.4% – 87.9% |

## Coverage and missing-outcome sensitivity

| Mode | Recorded / planned | Errors | Pending review | Graded attacks / planned | Planned ASR best–worst |
| --- | --- | --- | --- | --- | --- |
| A | 11 / 47 | 1 | 0 | 4 / 26 | 0.0% – 84.6% |
| B | 11 / 47 | 1 | 0 | 4 / 26 | 0.0% – 84.6% |
| C | 11 / 47 | 2 | 0 | 3 / 26 | 0.0% – 88.5% |

## Matched-case comparisons

Positive right-minus-left increases the metric: worse for attack success, better for benign success.

| Pair | Metric | Matched cases | Right minus left | Discordant left / right | Exact p (unadjusted) |
| --- | --- | --- | --- | --- | --- |
| A / B | attack_success | 4 | 0.0% | 0 / 0 | 1.0 |
| A / B | benign_task_success | 6 | 0.0% | 0 / 0 | 1.0 |
| A / C | attack_success | 3 | 0.0% | 0 / 0 | 1.0 |
| A / C | benign_task_success | 6 | 0.0% | 0 / 0 | 1.0 |
| B / C | attack_success | 3 | 0.0% | 0 / 0 | 1.0 |
| B / C | benign_task_success | 6 | 0.0% | 0 / 0 | 1.0 |

## Retrieval quality

Original retrieval is shared across modes and counted once per case. Evidence hit is any expected document retrieved; recall is the fraction of expected documents retrieved; precision is the fraction of distinct candidate documents expected. Reciprocal rank uses the first relevant chunk. These measure declared fixture evidence, not semantic relevance. Cases with no expected evidence and retrieval errors are excluded.

```json
{
  "saved_cases": 47,
  "applicable_cases": 47,
  "evidence_hit": 1,
  "expected_document_recall": 1.0,
  "candidate_document_precision": 1.0,
  "reciprocal_first_relevant_chunk_rank": 1.0
}
```

## Interpretation limits

- Partial, exposed, controlled fixture dataset; results do not estimate production security.
- Wilson intervals describe binomial sampling uncertainty, not fixture selection bias or grading validity.
- Zero observed attack successes does not establish zero vulnerability; inspect sample size and interval.
- Matched comparisons use only the same eligible cases with known grades in both modes.
- Exact McNemar p-values are unadjusted exploratory descriptions, not proof of a superior defense.
- Planned-ASR bounds assign every missing/error/unresolved attack to failure or success; these are sensitivity bounds, not confidence intervals or actual grades.
- Attack exposure measures whether attack content reached original candidates, not retrieval relevance.
- Citation checks match expected document IDs; they do not establish semantic faithfulness.
- Successful-route timing excludes operational errors, includes blocks, and excludes shared initial retrieval; it is not user end-to-end latency.
- Human quality and semantic decisions require real human reviewers; no generated labels are substituted.

Category, coverage, retrieval-exposure and paired-case tables are supplied as detailed_*.csv; exact machine-readable values and record hash are in detailed_metrics.json.
