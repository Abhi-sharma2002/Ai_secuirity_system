# PDF implementation and verification — 27 October 2026

The local application is running at **http://127.0.0.1:8501**. Manual Azure
answering uses the existing trial allocation. The completed benchmark scope is
closed; no automatic retry, renewal or additional benchmark is scheduled.

## Delivered

- All five PDF pages mapped to the implementation in [ASSIGNMENT_TRACEABILITY.md](ASSIGNMENT_TRACEABILITY.md).
- Active dataset: 45 synthetic documents and 47 cases. Frozen fixture hashes and supporting quotes validate.
- Three actual pipelines: A baseline, B instruction separation, C screening plus output checks, with shared answering settings and original case evidence.
- **141/141 A/B/C records saved.** The authorized continuation added 108 rows using 124 of at most 144 calls. Its unused 20-call capacity is closed; 783 calls remain in the pre-existing general allocation.
- Five primary metrics, per-case documents/answers/grades, explicit human-review forms, charts and generated technical report.
- Local upload, real CPU indexing, retrieval, API and all UI workspaces verified. Real saved-case comparison and source inspection verified against the running app without model calls.
- Final regression suite: **155 tests passed, 12 subtests passed**. Tests use temporary synthetic data and do not count as observed model effectiveness.
- Empty unused modules and regenerable caches removed; optional analyses archived. Original datasets, answers, receipts, accounting and stop flags preserved.

## Actual results and interpretation

| Metric | A | B | C |
|---|---|---|---|
| Attack success | 2/18 (11.1%) | 0/19 (0%) | 0/20 (0%) |
| Benign task success | 19/19 | 19/19 | 19/19 |
| Benign false positives | N/A | N/A | 0/19 |
| Mean route time | 3.56 s | 3.65 s | 5.80 s |
| Human quality | Not yet rated | Not yet rated | Not yet rated |

These are provisional rates over graded, non-error rows. There are **13
operational errors** and **14 answers awaiting human judgment**. No human scores
were fabricated. The quality forms and correction workflow are working.

The important trade-off: on graded attack cases, A completed the legitimate
task in 18/18, B in 19/19 and C in 0/20; C blocked all 20. B therefore shows the
most promising observed balance, while C's blocking loses useful answers under
attack and costs more time. This is a provisional interpretation, not proof of
security or a final human-reviewed recommendation.

Three A outputs quoting/disavowing malicious text were retrospectively changed
from automatic grades to pending review after a warning-detector bug was found.
Original labels/CSVs are archived and the amendment is recorded in run metadata.
Raw responses, source evidence and timings were not changed. The initial 33 rows
remain unchanged. The original benchmark and all prior stop flags are preserved.

Use [DEMO.md](DEMO.md) for the mentor walkthrough and [HUMAN_REVIEW.md](HUMAN_REVIEW.md)
for the real human step. [REPORT.md](REPORT.md) and [METRICS_EXPLAINED.md](METRICS_EXPLAINED.md)
are regenerated from the saved records.
