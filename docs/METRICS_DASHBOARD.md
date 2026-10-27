# Metrics and test cases in the application

Open **Metrics / evaluation**. The top table shows the five required metrics:
ASR, benign task success, false-positive rate, human quality and average latency.
Every rate displays its numerator and denominator. Coverage above the table
shows missing rows, errors and human-review counts.

Use **Test case for A/B/C comparison** to inspect one question, expected answer,
source documents and the three actual responses. Expand the source evidence to
read the relevant text and see what C retained or removed. Missing answers are
shown as not run; provider failures remain operational errors.

Use **Human review — check an answer and enter your own judgment** to enter a
real quality score or correct an ambiguous/wrong automatic grade. Follow
[the review steps](HUMAN_REVIEW.md). Refresh after saving.

The main question is whether a defense reduces malicious behavior without
losing legitimate answers. A low ASR alone does not establish a useful defense.
An attack can succeed even when the answer also contains the correct fact.

Charts and downloads come from saved records. Refreshing makes no LLM calls.
Stale charts are withheld until regenerated. A/B have no screening classifier,
so classifier false positives are N/A; benign task success still measures their
normal-task performance. Latency includes C screening/generation and timed
errors, but excludes the frozen shared initial retrieval.

Supporting diagnostics (exposed ASR, categories, citation-document match, p95
latency and agreement) are collapsed below the primary metrics. Human quality
remains N/A until a person actually submits a rating. Source-ID citation checks
do not prove that every assertion is supported.

UI masking hides recognized payment-card numbers. It does not alter raw answers
or count as model resistance. Use preserved local evidence for exact protected
marker review. Historical results are under **Saved experiments**.
